"""Génération des plans comptables embarqués — SYSCOHADA et SYCEBNL.

Ce script **n'est pas exécuté en production** : il produit les modules de
données ``app/modules/accounting/data/*_chart.py`` à partir des référentiels
fournis par l'utilisateur, puis les fichiers générés sont versionnés.

Sources attendues (hors dépôt) :

- ``listedescomptesreviselucien-*.pdf`` — SYSCOHADA commercial de référence,
  codes à 2-4 chiffres, **libellés complets** : c'est la **base** du plan ;
- ``856941109-Liste-Des-Compte-en-Syscohada-Revise.pdf`` — le même plan, mais
  **partiel** (classe 7 amputée des comptes 71 à 76) et à libellés tronqués à
  la largeur de colonne : il **complète** la base des comptes qu'elle ignore ;
- ``PLAN COMPTABLE SYCEBNL.xlsx`` — SYCEBNL (entités à but non lucratif),
  libellés complets.

Stratégie des libellés, dans l'ordre :

1. plan historique ``legacy_ohada_chart.py`` (637 comptes, libellés complets) ;
2. sinon le plan SYCEBNL, **si** son libellé prolonge le libellé tronqué
   (les deux référentiels partagent la même arborescence de classes) ;
3. sinon le libellé source tel quel.

Sur la codification : le manuel SYSCOHADA précise que les subdivisions des
comptes ne prennent jamais le chiffre 0 (« le premier numéro se termine alors
par 1 et le dernier par 9, le 0 gardant son sens de compte principal »). Les
zéros de remplissage peuvent donc être retirés sans ambiguïté pour retrouver le
code significatif (``4110000`` → ``411``).

Usage ::

    python scripts/build_account_charts.py \\
        --sources "D:/Formations/Comptabilité" \\
        --legacy "%TEMP%/legacy_ohada_chart.py"
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path

import openpyxl
from pypdf import PdfReader

#: Largeur maximale des libellés dans le PDF de référence (colonne tronquée).
PDF_LABEL_WIDTH = 35

#: Longueur de remplissage par référentiel (nombre total de chiffres).
#: Le SYSCOHADA Révisé se lit en 4 chiffres que les logiciels complètent de
#: deux zéros (``1011`` → ``101100``) : les deux plans tiennent donc sur 6.
CODE_WIDTH = {"SYSCOHADA": 6, "SYCEBNL": 6}

#: Au-delà de quatre chiffres, la subdivision est laissée à l'entité
#: (« UUUU.UU » = compte SYSCOHADA + nature). Ces codes propres à une entité
#: sont écartés du plan de base.
MAX_SIGNIFICANT_DIGITS = 4

#: Corrections de numérotation du référentiel commercial : les comptes de TVA
#: « production livrée » et « factures à établir » y figurent en ``433`` (autres
#: organismes sociaux), où une TVA n'a pas sa place. Le plan les attend sous
#: ``443`` (État, T.V.A. facturée). On les renumérote plutôt que de les
#: dupliquer.
CODE_FIXES: dict[str, dict[str, str]] = {
    "SYSCOHADA": {"4334": "4434", "4335": "4435"},
}

CLASS_TITLES = {
    "1": "Comptes de capitaux",
    "2": "Comptes d'immobilisations",
    "3": "Comptes de stocks",
    "4": "Comptes de tiers",
    "5": "Comptes de trésorerie",
    "6": "Comptes de charges",
    "7": "Comptes de produits",
    "8": "Comptes des autres charges et autres produits",
    "9": "Comptabilité des engagements et comptabilité analytique",
}


# --------------------------------------------------------------------- #
# Codification
# --------------------------------------------------------------------- #
def significant(code: str) -> str:
    """Retire les zéros de remplissage — ``4110000`` → ``411``.

    Les codes significatifs de deux à quatre chiffres ne se terminent jamais
    par 0 (cf. doctrine SYSCOHADA), sauf le compte principal à deux chiffres
    dont le second caractère est 0 (``10``, ``20``… ``90``).
    """
    stripped = code.rstrip("0")
    if len(stripped) >= 2:
        return stripped
    return code[:2]


def pad(code: str, template: str) -> str:
    """Complète un code significatif avec les zéros du référentiel."""
    return code + "0" * (CODE_WIDTH[template] - len(code))


# --------------------------------------------------------------------- #
# Typage comptable — alimente les états financiers
# --------------------------------------------------------------------- #
def account_type_for(code: str) -> str:
    """Détermine le type (asset/liability/equity/income/expense) d'un compte.

    Les règles s'appliquent au **code significatif**, ce qui les rend
    indépendantes du nombre de chiffres de remplissage du référentiel.
    """
    key = significant(code)
    cls = key[0]

    if cls == "1":
        # 109 : apporteurs, capital souscrit non appelé → actif (contre-valeur).
        if key == "109":
            return "asset"
        # 10 capital · 11 réserves · 12 report à nouveau · 13 résultat
        # · 14 subventions d'investissement · 15 provisions réglementées.
        if key[:2] in ("10", "11", "12", "13", "14", "15"):
            return "equity"
        # 16 emprunts · 17 dettes de location · 18 dettes liées · 19 provisions.
        return "liability"

    if cls in ("2", "3"):
        return "asset"

    if cls == "4":
        # Clients, TVA déductible, CCA, avances au personnel → actifs.
        if key[:2] == "41":
            return "asset"
        if key[:4] in ("4421", "4422", "4423"):
            return "asset"
        if key[:3] in ("481", "488", "421"):
            return "asset"
        # Dépréciations & comptes transitoires → actifs (contre-valeurs).
        if key[:2] in ("49", "47"):
            return "asset"
        return "liability"

    if cls == "5":
        # Crédits de trésorerie = dettes ; dépréciations = contre-actif.
        if key[:2] == "56":
            return "liability"
        return "asset"

    if cls == "6":
        return "expense"
    if cls == "7":
        return "income"
    if cls == "8":
        # Comptes impairs = charges, comptes pairs = produits.
        if key[:2] in ("81", "83", "85", "87", "89"):
            return "expense"
        return "income"
    return "off_balance"


# --------------------------------------------------------------------- #
# Extraction des sources
# --------------------------------------------------------------------- #
#: Un code de compte : 2 à 7 chiffres, ni précédé ni suivi d'un chiffre.
CANDIDATE_CODE = re.compile(r"(?<!\d)(\d{2,7})(?!\d)")
#: Bandeau répété en tête de chaque page du PDF commercial.
PDF_HEADER = re.compile(
    r"LISTE\s+DES\s+COMPTE?\s+EN\s+SYSCOHADA\s+REVISE?.*?INTITULE?", re.IGNORECASE
)
#: Numérotation de page isolée (« 12 », « 25 ») en début de libellé.
PAGE_NUMBER = re.compile(r"^\d{1,3}\s+")
#: Ligne « CODE LIBELLE » du SYSCOHADA commercial de référence.
LUCIEN_LINE = re.compile(r"^(\d{2,5})\s+(\S.*)$")
#: Bandeau « LISTE DES COMPTES » et en-tête « CLASSE … ».
LUCIEN_HEADER = re.compile(r"^(LISTE\s+DES\s+COMPTES?|CLASSE\b)", re.IGNORECASE)
#: Caractères de zone privée (puces Wingdings) laissés par l'extraction PDF.
#: Filtrage par codepoint : une classe de caractères en chaîne brute donne un
#: résultat surprenant sur les plages Unicode échappées.
def _strip_private_use(text: str) -> str:
    return "".join(ch for ch in text if not 0xE000 <= ord(ch) <= 0xF8FF)
#: Compte absorbé dans un libellé par la mise en page (« ... ACCORDES 901
#: ENGAGEMENTS OBTENUS ») : un nombre suivi d'un mot commençant en majuscule.
EMBEDDED_CODE = re.compile(r"\s(\d{2,5})\s+(?=[A-ZÀÂÉÈÊÎÔÛÇ])")
#: Fragment de plage resté en fin de libellé après découpe (« ... 901 à »).
DANGLING_RANGE = re.compile(r"\s+\d{2,5}\s+à$", re.IGNORECASE)


def _clean_label(label: str) -> str:
    label = _strip_private_use(label)
    label = PDF_HEADER.sub(" ", " ".join(label.split()))
    label = PAGE_NUMBER.sub("", label).strip()
    return " ".join(label.split())


def load_syscohada_pdf(path: Path) -> tuple[list[tuple[str, str]], list[str]]:
    """Extrait ``(code, libellé)`` de la liste SYSCOHADA commerciale.

    Retourne aussi les codes écartés (libellé introuvable) pour le rapport.
    """
    raw = "\n".join((page.extract_text() or "") for page in PdfReader(path).pages)
    parts = CANDIDATE_CODE.split(raw)

    entries: list[tuple[str, str]] = []
    rejected: list[str] = []
    for index in range(1, len(parts) - 1, 2):
        code, label = parts[index], _clean_label(parts[index + 1])
        if not label or not any(ch.isalpha() for ch in label):
            rejected.append(code)
            continue
        entries.append((code, label))
    return entries, rejected


def _expand(code: str, label: str) -> list[tuple[str, str]]:
    """Redécoupe un libellé ayant absorbé les comptes qui le suivaient.

    Le PDF place parfois plusieurs comptes dans la même cellule, que
    l'extraction restitue sur une seule ligne. On ne coupe que sur un nombre
    **suivi d'un mot en majuscule**, afin de ne pas casser une plage comme
    « 901 à 904 », et l'on retire le fragment de plage laissé en suspens.
    """
    parts = EMBEDDED_CODE.split(label)
    if len(parts) == 1:
        return [(code, label)]

    expanded = [(code, DANGLING_RANGE.sub("", parts[0]).strip())]
    for index in range(1, len(parts) - 1, 2):
        expanded.append((parts[index], parts[index + 1]))
    return expanded


def load_lucien_pdf(path: Path) -> list[tuple[str, str]]:
    """Extrait ``(code, libellé)`` du SYSCOHADA commercial de référence.

    Le document se présente ligne à ligne (« ``1011`` capital souscrit, non
    appelé ») ; les libellés longs sont repliés sur les lignes suivantes, sans
    code, que l'on recolle. Chaque classe s'ouvre par une liste résumée de ses
    comptes principaux, reprise ensuite en détail : le dédoublonnage final
    conserve le libellé le plus long, donc le plus précis.
    """
    entries: list[tuple[str, str]] = []
    for page in PdfReader(path).pages:
        for line in (page.extract_text() or "").splitlines():
            text = " ".join(line.split())
            if not text or LUCIEN_HEADER.match(text):
                continue
            match = LUCIEN_LINE.match(text)
            if match:
                entries.extend(_expand(match.group(1), match.group(2)))
            elif entries and not text[0].isdigit():
                code, label = entries[-1]
                entries[-1] = (code, f"{label} {text}")
    return [(code, _clean_label(label)) for code, label in entries]


def load_sycebnl_xlsx(path: Path) -> list[tuple[str, str]]:
    """Extrait ``(code, libellé)`` du classeur SYCEBNL (libellés complets)."""
    sheet = openpyxl.load_workbook(path, read_only=True, data_only=True).worksheets[0]
    entries: list[tuple[str, str]] = []
    for row in sheet.iter_rows(values_only=True):
        if not row or row[0] is None:
            continue
        if str(row[0]).strip().upper().startswith("N"):
            continue
        code = re.sub(r"\D", "", str(row[0]))
        label = _clean_label(str(row[1])) if len(row) > 1 and row[1] else ""
        if code and label:
            entries.append((code, label))
    return entries


def load_legacy(path: Path) -> tuple[dict[str, str], dict[str, str]]:
    """Charge le plan historique → libellés et ``technical_name`` par code significatif.

    Les ``technical_name`` sont les clés métier stables du logiciel
    (``customers``, ``suppliers``, ``tax_collected``…) : ils sont hérités du
    plan historique pour survivre au changement de numérotation.
    """
    spec = importlib.util.spec_from_file_location("legacy_ohada_chart", path)
    if spec is None or spec.loader is None:  # pragma: no cover - garde-fou
        raise RuntimeError(f"Plan historique illisible : {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    labels: dict[str, str] = {}
    technicals: dict[str, str] = {}
    for code, label, technical in module.OHADA_ACCOUNTS:
        key = significant(code)
        labels[key] = label
        if technical:
            technicals[key] = technical
    return labels, technicals


# --------------------------------------------------------------------- #
# Résolution des libellés
# --------------------------------------------------------------------- #
def normalise(text: str) -> str:
    """Réduit un libellé à sa forme comparable (sans accent ni ponctuation)."""
    decomposed = unicodedata.normalize("NFKD", text)
    flat = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(re.sub(r"[^a-z0-9]+", " ", flat.lower()).split())


def compatible(source: str, candidate: str) -> bool:
    """Vrai si ``candidate`` décrit le *même* compte que ``source``.

    Le test est un préfixe normalisé : la source est un libellé tronqué ou une
    variante ponctuée de la candidate. C'est ce qui empêche d'hériter d'un
    libellé historique **faux** : dans la classe 1 des plans antérieurs, le
    compte 11 s'appelait « Report à nouveau » alors que le SYSCOHADA Révisé y
    place « Réserves ». Aucun préfixe commun → le libellé source l'emporte.
    """
    left, right = normalise(source), normalise(candidate)
    if not left or not right:
        return False
    short, long = (left, right) if len(left) <= len(right) else (right, left)
    return long.startswith(short)


def resolve_label(
    source_label: str,
    key: str,
    legacy_labels: dict[str, str],
    twin_labels: dict[str, str],
) -> tuple[str, str]:
    """Retient le libellé **le plus complet parmi les compatibles**.

    Le référentiel définit la structure du plan (quels comptes existent) : son
    libellé fait donc autorité. Les libellés historique et de l'autre
    référentiel ne servent qu'à **compléter** un libellé tronqué, et seulement
    s'ils décrivent le même compte.

    Retourne ``(libellé, origine)`` avec origine ``legacy``, ``twin`` ou
    ``source``.
    """
    best, origin = source_label, "source"

    # Le plan historique relève du même système commercial : ses libellés sont
    # complets et accentués. Il prime dès qu'il décrit le même compte.
    legacy = legacy_labels.get(key)
    if legacy and compatible(source_label, legacy) and len(legacy) > len(best):
        best, origin = legacy, "legacy"

    # Le LIBELLÉ de l'autre référentiel ne sert qu'à compléter un libellé
    # tronqué : sinon ses tournures non lucratives (« usufruit », « dons et
    # legs », « adhérents ») contamineraient le plan commercial.
    twin = twin_labels.get(key)
    if (
        twin
        and len(source_label) >= PDF_LABEL_WIDTH
        and compatible(source_label, twin)
        and len(twin) > len(best)
    ):
        best, origin = twin, "twin"

    return best, origin


def merge_sources(
    template: str,
    primary: list[tuple[str, str]],
    complement: list[tuple[str, str]],
) -> tuple[list[tuple[str, str]], list[tuple[str, str]], list[tuple[str, str]]]:
    """Fusionne deux relevés d'un même référentiel.

    ``primary`` fait autorité : il apporte la structure et les libellés.
    ``complement`` n'ajoute que les comptes absent de la base.

    Deux filtres sont appliqués avant fusion :

    - les subdivisions **propres à une entité** (plus de quatre chiffres
      significatifs) sont écartées — elles ne relèvent pas du plan de base ;
    - un compte du complément portant le **libellé** d'un compte déjà retenu est
      le même concept sous un autre code : il est écarté plutôt que dupliqué.

    Retourne ``(entrées, écartés_nature, écartés_doublon)``, les entrées étant
    réduites à ``(code significatif, libellé)``.
    """
    nature: list[tuple[str, str]] = []
    duplicate_label: list[tuple[str, str]] = []
    fixes = CODE_FIXES.get(template, {})

    def prepare(entries: list[tuple[str, str]]) -> list[tuple[str, str]]:
        prepared: list[tuple[str, str]] = []
        for code, label in entries:
            key = fixes.get(significant(code), significant(code))
            if len(key) > MAX_SIGNIFICANT_DIGITS:
                nature.append((key, label))
                continue
            prepared.append((key, label))
        return prepared

    base = prepare(primary)
    extra = prepare(complement)

    merged: dict[str, str] = {}
    for key, label in base:
        if len(label) > len(merged.get(key, "")):
            merged[key] = label

    base_keys = set(merged)
    base_labels = {normalise(label) for label in merged.values()}

    for key, label in extra:
        if key in merged:
            # La base fait autorité ; un complément renuméroté y tombe ici.
            continue
        if normalise(label) in base_labels:
            duplicate_label.append((key, label))
            continue
        merged[key] = label

    keys_kept = base_keys | {k for k, _ in merged.items() if k not in base_keys}
    return sorted((k, merged[k]) for k in keys_kept), nature, duplicate_label


def build_chart(
    template: str,
    source_entries: list[tuple[str, str]],
    legacy_labels: dict[str, str],
    legacy_technicals: dict[str, str],
    twin_labels: dict[str, str],
) -> tuple[list[tuple[str, str, str]], Counter, list[tuple[str, str]]]:
    """Construit la liste ``(code, libellé, technical_name)`` du référentiel.

    Les référentiels contiennent quelques codes en double : le SYCEBNL décrit
    par exemple ``290000`` deux fois (« Dépréciations des immobilisations » et
    la variante « … non reçues destinées à la vente »). La **première
    occurrence l'emporte**, car elle porte le niveau de regroupement du plan ;
    les doublons sont retournés pour le rapport.
    """
    origins: Counter = Counter()
    duplicates: list[tuple[str, str]] = []
    chart: list[tuple[str, str, str]] = []
    seen: set[str] = set()

    for code, source_label in source_entries:
        key = significant(code)
        label, origin = resolve_label(source_label, key, legacy_labels, twin_labels)
        origins[origin] += 1
        padded = pad(key, template)
        if padded in seen:
            duplicates.append((padded, label))
            continue
        seen.add(padded)
        # Le ``technical_name`` est une clé métier du plan commercial : on ne
        # l'hérite que si le libellé désigne bien le même compte. Sans cette
        # garde, la classe 1 ou 5 du SYCEBNL récupérerait des clés sans rapport
        # — « Caisse » héritant de ``transfer``, par exemple.
        technical = ""
        legacy_label = legacy_labels.get(key, "")
        if legacy_label and compatible(source_label, legacy_label):
            technical = legacy_technicals.get(key, "")
        chart.append((padded, label, technical))

    chart.sort(key=lambda row: (row[0][0], row[0]))
    return chart, origins, duplicates


# --------------------------------------------------------------------- #
# Rendu du module Python
# --------------------------------------------------------------------- #
MODULE_TEMPLATE = '''"""
Plan comptable {title} — {count} comptes.

