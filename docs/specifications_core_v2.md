# Spécifications fonctionnelles — ERP de gestion et distribution de matériaux de construction

## 1. Vision du produit

L'application est un ERP verticalisé destiné aux quincailleries, négoces, distributeurs et entreprises spécialisées dans les matériaux de construction.

L'objectif est de proposer une alternative plus simple, plus ciblée et plus modulable qu'un ERP généraliste comme Odoo, avec une forte adaptation aux réalités du commerce de matériaux de construction.

Le système doit couvrir deux modèles commerciaux principaux :

1. **Négoce avec stock** : l'entreprise achète, réceptionne, stocke puis revend les produits.
2. **Distribution sans stock** : le client commande, l'entreprise passe la commande auprès du fournisseur et le produit peut être livré directement au client sans transiter par le stock de l'entreprise.

Un troisième cas doit être géré :

3. **Mode hybride** : une partie d'une commande peut être satisfaite depuis le stock et le solde déclencher automatiquement un besoin d'achat fournisseur.

---

# 2. Principes architecturaux fondamentaux

## 2.1 Architecture complètement modulaire

L'application doit être conçue comme un ensemble de modules indépendants et démontables.

Un module doit pouvoir :

- être installé ;
- être activé ou désactivé ;
- être supprimé sans casser le reste de l'application ;
- fonctionner indépendamment des autres modules lorsque cela est fonctionnellement possible ;
- exposer des interfaces/services permettant aux autres modules de l'utiliser ;
- posséder ses propres permissions ;
- posséder ses propres paramètres ;
- posséder ses propres tables ou domaines de données lorsque cela est pertinent.

### Principe

> Aucun module métier ne doit être structurellement indispensable à tous les autres.

Exemple :

- Le module **Facturation** peut fonctionner sans le module **Stock**.
- Le module **Paiements** peut fonctionner sans le module **Livraison**.
- Le module **Livraison** peut fonctionner à partir d'une commande sans nécessiter un stock interne.
- Le module **Stock** peut fonctionner sans le module **Comptabilité complète**.
- Le module **Catalogue** constitue un socle réutilisable, mais les modules doivent éviter les dépendances fortes inutiles.

---

# 3. Architecture modulaire proposée

## 3.1 Core / Noyau

Le Core fournit uniquement les services transversaux :

- utilisateurs ;
- authentification ;
- rôles et permissions ;
- entreprises ;
- agences ;
- paramètres généraux ;
- devise ;
- taxes ;
- numérotation des documents ;
- journalisation ;
- notifications ;
- configuration ;
- API ;
- système de modules ;
- événements internes.

Le Core ne doit pas contenir de logique métier spécifique à la vente ou au stock.

---

## 3.2 Module Catalogue / Produits

Gestion centralisée des produits et services.

Un produit peut avoir :

- référence/SKU ;
- code-barres ;
- désignation ;
- description ;
- catégorie ;
- marque ;
- unité de mesure ;
- unités d'achat et de vente ;
- coefficient de conversion ;
- prix d'achat ;
- prix de vente ;
- prix par client ou catégorie de client ;
- fournisseur principal ;
- fournisseurs alternatifs ;
- délai d'approvisionnement ;
- seuil de stock ;
- stockable ou non stockable ;
- vendu à l'unité ou selon une longueur/quantité variable ;
- paramètres spécifiques à la famille de produit.

### Types de produits

Le système doit au minimum gérer :

- produit stocké ;
- produit non stocké / sur commande ;
- produit hybride ;
- service.

### Produit stocké

Le produit est physiquement géré dans les entrepôts de l'entreprise.

### Produit sur commande

Le produit est commercialisé sans obligation de possession en stock.

Une vente peut déclencher un besoin d'achat fournisseur.

### Produit hybride

Le produit peut être satisfait partiellement ou totalement par le stock, puis complété par un achat fournisseur.

---

# 4. Module Clients / CRM

Gestion :

- particuliers ;
- entreprises ;
- professionnels ;
- contacts ;
- adresses ;
- chantiers ;
- historique commercial ;
- devis ;
- commandes ;
- factures ;
- paiements ;
- créances ;
- limites de crédit ;
- conditions commerciales.

## 4.1 Gestion des chantiers

Un client peut posséder plusieurs chantiers.

Exemple :

