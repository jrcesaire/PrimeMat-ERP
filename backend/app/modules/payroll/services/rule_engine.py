"""
Moteur de calcul de paie — évaluation **sûre** des règles (sans ``eval``).

Reprend le principe d'OCA/payroll (règles ordonnées par ``sequence``,
évaluées séquentiellement, résultats cumulés réutilisables) mais **sans
exécuter de code Python arbitraire** : les expressions ``condition`` et
``formula`` sont analysées avec le module standard ``ast`` et n'acceptent
qu'un sous-ensemble d'opérations (arithmétique, comparaisons, booléens,
appels à des fonctions whitelistées). Toute autre construction (attribut,
import, lambda, boucle, compréhension) est rejetée.
"""
from __future__ import annotations

import ast
import operator
from datetime import date
from typing import Any

from app.modules.payroll.models.payslip import Payslip
from app.modules.payroll.models.structure import PayrollRule

#: SMIG mensuel (Côte d'Ivoire, 2026) — sert de base au plafond CNPS (45×SMIG).
SMIG_MENSUEL_CI = 75000.0
#: Réduction d'impôt par demi-part supplémentaire (RICF), en FCFA/mois.
RICF_PAR_DEMI_PART = 5500.0

# --- Opérateurs et fonctions autorisés -------------------------------------
_BIN_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY_OPS = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
    ast.Not: operator.not_,
}
_CMP_OPS = {
    ast.Eq: operator.eq,
    ast.NotEq: operator.ne,
    ast.Lt: operator.lt,
    ast.LtE: operator.le,
    ast.Gt: operator.gt,
    ast.GtE: operator.ge,
}
_SAFE_FUNCS: dict[str, Any] = {
    "min": min, "max": max, "round": round, "abs": abs, "int": int, "float": float,
}

#: Nœuds AST acceptés par l'évaluateur — tout le reste est rejeté.
_ALLOWED_NODES: tuple[type, ...] = (
    ast.Expression, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare,
    ast.Name, ast.Load, ast.Constant, ast.Call,
    ast.And, ast.Or,
    ast.Add, ast.Sub, ast.Mult, ast.Div, ast.FloorDiv, ast.Mod, ast.Pow,
    ast.UAdd, ast.USub, ast.Not,
    ast.Eq, ast.NotEq, ast.Lt, ast.LtE, ast.Gt, ast.GtE,
)


class RuleEvaluationError(ValueError):
    """Expression de règle invalide ou non autorisée."""


def safe_eval(expression: str | None, context: dict[str, Any]) -> Any:
    """Évalue une expression arithmétique/booléenne restreinte.

    Lève ``RuleEvaluationError`` si l'expression contient un nœud non autorisé.
    """
    if expression is None or not str(expression).strip():
        return None
    try:
        tree = ast.parse(str(expression), mode="eval")
    except SyntaxError as exc:
        raise RuleEvaluationError(f"Expression invalide : {exc}") from None
    for node in ast.walk(tree):
        if not isinstance(node, _ALLOWED_NODES):
            raise RuleEvaluationError(
                f"Nœud interdit dans une règle : {type(node).__name__}"
            )
    try:
        return _eval_node(tree.body, context)
    except RuleEvaluationError:
        raise
    except Exception as exc:  # noqa: BLE001 - remonté en erreur métier
        raise RuleEvaluationError(f"Évaluation impossible : {exc}") from None


def _eval_node(node: ast.AST, ctx: dict[str, Any]) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ctx:
            return ctx[node.id]
        raise RuleEvaluationError(f"Variable inconnue : {node.id}")
    if isinstance(node, ast.BinOp):
        op = _BIN_OPS.get(type(node.op))
        if op is None:
            raise RuleEvaluationError("Opérateur binaire non autorisé")
        return op(_eval_node(node.left, ctx), _eval_node(node.right, ctx))
    if isinstance(node, ast.UnaryOp):
        op = _UNARY_OPS.get(type(node.op))
        if op is None:
            raise RuleEvaluationError("Opérateur unaire non autorisé")
        return op(_eval_node(node.operand, ctx))
    if isinstance(node, ast.BoolOp):
        values = [_eval_node(v, ctx) for v in node.values]
        return all(values) if isinstance(node.op, ast.And) else any(values)
    if isinstance(node, ast.Compare):
        left = _eval_node(node.left, ctx)
        for op_node, comparator in zip(node.ops, node.comparators):
            op = _CMP_OPS.get(type(op_node))
            if op is None:
                raise RuleEvaluationError("Comparateur non autorisé")
            right = _eval_node(comparator, ctx)
            if not op(left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name) or node.func.id not in _SAFE_FUNCS:
            raise RuleEvaluationError("Fonction non autorisée")
        args = [_eval_node(a, ctx) for a in node.args]
        return _SAFE_FUNCS[node.func.id](*args)
    raise RuleEvaluationError(f"Expression non autorisée : {type(node).__name__}")


