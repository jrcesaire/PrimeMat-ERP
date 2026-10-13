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
- Stock (entrepôts, mouvements, seuils)
- Achats (fournisseurs, bons de commande, réceptions)
- Livraison (bons de livraison, transport)
- Facturation (factures, avoirs, PDF)
- Paiements (espèces, virement, chèque, Mobile Money)
- Finance / Trésorerie
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

### 🚧 Modules à venir
Achats, Livraison, Facturation, Paiements, Finance, Reporting — squelettes en place, routeurs chargés dynamiquement.

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
