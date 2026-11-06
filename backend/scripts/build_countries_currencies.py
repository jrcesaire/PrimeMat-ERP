"""
Génère le référentiel pays et devises utilisé par les formulaires.

Source de vérité : l'extrait officiel « Codes ISO des pays et monnaies » de la
Banque de France (espace déclarants). Il fournit les **codes** — ISO 3166-1
alpha-2 pour les pays, ISO 4217 pour les devises — et les libellés français
des devises.

Deux compléments viennent de la base CLDR (bibliothèque ``babel``), parce que
l'extrait déclaratif ne les porte pas correctement :

- **libellés de pays** : le fichier de la Banque de France les écrit en
  capitales, avec une accentuation partielle (« COTE D'IVOIRE », « ALGERIE »)
  et des mentions entre parenthèses propres à la déclaration. Les noms CLDR
  sont la référence des systèmes d'exploitation et restent corrects.
- **symboles et décimales** : absents du fichier ; ``babel`` applique la
  norme ISO 4217 (0 décimale pour le franc CFA, 2 pour l'euro, 3 pour le dinar
  bahreïni, 4 pour l'unité d'investissement chilienne).

Un extrait déclaratif vieillit : celui-ci a été publié en mars 2019 et plusieurs
devises ont changé depuis. Le résultat est donc **contrôlé contre CLDR à chaque
exécution** — devises qui n'ont plus cours dans leur territoire, territoires ISO
absents, devises qu'aucun territoire ne pratique. Une divergence qui n'est pas
explicitement motivée dans ``COUNTRY_CURRENCY_FIXES`` fait échouer la génération :
la mise à jour de la source est demandée plutôt que reportée en silence.

Écarts assumés et documentés en fin de génération :

- ``XG`` (Gaza et Jéricho) et ``XZ`` (Zone franc) : codes internes à la
  Banque de France, absents de la norme ISO 3166-1 — écartés ;
- ``CFA`` : code d'agrégat de la Banque de France, absent de la norme
  ISO 4217 (les francs CFA réels sont ``XOF`` et ``XAF``) — écarté ;
- ``XAU`` (or) : code ISO 4217, mais classé par la norme parmi les
  « opérations sur métaux précieux » et non parmi les devises de facturation —
  écarté de la liste des devises sélectionnables ;
- ``ANG``, ``BGN``, ``CLF``, ``CUC``, ``HRK``, ``SLL``, ``SVC``, ``VEF`` et
  ``ZWL`` : devises sans territoire aujourd'hui, remplacées depuis 2019 par
  leur successeur (voir ``COUNTRY_CURRENCY_FIXES``) — écartées, car proposer à
  une nouvelle installation de facturer dans une devise qui n'a plus cours
  n'aurait pas de sens ;
- ``PS`` (Territoires palestiniens) : l'extrait ne lui attribue aucune devise et
  CLDR en propose deux (``ILS`` et ``JOD``). Trancher reviendrait à prendre
  position ; la devise reste vide et le formulaire la demande à l'utilisateur.

Les codes ISO 4217 qui ne sont pas des devises de facturation — unités de compte
(``CLF``, ``BOV``, ``CHE``, ``CHW``, ``COU``, ``MXV``, ``USN``, ``UYI``), métaux
précieux (``XAU``, ``XAG``, ``XPT``, ``XPD``), droits de tirage (``XDR``) et
devises historiques (``FRF``, ``DEM``, ``ITL``…) — sont hors périmètre par
construction : la liste ne retient que les devises **ayant cours** dans au moins
un territoire.

Prérequis : ``openpyxl`` — dépendance d'exécution de l'application, elle lit et
écrit déjà les classeurs (``requirements.txt``) — et ``babel`` (voir
``requirements-dev.txt``). ``babel`` apporte CLDR ; sa version est figée, car
elle détermine le contrôle automatique.

Produit :

- ``backend/app/core/data/countries_currencies.py`` — peuplement des devises ;
- ``frontend/src/lib/countries-currencies.ts`` — listes des formulaires.

Usage ::

    cd backend
    python scripts/build_countries_currencies.py
    python scripts/build_countries_currencies.py --source /chemin/vers/extrait.xlsx
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import date

from babel import Locale
from babel.numbers import (
    get_currency_precision,
    get_currency_symbol,
    get_territory_currencies,
)
from openpyxl import load_workbook

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROJECT_DIR = os.path.dirname(BACKEND_DIR)

DEFAULT_SOURCE = os.path.join(
    os.path.dirname(PROJECT_DIR),
    "banque_de_france_espace_declarants_codes_iso_pays_monnaies_03_2019.xlsx",
)

PYTHON_OUT = os.path.join(BACKEND_DIR, "app", "core", "data", "countries_currencies.py")
TYPESCRIPT_OUT = os.path.join(PROJECT_DIR, "frontend", "src", "lib", "countries-currencies.ts")

#: Feuille et première ligne de données du classeur.
SHEET_NAME = "Codes_ISO_pays_monnaies"
FIRST_DATA_ROW = 5

#: Codes écartés, avec leur motif (voir l'en-tête du module).
DROPPED_COUNTRY_CODES = {
    "XG": "code interne Banque de France, hors ISO 3166-1",
    "XZ": "code interne Banque de France, hors ISO 3166-1",
}
DROPPED_CURRENCY_CODES = {
    "CFA": "agrégat Banque de France, hors ISO 4217 (voir XOF et XAF)",
    "XAU": "or : opérations sur métaux précieux, pas une devise de facturation",
    # Devises remplacées depuis la publication de l'extrait : aucun territoire ne
    # les pratique plus, leur successeur figure dans COUNTRY_CURRENCY_FIXES.
    "ANG": "remplacé par le florin caribéen (XCG) le 31/03/2025",
    "BGN": "remplacé par l'euro le 01/01/2026 (décision UE 2025/1407)",
    "CLF": "unité de compte (unité d'investissement), pas une devise",
    "CUC": "supprimé en 2021 au profit du peso cubain (CUP)",
    "HRK": "remplacé par l'euro le 01/01/2023",
    "SLL": "remplacé par le nouveau leone (SLE) en 2022",
    "SVC": "remplacé par le dollar américain en 2001",
    "VEF": "remplacé par le bolívar soberano (VES)",
    "ZWL": "remplacé par le Zimbabwe Gold (ZWG) en 2024",
}

#: Corrections orthographiques de la source, nommément désignées.
#: L'extrait déclaratif écrit un libellé tout en capitales et un autre sans
#: accent ; on les corrige un par un plutôt que par une règle générale, afin de
#: laisser tous les autres libellés strictement tels quels.
CURRENCY_LABEL_FIXES: dict[str, str] = {
    "CDF": "Franc du Congo démocratique",
    "USD": "Dollar des États-Unis",
}

#: Codes CLDR qui ne désignent pas un pays : agrégats (``EU``, ``EZ``, ``UN``,
#: ``QO``) et codes d'essai ou indéterminés (``XA``, ``XB``, ``ZZ``). Ils sont
#: exclus de la liste des pays comme du contrôle de complétude. ``XK`` (Kosovo)
#: n'en fait pas partie : attribué par usage, il rend service au quotidien et
#: figure dans l'extrait.
NON_TERRITORY_CODES = {"EU", "EZ", "UN", "QO", "XA", "XB", "ZZ"}

#: Codes que CLDR traite comme des territoires distincts alors que ce sont des
#: subdivisions ou des rattachements : les Canaries et Ceuta et Melilla
#: (Espagne), Clipperton (France), l'île de l'Ascension et Tristan da Cunha
#: (Sainte-Hélène), Diego Garcia (Territoire britannique de l'océan Indien). Le
#: pays de rattachement figure déjà dans la liste : il n'y a rien à ajouter, mais
#: l'écart est affiché pour qu'il reste un choix et non un oubli.
SUBDIVISION_CODES = {"AC", "CP", "DG", "EA", "IC", "TA"}

#: Devise d'un pays corrigée : ``code → (devise retenue, motif)``.
#: L'extrait a figé des devises qui n'ont plus cours ; chaque correction est
#: vérifiée contre CLDR pendant la génération. La Bulgarie est le seul cas où
#: CLDR 2.17 est lui-même en retard : son adoption de l'euro, décidée par
#: l'Union européenne, est postérieure à la version de CLDR embarquée.
COUNTRY_CURRENCY_FIXES: dict[str, tuple[str, str]] = {
    "BG": ("EUR", "euro depuis le 01/01/2026 (décision UE 2025/1407)"),
    "CL": (
        "CLP",
        "CLF est une unité de compte — l'unité d'investissement — "
        "et non une devise de facturation",
    ),
    "CU": (
        "CUP",
        "CUC supprimé en 2021 : le peso cubain reste seul en circulation",
    ),
    "CW": ("XCG", "florin caribéen (XCG) en circulation depuis le 31/03/2025"),
    "HR": ("EUR", "euro depuis le 01/01/2023"),
    "SL": ("SLE", "nouveau leone (SLE) en circulation depuis 2022"),
    "SV": ("USD", "dollar américain seul moyen de paiement depuis 2001"),
    "SX": ("XCG", "florin caribéen (XCG) en circulation depuis le 31/03/2025"),
    "TL": ("USD", "dollar américain monnaie officielle depuis 2000"),
    "VE": ("VES", "bolívar soberano (VES) a remplacé le bolívar fuerte (VEF)"),
    "VG": ("USD", "dollar américain monnaie officielle du territoire"),
    "ZW": (
        "ZWG",
        "Zimbabwe Gold (ZWG), monnaie nationale depuis 2024 ; le dollar "
        "américain reste cours légal, la devise retenue est la monnaie nationale",
    ),
}

#: Territoires à code ISO 3166-1 propre que l'extrait ne liste pas : la Banque
#: de France rattache les départements et collectivités d'outre-mer ainsi que
#: Monaco à la France, alors qu'ils sont sélectionnables comme pays de facturation.
EXTRA_COUNTRIES: dict[str, str] = {
    "GF": "EUR",  # Guyane
    "GP": "EUR",  # Guadeloupe
    "MC": "EUR",  # Monaco
    "MQ": "EUR",  # Martinique
    "PM": "EUR",  # Saint-Pierre-et-Miquelon
    "RE": "EUR",  # La Réunion
    "YT": "EUR",  # Mayotte
}

#: Devises créées après la publication de l'extrait, avec leur libellé français.
#: Symbole et décimales viennent de CLDR, jamais d'une invention : babel ne
#: connaît pas encore le symbole des plus récentes, le code est alors affiché
#: tel quel. Le bolívar soberano (``VES``) n'y figure pas : créé en 2018, il est
#: déjà libellé par l'extrait, qui continue pourtant de rattacher ``VE`` au
#: bolívar fuerte. Un complément qui doublerait un libellé de l'extrait serait
#: sans effet : le rapport de génération le signale.
EXTRA_CURRENCIES: dict[str, str] = {
    "SLE": "Leone",
    "XCG": "Florin caribéen",
    "ZWG": "Zimbabwe Gold",
}


def _clean(value: object) -> str:
    """Normalise une cellule : ``None`` → chaîne vide, espaces retirés."""
    return str(value).strip() if value is not None else ""


def read_bo_france(source: str) -> tuple[dict[str, str], dict[str, str], list[str]]:
    """Lit l'extrait et renvoie les pays, les devises et les pays sans devise.

    Les lignes secondaires — un même pays déclarant plusieurs devises, comme le
    Chili (``CLF`` puis ``CLP``) ou Cuba (``CUC`` puis ``CUP``) — ont un nom de
    pays vide : la première ligne donne la devise principale, les suivantes
    enrichissent la liste des devises sans créer de pays en double.

    Deux pays sont déclarés sans devise (l'Antarctique et les territoires
    palestiniens) : ils sont renvoyés à part pour ne pas disparaître de la
    liste des pays.
    """
    workbook = load_workbook(source, read_only=True, data_only=True)
    sheet = workbook[SHEET_NAME]
    rows = list(sheet.iter_rows(values_only=True))[FIRST_DATA_ROW:]

    country_currency: dict[str, str] = {}
    currency_labels: dict[str, str] = {}
    without_currency: list[str] = []

    for row in rows:
        country_code = _clean(row[1] if len(row) > 1 else "")
        currency_label = _clean(row[2] if len(row) > 2 else "")
        currency_code = _clean(row[3] if len(row) > 3 else "")

        if currency_code and currency_label:
            currency_labels.setdefault(currency_code, currency_label)
        if not country_code:
            continue
        if country_code in country_currency or country_code in without_currency:
            continue

        if currency_code:
            country_currency[country_code] = currency_code
        else:
            without_currency.append(country_code)

    return country_currency, currency_labels, without_currency


def french_country_names() -> dict[str, str]:
    """Noms de pays en français selon CLDR (``babel``), indexés par ISO alpha-2."""
    locale = Locale.parse("fr")
    return {
        code: name
        for code, name in locale.territories.items()
        if len(code) == 2 and code.isalpha() and code.isupper()
    }


def clean_symbol(code: str) -> str:
    """Symbole d'une devise, sans espace fine insécable.

    ``babel`` renvoie ``F\\u202fCFA`` pour le franc CFA : l'espace fine est
    typographiquement correcte mais s'affiche mal dans un champ de formulaire.
    """
    try:
        symbol = get_currency_symbol(code, locale="fr")
    except Exception:  # noqa: BLE001 — une devise inconnue ne doit pas bloquer
        return code
    symbol = symbol.replace("\u202f", " ").replace("\u00a0", " ").strip()
    return symbol or code


def build(
    country_currency: dict[str, str],
    currency_labels: dict[str, str],
    without_currency: list[str],
) -> tuple[
    list[tuple[str, str, str]],
    dict[str, tuple[str, str, int]],
    dict[str, list[str]],
]:
    """Croise les deux sources et renvoie les données retenues + le rapport.

    C'est ici que l'extrait est rajeuni : ``COUNTRY_CURRENCY_FIXES`` corrige les
    devises qui n'ont plus cours, ``EXTRA_COUNTRIES`` complète les territoires
    que la Banque de France rattache à la France et ``EXTRA_CURRENCIES`` ajoute
    les devises créées depuis 2019.
    """
    names = french_country_names()
    report: dict[str, list[str]] = {
        "dropped_countries": [],
        "dropped_currencies": [],
        "unknown_country_names": [],
        "used_without_label": [],
        "countries_without_currency": [],
        "missing_from_source": [],
        "currency_corrections": [],
        "added_countries": [],
        "added_currencies": [],
        "redundant_extra_currencies": [],
        "subdivision_territories": [],
    }

    # 1. Devises corrigées : l'extrait de 2019 a figé des devises sans cours.
    corrected = dict(country_currency)
    for code, (currency, motive) in sorted(COUNTRY_CURRENCY_FIXES.items()):
        previous = corrected.get(code, "")
        if previous == currency:
            continue
        report["currency_corrections"].append(
            f"{code} : {previous or '(sans devise)'} → {currency} — {motive}"
        )
        corrected[code] = currency

    # 2. Territoires absents de l'extrait, avec la devise qui y a cours.
    corrected.update(EXTRA_COUNTRIES)

    countries: list[tuple[str, str, str]] = []
    for code in sorted(set(corrected) | set(without_currency)):
        if code in DROPPED_COUNTRY_CODES:
            report["dropped_countries"].append(f"{code} — {DROPPED_COUNTRY_CODES[code]}")
            continue
        name = names.get(code)
        if name is None:
            # Aucun nom CLDR : on le signale plutôt que d'en inventer un.
            report["unknown_country_names"].append(code)
            name = code
        currency = corrected.get(code, "")
        if not currency:
            report["countries_without_currency"].append(f"{code} — {name}")
        countries.append((code, name, currency))

    currencies: dict[str, tuple[str, str, int]] = {}
    # Les pays déclarés sans devise (Antarctique, territoires palestiniens)
    # laissent une chaîne vide : elle ne doit pas devenir un code de devise.
    used = {currency for _, _, currency in countries if currency}
    for code in sorted(used | set(currency_labels) | set(EXTRA_CURRENCIES)):
        if code in DROPPED_CURRENCY_CODES:
            report["dropped_currencies"].append(f"{code} — {DROPPED_CURRENCY_CODES[code]}")
            continue
        label = currency_labels.get(code, EXTRA_CURRENCIES.get(code))
        if label is None:
            # Devise employée par un pays mais sans libellé dans le fichier :
            # ne devrait pas arriver — on le signale et on retombe sur le code.
            report["used_without_label"].append(code)
            label = code
        label = CURRENCY_LABEL_FIXES.get(code, label)
        currencies[code] = (label, clean_symbol(code), get_currency_precision(code))

    report["added_countries"] = [
        f"{code} — {currency}" for code, _name, currency in countries if code in EXTRA_COUNTRIES
    ]
    report["added_currencies"] = sorted(
        f"{code} — {currencies[code][0]}"
        for code in EXTRA_CURRENCIES
        if code in currencies and code not in currency_labels
    )
    # Un complément déjà libellé par l'extrait ne sert à rien : le libellé de la
    # source l'emporte, l'autre est du code mort.
    report["redundant_extra_currencies"] = sorted(
        f"{code} — déjà libellé par l'extrait : {currency_labels[code]}"
        for code in EXTRA_CURRENCIES
        if code in currency_labels
    )
    report["missing_from_source"] = sorted(
        f"{code} — {name}"
        for code, name in names.items()
        if code not in corrected
        and code not in without_currency
        and code not in DROPPED_COUNTRY_CODES
        and code not in NON_TERRITORY_CODES
        and code not in SUBDIVISION_CODES
    )
    report["subdivision_territories"] = sorted(
        f"{code} — {names[code]}" for code in SUBDIVISION_CODES if code in names
    )
    return countries, currencies, report


def audit_cldr(
    countries: list[tuple[str, str, str]],
    source_currencies: dict[str, str],
) -> tuple[list[str], list[str], list[str]]:
    """Contrôle la liste obtenue contre CLDR et trie les écarts.

    Renvoie trois listes :

    - **divergences** : la devise retenue n'a pas cours dans ce pays selon CLDR,
      et son remplacement n'est pas prévu par ``COUNTRY_CURRENCY_FIXES``. C'est
      une anomalie : la génération doit échouer pour que la source soit revue ;
    - **retards** : CLDR indique encore exactement la devise de l'extrait — il
      ne connaît pas un changement officiel postérieur à sa version ;
    - **inconnues** : CLDR ne connaît pas la devise de ce territoire ; faute de
      référence, la devise de l'extrait est conservée telle quelle.
    """
    divergences: list[str] = []
    lags: list[str] = []
    unknown: list[str] = []
    for code, name, currency in countries:
        if not currency:
            continue
        current = set(get_territory_currencies(code, tender=True))
        if currency in current:
            continue
        if not current:
            unknown.append(f"{code} {name} : {currency}")
            continue
        listing = "/".join(sorted(current))
        if current == {source_currencies.get(code, "")}:
            lags.append(f"{code} {name} : {currency} — CLDR indique {listing}")
            continue
        divergences.append(f"{code} {name} : {currency} — CLDR indique {listing}")
    return divergences, lags, unknown


def _quote(value: str) -> str:
    """Littéral de chaîne valide en Python comme en TypeScript."""
    return json.dumps(value, ensure_ascii=False)


PYTHON_TEMPLATE = '''"""
Référentiel pays et devises des formulaires et du peuplement de la base.