- Client : Entreprise ABC
- Chantier : Cocody
- Chantier : Bingerville
- Chantier : Yopougon

Un chantier peut être associé à :

- devis ;
- commandes ;
- livraisons ;
- factures ;
- paiements ;
- produits ;
- marges ;
- documents.

---

# 5. Module Ventes

Le cycle de vente doit pouvoir fonctionner indépendamment du stock.

Workflow principal :

**Prospect/Client → Devis → Commande → Facturation → Paiement → Livraison**

Mais chaque étape doit pouvoir être utilisée séparément selon les besoins.

Fonctionnalités :

- devis ;
- commandes ;
- ventes comptoir ;
- lignes de vente ;
- remises ;
- prix négociés ;
- acomptes ;
- paiements partiels ;
- factures ;
- avoirs ;
- retours ;
- bons de livraison ;
- conditions de vente ;
- validité du devis ;
- suivi du statut.

---

# 6. Gestion spécifique des tôles BAC

## 6.1 Particularité métier

Les tôles BAC peuvent être commandées avec plusieurs longueurs différentes dans un même devis ou une même facture.

Exemple :

- 10 feuilles de 5,50 m ;
- 20 feuilles de 4,50 m ;
- 15 feuilles de 3,00 m.

Il ne faut donc pas considérer la ligne comme une simple quantité × prix unitaire.

## 6.2 Nomenclature des tôles BAC

Une tôle BAC doit pouvoir être définie avec notamment :

- profil ;
- matière ;
- épaisseur ;
- largeur utile ;
- largeur totale ;
- couleur ;
- finition ;
- longueur ;
- unité de vente ;
- coût unitaire par mètre ou unité de calcul ;
- prix de vente ;
- fournisseur.

## 6.3 Lignes multi-longueurs

Une ligne de devis/facture de tôle BAC peut contenir plusieurs sous-lignes de coupe.

Exemple :

| Quantité | Longueur | Calcul |
|---:|---:|---:|
| 10 | 5,50 m | 10 × 5,50 |
| 20 | 4,50 m | 20 × 4,50 |
| 15 | 3,00 m | 15 × 3,00 |

La quantité facturable en longueur totale est :

**(10 × 5,50) + (20 × 4,50) + (15 × 3,00)**

Soit :

**55 + 90 + 45 = 190 mètres**

Si le coût/prix unitaire est de **X FCFA/mètre** :

**Montant = 190 × X**

## 6.4 Formule générale

Pour chaque sous-ligne :

**Montant sous-ligne = Quantité × Longueur × Prix unitaire**

Total de la ligne :

**Montant total = Σ(Quantité × Longueur × Prix unitaire)**

Le système doit conserver séparément :

- quantité ;
- longueur unitaire ;
- longueur totale ;
- prix unitaire ;
- montant de la sous-ligne ;
- montant total.

## 6.5 Affichage sur devis et facture

Le document doit pouvoir afficher :

**Tôle BAC — Profil X**

- 10 × 5,50 m
- 20 × 4,50 m
- 15 × 3,00 m

**Total : 190 mètres**

Le client doit pouvoir comprendre clairement comment le montant a été calculé.

## 6.6 Découpe et commande fournisseur

Lorsqu'une commande de tôle BAC est destinée à un fournisseur, les longueurs doivent être transmises individuellement.

Exemple :

**Commande fournisseur**

- BAC Profil X — 10 × 5,50 m
- BAC Profil X — 20 × 4,50 m
- BAC Profil X — 15 × 3,00 m

Le système ne doit jamais perdre le détail des longueurs lors du passage du devis vers la commande, puis vers la livraison ou la facture.

---

# 7. Module Stock

Le module stock doit être indépendant.

Fonctionnalités :

- entrepôts ;
- magasins ;
- emplacements ;
- entrées ;
- sorties ;
- transferts ;
- réservations ;
- inventaires ;
- ajustements ;
- pertes ;
- produits endommagés ;
- mouvements ;
- historique ;
- stock disponible ;
- stock réservé ;
- stock réel ;
- stock virtuel ;
- seuils d'alerte ;
- valorisation.

## 7.1 Unités de mesure

Le stock doit supporter des unités différentes selon le produit.

Exemples :