def build_context(
    payslip: Payslip,
    days_in_month: int = 30,
    params: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Construit le dictionnaire de variables exposé aux règles.

    ``params`` : paramètres de paie (SMIG, taux CNPS, plafond, RICF…) qui
    surchargent les valeurs par défaut codées en dur.
    """
    contract = payslip.contract
    employee = payslip.employee
    wage = float(getattr(contract, "wage", 0) or 0)
    worked = {
        w.work_entry_type: float(w.number_of_days or 0) for w in payslip.worked_days
    }
    inputs = {i.input_code: float(i.amount or 0) for i in payslip.inputs}
    days = sum(worked.values()) if worked else days_in_month
    parts = float(getattr(employee, "tax_parts", 1) or 1)

    # Ancienneté en années — base de la prime d'ancienneté (2 % à 2 ans, +1 %/an).
    reference = getattr(payslip, "date_to", None) or date.today()
    start = getattr(contract, "date_start", None) or getattr(employee, "hire_date", None)
    seniority = max(0.0, (reference - start).days / 365.25) if start else 0.0

    ctx: dict[str, Any] = {
        "SALAIRE_BASE": wage,
        "WAGE": wage,
        "TAUX": float(getattr(contract, "work_rate", 100) or 100),
        "SMIG": SMIG_MENSUEL_CI,
        "PARTS": parts,
        "SENIORITY": seniority,
        "days": days,
        "worked_days": worked,
        "inputs": inputs,
        "INPUTS_TOTAL": sum(inputs.values()),
        "lines": {},          # code_règle -> total calculé
        "categories": {},     # code_catégorie -> cumul
        "employee": employee,
        "contract": contract,
        "payslip": payslip,
    }
    # Chaque élément variable devient une variable utilisable par les règles
    # (ex. un input « PRIME_TRANSPORT » est lu via ``PRIME_TRANSPORT``).
    for raw_code, amount in inputs.items():
        key = str(raw_code).strip().upper().replace(" ", "_")
        if key.isidentifier():
            ctx.setdefault(key, amount)
    # Paramètres de paie configurables (SMIG, taux CNPS, plafond, RICF…).
    if params:
        for key, value in params.items():
            if isinstance(value, (int, float)):
                ctx[key] = float(value)
    return ctx


def compute_amount(rule: PayrollRule, ctx: dict[str, Any]) -> float:
    """Montant d'une règle selon son ``amount_type``."""
    amount_type = (rule.amount_type or "fixed").lower()
    if amount_type == "fixed":
        return float(rule.amount_fixed or 0)
    if amount_type == "percentage":
        base = _resolve_reference(rule.percentage_of, ctx)
        return base * float(rule.percentage or 0) / 100.0
    if amount_type == "scale":
        base = _resolve_reference(rule.percentage_of or "BRUT", ctx)
        return _compute_scale(rule.scale_brackets, base)
    if amount_type == "formula":
        value = safe_eval(rule.formula, ctx)
        try:
            return float(value or 0)
        except (TypeError, ValueError):
            raise RuleEvaluationError(
                f"La formule de la règle {rule.code} ne renvoie pas un nombre"
            ) from None
    raise RuleEvaluationError(f"Type de montant inconnu : {rule.amount_type}")


def _resolve_reference(reference: str | None, ctx: dict[str, Any]) -> float:
    """Valeur d'une ligne ou d'une catégorie désignée par son code."""
    if not reference:
        return 0.0
    if reference in ctx["lines"]:
        return ctx["lines"][reference]
    if reference in ctx["categories"]:
        return ctx["categories"][reference]
    if reference in ctx:
        try:
            return float(ctx[reference] or 0)
        except (TypeError, ValueError):
            return 0.0
    return 0.0


def _compute_scale(brackets: list | None, base: float) -> float:
    """Impôt progressif par tranches (barème), appliqué sur ``base``.

    ``brackets`` : ``[{"up_to": 75000, "rate": 0}, {"up_to": 240000, "rate": 16},
    ..., {"up_to": None, "rate": 32}]``. Chaque palier taxe la portion de
    revenu comprise entre le plafond précédent et son ``up_to``.
    """
    if not brackets:
        return 0.0
    ordered = sorted(
        brackets,
        key=lambda b: (b.get("up_to") is None, float(b.get("up_to") or 0)),
    )
    total = 0.0
    previous = 0.0
    for bracket in ordered:
        up_to = bracket.get("up_to")
        rate = float(bracket.get("rate", 0) or 0)
        if up_to is None:
            portion = max(0.0, base - previous)
        else:
            upper = float(up_to)
            portion = max(0.0, min(base, upper) - previous)
            previous = upper
        total += portion * rate / 100.0
    return total


def rule_applies(rule: PayrollRule, ctx: dict[str, Any]) -> bool:
    """Évalue la ``condition`` d'une règle (vide = toujours applicable)."""
    if not rule.condition:
        return True
    return bool(safe_eval(rule.condition, ctx))


__all__ = [
    "RuleEvaluationError",
    "safe_eval",
    "build_context",
    "compute_amount",
    "rule_applies",
]