Généré par ``backend/scripts/build_countries_currencies.py`` — ne pas modifier
à la main : relancer le script après avoir mis à jour le fichier source.

Source : extrait officiel « Codes ISO des pays et monnaies » de la Banque de
France (mars 2019), complété par la base CLDR (``babel``) pour les libellés de
pays, les symboles et les décimales ISO 4217. Le nom du fichier figure dans
``SOURCE`` ; l'en-tête du générateur documente les codes écartés et pourquoi.
"""

from __future__ import annotations

#: Jeu de données ayant servi à la génération.
SOURCE = {source}
GENERATED_ON = {generated_on}

#: Pays : ``(code ISO 3166-1 alpha-2, libellé français, code ISO 4217)``.
COUNTRIES: tuple[tuple[str, str, str], ...] = (
{countries}
)

#: Devises : code ISO 4217 → ``(libellé français, symbole, décimales)``.
#: Forme attendue par :func:`app.core.services.seed_service.seed_base_currencies`.
CURRENCIES: dict[str, tuple[str, str, int]] = {{
{currencies}
}}
'''


TYPESCRIPT_TEMPLATE = """/**
 * Référentiel pays et devises — listes des formulaires.
 *
 * Généré par `backend/scripts/build_countries_currencies.py` — ne pas modifier
 * à la main : relancer le script après avoir mis à jour le fichier source.
 *
 * Source : extrait officiel « Codes ISO des pays et monnaies » de la Banque de
 * France (mars 2019), complété par la base CLDR (`babel`) pour les libellés de
 * pays, les symboles et les décimales ISO 4217. Le nom du fichier figure dans
 * `REFERENCE_SOURCE` ; l'en-tête du générateur documente les codes écartés.
 */