- sac ;
- pièce ;
- barre ;
- mètre ;
- kilogramme ;
- litre ;
- rouleau ;
- carton ;
- palette ;
- feuille.

Le système doit permettre les conversions :

**1 palette = 50 sacs**

**1 rouleau = 100 mètres**

etc.
Le système doit permettre les ajouts de nouvelles unités de mesures et la modification de unités de produits déjà créés

---

# 8. Approvisionnement et achats

Le module Achats doit pouvoir fonctionner avec ou sans Stock.

Fonctionnalités :

- fournisseurs ;
- demandes de prix ;
- commandes fournisseurs ;
- lignes d'achat ;
- réceptions ;
- factures fournisseurs ;
- paiements fournisseurs ;
- prix d'achat ;
- délais ;
- fournisseurs alternatifs.

## 8.1 Génération des besoins

Une commande client peut générer automatiquement un besoin d'achat.

Exemple :

Commande client :

- 500 sacs de ciment ;
- stock disponible : 100.

Besoin fournisseur :

**400 sacs**

Le système doit distinguer :

- quantité commandée par le client ;
- quantité disponible en stock ;
- quantité réservée ;
- quantité à acheter ;
- quantité déjà commandée au fournisseur ;
- quantité restante à approvisionner.

---

# 9. Distribution sans stock

Le mode distribution doit être une fonctionnalité native.

Workflow :

**Client → Commande client → Besoin d'achat → Commande fournisseur → Livraison directe**

Le produit peut ne jamais entrer dans le stock de l'entreprise.

## 9.1 Livraison directe

Le système doit permettre :

**Fournisseur → Client**

sans mouvement physique dans l'entrepôt de l'entreprise.

La commande doit conserver la traçabilité :

- client ;
- fournisseur ;
- commande client ;
- commande fournisseur ;
- produit ;
- quantité ;
- prix fournisseur ;
- prix client ;
- marge ;
- livraison ;
- statut.

---

# 10. Mode hybride

Le moteur d'approvisionnement doit gérer automatiquement les commandes mixtes.

Exemple :

Commande client :

- 100 sacs de ciment ;
- 50 barres de fer ;
- 30 tôles BAC.

Disponibilité :

- ciment : 80 en stock ;
- fer : 50 en stock ;
- tôles BAC : 0 en stock.

Le système crée :

### Stock

- ciment : réservation de 80 ;
- fer : réservation de 50.

### Besoins d'achat

- ciment : 20 ;
- tôles BAC : 30.

Le système doit permettre de transformer les besoins en commandes fournisseurs.

---

# 11. Module Livraison

Le module Livraison doit être indépendant du Stock.

Une livraison peut provenir :

- du stock interne ;
- d'une commande fournisseur ;
- d'une livraison directe fournisseur → client.

Gestion :

- bon de livraison ;
- adresse ;
- chantier ;
- véhicule ;
- chauffeur ;
- date prévue ;
- date réelle ;
- produits ;
- quantités ;
- statut ;
- frais de transport ;
- preuve de livraison ;
- signature ;
- photo éventuelle.

---

# 12. Module Paiements

Le module Paiements doit être indépendant de la facturation.

Il doit pouvoir enregistrer :

- paiement client ;
- acompte ;
- paiement partiel ;
- solde ;
- remboursement ;
- paiement fournisseur ;
- caisse ;
- banque ;
- moyens de paiement.

Moyens configurables :

- espèces ;
- virement ;
- chèque ;
- carte ;
- Mobile Money ;
- autres.

Le système doit permettre d'associer un paiement à :

- une facture ;
- une commande ;
- un client ;
- un fournisseur ;
- un chantier ;
- une caisse ;
- un compte bancaire.

---

# 13. Module Facturation

Le module Facturation doit fonctionner indépendamment du Stock.

Fonctionnalités :

- factures ;
- factures d'acompte ;
- factures partielles ;
- factures finales ;
- avoirs ;
- échéances ;
- taxes ;
- remises ;
- conditions de paiement ;
- numérotation ;
- PDF ;
- envoi du document.

Une facture ne doit pas nécessairement provoquer un mouvement de stock.

---

# 14. Module Finance / Trésorerie

Le module doit couvrir dans un premier temps :

- caisses ;
- comptes bancaires ;
- recettes ;
- dépenses ;
- créances ;
- dettes ;
- échéances ;
- rapprochement des paiements ;
- suivi de trésorerie ;
- marge.

