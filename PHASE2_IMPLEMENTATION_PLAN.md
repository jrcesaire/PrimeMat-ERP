# Phase 2 — Implémentation comptable SYSCOHADA (PrimeMAT ERP)

**Objectif :** Couvrir les écarts identifiés entre le PRD SYSCOHADA et le module comptable existant (Phase 1 déjà livrée).

**Durée estimée totale : ~26 jours/homme (jh)** — backend + frontend inclus.

---

## 1. Gap Analysis détaillée

| # | Domaine | État actuel | Écart PRD | Priorité |
|---|---------|-------------|-----------|----------|
| 1 | Lettrage tiers (411/401) | Paiements comptabilisés mais jamais rapprochés des factures | Solde tiers jamais soldé, lettrage manuel impossible | Critique |
| 2 | Avoirs / notes de crédit | Aucun modèle, aucune comptabilisation | Impossible d'émettre un avoir client ou fournisseur | Critique |
| 3 | Factures fournisseurs (achats) | Mapping compte 601/4452/401 dans PostingService mais pas de document source | Pas de saisie de facture fournisseur → pas de comptabilisation achats | Critique |
| 4 | Immobilisations & amortissements | Aucun modèle FixedAsset / Depreciation | Pas de suivi des immobilisations, pas d'amortissement automatique | Haute |
| 5 | Rapprochement bancaire | Aucun modèle BankStatement / Reconciliation | Relevé bancaire non rapproché, solde banque non justifié | Haute |
| 6 | TVA déclarative | Aucun registre TVA / déclaration | Impossible de déclarer la TVA (collectée vs déductible) | Haute |
| 7 | États auxiliaires | Bilan, compte de résultat, balance générale existent | Pas de balance âgée, pas de grand livre auxiliaire par tiers, pas de chéancier | Moyenne |
| 8 | Clôture d'exercice | FiscalYear existe (open/closed) | Pas de report à nouveau automatique (compte 12), pas de verrouillage écritures | Moyenne |
| 9 | Audit trail | Aucun historique des écritures publiées | Pas de traçabilité qui a modifié quoi et quand | Moyenne |

---

## 2. Plan d'implémentation par domaine

### Domaine 1 — Lettrage des comptes tiers (3,5 jh)

**Backend (1,5 jh)**
- Modèle `InvoiceAllocation` (lettrage facture ↔ paiement)
- Service `LedgerService.allocate_payment()` : rapproche un paiement avec une ou plusieurs factures, crée les écritures de contrepassation si nécessaire
- API `POST /journal-entries/{entry_id}/allocate`, `GET /allocations/{partner_id}`
- Contrainte : un paiement ne peut être lettré que sur des factures du même partenaire, même devise

**Frontend (2 jh)**
- Écran « Lettrage client/fournisseur » : liste des factures en attente, sélection des factures à lettrer avec un paiement
- Affichage du solde restant à lettrer par tiers

### Domaine 2 — Avoirs / notes de crédit (2,5 jh)

**Backend (1,5 jh)**
- Modèle `CreditNote` (client et fournisseur), état draft/issued/applied
- `PostingService.post_credit_note()` : D 401/411 / C 709/609 (ou inversé selon sens)
- Idempotence via source_type/source_id comme pour les factures

**Frontend (1 jh)**
- Écran de saisie d'avoir (lié à une facture d'origine)
- Liste des avoirs disponibles à imputer

### Domaine 3 — Factures fournisseurs / Achats (3 jh)

**Backend (1,5 jh)**
- Modèle `PurchaseInvoice` (facture fournisseur), `PurchaseInvoiceLine`
- États : draft / posted / paid / cancelled
- `PostingService.post_purchase_invoice()` : D 601 + 4452 / C 401
- Lien vers le module payments pour règlement fournisseur

**Frontend (1,5 jh)**
- Saisie de facture fournisseur (fournisseur, lignes, TVA, échéance)
- Liste des factures fournisseurs à payer

### Domaine 4 — Immobilisations & amortissements (4 jh)

