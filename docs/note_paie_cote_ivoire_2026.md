# Note de référence — Paie Côte d'Ivoire (barème 2026)

**Objet :** agréger la méthode de calcul de la paie ivoirienne et le **barème 2026**,
puis confronter ces règles au module Paie PrimeMAT.

**Sources**
- Formation « Comptabilité / Paie » (`D:\Formations\Comptabilité\Paie`) :
  - `859493087-Calcul-ITS.pdf` — **barème ITS 2026** et RICF ;
  - `1035218650-Bareme-Des-Salaires-Cote-d.pdf` — grilles salariales, **SMIG 2026** ;
  - `428882701-Explication-bulletin-paie-Cote-d-Ivoire.pdf` — anatomie d'un bulletin ;
  - `660947642-COURS-RH.pdf` — élaboration de la paie (primes, HS, indemnités) ;
  - `135475775-Cours-de-Fiscalite-001.pdf` — fiscalité (dont ancien régime) ;
  - `587925533-rgl2d.xlsx` — modèle de bulletin (système **2021** : IS/CN/IGR/CR).
- Simoon CV — Barème des salaires Côte d'Ivoire 2026 (SMIG, grilles). *(Ne traite
  ni de l'ITS ni de la CNPS.)*

---

## 1. Salaire brut imposable (SBI)

```
SBI = salaire de base + sursalaire + heures supplémentaires
      + primes imposables + indemnités imposables + avantages en nature
```

- **Durée légale** : 40 h/semaine → **173,33 h/mois**. Taux horaire
  `TH = (salaire catégoriel [+ sursalaire]) / 173,33`.
- **Heures supplémentaires** (majoration du salaire réel) :
  `RHS = TH × (1 + taux) × nombre d'heures`
  | Tranche | Majoration |
  |---|---|
  | 41ᵉ–46ᵉ h | +15 % |
  | 47ᵉ–55ᵉ h | +50 % |
  | nuit (21 h–5 h) | +75 % |
  | dimanche / jours fériés (jour) | +75 % |
  | nuit dimanche / jours fériés | +100 % |
- **Prime d'ancienneté** (obligatoire) : **2 %** du salaire de base catégoriel après
  2 ans, **+1 %/an** jusqu'à la 25ᵉ année incluse.
- **Indemnité de transport** : exonérée à hauteur de la carte SOTRA —
  **30 000 FCFA (Abidjan)**, 25 000 (Bouaké), 21 000 (autres villes) ; le surplus
  est imposable.
- **Primes exonérées** dans la limite de **10 %** de la rémunération totale en
  numéraire (représentation, déplacement, salissure, tenue, caisse, responsabilité,
  fonction).
- **Avantages en nature** (valorisations administratives) : logement, mobilier,
  électricité, eau, domesticité, téléphone, nourriture — barèmes par nombre de pièces.
  Le **véhicule de fonction n'est pas taxable**.

---

## 2. Retenues fiscales — ITS 2026 (barème progressif)