La comptabilité générale complète peut être ajoutée comme module indépendant ultérieurement.

---

# 15. Module Reporting / BI

Tableau de bord configurable.

Indicateurs :

- chiffre d'affaires ;
- marge brute ;
- ventes ;
- achats ;
- stock ;
- rotation des stocks ;
- créances ;
- dettes ;
- commandes en cours ;
- commandes fournisseurs ;
- livraisons ;
- produits les plus vendus ;
- produits à faible rotation ;
- clients les plus rentables ;
- fournisseurs les plus utilisés.

Les tableaux de bord doivent être dépendants uniquement des données disponibles dans les modules installés.

---

# 16. Gestion des marges

Le système doit calculer :

### Marge prévisionnelle

Lors du devis :

**Prix de vente - coût d'achat prévu**

### Marge réelle

Après achat/réception/facture fournisseur :

**Prix de vente réel - coût réel**

Pour une tôle BAC :

**Marge = montant de vente - coût réel des longueurs commandées**

Le coût doit pouvoir être calculé à partir de :

**Σ(Quantité × Longueur × coût unitaire)**

---

# 17. Workflow générique de commande

## 17.1 Vente avec stock

**Devis**

↓

**Commande**

↓

**Réservation stock**

↓

**Préparation**

↓

**Livraison**

↓

**Facturation**

↓

**Paiement**

---

## 17.2 Vente sans stock

**Devis**

↓

**Commande**

↓

**Besoin d'achat**

↓

**Commande fournisseur**

↓

**Livraison directe**

↓

**Facturation**

↓

**Paiement**

---

## 17.3 Vente hybride

**Commande**

↓

**Analyse disponibilité**

↓

**Réservation stock**

+

**Création besoin d'achat**

↓

**Approvisionnement**

↓

**Livraison**

↓

**Facturation**

↓

**Paiement**

---

# 18. Système d'événements inter-modules

Pour préserver l'indépendance des modules, les communications doivent privilégier des événements métier.

Exemples :

- `sales.order.created`
- `sales.order.confirmed`
- `inventory.stock.reserved`
- `inventory.stock.released`
- `purchase.need.created`
- `purchase.order.created`
- `purchase.receipt.completed`
- `delivery.created`
- `delivery.completed`
- `invoice.created`
- `payment.received`

Un module peut écouter un événement sans être directement couplé à l'implémentation interne du module émetteur.

---

# 19. Dépendances fonctionnelles

Les dépendances doivent être minimisées.

### Core

Aucune dépendance métier.

### Catalogue

Dépend principalement du Core.

### Clients

Dépend principalement du Core.

### Ventes

Peut utiliser Catalogue et Clients.

### Stock

Peut utiliser Catalogue.

### Achats

Peut utiliser Catalogue et Fournisseurs.

### Livraison

Peut utiliser les données de commande, mais ne doit pas dépendre obligatoirement du Stock.

### Facturation

Peut fonctionner à partir d'une commande ou être créée indépendamment.

### Paiements

Peut fonctionner indépendamment d'une facture.

### Reporting

Consomme les données disponibles sans imposer l'installation de tous les modules.

---

# 20. Principe de suppression d'un module

La suppression d'un module ne doit pas entraîner automatiquement la suppression des données fondamentales des autres modules.

Exemple :

Si le module Stock est désactivé :

- les produits restent disponibles ;
- les clients restent disponibles ;
- les fournisseurs restent disponibles ;
- les devis restent disponibles ;
- les factures restent disponibles ;
- les paiements restent disponibles.

Les fonctionnalités nécessitant le Stock deviennent simplement indisponibles ou sont remplacées par un comportement adapté.

---

# 21. Multi-entreprises et multi-sites

Prévoir dès l'architecture :

- plusieurs entreprises ;
- plusieurs agences ;
- plusieurs magasins ;
- plusieurs entrepôts ;
- plusieurs caisses ;
- utilisateurs par agence ;
- permissions par rôle ;
- permissions par entreprise ;
- données isolées par entreprise.

---

# 22. Sécurité et traçabilité

Chaque action importante doit être journalisée :

- utilisateur ;
- date ;
- heure ;
- action ;
- ancien état ;
- nouvel état ;
- document concerné.

