# Document de Spécification des Exigences Produit (PRD)

**Projet :** Amélioration du Module Point de Vente (PoS) – Introduction des Sessions de Caisse et Refonte UI/UX  
**Version :** 1.0  
**Date :** 25 Octobre 2026  
**Statut :** En cours de validation

---

## 1. Résumé Exécutif

Ce document décrit les améliorations fonctionnelles et ergonomiques à apporter au module PoS de l'ERP actuel. L'objectif principal est d'introduire une gestion rigoureuse des "Sessions de Caisse" journalières pour améliorer la traçabilité financière, tout en refondant l'interface utilisateur pour offrir une expérience "Plein Écran" immersive, distincte du reste de l'ERP.

## 2. Objectifs

* **Fiabilité Financière :** Assurer un suivi précis des flux de trésorerie via des sessions journalières fermées automatiquement.
* **Expérience Utilisateur (UX) :** Simplifier l'accès aux fonctions critiques du PoS en isolant l'interface de vente du reste de l'ERP (mode immersif).
* **Centralisation :** Regrouper les paramètres spécifiques au PoS et faciliter la navigation entre la vente, le catalogue et l'historique.

## 3. Portée (Scope)

### Inclus (In-Scope)

* Logique backend et frontend pour la création, gestion et clôture automatique des "Sessions de Caisse".
* Refonte de l'écran d'accueil du module PoS (Menu Principal).
* Modification du comportement de l'interface (Mode Plein Écran / Immersif).
* Intégration des achats de quincaillerie dans le flux global des achats.

### Exclus (Out-of-Scope)

