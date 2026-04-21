# Portail éducatif IA

Portail web d'apprentissage quotidien pour élève de troisième (France), avec leçon du jour et QCM générés par Claude, couvrant les 7 matières du programme officiel.

Voir [docs/specifications.md](docs/specifications.md) pour le cahier des charges complet.

## Architecture

- **Back-end** : Django 5 + Django REST Framework, PostgreSQL (SQLite en dev).
- **Front-end** : Vue 3 + Vite + Pinia + Vue Router + Tailwind.
- **IA** : SDK `anthropic` (Claude), génération hors-ligne via Claude Code, API Haiku en prod.

```
portail-educatif/
├── backend/        Django : utilisateurs, contenu, progression, ia
├── frontend/       Vue 3 + Vite
├── scripts/        import plan annuel, génération leçons/QCM
└── docs/           spécifications, plans annuels, prompts IA
```

## Statut

- ✅ **Phase 1 — Socle technique** (specs §8.2) : Django 5 + DRF + JWT + CORS, 4 apps (`utilisateurs`, `contenu`, `progression`, `ia`), modèles `Utilisateur`/`Famille`, Vue 3 + Vite + Pinia + Tailwind, route `/api/v1/ping/` opérationnelle.
- ⏳ **Phase 2 — Gestion du contenu** : à venir (modèles `contenu`, import plan annuel, admin Django).

## Démarrage rapide

### 1. Backend

```bash
# À la racine du dépôt
python -m venv .venv
source .venv/Scripts/activate        # Windows Git Bash
# .venv\Scripts\activate.bat         # Windows cmd
# source .venv/bin/activate          # Linux/macOS

cd backend
pip install -r requirements.txt

# Configuration locale
cp ../.env.example ../.env           # puis éditer .env

# Base de données (SQLite par défaut)
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver 127.0.0.1:8001   # http://127.0.0.1:8001
```

> Le port `8001` est utilisé par défaut dans le proxy Vite (voir `frontend/vite.config.js`). Changer simultanément ici et dans `vite.config.js` si besoin.

### 2. Frontend

```bash
cd frontend
npm install
npm run dev                          # http://localhost:5173
```

### 3. Vérification

Ouvrir http://localhost:5173 : la page d'accueil doit afficher le résultat de l'appel `/api/v1/ping/` du back-end.

## Documentation interne

- [docs/specifications.md](docs/specifications.md) — cahier des charges
- [docs/prompts_ia.md](docs/prompts_ia.md) — prompts de génération IA
- [docs/plans_annuels/](docs/plans_annuels/) — plans annuels des 7 matières
