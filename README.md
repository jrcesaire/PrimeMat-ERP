# ERP Matériaux de Construction

Un ERP modulaire et verticalisé pour la gestion, le négoce et la distribution de matériaux de construction.

> Alternative simple, ciblée et modulaire à un ERP généraliste, adaptée aux réalités du commerce de matériaux de construction.

## Stack technique

| Domaine          | Technologie                                    |
| ---------------- | ---------------------------------------------- |
| Frontend         | Next.js + React + TypeScript                   |
| Backend          | Python + FastAPI                               |
| ORM              | SQLAlchemy 2 + Alembic                         |
| Base de données  | PostgreSQL                                     |
| Cache            | Redis                                          |
| Jobs asynchrones | Celery                                         |
| Broker           | Redis                                          |
| PDF              | WeasyPrint                                     |
| Designer No-Code | React + dnd-kit                              |
| Fichiers         | S3-compatible / MinIO                          |
| Auth             | Auth maison bien structurée (JWT)              |
| API              | REST + OpenAPI                                 |
| Temps réel       | WebSocket                                      |
| Mobile           | Flutter (phase ultérieure)                     |
| Déploiement      | Docker + Nginx                                 |
| CI/CD            | GitHub Actions                                 |
| Monitoring       | Sentry + Prometheus + Grafana                  |

## Architecture

L'application est conçue comme un ensemble de **modules indépendants et démontables**. Le Core fournit les services transversaux (utilisateurs, auth, multi-entreprise, permissions, événements, moteur documentaire, stockage, sauvegarde), tandis que les modules métier (Catalogue, CRM, Ventes, Stock, Achats, Livraison, Facturation, Paiements, Finance, Reporting) peuvent être installés, activés ou désactivés indépendamment.