export interface Country {{
  /** Code ISO 3166-1 alpha-2 (« CI »). */
  code: string;
  /** Libellé français (« Côte d'Ivoire »). */
  name: string;
  /** Code ISO 4217 de la devise ayant cours dans ce pays (« XOF »). */
  currency: string;
}}

export interface Currency {{
  /** Code ISO 4217 (« XOF »). */
  code: string;
  /** Libellé français (« Franc CFA - BCEAO »). */
  name: string;
  /** Symbole d'affichage (« FCFA ») ; à défaut, le code. */
  symbol: string;
  /** Décimales monétaires ISO 4217 (0 pour le franc CFA, 2 pour l'euro). */
  decimals: number;
}}

/** Jeu de données ayant servi à la génération. */
export const REFERENCE_SOURCE = {source_ts};
export const REFERENCE_DATE = {generated_on_ts};

/** Les {country_count} pays de l'extrait, triés par code ISO. */
export const COUNTRIES: Country[] = [
{countries}
];

/** Les {currency_count} devises de l'extrait, triées par code ISO. */
export const CURRENCIES: Currency[] = [
{currencies}
];

const COUNTRY_BY_CODE = new Map(COUNTRIES.map((c) => [c.code, c]));
const CURRENCY_BY_CODE = new Map(CURRENCIES.map((c) => [c.code, c]));