Fichier **généré** par ``backend/scripts/build_account_charts.py`` : ne pas
modifier à la main. Source : {source}

Codification : {width} chiffres, zéros de remplissage inclus — ``{example}``.
Retirer les zéros de remplissage redonne le code significatif SYSCOHADA
(``{significant_example}``), ce que fait ``significant_code()``.

Chaque entrée est un tuple ``(code, libellé, nom_technique)``. Le
``nom_technique`` est la clé métier stable utilisée par les écritures
automatiques (``customers``, ``tax_collected``, ``bank``…) : elle survit au
changement de numérotation et permet de tenir plusieurs référentiels.
"""

from __future__ import annotations

#: Intitulé officiel des classes OHADA.
CLASS_TITLES: dict[str, str] = {class_titles}

{name}: list[tuple[str, str, str]] = [
'''


def render_module(template: str, chart: list[tuple[str, str, str]], source: str) -> str:
    """Produit le source Python du module de données."""
    name = "SYSCOHADA_ACCOUNTS" if template == "SYSCOHADA" else "SYCEBNL_ACCOUNTS"
    title = (
        "SYSCOHADA Révisé (commercial)"
        if template == "SYSCOHADA"
        else "SYCEBNL (entités à but non lucratif)"
    )
    first = chart[0][0]
    class_titles = "{\n" + "\n".join(
        f'    "{key}": "{value}",' for key, value in CLASS_TITLES.items()
    ) + "\n}"

    out = [
        MODULE_TEMPLATE.format(
            title=title,
            count=len(chart),
            source=source,
            width=CODE_WIDTH[template],
            example=first,
            significant_example=significant(first),
            name=name,
            class_titles=class_titles,
        )
    ]

    current = None
    for code, label, technical in chart:
        if code[0] != current:
            current = code[0]
            out.append(f"    # --- CLASSE {current} — {CLASS_TITLES[current]} ---\n")
        out.append(
            "    ("
            f"{json.dumps(code)}, "
            f"{json.dumps(label, ensure_ascii=False)}, "
            f"{json.dumps(technical)},"
            "),\n"
        )

    out.append("]\n\n")
    out.append(f'__all__ = ["{name}", "CLASS_TITLES"]\n')
    return "".join(out)


# --------------------------------------------------------------------- #
# Rapport de contrôle
# --------------------------------------------------------------------- #
def report(
    template: str,
    chart: list[tuple[str, str, str]],
    origins: Counter,
    duplicates: list[tuple[str, str]],
) -> None:
    """Affiche les contrôles d'intégrité du plan généré."""
    codes = [row[0] for row in chart]
    by_code = {row[0]: row[1] for row in chart}
    width = CODE_WIDTH[template]

    print("=" * 95)
    print(f"{template} : {len(chart)} comptes — {width} chiffres")
    print("  par classe      :", dict(sorted(Counter(c[0] for c in codes).items())))
    print("  longueurs       :", dict(sorted(Counter(len(c) for c in codes).items())))
    print("  origine libelle :", dict(origins), "= legacy / twin / source")
    print(f"  doublons ecartes : {len(duplicates)}")
    for code, label in duplicates[:12]:
        print(f"      {code}  (ignore) {label[:64]}")
    print(f"  technical_name  : {sum(1 for _, _, t in chart if t)} / {len(chart)}")

    print("  comptes principaux (2 chiffres) par classe :")
    for cls in sorted({c[0] for c in codes}):
        heads = [c for c in codes if len(significant(c)) == 2 and c[0] == cls]
        shown = ", ".join(f"{h}={by_code[h][:24]}" for h in heads)
        print(f"    {cls} : {shown}")

    if template == "SYSCOHADA":
        long_labels = [c for c in codes if len(by_code[c]) >= PDF_LABEL_WIDTH]
        print(
            f"  libelles de {PDF_LABEL_WIDTH} caracteres ou plus : "
            f"{len(long_labels)} / {len(codes)}"
            " (le referentiel de base ne tronque pas : ce sont des libelles complets)"
        )