Les opérations sensibles doivent être protégées :

- suppression ;
- modification de prix ;
- remise exceptionnelle ;
- annulation de facture ;
- validation de paiement ;
- sortie de stock ;
- modification d'un coût d'achat.

---

# 23. Vision évolutive

Le produit doit pouvoir évoluer progressivement vers :

- comptabilité complète ;
- POS ;
- application mobile ;
- portail client ;
- portail fournisseur ;
- commandes en ligne ;
- catalogue B2B ;
- intégration WhatsApp ;
- intégration Mobile Money ;
- gestion des chauffeurs ;
- géolocalisation ;
- BI avancée ;
- prévisions de stock ;
- recommandations d'achat ;
- IA commerciale ;
- marketplace B2B.

---

# 24. Philosophie produit

L'ERP doit respecter cinq principes :

1. **Simple** : une quincaillerie ne doit pas avoir besoin d'un consultant pour faire une vente.
2. **Modulaire** : l'entreprise paie et active uniquement ce dont elle a besoin.
3. **Métier** : les workflows doivent refléter la réalité des négoces de matériaux.
4. **Évolutif** : l'architecture doit permettre l'ajout de modules sans refonte du Core.
5. **Data-driven** : chaque transaction doit pouvoir alimenter les indicateurs de pilotage.

## Positionnement

> **Un ERP modulaire spécialisé dans la gestion, le négoce et la distribution des matériaux de construction, capable de gérer aussi bien le commerce avec stock que la vente sur commande fournisseur.**
---

# 25. Sauvegarde et restauration

Le Core doit intégrer un système de sauvegarde cloud permettant de protéger les données de l'ERP et de restaurer l'environnement en cas de perte, corruption ou incident.

## 25.1 Principe

Le système doit permettre :
- sauvegarde locale en temps réel ;
- sauvegarde manuelle ;
- sauvegarde automatique en temps réel par actualisation/modification d'une donnée ;
- sauvegarde complète et incrémentale lorsque possible ;
- restauration complète ;
- historique et versions ;
- vérification d'intégrité ;
- chiffrement avant transfert ;
- gestion de plusieurs destinations ;
- notifications du résultat.

## 25.2 Fournisseurs

Le système doit utiliser une couche d'abstraction permettant de connecter différents fournisseurs cloud, notamment :
- Google Drive ;
- Dropbox ;
- Microsoft OneDrive ;
- iCloud Drive, sous réserve des API officiellement disponibles ;
- Amazon S3 ;
- tout autre fournisseur compatible avec les API/protocoles de stockage supportés.

L'ajout d'un fournisseur ne doit pas nécessiter de modifier les modules métier.

## 25.3 Configuration

L'administrateur doit pouvoir connecter un compte cloud, choisir le dossier de destination, définir la fréquence et la rétention, sélectionner les données à sauvegarder, lancer une sauvegarde immédiate et restaurer une version.

## 25.4 Sécurité

Les sauvegardes doivent utiliser des connexions sécurisées, OAuth ou le mécanisme officiel du fournisseur, ne pas exposer les identifiants et journaliser les opérations.

---

# 26. Génération automatique des documents PDF

Le système doit disposer d'un moteur centralisé de génération PDF indépendant des modules métier.

Documents concernés notamment :
- devis ;
- commandes ;
- factures ;
- avoirs ;
- bons de livraison ;
- bons de commande fournisseur ;
- reçus ;
- rapports ;
- états de stock ;
- états financiers ;
- rapports commerciaux et de livraison.

La génération peut être déclenchée automatiquement par un événement : validation de devis, confirmation de commande, création de facture, livraison, paiement ou génération planifiée d'un rapport.

Le PDF peut ensuite être téléchargé, imprimé, envoyé, partagé, archivé ou sauvegardé dans le cloud.

---

# 27. Designer No-Code de documents

Le Core doit intégrer un éditeur visuel permettant de créer et personnaliser les modèles de documents sans programmation.

L'utilisateur construit son document par glisser-déposer de blocs.

L'éditeur doit permettre :
- ajout, déplacement, redimensionnement et suppression de blocs ;
- duplication ;
- alignement ;
- marges et espacements ;
- typographie et couleurs ;
- bordures et arrière-plans ;
- insertion d'images et logos ;
- insertion de textes et champs dynamiques ;
- tableaux ;
- signatures ;
- QR Codes et codes-barres ;
- en-têtes, pieds de page et pagination ;
- aperçu en temps réel.