* Modification des algorithmes de calcul de taxes ou de TVA existants.
* Changements majeurs sur le module de comptabilité générale (sauf l'incrémentation des achats mentionnée).

---

## 4. Spécifications Fonctionnelles Détaillées

### 4.1. Gestion des Sessions de Caisse

#### 4.1.1. Définition

Une "Session de Caisse" représente l'ensemble des transactions comptoir effectuées sur une période de 24 heures (cycle journalier).

#### 4.1.2. Cycle de Vie de la Session

1. **Ouverture :** Une nouvelle session démarre automatiquement lors de la première action de vente de la journée ou manuellement par l'utilisateur autorisé.
2. **Solde Initial (Fonds de Caisse) :** Le solde disponible au début d'une nouvelle session est égal au solde final de la session précédente.
   * *Note :* Lors de la toute première utilisation du système, le solde initial doit être défini manuellement ou par défaut à 0.
3. **Clôture Automatique :** La session se ferme automatiquement à la fin de la journée (minuit ou heure configurée dans les réglages).
4. **Rapport de Clôture :** À la fermeture, un état récapitulatif est généré avec le solde disponible total.

#### 4.1.3. Règles Métier

* Il ne peut y avoir qu'une seule session active par point de vente/caisse à un instant T.
* Les ventes réalisées sont directement liées à l'ID de la session active.

### 4.2. Interface Utilisateur (UI) & Navigation

#### 4.2.1. Mode Immersif (Full Screen)

* **Comportement :** Lorsque l'utilisateur clique sur l'onglet "PoS" dans la barre de navigation principale de l'ERP, l'interface bascule en mode plein écran.
* **Masquage :** La barre latérale (Sidebar) standard de l'ERP doit être masquée pour maximiser l'espace de travail.
* **Sortie du Mode :** Un bouton "Quitter" accompagné d'une icône de sortie doit être visible en haut à gauche (Top-Left) de l'écran PoS.
  * **Action :** Cliquer sur ce bouton ferme l'interface PoS et ramène l'utilisateur à l'interface standard de l'ERP (avec la Sidebar visible).

#### 4.2.2. Écran d'Accueil du PoS (Dashboard)

Lors de l'accès au module PoS, l'utilisateur arrive sur un menu centralisé.

* **Disposition :** Les éléments doivent être centrés horizontalement et verticalement sur l'écran.
* **Padding Global :** L'ensemble du contenu du menu doit respecter une marge interne (padding) de 80px à droite et 80px à gauche.
* **Éléments du Menu (Boutons) :**
  1. **+ Nouvelle Vente :** Bouton existant, déplacé au centre. *Action :* Lance le processus de scan/saisie de produits.
  2. **Historique des Ventes :** Accès à la liste des transactions de la session en cours et des sessions précédentes.
  3. **Ajout de Produits :** Permet d'ajouter rapidement un nouveau produit au catalogue depuis l'interface PoS.
  4. **Modifier Catalogue :** Accès à la gestion complète des articles (prix, stocks, catégories).
  5. **Achats :**
     * *Contexte :* Dédié aux achats de fournitures/quincaillerie nécessaires au fonctionnement ou à la revente immédiate.
     * *Intégration :* Ces achats s'incrémentent dans le module "Achats Globaux" de l'entreprise pour une consolidation comptable correcte.
  6. **Réglages :** Menu regroupant exclusivement les paramètres liés au PoS (ex : configuration imprimante ticket, taux de remise max, gestion des caissiers, horaires d'ouverture).

---

## 5. Spécifications Techniques & UX

### 5.1. Maquette Wireframe (Description Textuelle)

```text
+-----------------------------------------------------------------------+
| [X Quitter]                                        (Logo/Info Caisse) |
|                                                                       |
|                                                                       |
|                    +-----------------------------+                    |
|                    | + Nouvelle Vente            |                    |
|                    +-----------------------------+                    |
|                                                                       |
|                    +-----------------------------+                    |
|                    | Historique des Ventes       |                    |
|                    +-----------------------------+                    |
|                                                                       |
|                    +-----------------------------+                    |
|                    | Ajout de Produits           |                    |
|                    +-----------------------------+                    |
|                                                                       |
|                    +-----------------------------+                    |
|                    | Modifier Catalogue          |                    |
|                    +-----------------------------+                    |
|                                                                       |
|                    +-----------------------------+                    |
|                    | Achats                      |                    |
|                    +-----------------------------+                    |
|                                                                       |
|                    +-----------------------------+                    |
|                    | Réglages                    |                    |
|                    +-----------------------------+                    |
|                                                                       |
|                                                                       |
+-----------------------------------------------------------------------+
<-- 80px Padding Left -->                    <-- 80px Padding Right -->
```

### 5.2. Comportement Responsive

* L'interface doit rester utilisable sur tablettes, mais le padding de 80px peut être réduit à 20px sur les écrans de largeur inférieure à 768px pour préserver l'espace utile.

### 5.3. Persistance des Données

* Le solde de caisse doit être persistant et sécurisé. Toute modification manuelle du solde (ajout/retrait de fonds hors vente) doit être journalisée avec l'ID de l'utilisateur et l'horodatage.

---

## 6. Critères d'Acceptation (User Stories)

| ID | En tant que... | Je veux... | Afin de... | Critère d'acceptation |
|----|----------------|------------|------------|-----------------------|
| US1 | Caissier | Voir l'interface PoS en plein écran sans la sidebar | Me concentrer uniquement sur la vente | La sidebar disparaît lors de l'entrée dans le module PoS. |
| US2 | Caissier | Quitter facilement le mode PoS | Retourner à la gestion administrative de l'ERP | Le bouton "Quitter" en haut à gauche fonctionne et restaure l'interface normale. |
| US3 | Gérant | Que la session de caisse se ferme automatiquement le soir | Avoir un rapport journalier fiable sans oubli humain | À 00:00 (ou heure config), la session passe au statut "Clôturée" et le solde est figé. |
| US4 | Gérant | Que la nouvelle session commence avec le solde de la veille | Éviter de ressaisir le fond de caisse manuellement chaque matin | Le solde initial de la session J+1 = Solde final de la session J. |
| US5 | Employé | Accéder aux achats de quincaillerie depuis le PoS | Gérer les ruptures de stock urgentes sans changer de module | Les achats saisis ici apparaissent dans le grand livre des achats de l'entreprise. |
| US6 | Designer UI | Respecter les marges de 80px | Assurer une esthétique aérée et centrée | Inspection CSS confirme `padding-left: 80px; padding-right: 80px;` sur le conteneur du menu. |

---

## 7. Annexes & Notes

* **Sécurité :** L'accès au bouton "Réglages" et à la clôture manuelle anticipée d'une session doit être restreint aux rôles "Administrateur" ou "Gérant".
* **Performance :** Le chargement de l'historique des ventes ne doit pas impacter la fluidité de l'écran d'accueil (chargement asynchrone recommandé).
* **Traçabilité :** Chaque session de caisse doit avoir un identifiant unique (ex : `SESSION-20261025-001`) pour faciliter les audits et la recherche dans l'historique.
* **Gestion des erreurs :** En cas de crash ou de déconnexion pendant une session, le système doit permettre de reprendre la session en cours au redémarrage sans perte de données.
