"""Audit des routes de l'API — inventaire, doublons, endpoints sans garde.

Usage : ``python backend/scripts/audit_routes.py``

1. **Inventaire** — nombre de routes par méthode et par module (préfixe).
2. **Doublons** — même chemin + méthode déclarés deux fois (le dernier gagne,
   silencieusement en production).
3. **Endpoints sans garde** — fonctions exposées sans aucune dépendance
   ``Depends(...)`` (ni authentification, ni permission) : à vérifier.
"""
from __future__ import annotations

import ast
import os
import sys
from collections import Counter

BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
os.chdir(BACKEND)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

METHODS = {"get", "post", "put", "patch", "delete"}


def exposed_endpoints() -> list[tuple[str, str, str, int]]:
    """(module, méthode, fonction, ligne) des endpoints déclarés dans app/."""
    found: list[tuple[str, str, str, int]] = []
    root = os.path.join("app")
    for dirpath, _dirs, files in os.walk(root):
        for name in files:
            if not name.endswith(".py"):
                continue
            path = os.path.join(dirpath, name)
            try:
                tree = ast.parse(open(path, encoding="utf-8").read())
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                for deco in node.decorator_list:
                    func = deco.func if isinstance(deco, ast.Call) else deco
                    if not isinstance(func, ast.Attribute):
                        continue
                    if str(func.attr).lower() in METHODS:
                        found.append((path, func.attr.upper(), node.name, node.lineno))
    return found


def has_guard(node: ast.AST) -> bool:
    """Vrai si la signature contient au moins un ``Depends(...)``."""
    for child in ast.walk(node):
        if (
            isinstance(child, ast.Call)
            and isinstance(child.func, ast.Name)
            and child.func.id == "Depends"
        ):
            return True
    return False


def main() -> int:
    from app.main import app

    schema = app.openapi()
    paths = schema.get("paths", {})

    rows: list[tuple[str, str]] = []
    for path, operations in paths.items():
        for method in operations:
            if method.lower() in METHODS:
                rows.append((path, method.upper()))

    print(f"Routes documentées (OpenAPI) : {len(rows)}")
    by_method = Counter(method for _p, method in rows)
    print("Par méthode :", dict(sorted(by_method.items())))

    by_module = Counter(p.split("/")[3] if len(p.split("/")) > 3 else "core" for p, _m in rows)
    print("\nPar module :")
    for module, count in sorted(by_module.items()):
        print(f"  {module:<14} {count:>4}")

    duplicates = {key: n for key, n in Counter(rows).items() if n > 1}
    print(f"\nDoublons (chemin + méthode) : {len(duplicates)}")
    # Les préfixes identiques sont attendus : GET /x et GET /x/{id} sont
    # distincts. Un vrai doublon = exactement la même paire chemin+méthode.
    if duplicates:
        for (path, method), count in sorted(duplicates.items()):
            print(f"  ⚠ {method} {path} × {count}")
    else:
        print("  aucun")

    print("\nEndpoints sans aucune dépendance Depends(...) (à vérifier) :")
    unguarded = 0
    for path, method, func, line in exposed_endpoints():
        tree = ast.parse(open(path, encoding="utf-8").read())
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == func:
                if not has_guard(node):
                    unguarded += 1
                    print(f"  ⚠ {path}:{line} {method} {func}")
                break
    if not unguarded:
        print("  aucun")

    print(f"\nTotal déclarations @router.* : {len(exposed_endpoints())}")
    print(f"Routes exposées (OpenAPI)   : {len(rows)}")
    return 1 if duplicates else 0


if __name__ == "__main__":
    sys.exit(main())
