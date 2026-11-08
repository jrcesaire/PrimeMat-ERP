# Rapport d'intégration — Logique OCA/payroll → Module Paie PrimeMAT

**Projet :** PrimeMAT ERP (ERP Matériaux de construction)
**Source analysée :** [OCA/payroll](https://github.com/OCA/payroll) — modules Odoo de gestion de la paie
**Objet :** analyser la logique d'OCA/payroll, en tirer les forces/faiblesses, et définir comment
s'en inspirer pour bâtir un **module Paie** parfaitement intégré à PrimeMAT.
**Date :** 07/11/2026 — **Statut :** proposition d'architecture (à valider)

---

## 0. Synthèse exécutive

OCA/payroll est la référence open-source de la paie sur Odoo. Sa force n'est pas le code
(réservé à Odoo) mais **le modèle conceptuel** : une paie *data-driven* où des **règles**
(rubriques) classées par catégories et ordonnées sont évaluées séquentiellement sur un
**bulletin**, avec un **moteur de calcul** piloté par la donnée (pas par du code figé).

PrimeMAT ne partage **pas** la stack d'Odoo (Python ORM maison, pas de FastAPI/SQLAlchemy).
On ne peut donc **pas porter le code** : on **réuse le modèle** (structures → règles →
catégories → bulletins → lot → écriture comptable) et on le réimplémente proprement dans
les briques PrimeMAT déjà en place : `TenantMixin`, RBAC `require_permission`, `SequenceService`,
`PostingService` (OHADA), moteur documentaire (WeasyPrint), `AuditService`, registre de modules.

**Recommandation :** créer un module `payroll` autonome (feuille de paie, contrats, employés,
périodes, moteur de règles, comptabilisation SYSCOHADA, bulletins PDF, déclarations CNPS/ITS),
câblé sur les conventions PrimeMAT existantes. Effort estimé : **~35–45 jh** pour un MVP
conforme Côte d'Ivoire, décomposé au §7.

---

## 1. Analyse du dépôt OCA/payroll

### 1.1 Nature & cadre

- Dépôt OCA (Odoo Community Association), **licence AGPL-3.0** (chaque module peut différer).
- Il ne fait que **compléter** le module `hr_payroll` d'Odoo : il **exige** donc `hr`
  (`hr.employee`, `hr.contract`) — qui n'existe **pas** dans PrimeMAT aujourd'hui.
- Branche active récente : **19.0** ; la branche **16.0** expose 7 modules stables.

### 1.2 Cartographie des modules (branche 16.0)

| Module | Version | Rôle |
|---|---|---|
| `payroll` | 16.0.1.6.4 | **Cœur** : bulletins, règles de salaire, structures, cotisations |
| `payroll_account` | 16.0.1.0.0 | Passerelle **paie → comptabilité** (écriture comptable depuis le bulletin) |
| `hr_payroll_period` | 16.0.1.1.0 | **Périodes de paie** (mensuelle, quinzaine…) |
| `payroll_contract_advantages` | 16.0.3.0.3 | **Avantages en nature** rattachés au contrat |
| `hr_payroll_document` | 16.0.1.3.2 | Gestion documentaire de la paie par employé (bulletins PDF) |
| `hr_payroll_document_pymupdf` | 16.0.1.0.1 | Lecture d'un bulletin PDF (parse PyMuPDF) |
| `hr_payroll_attendance_report` | 16.0.1.0.0 | Présences/temps sur le bulletin |

### 1.3 Modèles du module `payroll` (le moteur)

Fichiers de `payroll/models/` et rôles :

| Modèle Odoo | Rôle | Équivalent métier PrimeMAT |
|---|---|---|
| `hr.employee` | Employé (hérité du module `hr`) | table `employees` |
| `hr.contract` | Contrat (salaire de base, structure, date) | table `payroll_contracts` |
| `hr.payroll.structure` | **Structure de paie** = jeu de règles | `payroll_structures` |
| `hr.salary.rule` | **Règle/rubrique** (calcul d'une ligne) | `payroll_rules` |
| `hr.salary.rule.category` | **Catégorie** (BASE, BRUT, NET, COTIS…) | `payroll_rule_categories` |
| `hr.contribution.register` | **Organisme de cotisation** (CNPS, caisse…) | `contribution_registers` |
| `hr.payslip` | **Bulletin de paie** | `payroll_payslips` |
| `hr.payslip.line` | Ligne du bulletin (résultat d'une règle) | `payroll_payslip_lines` |
| `hr.payslip.input` / `hr.rule.input` | **Éléments variables** saisis (primes, retenues) | `payroll_inputs` |
| `hr.payslip.worked_days` | **Jours/heures travaillés** | `payroll_worked_days` |
| `hr.payslip.run` | **Lot** de bulletins d'une période | `payroll_runs` |

### 1.4 La logique du moteur (à retenir)

Le cœur (`hr_payslip.py`, ~825 lignes) enchaîne :

1. **Onchange employé/période** : `_get_employee_contracts()` → on déduit le contrat actif à la date.
2. **Collecte des entrées** : `get_inputs()` (éléments variables) et
   `get_worked_day_lines()` (jours travaillés) alimentent un **dictionnaire local**.
3. **`compute_sheet()`** : itère les **règles de la structure** triées par `sequence`,
   évalue chacune (`condition` puis `amount_python_compute`) et **génère une ligne**
   (`hr.payslip.line`) ; chaque règle peut lire les résultats **déjà calculés** des règles
   précédentes (`line_sum_where`, total d'une catégorie, etc.).
4. **Catégorisation** : BASE / BRUT / NET / COTISATIONS permettent de calculer en cascade
   (ex. cotisation = % du BRUT).
5. **Workflow d'état** : `draft → verify → done / cancel`, avec passages en lot via
   `hr.payslip.run`.
6. **Comptabilisation** (`payroll_account`) : agrège les lignes par compte comptable de la
   règle et produit une **pièce comptable** (débit/crédit équilibrés).

> **Idée maîtresse :** la paie n'est pas codée en dur, elle est **décrite en données**
> (structures + règles + paramètres). Ajouter une prime = ajouter des données, pas du code.

---
## 2. Rappel de l'environnement PrimeMAT (contraintes d'intégration)

Tout module doit respecter les conventions **réellement** en place :

| Brique PrimeMAT | Détail | Conséquence pour le module Paie |
|---|---|---|
| **Base + TenantMixin** (`app/core/database.py`) | `id`, `company_id`, `created_at/updated_at`, `created_by/updated_by` ; `__tablename__` auto snake_case pluriel | Chaque table paie hérite de `Base, TenantMixin` |
| **Multi-entreprise auto** | Filtre `company_id` injecté par l'event `do_orm_execute` | Isolation société gratuite ; ne pas réimplémenter |
| **RBAC** (`app/core/dependencies/permissions.py`) | `require_permission(resource, action)` ; `SYSTEM_PERMISSIONS` + `ROLES` seedés (`seed_service.py`) | Ajouter ressources `payslip`, `contract`, `payroll_rule`… + rôle RH |
| **Registre de modules** (`app/core/modules.py` + `app/api/api.py`) | `AVAILABLE_MODULES`, `MODULE_ROUTES`, `ModuleInfo` (`installed/active/inactive`) | Déclarer `payroll` aux 3 endroits + `settings.default_modules` |
| **Séquences** (`app/core/services/sequence_service.py`) | `next_value(model, prefix)` piloté par `doc_nomenclature` | Numérotation `PAIE-000123-2411`, bulletins par lot |
| **Comptabilité OHADA** (`PostingService`, `accounting/data`) | Comptes résolus par **clé métier** (`salaries`, `staff`, `social`, `state`…) via alias — **aucun code en dur** | Ajouter les clés paie + méthode `post_payslip()` idempotente (`source_type="payslip"`) |
| **Moteur documentaire** (`app/core/documents/engine.py`, `resources/templates/*.html`) | Templates HTML→PDF WeasyPrint (`invoice.html`, `quote.html`…) + `ContextBuilder` | Ajouter `payslip.html` + `arender_payslip()` |
| **Audit** (`AuditService.log`) | Journalise action/entité/valeurs | `payslip.validated`, `payslip.paid`, `rule.changed`… |
| **Alembic** (`backend/alembic/versions`) | Migrations versionnées, appliquées au démarrage | 1 migration par lot de tables |

### Écart structurel à combler : **absence de RH**

OCA/payroll **dépend** de `hr` (employés + contrats). PrimeMAT n'a **aucun** module RH :
pas d'`employee`, pas de `contract`, pas de `departments`. **Le module Paie doit donc
embarquer son propre socle « personnel »** (employés + contrats) — ou être précédé d'un
mini-module `hr`. Recommandation : **socle dans `payroll` d'abord** (livrer vite), scinder
en `hr` + `payroll` plus tard si le besoin RH s'élargit (congés, présences, évaluations).

Bonne nouvelle : le **plan comptable OHADA déjà embarqué** (`ohada_chart.py`) contient déjà
tout le nécessaire paie, ce qui réduit fortement l'effort d'intégration comptable :

| Clé/besoin | Compte SYSCOHADA déjà présent |
|---|---|
| Rémunérations dues | `422000` PERSONNELS, RÉMUNÉRATIONS DUES |
| Avances/acomptes | `421000`/`421100`/`421200` |
| Oppositions / saisies-arrêts | `423000` |
| Sécurité sociale (CNPS) | `431000`, + retraite `431300` |
| Autres organismes sociaux | `433000` |
| Impôts retenus à la source / ITS | `447000`, `447200` « Impôts sur salaires » |
| Charges de personnel | clé `salaries` → `661000` |
| Trésorerie (paiement) | `521000` (banque), `571000` (caisse) |

---

## 3. Points forts d'OCA/payroll

1. **Paie data-driven** : règles/structures/paramètres en base → aucune modification de code
   pour changer un taux, une prime ou une cotisation. C'est **le** point à reprendre.
2. **Moteur générique et testé** : structures → règles → catégories couvrent un spectre très
   large (primes, retenues, cotisations, avantages en nature) sans schéma rigide.
3. **Catégorisation (BASE/BRUT/NET/COTIS)** : permet les calculs **en cascade** (cotisation =
   % du brut) et une lecture métier claire du bulletin.
4. **Séquençage explicite** (`sequence`) : l'ordre d'évaluation est piloté par la donnée, et
   une règle peut lire les résultats précédents (`line_sum_where`, totaux de catégorie).
5. **Découplage paie / comptabilité** (`payroll_account`) : la comptabilisation est un module
   à part, idempotente — **exactement** le pattern `source_type/source_id` déjà utilisé dans
   `PostingService.post_payment` / `post_credit_note`.
6. **Périodes & lots** (`hr_payroll_period`, `hr.payslip.run`) : le traitement mensuel est un
   lot, ce qui simplifie validation en masse, écritures groupées, archivage.
7. **Avantages en nature** (`payroll_contract_advantages`) : modélise les avantages liés au
   contrat (logement, véhicule) — fréquent et valorisé dans la paie ivoirienne.
8. **Gestion documentaire** (`hr_payroll_document`) : bulletins archivés par employé.
9. **Maturité & communauté OCA** : règles éprouvées, workflow d'état, multidevise.

## 4. Points faibles / limites d'OCA/payroll

1. **Dépendance forte à Odoo (`hr`, `BaseModel`, ORM, vues XML)** → **non portable** tel quel
   dans PrimeMAT. Seul le **modèle conceptuel** est réellement réutilisable.
2. **Règles = code Python évalué (`amount_python_compute`, `condition`)** → une règle est du
   **code arbitraire** : surface d'attaque + risque d'erreur. **À ne pas répliquer avec
   `eval()`** côté PrimeMAT (RCE, invérifiable, non auditable).
3. **UX/complexité** : l'écran de règles est dense — courbe d'apprentissage forte pour un
   non-expert paie.
4. **Aucune conformité locale par défaut** : pas de règle CNPS / ITS (Côte d'Ivoire) fournie ;
   le paramétrage est à créer intégralement.
5. **Modules périphériques** (pymupdf, attendance) : utilitaires, pas socle.
6. **Pas de « déclarations sociales »** (bordereau CNPS) ni d'écritures fiscales intégrées —
   uniquement la pièce comptable de base.
7. **Licence AGPL-3.0** : copier le *code* imposerait l'AGPL. PrimeMAT étant **propriétaire**
   (« Tous droits réservés »), il faut **réimplémenter les idées** (une architecture/idée n'est
   pas soumise au droit d'auteur), jamais copier le code.

---

## 5. Ce qu'on garde, ce qu'on adapte, ce qu'on rejette

| Concept OCA/Odoo | Décision | Réimplémentation PrimeMAT |
|---|---|---|
| Structures + Règles + Catégories (data-driven) | **GARDER** | `payroll_structures`, `payroll_rules`, `payroll_rule_categories` |
| Séquence des règles (`sequence`) | **GARDER** | Colonne `sequence` + tri au calcul |
| Catégories BASE/BRUT/NET/COTIS | **GARDER** | `payroll_rule_categories.code` + totaux par catégorie |
| Organismes de cotisation (`contribution.register`) | **GARDER** | `contribution_registers` (CNPS, retraite, mutuelle) |
| Bulletin + lignes + éléments variables + jours | **GARDER** | `payroll_payslips`, `..._lines`, `payroll_inputs`, `payroll_worked_days` |
| Lot de paie par période | **GARDER** | `payroll_runs` + `payroll_periods` |
| Comptabilisation dédiée idempotente | **GARDER/ADAPTER** | `PostingService.post_payslip()` (source `payslip`) |
| Avantages en nature liés au contrat | **ADAPTER** | `contract_advantages` |
| Numérotation des bulletins | **ADAPTER** | `SequenceService.next_value("payslip", "PAIE")` |
| Règles = **code Python évalué** | **REJETER** | DSL sûr : types déclaratifs + évaluateur AST whitelisté (§6.4) |
| Dépendance `hr` Odoo | **REJETER** | Socle `employees` + `payroll_contracts` propres au module |
| Vues XML / ORM Odoo | **REJETER** | FastAPI + SQLAlchemy async + Next.js |
| Parsing PDF (pymupdf) | **DIFFÉRER** | Optionnel (phase 3+), non prioritaire |

---

## 6. Conception cible — le module `payroll` PrimeMAT

### 6.1 Enregistrement du module (intégration « parfaite »)

Trois points d'ancrage, identiques à tous les modules existants :

1. `app/core/modules.py` → `AVAILABLE_MODULES["payroll"] = "app.modules.payroll"`
2. `app/core/config.py` → ajouter `"payroll"` à `default_modules` (opt-in recommandé)
3. `app/api/api.py` → `MODULE_ROUTES["payroll"] = ("/payroll", "app.modules.payroll.api")`

Le module est alors installable/activable via l'API `/core/modules` existante et ses tables
sont créées par migration Alembic.

### 6.2 Arborescence du module

```
backend/app/modules/payroll/
├── __init__.py
├── models/
│   ├── __init__.py            # import de TOUS les modèles (metadata SQLAlchemy)
│   ├── employee.py            # Employee (socle personnel)
│   ├── contract.py            # PayrollContract + ContractAdvantage
│   ├── structure.py           # PayrollStructure, PayrollRuleCategory, PayrollRule
│   ├── contribution.py        # ContributionRegister
│   ├── period.py              # PayrollPeriod (période + lot)
│   └── payslip.py             # Payslip, PayslipLine, PayslipInput, PayslipWorkedDay
├── schemas/                   # Pydantic (Create/Read/Update)
├── services/
│   ├── employee_service.py
│   ├── contract_service.py
│   ├── structure_service.py   # CRUD structures/règles (admin paie)
│   ├── rule_engine.py         # MOTEUR : évalue règles -> lignes (§6.4)
│   ├── payslip_service.py     # compute_sheet, workflow état, lots
│   └── payroll_posting.py     # passerelle vers PostingService (§6.5)
├── seed/
│   └── payroll_ci.py          # paramétrage paie Côte d'Ivoire (CNPS/ITS) + catégories
└── api/
    ├── __init__.py            # expose `routers`
    ├── employees.py
    ├── contracts.py
    ├── structures.py
    ├── periods.py
    └── payslips.py
```

---

### 6.3 Modèle de données (SQLAlchemy 2, héritage `Base, TenantMixin`)

Correspondance directe avec les modèles Odoo (§1.3) ; colonnes communes héritées
(`id`, `company_id`, `created_at`, …) :

| Table PrimeMAT | Champs clés (hors mixin) | Source Odoo |
|---|---|---|
| `employees` | `reference` (matricule, unique/company), `last_name`, `first_name`, `birth_date`, `hire_date`, `end_date`, `job_title`, `department`, `partner_id`, `bank_account`, `cnps_number`, `tax_id` (NCC), `marital_status`, `dependents`, `status` | `hr.employee` |
| `payroll_contracts` | `employee_id`, `reference`, `date_start`, `date_end`, `structure_id`, `wage`, `wage_type` (mensuel/jour/heure), `currency_id`, `work_rate`, `state` | `hr.contract` |
| `contract_advantages` | `contract_id`, `rule_code`, `amount`, `nature`, `is_taxable` | `payroll_contract_advantages` |
| `payroll_structures` | `name`, `code`, `country` (CI), `is_default` | `hr.payroll.structure` |
| `payroll_rule_categories` | `name`, `code` (BASE, BRUT, COTIS, NET…), `sequence`, `structure_id` | `hr.salary.rule.category` |
| `payroll_rules` | `structure_id`, `name`, `code` (unique/company), `category_id`, `sequence`, `amount_type` (fixed/percentage/formula), `amount_fixed`, `percentage_of`, `formula`, `condition`, `appears_on_payslip`, `contribution_register_id`, `account_debit`, `account_credit`, `is_active` | `hr.salary.rule` |
| `contribution_registers` | `name`, `code`, `partner_id`, `account_code` | `hr.contribution.register` |
| `payroll_periods` | `name`, `date_start`, `date_end`, `payment_date`, `state`, `fiscal_year_id` | `hr_payroll_period` |
| `payroll_runs` | `period_id`, `reference`, `state` (draft/validated/paid), `entry_id` | `hr.payslip.run` |
| `payroll_payslips` | `run_id`, `period_id`, `number` (séquence), `employee_id`, `contract_id`, `structure_id`, `date_from`, `date_to`, `state` (draft/verify/done/cancel/paid), `gross`, `total_deductions`, `net_wage`, `employer_cost`, `entry_id` | `hr.payslip` |
| `payroll_payslip_lines` | `payslip_id`, `rule_id`, `category_id`, `code`, `name`, `sequence`, `amount`, `quantity`, `rate`, `total` | `hr.payslip.line` |
| `payroll_inputs` | `payslip_id`, `input_code`, `name`, `amount`, `quantity` | `hr.payslip.input` |
| `payroll_worked_days` | `payslip_id`, `work_entry_type`, `number_of_days`, `number_of_hours` | `hr.payslip.worked_days` |

> **Conseils d'intégration :** montants en `Numeric(14, 4)` (convention PrimeMAT) ; devises via
> le Core (`currencies`) ; rattacher l'employé à un `Partner` (CRM) ; indexer `company_id`,
> `employee_id`, `state`. `employees` doit porter une **contrainte d'unicité**
> `(company_id, reference)`.

---

### 6.4 Le moteur de calcul — un DSL sûr (au lieu de `eval` Python)

**Principe OCA conservé** (règles ordonnées par `sequence`, évaluées séquentiellement,
résultats lisibles par les règles suivantes), **mais exécution sûre**.

Trois `amount_type` couvrent ~90 % des besoins paie sans exécuter de code arbitraire :

| `amount_type` | Sens | Exemple |
|---|---|---|
| `fixed` | Montant fixe | Prime de transport = 20 000 F |
| `percentage` | % d'une autre ligne/catégorie | CNPS salarié = 6,3 % du BRUT |
| `formula` | Expression arithmétique **restreinte** | `SALAIRE_BASE * 2` (13e mois) |

Pour `formula`, **ne jamais utiliser `eval()`**. Implémenter un évaluateur basé sur le module
stdlib **`ast`** : whitelist stricte des nœuds autorisés (`BinOp`, `UnaryOp`, `Name`,
`Constant`, `Call` vers fonctions listées), contexte = dict de variables (`SALAIRE_BASE`,
`BRUT`, `NET`, `COTIS`, totaux de catégorie, `inputs`, `worked_days`, `contract`, `employee`)
et fonctions (`min`, `max`, `round`, `abs`). Interdire attributs (`.`), imports, boucles,
`lambda`, compréhensions. Toute erreur → `ValueError` remonté en HTTP 400 comme les autres
contrôles métier.

Pseudo-algorithme du moteur (`rule_engine.py`), calqué sur `compute_sheet()` :

```
async def compute(payslip) -> list[PayslipLine]:
    ctx = {
        "employee": ..., "contract": ...,
        "worked_days": {w.code: w.number_of_days for w in payslip.worked_days},
        "inputs":      {i.input_code: i.amount for i in payslip.inputs},
        "categories":  {},            # totaux cumulés par catégorie
        "lines":       {},            # code_règle -> total déjà calculé
    }
    lines = []
    for rule in structure.rules ordered by sequence:      # + règles custom + avantages
        if not appears_on_payslip(rule): continue
        if not safe_eval_bool(rule.condition, ctx): continue
        amount = compute_amount(rule, ctx)                # fixed / percentage / formula
        ctx["lines"][rule.code] = amount
        ctx["categories"][rule.category_code] += amount
        ctx["BRUT"|"NET"|...] = ctx["categories"][...]
        lines.append(PayslipLine(rule=rule, amount=..., total=amount))
    return lines
```

Puis `payslip_service.compute_sheet()` agrège (`gross`, `total_deductions`, `net_wage`,
`employer_cost`) et passe l'état `draft → verify`.

### 6.5 Intégration comptable OHADA (via `PostingService` existant)

On **étend** `PostingService` (pas de second moteur comptable). Ajout de clés d'alias paie
dans `accounting/data/__init__.py` (`SEMANTIC_ACCOUNTS["SYSCOHADA"]`) :

```python
"salaries":        "661000",   # existe déjà (charges de personnel)
"payroll_payable": "422000",   # personnels, rémunérations dues
"social_charges":  "431000",   # sécurité sociale / CNPS
"income_tax":      "447000",   # impôts retenus à la source (ITS)
```

Nouvelle méthode, **idempotente** comme les autres (`source_type="payslip"`) :

```
PostingService.post_payslip(payslip) →
  D 661000 (charges de personnel, = brut)                 [par catégorie de charge]
  C 422000 (rémunérations dues,   = net à payer)
  C 431000 (CNPS salarié + patronal)      [par contribution_register]
  C 447000 (ITS retenu)
  -- équilibre débit == crédit vérifié par JournalEntry (total_debit == total_credit) --
```

- Journal dédié **« PAI »** (type `misc`) créé au seed, comme `ACH/VTE/BAN/CAI`.
- Au paiement (`payroll_run.state=paid`) : **D 422000 / C 521000 (ou 571000)** via une
  méthode `post_payslip_payment()` réutilisant `treasury_kind`/`bank`/`cash`.
- Les comptes restent **résolus par alias** → compatible SYSCOHADA **et** SYCEBNL.

### 6.6 Bulletins de paie PDF (moteur documentaire)

- Template `backend/resources/templates/payslip.html` calqué sur `invoice.html`
  (mêmes classes `model-*`, en-tête société, logo, syntaxe Jinja `{% %}`).
- `DocumentEngine.arender_payslip(payslip_id)` + branche dans `ContextBuilder.load_payslip()`.
- Route `GET /payroll/payslips/{id}/pdf` identique à `print_receipt`
  (`StreamingResponse`, `content_disposition`).
- Le bulletin imprime : identité employé, période, lignes groupées par catégorie
  (BRUT → retenues → NET), totaux, mention de confidentialité.

---

### 6.7 Périodes & lots de paie

- `payroll_periods` : période (mois/quinzaine) avec `date_start/date_end/payment_date`,
  rattachée au `FiscalYear` du module comptabilité (cohérence d'exercice).
- `payroll_runs` : un **lot** par période ; `PayslipService.generate_run(period_id)` crée un
  bulletin par contrat actif, calcule, laisse en `draft`.
- Workflow du lot : `draft → validated → paid` ; la validation **fige** les bulletins et
  déclenche `post_payslip()` ; l'annulation remet en brouillon et **supprime l'écriture**
  (même cascade que `PaymentService.back_to_draft`).

### 6.8 Déclarations sociales & fiscales (Côte d'Ivoire)

Là où OCA/payroll s'arrête, PrimeMAT va plus loin (valeur métier forte) :

- **Bordereau CNPS** : agrégat par `contribution_register` (parts salariale + patronale)
  par période → PDF (`cnps_return.html`) + écriture de déclaration.
- **État ITS / ITS sur salaires** (impôt sur traitements et salaires) : récapitulatif des
  retenues (`447000`) par employé/période → export (PDF/Excel) réutilisant le service
  d'export existant (modèle `SalesExportService`).
- **Livre de paie** et **état nominatif** : export Excel.

### 6.9 Permissions & rôles (bloc à ajouter dans `seed_service.py`)

```python
# SYSTEM_PERMISSIONS
"employee":         ["view", "create", "edit", "delete"],
"contract":         ["view", "create", "edit", "delete"],
"payslip":          ["view", "create", "edit", "validate", "cancel", "pay"],
"payroll_structure":["view", "edit"],
"payroll_period":   ["view", "create", "edit", "close"],
```

```python
# ROLES — rôle RH dédié
{"code": "hr", "name": "Ressources humaines", "is_system": True, "is_global": False,
 "permissions": {
    "employee": ["view", "create", "edit", "delete"],
    "contract": ["view", "create", "edit", "delete"],
    "payslip": ["view", "create", "edit", "validate"],
    "payroll_structure": ["view"], "payroll_period": ["view", "create"],
    "report": ["view"]}},
```

Le rôle **Comptable** reçoit `payslip:view` + `payslip:pay` (paiement + comptabilisation).
La synchronisation `sync_system_permissions()` (add-only) propage ces ajouts aux bases
existantes — aucun script manuel.

### 6.10 API REST (module `payroll/api` → préfixe `/api/v1/payroll`)

| Méthode & route | Permission | Rôle |
|---|---|---|
| `GET/POST/PUT/DELETE /employees` | `employee:*` | CRUD employés |
| `GET/POST/PUT/DELETE /contracts` | `contract:*` | CRUD contrats |
| `GET/POST/PUT /structures`, `/rules`, `/categories` | `payroll_structure:*` | Paramétrage |
| `GET/POST /periods`, `POST /periods/{id}/close` | `payroll_period:*` | Périodes |
| `POST /runs` , `POST /runs/{id}/validate`, `/paid` | `payslip:*` | Lots |
| `GET /payslips`, `GET /payslips/{id}` | `payslip:view` | Consultation |
| `POST /payslips/{id}/compute`, `/validate`, `/cancel` | `payslip:*` | Calcul/workflow |
| `GET /payslips/{id}/pdf` | `payslip:view` | Bulletin PDF |
| `GET /declarations/cnps`, `/declarations/its` | `report:view` | Déclarations |

Chaque route : dépendance `require_permission(...)`, schémas Pydantic, service dédié,
`AuditService.log(...)` sur les transitions d'état — copie conforme du style
`app/modules/payments/api/payments.py`.

### 6.11 Frontend (Next.js `src/app/dashboard`)

- Nouveau dossier `payroll/` (pages) : `employees`, `contracts`, `structures`, `periods`,
  `runs`, `payslips/[id]` — même structure que `payments/` et `purchases/`.
- Hooks `usePayroll.ts` calqués sur `usePurchases.ts` / `useOperations.ts`.
- Entrée de navigation « Paie » conditionnée à l'activation du module.
- Types TypeScript ajoutés dans `lib/types.ts` (Employee, Contract, Payslip, PayslipLine…).

### 6.12 Événements & audit

- Publier des événements inter-modules (système d'events du Core) : `payroll.payslip.validated`
  → permet à `reporting`/`finance` de réagir (charges de personnel, trésorerie prévisionnelle).
- Journaliser via `AuditService` : `payslip.created`, `payslip.validated`, `payslip.paid`,
  `rule.changed` (avant/après) — exigence de traçabilité RH/paie.

---

## 7. Plan d'implémentation (gap analysis, effort en j/h)

| # | Domaine | Livrables | Backend | Frontend | Priorité |
|---|---|---|---|---|---|
| 1 | Socle personnel | `employees`, `payroll_contracts`, CRUD, permissions, migration | 3 jh | 2 jh | **Critique** |
| 2 | Catégories & structures | `payroll_rule_categories`, `payroll_structures`, `payroll_rules`, CRUD | 3 jh | 2 jh | **Critique** |
| 3 | Moteur de calcul | `rule_engine.py` (DSL `ast` sûr), `compute_sheet`, tests unitaires | 4 jh | — | **Critique** |
| 4 | Périodes & lots | `payroll_periods`, `payroll_runs`, génération de masse | 2 jh | 2 jh | Haute |
| 5 | Bulletin + PDF | `payslip.html`, `arender_payslip`, route PDF | 1,5 jh | 1 jh | Haute |
| 6 | Comptabilisation | `post_payslip`, `post_payslip_payment`, alias comptes, journal PAI | 3 jh | — | **Critique** |
| 7 | Paramétrage CI | seed catégories + règles (base, CNPS salarié/patronal, ITS, primes) | 3 jh | — | Haute |
| 8 | Déclarations | bordereau CNPS, état ITS, livre de paie (PDF/Excel) | 3 jh | 1,5 jh | Moyenne |
| 9 | Avantages en nature | `contract_advantages` + intégration au moteur | 1,5 jh | 1 jh | Moyenne |
| 10 | Frontend complet | pages, hooks, navigation, types | — | 5 jh | Haute |
| 11 | Tests & doc | tests e2e (comme `scripts/e2e_documents.py`), doc utilisateur | 3 jh | — | Haute |

**Total estimé : ~35–42 j/h** pour un MVP conforme Côte d'Ivoire. Ordre conseillé :
`1 → 2 → 3 → 7 → 4 → 5 → 6 → 10 → 8 → 9 → 11`.

---

## 8. Risques & points de vigilance

| Risque | Impact | Mitigation |
|---|---|---|
| **Sécurité du moteur de règles** (règles = code) | RCE si `eval` | DSL `ast` whitelisté + tests ; jamais `eval`/`exec` |
| **Conformité légale CI** (barèmes CNPS/ITS évolutifs) | Paie fausse | Paramétrage en **données** (règles), daté par période ; validation par un expert paie |
| **Données personnelles** (RH sensibles) | RGPD/confidentialité | RBAC fin, audit, restriction `payslip:view` par rôle, pas d'exposition aux rôles ventes/stock |
| **Multi-entreprise** | Fuite inter-sociétés | S'appuyer sur le filtre `company_id` automatique ; tester |
| **Arrondis & devises** | Écarts de centimes | `Numeric(14,4)`, arrondi centralisé (`round`) dans le moteur, tests |
| **Licence AGPL d'OCA** | Contamination licence | **Ne réimplémenter que les idées**, zéro copie de code |
| **Scope creep RH** | Retard MVP | Rester sur paie ; scinder `hr` plus tard (congés, présences) |
| **Idempotence comptable** | Double écriture | `source_type/source_id` comme `Payment`/`CreditNote` |

---

## 9. Tests & critères d'acceptation

- **Unitaires moteur** : 1 contrat → 1 bulletin attendu (brut, cotisations, ITS, net) sur un
  jeu de règles CI de référence ; cas limites (0 jour, prime, avantage en nature, exonération).
- **Sécurité DSL** : refuser `__import__`, `open`, attributs, expressions non whitelistées.
- **Intégration comptable** : `post_payslip` produit une écriture **équilibrée** et
  **idempotente** (rejouer ne crée pas de doublon).
- **Multi-tenant** : un bulletin de la société A est invisible pour la société B.
- **e2e** : créer employé → contrat → période → lot → calculer → valider → PDF → écriture.
- **Critères d'acceptation** : bulletin PDF conforme, net = brut − retenues (vérifié),
  écriture comptable équilibrée, déclaration CNPS/ITS exportable, tout tracé dans l'audit.

---

## 10. Conclusion

OCA/payroll apporte **le bon modèle conceptuel** (structures, règles, catégories, bulletins,
lots, comptabilisation découplée) mais **pas du code réutilisable** dans PrimeMAT (stack Odoo,
licence AGPL, `eval` Python). La stratégie optimale est une **réimplémentation fidèle du
modèle dans les conventions PrimeMAT** : `Base + TenantMixin`, RBAC, `SequenceService`,
`PostingService` (OHADA — déjà doté des comptes 42/43/44/66), moteur documentaire, audit.

On gagne ainsi : une paie **data-driven** (paramétrable sans code), **sûre** (DSL `ast`,
pas d'`eval`), **conforme Côte d'Ivoire** (CNPS/ITS, SYSCOHADA), **parfaitement intégrée**
(modules registry, permissions, comptabilité, PDF, front) et **sans dette de licence**.

**Prochaine étape proposée :** valider ce rapport, puis démarrer le lot 1 (socle personnel +
structure de paie) — je peux générer les modèles SQLAlchemy, la migration Alembic, le bloc de
permissions et le squelette d'API dès validation.

---
*Rapport généré pour le projet PrimeMAT ERP. Aucun code d'OCA/payroll (AGPL-3.0) n'a été
copié : seules des idées d'architecture ont été réutilisées.*

