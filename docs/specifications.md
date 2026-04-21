# Portail éducatif IA — Document de spécifications

**Version 1.0** — Document de référence pour le développement avec Claude Code

---

## 1. Vision et objectifs

### 1.1 Contexte

Ce portail web a pour vocation de faciliter l'apprentissage quotidien d'élèves de classe de troisième en France, en proposant chaque jour une leçon courte suivie d'un QCM de validation, sur les sept matières principales du programme officiel.

### 1.2 Principes directeurs

Le portail repose sur quatre principes simples :

- **Régularité** : une thématique par jour, suffisamment courte pour être intégrée dans le quotidien d'un adolescent (10 minutes de lecture + 5 à 10 minutes de QCM).
- **Progressivité** : les thématiques suivent un plan annuel cohérent, aligné sur les programmes officiels du Bulletin officiel de l'Éducation nationale.
- **Autonomie** : l'élève peut consulter la leçon et passer le QCM à des moments différents de la journée, à son rythme.
- **Accompagnement parental** : les parents disposent d'une vue de suivi pour accompagner sans être intrusifs.

### 1.3 Public cible

- **Utilisateur principal** : élève en classe de troisième (14-15 ans).
- **Utilisateur secondaire** : parent accompagnant la scolarité de son enfant.
- **Utilisateur administrateur** : gestionnaire du portail (initialement, le concepteur du projet).
- **Ouverture future** : plusieurs familles et plusieurs élèves pourront utiliser la plateforme.

### 1.4 Matières couvertes

Sept matières du programme officiel de troisième :

1. Français
2. Mathématiques
3. Physique-Chimie
4. Sciences de la Vie et de la Terre (SVT)
5. Histoire
6. Géographie
7. Technologie

---

## 2. Fonctionnalités de la version 1

### 2.1 Espace élève

- Connexion sécurisée par identifiant et mot de passe.
- Tableau de bord affichant la thématique du jour.
- Lecture de la leçon du jour (environ 1500 mots, 10 minutes).
- Passage du QCM de 10 questions avec correction immédiate et explications.
- Possibilité de dissocier lecture et QCM dans la journée.
- Historique des thématiques passées, leçons et résultats.
- Questions libres à l'IA sur le contenu de la leçon du jour (avec limitation quotidienne).
- Visualisation de sa progression globale (graphiques simples).

### 2.2 Espace parent

- Connexion sécurisée, rattaché à un ou plusieurs enfants.
- Tableau de bord de suivi : thématiques terminées, scores moyens par matière, temps passé.
- Vue détaillée par jour des leçons étudiées.
- Repérage des matières en difficulté (scores systématiquement bas).
- Consultation de l'historique des questions libres posées par l'enfant.
- Rapport hebdomadaire envoyé par email (optionnel, phase ultérieure).

### 2.3 Espace administrateur

- Interface d'administration Django native.
- Gestion des familles et des utilisateurs.
- Gestion du plan annuel des thématiques.
- Visualisation et édition des leçons et QCM générés.
- Possibilité de relancer une génération de contenu.
- Tableau de bord de consommation API et coûts.

### 2.4 Hors périmètre de la version 1

Les éléments suivants sont identifiés comme intéressants mais reportés à des versions ultérieures :

- Application mobile dédiée (le portail web sera responsive, donc utilisable sur mobile).
- Notifications push ou par SMS.
- Système de badges et gamification avancée.
- Export PDF des leçons.
- Chat en direct entre élève et parent.
- Intégration avec Pronote ou d'autres ENT.
- Support multi-niveaux (seconde, quatrième, etc.).

---

## 3. Architecture technique

### 3.1 Pile technologique

**Back-end** :

- Python 3.12+
- Django 5.x
- Django REST Framework pour l'exposition de l'API
- PostgreSQL 16+ comme base de données
- Bibliothèque `anthropic` (SDK officiel) pour les appels à l'API Claude

**Front-end** :

- Vue.js 3 (Composition API)
- Vite comme outil de compilation
- Vue Router pour la navigation
- Pinia pour la gestion d'état
- Axios pour les appels HTTP
- TailwindCSS pour le style (recommandé, rapide à mettre en œuvre)

**Infrastructure** :

- Hébergement à définir (VPS, Railway ou Render)
- Gunicorn + Nginx en production
- Certificat SSL via Let's Encrypt