---

# 28. Bibliothèque de blocs

## 28.1 Blocs génériques

- texte ;
- titre ;
- image ;
- logo ;
- ligne ;
- séparateur ;
- tableau ;
- signature ;
- QR Code ;
- code-barres ;
- pied de page ;
- pagination ;
- bloc libre.

## 28.2 Blocs métier

- informations entreprise ;
- informations client ;
- informations fournisseur ;
- adresse de facturation ;
- adresse de livraison ;
- informations chantier ;
- numéro du document ;
- date ;
- conditions de paiement ;
- tableau des produits ;
- sous-total ;
- remise ;
- livraison ;
- taxes ;
- Total HT ;
- Total TTC ;
- montant payé ;
- reste à payer ;
- coordonnées bancaires ;
- moyens de paiement ;
- notes ;
- conditions générales.

---

# 29. Modèle de facture personnalisable

## 29.1 En-tête

Le bloc d'en-tête doit pouvoir contenir :
- logo ;
- nom/raison sociale ;
- adresse ;
- téléphone ;
- e-mail ;
- site web ;
- numéro fiscal ;
- registre de commerce ;
- autres informations légales.

## 29.2 Informations client

Le modèle doit pouvoir afficher :
- nom du client ;
- entreprise ;
- téléphone ;
- e-mail ;
- adresse de facturation ;
- adresse de livraison ;
- adresse du chantier ;
- identifiants fiscaux lorsque disponibles.

Les adresses de facturation et de livraison doivent pouvoir être différentes.

## 29.3 Bloc de facturation

Le tableau doit être personnalisable avec notamment :
- référence ;
- désignation ;
- description ;
- quantité ;
- unité ;
- longueur ;
- prix unitaire ;
- remise ;
- taxe ;
- Total HT ;
- Total TTC.

Les colonnes peuvent être ajoutées, supprimées, réordonnées, renommées, redimensionnées ou masquées.

## 29.4 Taxes

Les taxes sont configurables dans les paramètres :
- activation/désactivation ;
- plusieurs taxes ;
- taux ;
- exonération légale ;
- affichage/masquage ;
- application par produit, client ou document.

Exemples : TVA, exonération légale, autres taxes configurables.

## 29.5 Remises

La remise peut être activée ou désactivée dans les paramètres.

Elle peut être appliquée :
- par ligne ;
- au document ;
- en pourcentage ;
- en montant fixe.

Lorsque la remise est désactivée, les éléments correspondants ne doivent pas apparaître dans le document.

---

# 30. Bloc Total

Le designer doit permettre d'insérer un bloc récapitulatif comprenant :
- Total HT ;
- Remise ;
- Livraison ;
- Taxes ;
- Exonération légale ;
- TVA ;
- autres taxes ;
- Total TTC ;
- montant payé ;
- reste à payer.

Chaque élément doit pouvoir être affiché/masqué, réordonné et personnalisé graphiquement.

---

# 31. Interface d'édition No-Code

Chaque bloc sélectionné doit disposer d'une barre d'outils ou d'un panneau de propriétés.

Actions :
- modifier ;
- déplacer ;
- copier ;
- dupliquer ;
- supprimer ;
- verrouiller ;
- masquer/afficher ;
- aligner ;
- redimensionner.

Les propriétés doivent être éditables sans code.

## 31.1 Champs dynamiques

L'utilisateur doit pouvoir insérer les champs dynamiques depuis une liste visuelle, sans connaître leur syntaxe technique.

Exemples de champs :
- entreprise ;
- client ;
- numéro de facture ;
- date ;
- Total HT ;
- Total TTC ;
- taxes ;
- remise ;
- montant payé ;
- reste à payer.

---

# 32. Templates et bibliothèque de modèles

Le système doit permettre :
- plusieurs modèles ;
- duplication ;
- modification ;
- suppression ;
- activation/désactivation ;
- modèle par défaut ;
- modèle par type de document ;
- modèle par entreprise/agence ;
- import/export de modèles.

Exemples : facture standard, facture premium, devis, bon de livraison, reçu, rapport de stock.

---

# 33. Aperçu et prévisualisation