/** Pays correspondant à un code ISO 3166-1, insensible à la casse. */
export function countryByCode(code?: string | null): Country | undefined {{
  return code ? COUNTRY_BY_CODE.get(code.toUpperCase()) : undefined;
}}

/** Devise correspondant à un code ISO 4217, insensible à la casse. */
export function currencyByCode(code?: string | null): Currency | undefined {{
  return code ? CURRENCY_BY_CODE.get(code.toUpperCase()) : undefined;
}}

/** Devise ayant cours dans un pays donné. */
export function currencyForCountry(
  countryCode?: string | null,
): Currency | undefined {{
  return currencyByCode(countryByCode(countryCode)?.currency);
}}

/**
 * Libellé d'une devise pour une liste déroulante : « Franc CFA - BCEAO (XOF) ».
 *
 * Retombe sur le code brut si la devise est inconnue, afin qu'une valeur déjà
 * enregistrée ne devienne jamais invisible dans un formulaire.
 */
export function currencyLabel(code?: string | null): string {{
  if (!code) return "";
  const currency = currencyByCode(code);
  return currency ? `${{currency.name}} (${{currency.code}})` : code.toUpperCase();
}}
"""


def write_python(
    path: str,
    countries: list[tuple[str, str, str]],
    currencies: dict[str, tuple[str, str, int]],
    source: str,
    generated_on: str,
) -> None:
    """Écrit le module Python du référentiel."""
    country_lines = "\n".join(
        f"    ({_quote(code)}, {_quote(name)}, {_quote(currency)}),"
        for code, name, currency in countries
    )
    currency_lines = "\n".join(
        f"    {_quote(code)}: ({_quote(label)}, {_quote(symbol)}, {decimals}),"
        for code, (label, symbol, decimals) in currencies.items()
    )
    _write(
        path,
        PYTHON_TEMPLATE.format(
            source=_quote(source),
            generated_on=_quote(generated_on),
            countries=country_lines,
            currencies=currency_lines,
        ),
    )


def write_typescript(
    path: str,
    countries: list[tuple[str, str, str]],
    currencies: dict[str, tuple[str, str, int]],
    source: str,
    generated_on: str,
) -> None:
    """Écrit le module TypeScript du référentiel."""
    country_lines = "\n".join(
        f"  {{ code: {_quote(code)}, name: {_quote(name)}, " f"currency: {_quote(currency)} }},"
        for code, name, currency in countries
    )
    currency_lines = "\n".join(
        f"  {{ code: {_quote(code)}, name: {_quote(label)}, "
        f"symbol: {_quote(symbol)}, decimals: {decimals} }},"
        for code, (label, symbol, decimals) in currencies.items()
    )
    _write(
        path,
        TYPESCRIPT_TEMPLATE.format(
            source=source,
            source_ts=_quote(source),
            generated_on_ts=_quote(generated_on),
            country_count=len(countries),
            currency_count=len(currencies),
            countries=country_lines,
            currencies=currency_lines,
        ),
    )


def _write(path: str, content: str) -> None:
    """Écrit un fichier en UTF-8, en créant l'arborescence si nécessaire."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8", newline="\n") as handle:
        handle.write(content)