### 3.2 Organisation du dépôt

```
portail-educatif/
├── backend/
│   ├── portail/              (configuration Django)
│   ├── utilisateurs/         (application : familles, rôles)
│   ├── contenu/              (application : programmes, thématiques)
│   ├── progression/          (application : suivi élèves)
│   ├── ia/                   (application : intégration Claude)
│   ├── manage.py
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   ├── views/
│   │   ├── router/
│   │   ├── stores/
│   │   └── services/
│   ├── public/
│   ├── package.json
│   └── vite.config.js
├── scripts/
│   ├── importer_plan_annuel.py
│   ├── generer_lecons.py
│   └── generer_qcm.py
├── docs/
│   ├── specifications.md     (ce document)
│   ├── plan_annuel.md
│   ├── prompts_ia.md
│   └── deploiement.md
└── README.md
```

### 3.3 Séparation des responsabilités

Le front-end Vue.js et le back-end Django sont deux applications indépendantes communiquant par API REST JSON. Cette séparation offre :

- Un développement parallèle possible.
- Un déploiement indépendant (front statique sur CDN, back sur serveur).
- Une évolution future facilitée vers une application mobile utilisant la même API.

---

## 4. Modèles de données

Les modèles sont organisés par application Django. Chaque modèle est décrit avec ses champs principaux.

### 4.1 Application `utilisateurs`

**Famille**

- `nom` (chaîne)
- `date_creation` (date et heure)
- `actif` (booléen, pour désactivation sans suppression)

**Utilisateur** (étend `AbstractUser` de Django)

- Champs standards : `username`, `email`, `password`, `first_name`, `last_name`
- `role` (choix : `eleve`, `parent`, `administrateur`)
- `date_naissance` (date, optionnel)
- `niveau_scolaire` (chaîne, par défaut `3e`)
- `famille` (clé étrangère vers Famille, nullable pour admin)
- `date_creation`

### 4.2 Application `contenu`

**Matiere**