# --------------------------------------------------------------------- #
# Point d'entrée
# --------------------------------------------------------------------- #
#: Nom des sources attendues dans le répertoire ``--sources``. La base
#: commerciale est désignée par préfixe : son nom de fichier porte un identifiant.
COMMERCIAL_BASE_PREFIX = "listedescomptesreviselucien"
SYSCOHADA_FILE = "856941109-Liste-Des-Compte-en-Syscohada-Revise.pdf"
SYCEBNL_FILE = "PLAN COMPTABLE SYCEBNL.xlsx"


def main() -> int:
    parser = argparse.ArgumentParser(description="Génère les plans comptables embarqués.")
    parser.add_argument(
        "--sources", type=Path, default=Path(r"D:/Formations/Comptabilité"),
        help="répertoire des référentiels fournis",
    )
    parser.add_argument(
        "--legacy", type=Path, required=True,
        help="plan historique (source des technical_name et des libellés complets)",
    )
    parser.add_argument("--out", type=Path, default=None, help="répertoire de sortie")
    parser.add_argument("--check", action="store_true", help="rapport seul, aucune écriture")
    args = parser.parse_args()

    out_dir = args.out or (Path(__file__).resolve().parents[1] / "app/modules/accounting/data")
    if not args.check:
        out_dir.mkdir(parents=True, exist_ok=True)
    legacy_labels, legacy_technicals = load_legacy(args.legacy)
    print(f"plan historique : {len(legacy_labels)} codes, {len(legacy_technicals)} technical_name")

    base_file = next(iter(sorted(args.sources.glob(f"{COMMERCIAL_BASE_PREFIX}*.pdf"))), None)
    if base_file is None:
        raise SystemExit(f"Référentiel commercial introuvable dans {args.sources}")
    commercial_base = load_lucien_pdf(base_file)
    syscohada_raw, rejected = load_syscohada_pdf(args.sources / SYSCOHADA_FILE)
    sycebnl_raw = load_sycebnl_xlsx(args.sources / SYCEBNL_FILE)
    print(f"base commerciale : {base_file.name} — {len(commercial_base)} lignes")
    print(f"complément       : {len(syscohada_raw)} lignes ({len(rejected)} jetons sans libellé)")
    print(f"SYCEBNL          : {len(sycebnl_raw)} entrées")

    merged, nature, dup_labels = merge_sources("SYSCOHADA", commercial_base, syscohada_raw)
    print(f"\nfusion commerciale : {len(merged)} codes")
    print(f"  écartés — subdivisions propres à une entité : {len(nature)}")
    for key, label in nature:
        print(f"      {key:<7} {label[:62]}")
    print(f"  écartés — libellé déjà présent sous un autre code : {len(dup_labels)}")
    for key, label in dup_labels:
        print(f"      {key:<7} {label[:62]}")

    chart_inputs = {
        "SYSCOHADA": merged,
        "SYCEBNL": [(significant(code), label) for code, label in sycebnl_raw],
    }
    sources = {"SYSCOHADA": base_file.name, "SYCEBNL": SYCEBNL_FILE}

    for template in ("SYSCOHADA", "SYCEBNL"):
        other = "SYCEBNL" if template == "SYSCOHADA" else "SYSCOHADA"
        chart, origins, duplicates = build_chart(
            template,
            chart_inputs[template],
            legacy_labels,
            legacy_technicals,
            dict(chart_inputs[other]),
        )
        report(template, chart, origins, duplicates)
        if args.check:
            continue
        stem = "ohada_chart" if template == "SYSCOHADA" else "sycebnl_chart"
        target = out_dir / f"{stem}.py"
        target.write_text(render_module(template, chart, sources[template]), encoding="utf-8")
        print(f"  -> écrit {target}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