Le designer doit proposer un aperçu en temps réel et un bouton de prévisualisation PDF.

L'utilisateur doit pouvoir :
- visualiser les pages ;
- tester avec des données fictives ;
- vérifier les montants ;
- vérifier les sauts de page ;
- vérifier les longueurs des tôles BAC ;
- visualiser le rendu final.

---

# 34. Gestion avancée des pages

Le moteur documentaire doit gérer :
- A4 ;
- A5 ;
- formats personnalisés ;
- portrait/paysage ;
- marges ;
- en-tête et pied de page ;
- pagination ;
- répétition de l'en-tête des tableaux ;
- sauts de page ;
- blocs conditionnels ;
- documents multi-pages.

Les tableaux de facturation doivent continuer automatiquement sur les pages suivantes.

---

# 35. Conditions d'affichage des blocs

Un bloc peut être affiché conditionnellement.

Exemples :
- TVA uniquement lorsqu'elle est applicable ;
- remise uniquement lorsqu'elle existe ;
- adresse de livraison uniquement lorsqu'elle est différente ;
- reste à payer uniquement si la facture n'est pas soldée ;
- exonération uniquement pour un client exonéré ;
- chantier uniquement lorsqu'il est associé.

Cette logique doit être configurable depuis l'interface No-Code.

---

# 36. Rapports automatiques

Le système doit permettre de créer des rapports programmés :
- ventes quotidiennes ;
- ventes hebdomadaires ;
- chiffre d'affaires mensuel ;
- marge ;
- stock ;
- créances ;
- dettes ;
- achats ;
- produits à faible rotation.

L'utilisateur définit :
- période ;
- filtres ;
- indicateurs ;
- modèle PDF ;
- destinataires ;
- fréquence ;
- heure d'envoi ;
- format.

Les rapports peuvent être automatiquement générés en PDF, archivés, envoyés par e-mail et sauvegardés dans le cloud.

---

# 37. Architecture du moteur documentaire

Le moteur documentaire reste indépendant des modules métier.

Flux :

**Données métier → Moteur documentaire → Template → PDF → Archivage / Envoi / Cloud**

Les modules métier fournissent les données ; le moteur documentaire récupère les données, sélectionne le modèle, applique les règles d'affichage, construit le document, génère le PDF et déclenche l'archivage ou l'envoi.

---

# 38. Extension du Core

Le Core fournit désormais :
- utilisateurs ;
- authentification ;
- rôles et permissions ;
- entreprises ;
- agences ;
- paramètres ;
- devise ;
- taxes ;
- numérotation ;
- journalisation ;
- notifications ;
- API ;
- système de modules ;
- événements internes ;
- stockage de fichiers ;
- sauvegarde cloud ;
- moteur documentaire PDF ;
- designer No-Code ;
- bibliothèque de templates ;
- archivage documentaire.

Les modules métier restent séparés :
- Catalogue ;
- Clients / CRM ;
- Ventes ;
- Stock ;
- Achats ;
- Livraison ;
- Facturation ;
- Paiements ;
- Finance ;
- Reporting / BI.

---

# 39. Indépendance des nouvelles fonctionnalités

Les nouvelles fonctionnalités doivent respecter la modularité :
- le moteur PDF ne dépend pas du Stock ;
- le designer ne dépend pas de la Facturation ;
- le stockage cloud ne dépend pas des Ventes ;
- la sauvegarde cloud ne dépend pas du moteur PDF ;
- le reporting peut utiliser le moteur PDF sans imposer tous les modules métier.

Le Core fournit les services génériques et les modules métier les exploitent.

---

# 40. Vision du Core

Le Core constitue la plateforme technique stable sur laquelle les modules métier sont branchés.

Architecture conceptuelle :

**CORE**
- Identity & Access
- Configuration
- Multi-entreprise
- Permissions
- Events
- Notifications
- File Storage
- Cloud Backup
- Document Engine
- No-Code Designer
- Templates
- PDF Engine
- Audit Log
- API

**MODULES MÉTIER**
- Catalogue
- CRM
- Ventes
- Stock
- Achats
- Livraison
- Facturation
- Paiements
- Finance
- Reporting / BI

Cette séparation doit permettre de développer, tester, installer, désactiver et faire évoluer chaque domaine indépendamment.