def print_report(
    report: dict[str, list[str]],
    countries: list[tuple[str, str, str]],
    currencies: dict[str, tuple[str, str, int]],
) -> None:
    """Affiche le bilan : ce qui a été retenu et ce qui a été écarté."""
    print()
    print(f"Pays retenus    : {len(countries)}")
    print(f"Devises retenues: {len(currencies)}")

    def section(title: str, items: list[str]) -> None:
        print()
        print(f"{title} ({len(items)}) :")
        for item in items:
            print(f"  - {item}")
        if not items:
            print("  (aucun)")

    section("Codes pays écartés", report["dropped_countries"])
    section("Codes devises écartées", report["dropped_currencies"])
    section(
        "Devises corrigées (extrait périmé)",
        report["currency_corrections"],
    )
    section("Pays ajoutés (absents de l'extrait)", report["added_countries"])
    section(
        "Devises ajoutées (postérieures à l'extrait)",
        report["added_currencies"],
    )
    section("Pays sans nom CLDR (code utilisé)", report["unknown_country_names"])
    section("Devises sans libellé source", report["used_without_label"])
    section("Pays déclarés sans devise", report["countries_without_currency"])
    section(
        "Pays connus de CLDR mais absents du fichier source",
        report["missing_from_source"],
    )
    section(
        "Territoires rattachés à un pays (non listés à part)",
        report["subdivision_territories"],
    )
    section(
        "Compléments de libellé sans effet (déjà dans l'extrait)",
        report["redundant_extra_currencies"],
    )
    section("CLDR en retard (écart constaté et assumé)", report["cldr_lags"])
    section("Devise inconnue de CLDR pour ce territoire", report["cldr_unknown"])
    section("Divergences avec CLDR (bloquantes)", report["cldr_divergences"])