- `code` (chaîne courte : `FR`, `MATH`, `PC`, `SVT`, `HIST`, `GEO`, `TECH`)
- `nom` (chaîne : « Français », « Mathématiques », etc.)
- `couleur` (code hexadécimal pour l'affichage)
- `ordre` (entier pour tri)

**ChapitreProgramme**

- `matiere` (clé étrangère)
- `titre` (chaîne)
- `description` (texte)
- `objectifs` (texte, compétences du BO)
- `ordre_programme` (entier)

**Thematique**

- `numero_jour` (entier, 1 à 180)
- `titre` (chaîne)
- `matiere` (clé étrangère)
- `chapitre` (clé étrangère vers ChapitreProgramme)
- `objectifs_apprentissage` (texte)
- `statut` (choix : `planifiee`, `generee`, `validee`, `archivee`)
- `date_prevue` (date, optionnelle : date calendaire associée)

**Lecon**

- `thematique` (clé étrangère, relation un-à-un)
- `contenu` (texte long, Markdown)
- `mots_cles` (liste, stockée en JSONField)
- `duree_lecture_estimee` (entier, en minutes)
- `modele_ia_utilise` (chaîne)
- `date_generation` (date et heure)
- `validee_par` (clé étrangère vers Utilisateur, nullable)

**QuestionQCM**

- `thematique` (clé étrangère)
- `enonce` (texte)
- `difficulte` (entier, 1 à 3)
- `ordre` (entier, position dans le QCM)
- `explication_generale` (texte, affichée après réponse)

**Proposition**

- `question` (clé étrangère)
- `texte` (texte)
- `est_correcte` (booléen)
- `explication` (texte, affichée si la proposition est choisie)
- `ordre` (entier)

### 4.3 Application `progression`

**ProgressionLecon**

- `eleve` (clé étrangère vers Utilisateur)
- `thematique` (clé étrangère)
- `lecon_lue` (booléen)
- `date_debut_lecture` (date et heure, nullable)
- `date_fin_lecture` (date et heure, nullable)
- `temps_passe_secondes` (entier)

**TentativeQCM**

- `eleve` (clé étrangère)
- `thematique` (clé étrangère)
- `date_debut` (date et heure)
- `date_fin` (date et heure, nullable)
- `score` (entier, sur 10)
- `terminee` (booléen)

**ReponseDonnee**

- `tentative` (clé étrangère)
- `question` (clé étrangère)
- `proposition_choisie` (clé étrangère)
- `correcte` (booléen)
- `date_reponse` (date et heure)

**QuestionLibre**

- `eleve` (clé étrangère)
- `thematique` (clé étrangère, contexte de la question)
- `question` (texte)
- `reponse` (texte)
- `date` (date et heure)
- `jetons_entree` (entier)
- `jetons_sortie` (entier)

### 4.4 Application `ia`

**ConsommationAPI**

- `date` (date et heure)
- `utilisateur` (clé étrangère, nullable pour les générations système)
- `type_appel` (choix : `generation_lecon`, `generation_qcm`, `question_libre`)
- `modele` (chaîne : `claude-sonnet-4-6`, `claude-haiku-4-5`, etc.)
- `jetons_entree` (entier)
- `jetons_sortie` (entier)
- `cout_estime_euros` (décimal)

Cette table permet de suivre les coûts en temps réel et de mettre en place des alertes si besoin.

---

## 5. Parcours utilisateurs principaux

### 5.1 Parcours élève — journée type

1. L'élève se connecte sur le portail.
2. Le tableau de bord affiche la thématique du jour avec la matière, le titre, et les objectifs.
3. L'élève clique sur « Commencer la leçon » et lit le contenu (chronomètre silencieux en arrière-plan).
4. À la fin de la leçon, le bouton « Passer au QCM » est proposé, mais l'élève peut aussi fermer et revenir plus tard.
5. Au passage du QCM, chaque question est affichée une par une avec ses 4 propositions.
6. Après chaque réponse, la correction est immédiate avec l'explication.
7. À la fin du QCM, le score est affiché avec un récapitulatif des erreurs.
8. Optionnellement, l'élève peut poser des questions libres à l'IA sur la leçon (limite : 5 par jour).

### 5.2 Parcours parent — consultation hebdomadaire

1. Le parent se connecte sur son espace.
2. Le tableau de bord montre les indicateurs de la semaine : jours actifs, thématiques terminées, score moyen par matière.
3. Le parent peut cliquer sur une journée pour voir le détail (leçon lue, score au QCM, questions posées).
4. Des indicateurs visuels signalent les matières où l'enfant a des difficultés récurrentes.

### 5.3 Parcours administrateur — préparation de l'année

1. L'administrateur accède à l'interface `/admin/` de Django.
2. Il importe le plan annuel des 180 thématiques (depuis un fichier JSON ou via interface).
3. Il lance la génération en masse des leçons et QCM via une commande Django.
4. Il valide les contenus générés avant publication, éventuellement en les éditant.
5. Il surveille la consommation API dans le tableau de bord dédié.

---

## 6. API REST

### 6.1 Conventions générales

- Préfixe : `/api/v1/`
- Format : JSON en entrée et en sortie
- Authentification : par jeton (à définir précisément, probablement JWT)
- Codes HTTP standards : 200, 201, 204, 400, 401, 403, 404, 500

### 6.2 Endpoints d'authentification

- `POST /api/v1/auth/login/` : connexion par identifiant/mot de passe, retourne un jeton d'accès et un jeton de rafraîchissement.
- `POST /api/v1/auth/refresh/` : rafraîchissement du jeton d'accès.
- `POST /api/v1/auth/logout/` : déconnexion (invalidation du jeton).
- `GET /api/v1/auth/me/` : retourne les informations de l'utilisateur connecté.

### 6.3 Endpoints élève

- `GET /api/v1/eleve/thematique-du-jour/` : récupère la thématique du jour.
- `GET /api/v1/eleve/lecon/{thematique_id}/` : récupère le contenu de la leçon.
- `POST /api/v1/eleve/lecon/{thematique_id}/lue/` : marque la leçon comme lue.
- `GET /api/v1/eleve/qcm/{thematique_id}/` : récupère les questions du QCM (sans les bonnes réponses).
- `POST /api/v1/eleve/qcm/{thematique_id}/reponse/` : envoie une réponse à une question.
- `POST /api/v1/eleve/qcm/{thematique_id}/terminer/` : termine le QCM et récupère le score.
- `GET /api/v1/eleve/historique/` : liste des thématiques passées avec progression.
- `POST /api/v1/eleve/question-libre/` : pose une question libre à l'IA sur une leçon.
- `GET /api/v1/eleve/progression/` : indicateurs de progression.

### 6.4 Endpoints parent

- `GET /api/v1/parent/enfants/` : liste des enfants rattachés.
- `GET /api/v1/parent/suivi/{eleve_id}/` : tableau de bord de l'enfant.
- `GET /api/v1/parent/suivi/{eleve_id}/jour/{date}/` : détail d'une journée.
- `GET /api/v1/parent/suivi/{eleve_id}/questions-libres/` : liste des questions posées par l'enfant.

### 6.5 Sécurité des endpoints

- Les endpoints élève vérifient que l'utilisateur connecté a le rôle `eleve` et accède à ses propres données.
- Les endpoints parent vérifient que l'utilisateur connecté est parent et que l'élève consulté appartient à sa famille.
- Les endpoints admin sont protégés par le rôle `administrateur` (ou passent par l'interface Django admin).

---

## 7. Intégration de l'IA

### 7.1 Stratégie d'utilisation

L'utilisation de l'IA se décompose en deux modes distincts pour optimiser les coûts :

**Mode préparation (hors production, via Claude Code ou scripts locaux)** :

- Génération en amont des 180 leçons et 180 QCM de l'année.
- Utilisation de Claude Code (inclus dans l'abonnement) pour produire le contenu.
- Import du contenu dans la base de données via des scripts Django.
- Coût API : zéro.

**Mode production (via l'API Claude facturée à l'usage)** :

- Questions libres des élèves sur les leçons.
- Régénération ponctuelle d'un contenu à la demande de l'administrateur.
- Utilisation du modèle Claude Haiku 4.5 pour optimiser les coûts.

### 7.2 Garde-fous sur les coûts

- Limite de 5 questions libres par élève par jour.
- Mise en cache des réponses à des questions similaires (normalisation de la question, recherche par similarité).
- Limite maximale de jetons en sortie (par exemple, 500 jetons par réponse).
- Tableau de bord de consommation avec alerte à partir d'un seuil configurable.
- Possibilité de couper temporairement la fonctionnalité en cas de dépassement.

### 7.3 Prompts de génération

Les prompts détaillés seront documentés dans `docs/prompts_ia.md`. Structure générale :

**Prompt de génération de leçon** :

- Rôle : professeur certifié expérimenté en classe de troisième.
- Contexte : programme officiel du Bulletin officiel de l'Éducation nationale, cycle 4.
- Contraintes : longueur cible 1500 mots, ton clair et pédagogique, adapté à un adolescent de 14-15 ans.
- Structure demandée : introduction accrocheuse, développement en 3 à 4 parties avec sous-titres, exemples concrets, synthèse finale.
- Format : Markdown.

**Prompt de génération de QCM** :

- Entrée : contenu complet de la leçon.
- Sortie : 10 questions structurées en JSON.
- Répartition de difficulté : 3 questions faciles (rappel), 5 moyennes (application), 2 exigeantes (raisonnement).
- Chaque question : 4 propositions, une seule correcte, explication pour chacune.
- Variété des formats : définitions, calculs, analyses, cas pratiques.

**Prompt de question libre** :

- Contexte limité à la leçon du jour (injection du contenu en préambule).
- Consigne de rester dans le périmètre du niveau troisième.
- Refus poli si la question sort du cadre éducatif.

### 7.4 Sécurité et protection de la clé API

- La clé API Claude est stockée dans une variable d'environnement serveur, jamais exposée au front-end.
- Tous les appels à l'API passent par le back-end Django.
- Un utilitaire `ServiceClaude` centralise les appels et enregistre automatiquement la consommation.

---

## 8. Plan de développement

### 8.1 Phase 0 — Préparation (hors code)

- Rédaction du plan annuel complet des 180 thématiques.
- Conception et test des prompts de génération sur un échantillon pilote.
- Génération du contenu initial via Claude Code.

### 8.2 Phase 1 — Socle technique

- Initialisation du projet Django avec les applications `utilisateurs`, `contenu`, `progression`, `ia`.
- Configuration de PostgreSQL et des migrations initiales.
- Initialisation du projet Vue.js avec Vite, Vue Router, Pinia, Axios.
- Mise en place de la communication front/back via une route test.
- Configuration de l'authentification (choix JWT à confirmer).

### 8.3 Phase 2 — Gestion du contenu

- Modèles Django complets pour les programmes, thématiques, leçons, QCM.
- Interface d'administration Django configurée pour chaque modèle.
- Commandes Django pour importer le plan annuel.
- Commandes Django pour importer les leçons et QCM générés.

### 8.4 Phase 3 — Espace élève minimal

- Écran de connexion.
- Tableau de bord avec thématique du jour.
- Écran de lecture de la leçon (avec rendu Markdown).
- Écran de QCM interactif.
- Enregistrement de la progression.

### 8.5 Phase 4 — Fonctionnalités élève complémentaires

- Historique des thématiques passées.
- Questions libres à l'IA (avec limitation).
- Visualisation de la progression globale.

### 8.6 Phase 5 — Espace parent

- Authentification et rattachement aux enfants.
- Tableau de bord de suivi.
- Vue détaillée par journée.
- Consultation des questions libres.

### 8.7 Phase 6 — Mise en production

- Configuration du serveur d'hébergement choisi.
- Déploiement du back-end Django avec Gunicorn et Nginx.
- Déploiement du front-end Vue compilé.
- Certificat SSL et nom de domaine.
- Sauvegardes automatiques de la base de données.

### 8.8 Phase 7 — Ouverture multi-familles

- Interface de création de famille et d'invitation de membres.
- Gestion des inscriptions et du paiement éventuel.
- Isolation stricte des données entre familles.

---

## 9. Contraintes et principes de développement

### 9.1 Qualité du code

- Code Python conforme à PEP 8, formaté avec Black.
- Code JavaScript conforme aux conventions Vue 3 (Composition API, `<script setup>`).
- Noms de variables et de fonctions en français autorisés pour le domaine métier (éviter le franglais dans les concepts pédagogiques).
- Commentaires en français.
- Tests unitaires pour la logique métier critique (calcul de scores, vérification de permissions).

### 9.2 Sécurité

- Mots de passe hachés par Django (configuration par défaut, suffisante).
- Protection CSRF activée sur toutes les vues sensibles.
- Validation systématique des entrées côté serveur.
- Pas de données sensibles dans les logs.
- Clé API Claude et autres secrets dans des variables d'environnement (`.env` non versionné).
- HTTPS obligatoire en production.
- Respect du RGPD : consentement, droit d'accès et de suppression des données.

### 9.3 Accessibilité et confort

- Interface responsive (ordinateur, tablette, smartphone).
- Contraste de couleurs conforme aux recommandations WCAG AA.
- Navigation clavier fonctionnelle.
- Possibilité d'augmenter la taille du texte.
- Pas de sons ni d'animations excessives.

### 9.4 Performance

- Temps de chargement de page inférieur à 2 secondes en conditions normales.
- Leçons et QCM préchargés pour éviter les attentes au passage du QCM.
- Pagination ou chargement différé des historiques longs.

---

## 10. Utilisation de ce document avec Claude Code

### 10.1 Comment exploiter ce document

Ce document est conçu pour être placé dans le dossier `docs/` du dépôt et utilisé comme référence par Claude Code lors de chaque session de développement. Les bonnes pratiques :

- Au début d'une session, demander à Claude Code de lire ce document avant toute action.
- Pour chaque phase du plan de développement, ouvrir une session dédiée et indiquer la phase en cours.
- Tenir ce document à jour au fil des décisions prises, en versionnant les évolutions.

### 10.2 Exemples de prompts pour Claude Code

Quelques exemples de prompts efficaces à utiliser avec Claude Code :

- « Lis le document `docs/specifications.md` puis initialise le projet Django selon la section 8.2, phase 1. »
- « Selon la section 4.2 du document de spécifications, crée les modèles Django de l'application `contenu` avec leurs migrations. »
- « Écris la commande Django pour importer le plan annuel depuis un fichier JSON, selon la section 8.3. »

### 10.3 Documents complémentaires à produire

Ce document de spécifications sera accompagné de :

- `plan_annuel.md` : les 180 thématiques détaillées avec leurs objectifs.
- `prompts_ia.md` : les prompts complets de génération de leçons, QCM et questions libres.
- `deploiement.md` : le guide de déploiement précis une fois l'hébergement choisi.

---

*Document rédigé pour accompagner le développement du portail éducatif IA. À faire évoluer au fil du projet.*