En 2026, l'**Impôt sur les Traitements et Salaires (ITS)** remplace l'ancien triptyque
IS + CN + IGR. Il est **progressif par tranches**, calculé **directement sur le
salaire brut imposable** (plus d'abattement de 80 % ni de déduction CN/IS préalable).

| Tranche de revenu mensuel | Taux |
|---|---|
| 0 – 75 000 | **0 %** |
| 75 001 – 240 000 | **16 %** |
| 240 001 – 800 000 | **21 %** |
| 800 001 – 2 400 000 | **24 %** |
| 2 400 001 – 8 000 000 | **28 %** |
| > 8 000 000 | **32 %** |

Chaque tranche est taxée **séparément** (méthode progressive) : `ITS = Σ tauxᵢ × (part de
la trancheᵢ effectivement atteinte)`.

### RICF — Réduction d'Impôt pour Charges de Famille

Réduction appliquée sur l'ITS brut selon les **parts fiscales** :
**+5 500 FCFA/mois par demi-part** au-delà de 1 part, soit `RICF = (parts − 1) × 11 000`.

**Détermination des parts** : célibataire/divorcé/veuf = **1** ; marié/veuf (chef de
famille) = **2** ; **+0,5 par enfant à charge** (plafond 5 parts).

**ITS net = ITS brut − RICF.**

> Exemples du support officiel (reproduits par le module) :
> - 1 800 000, 2 parts → ITS brut **384 000**, RICF −11 000 → **373 000**.
> - 8 500 000, 2 parts → ITS brut **2 256 000**, RICF −11 000 → **2 245 000**.

---

## 3. Retenues sociales — CNPS

| Cotisation | Taux | Assiette |
|---|---|---|
| Retraite **salarié** (CR) | **6,3 %** | salaire brut social |
| Retraite **employeur** | répartie ci-dessous | salaire brut social |
| Prestations familiales (employeur) | **5,75 %** | salaire brut social |
| Accidents du travail (employeur) | **2 %** (variable 2–5 %) | salaire brut social |
| **Total employeur (≈)** | **15,45 %** | salaire brut social |

**Plafond** : cotisation plafonnée à **45 × SMIG**. Avec le **SMIG 2026 = 75 000 FCFA**,
le plafond est **3 375 000 FCFA** (historiquement 2 700 000, soit 45 × 60 000).

---

## 4. Du brut au net

```
Total retenues = ITS net + CNPS salarié (+ avances, acomptes, prêts, oppositions)
Salaire net    = SBI − Total retenues
Net à payer    = Salaire net + indemnité de transport NON imposable
                 − avances − acomptes
```

---

## 5. Pour mémoire — ancien système (encore présent dans l'Excel 2021)

- **IS** = 1,2 % × SBI (ou 1,5 % × salaire cédulaire = 80 % du SBI).
- **CN** (contribution nationale), progressive sur le salaire cédulaire (80 % du SBI) :
  ≤50 000 : 0 ; 50 000–130 000 : 1,5 % ; 130 000–200 000 : 5 % ; >200 000 : 10 %.
- **IGR** : barème par **quotient familial** `Q = R/N`,
  `R = 0,85 × (0,8 × SBI − (IS + CN))`, N = parts (cf. §2).
- **CR** (retraite CNPS salarié) = 6,3 %, plafond 2 700 000.

---

## 6. Confrontation avec le module Paie PrimeMAT

| Règle métier | Implémentation initiale | Statut après correction |
|---|---|---|
| SBI = base + primes + indemnités + avantages | Catégories BASE + PRIME + éléments variables | ✅ **`PRIMES = INPUTS_TOTAL`** alimente le brut |
| **ITS 2026 progressif** (0/16/21/24/28/32 %) | Placeholder `formula = "0"` ❌ | ✅ Règle `ITS_BRUT` `amount_type = scale` + barème 2026 |
| **RICF** (parts fiscales) | Absent ❌ | ✅ Règle `RICF` (formule) + `PARTS` au contexte |
| **Parts fiscales** | Absent ❌ | ✅ `Employee.tax_parts` (dérivé de la situation + enfants) |
| **CNPS salarié 6,3 %** | Oui, **non plafonné** ⚠️ | ✅ Plafonné à **45 × SMIG** (formule `min(BRUT, 45*SMIG)*6.3/100`) |
| **CNPS employeur (15,45 %)** | Oui, non plafonné ⚠️ | ✅ Plafonné, libellé « retraite + PF + AT » |
| SMIG 2026 (75 000) | Absent | ✅ Variable `SMIG` du contexte |
| Prime d'ancienneté, HS, exonération transport | Non modélisés | ⏳ À compléter (paramétrable, cf. §7) |

### Corrections apportées au code
- `models/employee.py` : colonne **`tax_parts`** (Numeric(3,1)).
- `models/structure.py` : colonne **`scale_brackets`** (JSON) sur `PayrollRule`.
- `services/rule_engine.py` : nouveau type **`amount_type = "scale"`** (barème progressif),
  constantes **SMIG 2026** et **RICF** ; contexte enrichi (`SMIG`, `PARTS`, `SENIORITY`,
  `INPUTS_TOTAL`, chaque élément variable, chaque ligne calculée exposée comme variable).
- `services/employee_service.py` : **dérivation automatique des parts fiscales**
  (situation matrimoniale + personnes à charge, plafond 5).
- `services/payslip_service.py` : chaque ligne calculée est exposée comme variable
  (permet `condition = "ITS_BRUT > 0"`).
- `seed/payroll_ci.py` : règles conformes 2026 (ITS barème + RICF + CNPS plafonnée).
- `schemas/__init__.py` : champs `tax_parts`, `scale_brackets`.
- Migration `payroll_module_20261107` : colonnes `tax_parts`, `scale_brackets`.

### Résultats de validation (exemples officiels reproduits)
| Cas | Attendu | Obtenu |
|---|---|---|
| 1 800 000, 2 parts → ITS net | 373 000 | **373 000** ✅ |
| 8 500 000, 2 parts → ITS net | 2 245 000 | **2 245 000** ✅ |
| 4 000 000 → CNPS salarié (plafond) | 212 625 (=3 375 000×6,3 %) | **212 625** ✅ |
| 1 800 000, 1 part → ITS | 384 000 (sans RICF) | **384 000** ✅ |

---

## 7. Points à finaliser (paramétrables, sans code)

- **Prime d'ancienneté** : règle `PRIME_ANCIENNETE` exploitant la variable `SENIORITY`
  (déjà exposée) — ex. `formula = "SALAIRE_BASE * min(2 + max(0, SENIORITY - 2), 25) / 100"`.
- **Exonération transport** (30 000 Abidjan) : saisir la part imposable en élément
  variable, ou ajouter une règle de déduction de l'exonération.
- **Avantages en nature** : valorisation via `contract_advantages` (barèmes logement/eau/
  électricité/domesticité) à saisir ; alimente `PRIMES`/inputs.
- **Net à payer** : avances, acomptes, prêts, oppositions (retenues post-net) — évolution
  du bulletin (lot suivant).
- **Barème & taux** : à confirmer chaque année (décrets) — modifiables en données.

> ⚠️ Le paramétrage est un **jeu de départ** : la validation finale des taux CNPS
> (branche accidents du travail, plafond) et du barème ITS 2026 doit être faite par un
> **expert paie** avant mise en production.


---

## 8. Livraisons (lots 5, 8, 10)

### Bulletins de paie (PDF)
- Template `resources/templates/payslip.html` (A4) — en-tête société, salarié,
  lignes groupées par catégorie, brut/retenues/**net à payer**/coût employeur.
- `ContextBuilder.load_payslip` + `DocumentEngine.arender_payslip`.
- Route `GET /payroll/payslips/{id}/pdf`.

### Déclarations CNPS / ITS
- Service `declaration_service` : bordereau CNPS (base, part salariale, part
  patronale par organisme) et état ITS (impôt retenu par salarié, net de la RICF).
- Routes JSON `GET /payroll/declarations/cnps` et `/its` (+ variantes `/pdf`).
- Templates `cnps_return.html`, `its_return.html`.

### Paramètres de paie configurables
- Service `settings_service` (réglage JSON `payroll_settings`, par entreprise) :
  **SMIG, taux CNPS salarié/patronal, plafond (×SMIG), RICF, exonération
  transport, barème ITS**.
- Routes `GET/PUT /payroll/settings` et `POST /payroll/settings/apply`
  (reporte les paramètres dans les règles de la structure).
- Les règles de la structure référencent des **variables** (`SMIG`,
  `CNPS_CEILING`, `CNPS_SAL_RATE`, `CNPS_PAT_RATE`, `RICF_HALF`) injectées par
  le moteur à partir des paramètres → un taux se change **sans code**.

### Saisie des paramètres à l'ajout d'un salarié
- `EmployeeCreate` accepte un bloc `contract` (structure, salaire de base,
  date de début, type de salaire) : le contrat est créé avec le salarié.
- Parts fiscales dérivées automatiquement (situation matrimoniale + personnes
  à charge), modifiables.

### Frontend (Next.js)
- Hook `usePayroll.ts` ; types dans `lib/types.ts` ; helpers PDF dans `lib/api/pdf.ts`.
- Pages `/dashboard/payroll` (hub), `.../employees`, `.../payslips`, `.../runs`,
  `.../declarations`, `.../settings` ; entrée de navigation « Paie » (section Finances).
- `tsc --noEmit` : **0 erreur**.

### Conformité vérifiée
- `ruff check` : *All checks passed* — backend **30 routes** Paie.
- Barème 2026 reproduit au centime (cf. §6).


---

## 9. Tests automatisés

- **Suite autonome** `backend/test_payroll.py` — 48 contrôles sur base SQLite
  temporaire : DSL de calcul sûr, barème ITS 2026 (1 800 000 / 2 parts → 373 000),
  CNPS plafonnée (45 × SMIG), paramètres configurables (plafond et barème
  modifiés → calcul modifié), salarié + contrat, calcul du bulletin
  (brut/retenues/net/coût employeur), workflow et lot de paie, comptabilisation
  **idempotente**, bordereau CNPS et état ITS.
  - `python backend/test_payroll.py` → `TOUTES LES VÉRIFICATIONS SONT PASSÉES (48 contrôles)`
- **Harnais pytest** `backend/tests/test_payroll.py` (rejoue la suite en
  sous-processus) : `python -m pytest -k payroll` → **1 passed**.
- Le test a révélé puis corrigé un défaut réel : en async, `session.get()`
  ne rejoue pas les chargeurs `selectin` d'un objet déjà présent en session
  (`MissingGreenlet`) → `PayslipService._load_rich()` charge désormais
  explicitement les relations du bulletin avant calcul/validation.