**Backend (2 jh)**
- Modèle `FixedAsset` (immobilisation), `Depreciation` (échéancier d'amortissement)
- Méthodes : linéaire, dégressif
- `DepreciationService.compute_depreciation()` : génère les écritures D 68111 / C 28111 (ou 29xxx)
- Clôture : amortissement mensuel automatique

**Frontend (2 jh)**
- Fiche immobilisation (date d'acquisition, valeur, durée, méthode)
- Tableau d'amortissement, écritures générées

### Domaine 5 — Rapprochement bancaire (3 jh)

**Backend (1,5 jh)**
- Modèle `BankStatement` (relevé), `BankReconciliation` (rapprochement)
- `BankReconciliationService.match()` : rapproche écritures comptables (511) avec lignes de relevé
- Écart de caisse → écriture d'ajustement (58/511)

**Frontend (1,5 jh)**
- Import de relevé bancaire (CSV/manuel)
- Écran de rapprochement : lignes comptables vs lignes relevé, bouton « Rapprocher »

### Domaine 6 — TVA déclarative (2,5 jh)

**Backend (1,5 jh)**
- Modèle `VATReturn` (déclaration TVA), `VATLine`
- Calcul automatique : TVA collectée (4431) vs TVA déductible (4452) sur une période
- États : draft / submitted / paid

**Frontend (1 jh)**
- Écran de déclaration TVA (période, montants pré-remplis, bouton « Déclarer »)
- Historique des déclarations

### Domaine 7 — États auxiliaires (3 jh)

**Backend (1,5 jh)**
- `FinancialService.aged_balance(partner_type, as_of)` : balance âgée par échéance (0-30, 31-60, 61-90, 90+)
- `FinancialService.partner_ledger(partner_id)` : grand livre auxiliaire d'un tiers
- `FinancialService.payment_schedule(as_of)` : chéancier des échéances à venir

**Frontend (1,5 jh)**
- Pages de reporting : Balance âgée clients, Balance âgée fournisseurs, Grand livre auxiliaire, Chéancier

### Domaine 8 — Clôture d'exercice automatisée (2 jh)

**Backend (1 jh)**
- `OHADAService.close_fiscal_year()` étendu : report à nouveau automatique (classe 6/7/8 → compte 12)
- Verrouillage des écritures sur exercice clôturé (status « posted » immodifiable)
- Réouverture d'exercice (avec mot de passe / droit admin)

**Frontend (1 jh)**
- Écran de clôture d'exercice avec confirmation
- Indicateur de verrouillage sur les écrans d'écriture

### Domaine 9 — Audit trail (2 jh)

**Backend (1 jh)**
- Modèle `AccountingAuditLog` : qui, quoi, quand, ancienne valeur, nouvelle valeur
- Déclencheurs sur création/modification/suppression d'écritures publiées

**Frontend (1 jh)**
- Écran d'historique des écritures (filtre par compte, période, utilisateur)

---

## 3. Récapitulatif des estimations

| Domaine | Backend | Frontend | Total |
|---------|---------|----------|-------|
| 1. Lettrage tiers | 1,5 | 2,0 | 3,5 |
| 2. Avoirs / notes de crédit | 1,5 | 1,0 | 2,5 |
| 3. Factures fournisseurs | 1,5 | 1,5 | 3,0 |
| 4. Immobilisations & amortissements | 2,0 | 2,0 | 4,0 |
| 5. Rapprochement bancaire | 1,5 | 1,5 | 3,0 |
| 6. TVA déclarative | 1,5 | 1,0 | 2,5 |
| 7. États auxiliaires | 1,5 | 1,5 | 3,0 |
| 8. Clôture d'exercice | 1,0 | 1,0 | 2,0 |
| 9. Audit trail | 1,0 | 1,0 | 2,0 |
| **TOTAL** | **13,0** | **12,5** | **25,5 jh** |

Marge de sécurité (10%) : **+2,5 jh** → **Total arrondi : 28 jh**

---

## 4. Séquençage recommandé (4 sprints de 1 semaine)

| Sprint | Domaines | Focus |
|--------|----------|-------|
| S1 | 1 (Lettrage) + 2 (Avoirs) | Solidifier le cœur comptable (tiers) |
| S2 | 3 (Achats fournisseurs) + 5 (Rapprochement bancaire) | Compléter les flux entrants et la trésorerie |
| S3 | 4 (Immobilisations) + 6 (TVA) | Immobilisations et conformité fiscale |
| S4 | 7 (États auxiliaires) + 8 (Clôture) + 9 (Audit) | Reporting, clôture, gouvernance |

---

## 5. Livrables attendus à la fin de Phase 2

- [ ] Lettrage automatique et manuel facture ↔ paiement
- [ ] Gestion des avoirs clients et fournisseurs
- [ ] Saisie et comptabilisation des factures fournisseurs
- [ ] Suivi des immobilisations et calcul d'amortissements
- [ ] Rapprochement bancaire (relevé ↔ écritures)
- [ ] Déclaration TVA (collectée / déductible)
- [ ] Balance âgée, grand livre auxiliaire, chéancier
- [ ] Clôture d'exercice avec report à nouveau automatique
- [ ] Audit trail des écritures comptables
- [ ] Migrations Alembic pour tous les nouveaux modèles
- [ ] Tests unitaires sur les services de comptabilisation

---

## 6. Dépendances et prérequis

- Phase 1 (module comptable de base) doit être en production ou en recette
- Les modules invoicing, payments, finance doivent être accessibles depuis le service de comptabilisation
- Le seed du plan comptable OHADA doit être exécuté pour chaque entreprise avant utilisation