### Core / Noyau
- Identity & Access (auth, utilisateurs, rôles, permissions)
- Configuration (entreprises, agences, devise, taxes, paramètres)
- Multi-entreprise / Multi-site
- Events (système d'événements inter-modules)
- Notifications
- File Storage (S3 / MinIO)
- Cloud Backup (Google Drive, Dropbox, OneDrive, S3...)
- Document Engine (PDF, designer No-Code, templates)
- Audit Log
- API + OpenAPI

### Modules métier
- Catalogue (produits, services, tôles BAC, unités de mesure)
- CRM (clients, contacts, chantiers)
- Ventes (devis, commandes, ventes comptoir)
- Point de vente / PoS (sessions de caisse, clôture automatique, mode immersif, achats de quincaillerie)
- Stock (entrepôts, mouvements, seuils)
- Achats (fournisseurs, bons de commande, réceptions, factures fournisseur)
- Livraison (bons de livraison, transport)
- Facturation (factures, avoirs, PDF)
- Paiements (espèces, virement, chèque, Mobile Money)
- Finance / Trésorerie (comptes, relevés, rapprochement bancaire)
- Comptabilité OHADA (plan comptable, journaux, grand livre, balance, clôture d'exercice, amortissements, déclarations de TVA, grand livre auxiliaire, journal d'audit)
- Reporting / BI

## Démarrage rapide

```bash
# Backend
cd backend
pip install -r requirements.txt
uvicorn app.main:app --reload

# Frontend
cd frontend
npm install
npm run dev
```

### Lancer toute la stack (recommandé)

```bat
Lancer-ERP.bat     :: backends (8001/8002) + frontend (3000), serveurs détachés
Arreter-ERP.bat    :: arrêt de tous les serveurs
```

Le **rechargement à chaud est actif** : modifier un fichier `.py` de
`backend/app` (ou un fichier du frontend) est pris en compte
automatiquement, sans redémarrer quoi que ce soit. Pour le désactiver :
`set ERP_RELOAD=0` avant de lancer le script.

> Les serveurs tournent **détachés** sur Windows (ils survivent à la fermeture de
> la fenêtre). Dans ce mode, le rechargement natif d'uvicorn échoue
> (`CTRL_C_EVENT` impossible sans console) : `backend/scripts/dev_server.py`
> applique donc un correctif qui relance l'ouvrier via `terminate()`, socket
> d'écoute conservée (aucune coupure). Logs applicatifs complets :
> `backend/logs/uvicorn_8001.log` et `backend/logs/uvicorn_8002.log`.


## 🔑 Accès par défaut (premier démarrage)

Au **premier démarrage** (base vide, mode dev), l'application crée automatiquement les données de démarrage :

| Élément | Valeur |
|---|---|
| **Entreprise** | Entreprise ABC (code `ABC`, devise XOF) |
| **Agence** | Agence principale (`AG-01`) |
| **Email admin** | `admin@abc.com` |
| **Mot de passe** | `Admin@12345` |
| **Rôles système** | `admin` (toutes permissions), `manager`, `sales`, `accountant`, `warehouse` |

> ⚠️ **Changez ce mot de passe en production** via `python -m scripts.seed_admin reset-password admin@abc.com NouveauMotDePasse123`, ou configurez des valeurs différentes dans le `.env` avant le premier démarrage (`FIRST_ADMIN_EMAIL`, `FIRST_ADMIN_PASSWORD`, `FIRST_COMPANY_CODE`...). Le bootstrap est **idempotent** : il ne s'exécute que si la base est vide et ne modifie jamais un compte existant.

Commandes utiles :

```bash
cd backend
python -m scripts.seed_admin                                    # crée les données de démarrage manuellement
python -m scripts.seed_admin seed                               # idem
python -m scripts.seed_admin reset-password <email> <nouveau>   # réinitialise un mot de passe
```

Vérification complète du bootstrap : `python backend/test_bootstrap_e2e.py`

## État d'avancement

### ✅ Core (opérationnel)
- **Auth JWT** : login/refresh/logout, hachage bcrypt, permissions RBAC (`resource:action`)
- **API Core** : `/core/auth/*`, `/core/users`, `/core/companies`, `/core/roles`, `/core/settings`, `/core/system` (modules, devises, taxes, info)
- **Multi-tenant** : `TenantMixin` (company_id + audit created_at/by), isolation par entreprise
- **EventBus** : événements inter-modules découplés (`sales.order.created`, `inventory.stock.reserved`, `purchase.need.created`...)
- **Numérotation** : séquences de documents (DEV-0001, COM-0001...)
- **Moteur documentaire** : Jinja2 → WeasyPrint → PDF, indépendant des modules métier
- **Stockage** : abstraction S3/MinIO ou local
- **Sauvegarde cloud** : S3, Google Drive, Dropbox, OneDrive via couche d'abstraction
- **Tâches Celery** : PDF, sauvegardes, rapports planifiés

### ✅ Modules métier implémentés
| Module | Endpoints | Fonctionnalités clés |
|---|---|---|
| **Catalogue** | 9 | Produits (stockable/on_demand/hybride/service), catégories, unités de mesure, conversions, **tôles BAC multi-longueurs** |
| **CRM** | 4 | Clients/fournisseurs (Partner), contacts, adresses, chantiers (sites) |
| **Ventes** | 6 | Devis avec lignes BAC, devis→commande (coupes préservées), analyse fulfillment hybride |
| **Stock** | 4 | Entrepôts, niveaux (réel/réservé/dispo), mouvements (entrée/sortie/transfert/ajustement/perte), réservations |

### ✅ Achats, Livraison, Facturation, Paiements, Finance, Reporting
Implémentés (routeurs chargés dynamiquement) : demandes d'achat, bons de commande, réceptions, factures fournisseur avec rapprochement 3 voies, bons de livraison, factures et avoirs, paiements multi-modes, trésorerie et rapports.

### ✅ Comptabilité OHADA & Point de vente (phase 2)
| Domaine | Fonctionnalités clés |
|---|---|
| **Comptabilité** | Plan comptable SYSCOHADA, journaux, écritures, grand livre, balance, compte de résultat, bilan, trésorerie, lettrage, clôture / réouverture d'exercice avec à-nouveaux, amortissements (linéaire + dégressif SYSCOHADA), déclarations de TVA, grand livre auxiliaire par tiers, échéancier de paiement, journal d'audit |
| **Point de vente** | Sessions de caisse (solde initial repris de la veille, clôture automatique, rapport de clôture), mode immersif plein écran, écran d'accueil à 6 tuiles, achats de quincaillerie consolidés dans le module Achats et le grand livre |

## Test du scénario métier (validé ✔)

Le scénario complet de la spécification est testé et validé :

```
Devis DEV-0001 :
  - 100 sacs ciment @ 5 000          =   500 000
  - Tôle BAC Profil X @ 3 500/m :
      10 × 5,50 m
      20 × 4,50 m                      =   665 000
      15 × 3,00 m     → total 190 m
  ────────────────────────────────────────────────
  TOTAL                              = 1 165 000 FCFA

confirm_quote() → commande COM-0001 (coupes BAC conservées)

analyze_fulfillment() [mode hybride] :
  - Ciment : stock dispo 80 → réservation 80, achat 20
  - Tôle BAC : stock 0    → achat fournisseur 190 m
```

Exécuter : `python backend/test_smoke.py`

## 🧪 Tests & intégration continue

### Backend — suites fonctionnelles (pytest)

Les suites sont des scripts autonomes (base SQLite temporaire, aucune dépendance
à PostgreSQL) réunis sous un même rapport pytest :

```bash
cd backend
pip install -r requirements.txt -r requirements-dev.txt

python -m pytest                     # toutes les suites
python -m pytest -k pos              # seulement l'achat de quincaillerie du PoS
python -m pytest -m slow             # suites longues uniquement
```

| Suite | Couverture |
|---|---|
| `test_fiscal_closing.py` | Clôture d'exercice : écritures de clôture (6/7/8 → 121/129), affectation du résultat (111/119), création de l'exercice suivant, réouverture, refus d'écriture sur exercice clôturé |
| `test_depreciation.py` | Amortissements : linéaire annuel / mensuel, dégressif SYSCOHADA avec bascule, arrondi absorbé par la dernière période, idempotence de l'écriture `D 681 / C 28x` |
| `test_vat_return.py` | TVA : calcul collectée / déductible, liquidation (`441`), stabilité de l'aperçu après liquidation, règlement `D 441 / C 521`, crédit reportable, garde-fous |
| `test_auxiliary_reports.py` | Grand livre par tiers (solde courant) et échéancier de paiement (tranches d'ancienneté) |
| `test_accounting_audit.py` | Journal d'audit comptable : traçabilité `created` / `posted`, filtres, lecture seule |
| `test_pos_purchase.py` | Achat de quincaillerie depuis le PoS : facture fournisseur réglée, ventilation HT / TVA au centime, dette ouverte si non réglé, décaissement caisse vs banque, rattachement au tiers, garde-fous |

Chaque suite est également exécutable seule : `python backend/test_vat_return.py`
(affiche le détail des vérifications et retourne un code de sortie exploitable).

### Frontend — tests unitaires (Jest)

```bash
cd frontend
npm install
npm test              # jest
npm test -- --watch   # mode interactif
npm run type-check    # tsc --noEmit
npm run lint          # ESLint 9 (flat config)
```

Les suites vivent à côté du code testé (`src/lib/*.test.ts`) et couvrent les
utilitaires de formatage, le store du mode immersif du PoS (`pos-focus`) et le
modèle de navigation — ce dernier vérifie notamment qu'aucun sous-menu ne pointe
deux fois vers la même route.

> Les tests tournent en environnement `node` (logique pure). Pour tester des
> composants React, installer `jest-environment-jsdom`, `@testing-library/react`
> et `@testing-library/jest-dom`, puis passer `testEnvironment` à `"jsdom"` dans
> `frontend/jest.config.js`.

### Intégration continue

Le workflow [`.github/workflows/ci.yml`](.github/workflows/ci.yml) s'exécute sur
chaque push (`main`, `develop`), chaque pull request et à la demande :

| Job | Contenu |
|---|---|
| **backend** | `ruff check app` puis `python -m pytest` |
| **frontend** | `npm run lint`, `npm run type-check`, `npm test -- --ci` |
| **frontend-build** | `npm run build` (informatif, non bloquant) |

### Dette technique connue

- **ESLint** : les règles `@typescript-eslint/no-explicit-any` et
  `no-unused-vars` sont en **avertissement** — ~50 occurrences historiques
  restent à résorber (`src/lib/types.ts`, `src/hooks/useCatalogue.ts`,
  `src/components/settings/*`…). Les repasser en `error` dans
  `frontend/eslint.config.mjs` une fois nettoyées.
- **Ruff** : `backend/ruff.toml` ne sélectionne que `E9` (erreurs de syntaxe /
  runtime) ; ~188 diagnostics historiques (imports non triés, variables
  inutilisées, réimports locaux) restent à traiter. Élargir `select` au fil de
  l'eau (`["E", "F", "I", "UP", "B"]`).
- **Build frontend** : `next build` n'a jamais pu être validé sur poste Windows
  (échec au spawn des workers de génération statique, `spawn UNKNOWN`). La
  compilation et la vérification de types passent ; le job CI
  `frontend-build` sert à confirmer le comportement sous Linux.
- **Versions** : l'environnement de développement peut dériver des fichiers
  `requirements*.txt` (ex. `fastapi` plus récent que le `0.115.6` épinglé).

## 🏷️ Modes de vente par catégorie (logique métier)

Le mode de vente d'un produit est **dérivé de sa catégorie** (jamais saisissable manuellement). Trois modes, hérités par les sous-catégories :

| Mode | Description | Prix requis | Exemples |
|---|---|---|---|
| **`unit`** | Vendu à l'unité | `selling_price` | Ciment, tôle ondulée, peinture |
| **`length`** | Vendu au mètre linéaire, coupes à la demande | `price_per_meter` | **Tôles BAC** (et variantes) |
| **`dual`** | Au ml **ou** à la pièce de longueur standard (facturée au prorata du ml) | `price_per_meter` | Accessoires de tôlerie (solin de rive…) |

### Arborescence standard (seed automatique)

Les **36 catégories racines** du référentiel sont créées au premier démarrage, dont :

```
Tôles et couverture                        (unit)
├── Tôles BAC                              (length)
│   ├── Tôle BAC Alu                       (hérite length)
│   ├── Tôle BAC Selflock (ghanéenne)      (hérite length)
│   └── Tuile BAC                          (hérite length)
├── Accessoires de tôlerie                 (dual)
│   ├── Solins et rives
│   ├── Faîtières et closoirs
│   └── Planches de rive
└── Tôles ondulées et laquées              (unit)
```

### Règles de vente

- **Tôle BAC (`length`)** : chaque ligne de devis/commande contient des **sous-lignes « longueur + quantité de pièces »** → `montant = Σ(qté pièces × longueur × prix/ml)`. Ex : `10×5,50 m + 20×4,50 m + 15×3,00 m = 190 m`.
- **Accessoire (`dual`)** : deux formes acceptées —
  - au ml sur mesure : sous-lignes comme une tôle BAC ;
  - à la pièce standard : `montant = quantité × unit_length × prix/ml` (ex. solin 10 pièces de 2,50 m à 1 800 F/ml = 45 000 F).
- **Validations automatiques** : coupes refusées sur un produit `unit` ; vente à la pièce refusée pour un produit `length` pur ; prix incohérent refusé à la création du produit (HTTP 400 avec message explicite).
- **Héritage** : toute nouvelle sous-catégorie créée sous « Tôles BAC » hérite automatiquement du mode `length`.

API : `GET /api/v1/catalogue/categories/tree` retourne l'arborescence avec les modes résolus (`resolved_sale_mode`, `sells_by_length`) pour les sélecteurs du frontend.

## Docker — Déploiement MVP

### 1. Préparer la configuration

```bash
cp backend/.env.example backend/.env
# Éditer backend/.env :
#   SECRET_KEY        → python -c "import secrets; print(secrets.token_urlsafe(64))"
#   FIRST_ADMIN_*     → identifiants du compte admin initial
#   DATABASE_URL      → laissé commenté : le compose force PostgreSQL
```

### 2. Lancer la stack complète

```bash
docker compose up -d --build
```

| Service | Rôle | Port hôte |
|---|---|---|
| `nginx` | Point d'entrée unique (reverse proxy) | **80** |
| `frontend` | Next.js (SSR) | interne |
| `backend` | FastAPI — applique les migrations Alembic au démarrage | interne |
| `worker` / `beat` | Celery (jobs asynchrones + planifiés) | interne |
| `db` | PostgreSQL 16 | interne |
| `redis` | Broker Celery | interne |
| `minio` | Stockage S3-compatible | 9001 (console) |

L'application est accessible sur **http://localhost** (port 80) :
- `/` → frontend Next.js
- `/api/*` → backend FastAPI (`/api/docs` pour Swagger)
- Le frontend est buildé avec `NEXT_PUBLIC_API_URL=/api/v1` (relatif → même origine, pas de CORS).

### 3. Première connexion

Au premier démarrage, le bootstrap crée automatiquement devises, entreprise,
permissions, rôles, arborescence de catégories et le compte admin défini dans
`.env`. Connectez-vous avec ces identifiants puis **changez le mot de passe**.

### 4. Migrations

- Appliquées automatiquement au démarrage du conteneur backend (`alembic upgrade head`)
- En développement : `python -m alembic upgrade head`
- Après modification des modèles : `python -m alembic revision --autogenerate -m "description"`

### 5. Checklist avant mise en production

- [ ] `SECRET_KEY` fort et unique (jamais celui du dépôt)
- [ ] Mots de passe admin/base de données robustes
- [ ] `DEBUG=false`, `ENVIRONMENT=production` (désactive CORS « * » et le mode verbeux)
- [ ] HTTPS devant nginx (TLS termination : Traefik, Certbot ou load balancer)
- [ ] Sauvegardes PostgreSQL planifiées + volume `postgres_data` persistant
- [ ] Sentry configuré (`SENTRY_DSN`) pour le suivi d'erreurs

## Documentation

- [Spécifications fonctionnelles](docs/specifications_core_v2.md)

## Licence

Propriétaire — Tous droits réservés.