def main() -> int:
    # Le rapport contient une flèche « → » et des accents que la page de code
    # cp1252 des consoles Windows ne sait pas encoder : sans cela, le script
    # plante à l'affichage du bilan, après avoir écrit les fichiers.
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    parser = argparse.ArgumentParser(
        description="Génère le référentiel pays et devises des formulaires."
    )
    parser.add_argument(
        "--source",
        default=DEFAULT_SOURCE,
        help="Extrait « Codes ISO des pays et monnaies » (xlsx).",
    )
    parser.add_argument("--python-out", default=PYTHON_OUT)
    parser.add_argument("--typescript-out", default=TYPESCRIPT_OUT)
    args = parser.parse_args()

    if not os.path.exists(args.source):
        print(f"Fichier source introuvable : {args.source}")
        return 1

    country_currency, currency_labels, without_currency = read_bo_france(args.source)
    countries, currencies, report = build(country_currency, currency_labels, without_currency)

    # Contrôle CLDR : ce que l'extrait ignorait est signalé, et ce qui diverge
    # sans motif documenté fait échouer la génération.
    divergences, lags, unknown = audit_cldr(countries, country_currency)
    report["cldr_divergences"] = divergences
    report["cldr_lags"] = lags
    report["cldr_unknown"] = unknown

    generated_on = date.today().isoformat()
    source_name = os.path.basename(args.source)

    write_python(args.python_out, countries, currencies, source_name, generated_on)
    write_typescript(args.typescript_out, countries, currencies, source_name, generated_on)

    print(f"Source                : {source_name}")
    print(f"Backend  (Python)     : {os.path.relpath(args.python_out, PROJECT_DIR)}")
    print("Frontend (TypeScript) : " f"{os.path.relpath(args.typescript_out, PROJECT_DIR)}")
    print_report(report, countries, currencies)

    blocking = (
        report["unknown_country_names"]
        + report["used_without_label"]
        + report["redundant_extra_currencies"]
        + report["cldr_divergences"]
    )
    if blocking:
        print()
        print("ATTENTION : divergences à corriger (voir ci-dessus).")
        return 1

    print()
    print("Génération terminée.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
