# Déploiement en production

Playbook de mise en ligne du portail. Cible : serveur Linux, PostgreSQL, front-end Vue compilé servi statiquement, back-end Django derrière un reverse proxy.

---

## 1. Prérequis serveur

- Python **3.12+** (le SDK `claude-agent-sdk` et Django 5.1 l'exigent)
- Node **20+** pour compiler le front-end (pas nécessaire à l'exécution)
- PostgreSQL **14+**
- Un reverse proxy (nginx, Caddy…) pour servir `frontend/dist/` et proxifier `/api/` vers Django
- Un runner Python (gunicorn recommandé)

## 2. Arborescence cible

```
/opt/portail-educatif/           # checkout du dépôt
├── backend/                     # Django
│   ├── staticfiles/             # généré par collectstatic
│   └── db.sqlite3               # non utilisé en prod
├── frontend/
│   └── dist/                    # généré par `npm run build` (à servir par nginx)
├── .env                         # config prod (non versionnée)
└── .venv/                       # venv Python
```

## 3. Variables d'environnement (`.env`)

Copier `.env.example` en `.env` et adapter :

```ini
DJANGO_SECRET_KEY=<50+ caractères aléatoires — générer via python -c "import secrets; print(secrets.token_urlsafe(64))">
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=portail.example.com,www.portail.example.com

DATABASE_URL=postgres://portail:<mot_de_passe>@localhost:5432/portail_educatif

CORS_ALLOWED_ORIGINS=https://portail.example.com

# Questions libres uniquement — voir §8 "Point ouvert"
ANTHROPIC_API_KEY=sk-ant-...

ANTHROPIC_MODEL_GENERATION=claude-sonnet-4-6
ANTHROPIC_MODEL_QUESTIONS_LIBRES=claude-haiku-4-5
QUESTIONS_LIBRES_MAX_PAR_JOUR=5
```

> **Ne jamais commiter `.env`**. Permissions : `chmod 600 .env`.

## 4. Installation back-end

```bash
# À la racine du dépôt cloné
python3 -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
pip install gunicorn
```

## 5. Base de données

### Création

```bash
sudo -u postgres psql <<SQL
CREATE USER portail WITH PASSWORD '<mot_de_passe>';
CREATE DATABASE portail_educatif OWNER portail;
SQL
```

### Migrations

```bash
cd backend
python manage.py migrate
```

### Peuplement du contenu pédagogique

Le contenu (leçons + QCM) est généré en dev via Claude Code, puis exporté en fixture versionnée. **La prod ne régénère rien** — elle charge le JSON committé.

```bash
python manage.py loaddata contenu.json
```

La fixture est recherchée dans `backend/contenu/fixtures/contenu.json` (dépôt) — pas besoin de préciser le chemin.

### Numérotation des jours (une seule fois)

```bash
python manage.py ordonnancer_jours
```

Cette commande attribue à chaque thématique son `numero_jour` global (1 à 180) en interclassant les matières.

### Superuser d'administration

```bash
python manage.py createsuperuser
```

## 6. Front-end

Compiler une seule fois, puis servir `frontend/dist/` en static via nginx.

```bash
cd frontend
npm ci
npm run build
```

Exemple de bloc nginx :

```nginx
server {
    server_name portail.example.com;
    listen 443 ssl;

    root /opt/portail-educatif/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /admin/ {
        proxy_pass http://127.0.0.1:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static/ {
        alias /opt/portail-educatif/backend/staticfiles/;
    }
}
```

Statiques Django (admin + DRF) :

```bash
cd backend
python manage.py collectstatic --noinput
```

## 7. Lancement du back-end

```bash
cd backend
gunicorn portail.wsgi:application \
    --bind 127.0.0.1:8001 \
    --workers 3 \
    --access-logfile - \
    --error-logfile -
```

En pratique, via un service systemd `/etc/systemd/system/portail-backend.service`.

## 8. Création des comptes famille

Via l'admin Django (`/admin/`) en étant connecté avec le superuser :

1. **Créer la famille** : `Utilisateurs → Familles → Ajouter`, nom = "Famille Guilleron".
2. **Créer le compte parent** : `Utilisateurs → Ajouter`, rôle = `parent`, famille = celle créée, cocher `staff` pour accès admin.
3. **Créer le compte élève** : rôle = `eleve`, famille = même, `niveau_scolaire = 3e`, `date_naissance` renseignée.
4. Vérifier la connexion depuis `/` avec les identifiants élève.

## 9. Mises à jour du contenu

Quand une nouvelle matière est générée en dev :

```bash
# En dev
cd backend
python manage.py exporter_contenu            # → backend/contenu/fixtures/contenu.json
git add backend/contenu/fixtures/contenu.json
git commit -m "..."
git push

# En prod
cd /opt/portail-educatif
git pull
cd backend
../.venv/bin/python manage.py loaddata contenu.json
../.venv/bin/python manage.py ordonnancer_jours
sudo systemctl restart portail-backend
```

> `loaddata` fait un upsert par clé primaire : les objets existants sont mis à jour, les nouveaux sont créés. Les progressions des élèves (`TentativeQCM`, `ProgressionLecon`, `QuestionLibre`) ne sont pas touchées — elles vivent dans les apps `progression` et `ia`, pas dans `contenu`.

## 10. Questions libres en prod — installation du CLI Claude Code

Décision : on installe **Claude Code sur le VPS** et on s'y authentifie une seule fois. Coût : 0 € (couvert par l'abonnement Max). L'élève n'a aucune visibilité sur ce mécanisme.

### Mise en place

1. **Installer le CLI** sur le VPS (étape 3 du déploiement) :
   ```bash
   curl -fsSL claude.ai/install.sh | bash    # ou la procédure officielle du moment
   ```

2. **Authentifier le CLI** — méthode "copie de credentials" (la plus simple) :
   - Identifier le fichier de credentials sur la machine de dev (typiquement `C:\Users\<toi>\.claude\` côté Windows)
   - Le copier sur le VPS au même chemin (`~/.claude/credentials.json` côté Linux)
   - Tester avec `claude --version` ou un appel `claude` simple pour vérifier que l'auth est reconnue

   Méthode alternative si la copie ne marche pas : tunnel SSH pour rejouer le flux OAuth complet (`ssh -L 8080:localhost:8080 user@vps`, puis `claude login` côté VPS, ouverture de l'URL affichée dans le navigateur Windows, callback forwardé via le tunnel).

3. **Vérifier que `claude-agent-sdk` trouve bien le CLI** depuis l'utilisateur qui exécute gunicorn (probablement `portail` ou `www-data`). Si gunicorn tourne sous un autre user, lui copier aussi les credentials dans son `~/.claude/`.

### Notes importantes

- **Le quota Max 5x est partagé** entre toutes tes sessions Claude Code (dev + prod). Avec `QUESTIONS_LIBRES_MAX_PAR_JOUR=5` en Haiku 4.5, la consommation reste très marginale (~quelques milliers de tokens/jour).
- **Le token OAuth se renouvelle silencieusement** : pas de re-login régulier à prévoir. Seul cas où l'opération est à refaire : changement de mot de passe Anthropic, ou invalidation globale de session.
- **`ANTHROPIC_API_KEY` reste vide dans `.env` prod** — on ne s'en sert pas avec cette option.

## 11. Sauvegardes

```bash
# Dump PostgreSQL quotidien
pg_dump -U portail portail_educatif | gzip > /backup/portail-$(date +%F).sql.gz
```

Le contenu pédagogique est recréable depuis `contenu.json` versionné en Git. Ce qui doit être sauvegardé en priorité : **la progression des élèves** (`progression_*`, `ia_questionlibre`).
