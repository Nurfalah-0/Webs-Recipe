# SeGizi E-Recipes

SeGizi is a recipe-sharing API for discovering, creating, saving, and reviewing
recipes. This repository is arranged as a monorepo so the backend and a future
frontend can live side by side.

## Repository layout

```text
.
├── backend/
│   ├── config/          # Django project configuration
│   ├── recipes/         # Models, API, permissions, and tests
│   ├── manage.py
│   └── requirements.txt
├── frontend/            # Reserved for the future client; currently empty
├── scripts/             # PowerShell MySQL backup/restore tools
├── .env.example          # Local environment template; copy to ignored .env
├── venv/                # Local Python environment; do not commit
├── .gitignore
└── README.md
```

The current application is the Django REST API. No React or other frontend has
been scaffolded yet.

## Requirements

- Python compatible with Django 5.2
- MySQL 8.0, with a database and account configured for the backend
- Windows PowerShell for the commands below (Command Prompt alternatives are
  included where useful)

The backend dependencies are listed in `backend/requirements.txt`. Django is
constrained to the 5.2 series to remain compatible with the project's MySQL 8.0
server. Use a Python version supported by the installed Django and
`mysqlclient` packages.

Django is configured to use MySQL. Migrations, management commands, and tests
connect to the database selected by `DB_NAME`, `DB_USER`, `DB_PASSWORD`,
`DB_HOST`, and `DB_PORT`; there is no SQLite database configuration.

## Set up the backend

Run these commands from the repository root.

### 1. Create or activate the virtual environment

If the root `venv/` already exists, activate it in PowerShell:

```powershell
.\venv\Scripts\Activate.ps1
```

In Command Prompt, activate it with:

```cmd
venv\Scripts\activate.bat
```

If you do not have a virtual environment yet, create one first:

```powershell
py -m venv venv
.\venv\Scripts\Activate.ps1
```

### 2. Install Python dependencies

```powershell
python -m pip install -r .\backend\requirements.txt
```

### 3. Configure environment and MySQL

Create a local `.env` file from the template:

```powershell
Copy-Item .\.env.example .\.env
```

Edit `.env` with the MySQL username, password, host, and port for your local
server. Django loads this file automatically. Do not put real credentials in
`.env.example` or commit `.env`; the latter is ignored by Git.

Important environment variables:

| Variable | Local development | Production |
| --- | --- | --- |
| `DJANGO_DEBUG` | `True` | Set to `False` |
| `DJANGO_SECRET_KEY` | Optional temporary key | Required, generated, and private |
| `DJANGO_ALLOWED_HOSTS` | Defaults to localhost | Explicit comma-separated host names |
| `DB_NAME`, `DB_USER`, `DB_PASSWORD` | Your local MySQL database/account | Required production database credentials |
| `DB_HOST`, `DB_PORT` | Usually `localhost`, `3306` | Provider-specific MySQL host and port |
| `CACHE_URL` | Optional; debug uses local memory cache | Required shared Redis URL |
| `CORS_ALLOWED_ORIGINS` | Local React/Vite origins | Exact trusted frontend origins |
| `CSRF_TRUSTED_ORIGINS` | Local origins when needed | Exact HTTPS origins for trusted browser clients |
| `DJANGO_SECURE_SSL_REDIRECT` | `False` in the example | HTTPS redirect must be enabled behind valid TLS |

Create the database if it does not already exist:

```sql
CREATE DATABASE `db_e-resep`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

### 4. Apply migrations and create an administrator

```powershell
python .\backend\manage.py migrate
python .\backend\manage.py createsuperuser
```

Migrations create the recipe tables, member/creator profiles, and API token
table. Existing accounts default to the Member role; Django staff accounts are
treated as Admins.

### 5. Start the development server

```powershell
python .\backend\manage.py runserver
```

The API is available at `http://127.0.0.1:8000/api/`. Django's administration
site is at `http://127.0.0.1:8000/admin/`.

Useful checks:

```powershell
python .\backend\manage.py check
python .\backend\manage.py makemigrations --check --dry-run
python .\backend\manage.py test recipes
```

The test runner uses MySQL from the same `DB_*` settings and creates a
temporary test database (normally `test_db_e-resep`). Ensure MySQL is running
and the configured database user can create and drop test databases.

After setting production environment variables, also run
`python .\backend\manage.py check --deploy` and resolve any warnings that apply
to your actual TLS/domain setup.

The API health endpoint is `GET /api/health/`. It checks database connectivity
using the configured MySQL connection.

## Accounts and roles

| Role | Capabilities |
| --- | --- |
| Guest | Search and view approved recipes, categories, and ingredients |
| Member | Register, log in, browse, bookmark recipes, and write reviews |
| Recipe Creator | Member capabilities, plus create, edit, and delete their own recipes |
| Admin | Manage users and roles, categories, and all recipes; approve recipes |

Registration always creates a Member account. An Admin can grant creator access
through `PATCH /api/users/{id}/` with:

```json
{
  "role": "creator"
}
```

The Admin user API also accepts `member` or `admin` for the role. Only an
existing Admin can manage users or assign roles.

New recipes are unapproved by default. Creators cannot approve their own
recipes; an Admin approves one with `PATCH /api/recipes/{id}/`:

```json
{
  "is_approved": true
}
```

Guests only receive approved recipes. A Creator can also see their own
unapproved recipes while editing them.

## Authentication

### Register

`POST /api/auth/register/`

```json
{
  "username": "recipe_fan",
  "email": "recipe_fan@example.com",
  "password": "choose-a-strong-password",
  "password_confirm": "choose-a-strong-password"
}
```

Registration returns an API token and the new account profile.

### Log in

`POST /api/auth/login/`

```json
{
  "username": "recipe_fan",
  "password": "choose-a-strong-password"
}
```

Use the returned token on protected API requests:

```http
Authorization: Token <your-token>
```

### Log out

Send `POST /api/auth/logout/` with the token header. This invalidates the
current API token.

## Common recipe actions

### Create a recipe (Creator)

Send `POST /api/recipes/` with the token header and a JSON body:

```json
{
  "title": "Soto Ayam",
  "description": "A comforting chicken soup.",
  "category": 1,
  "prep_time": 20,
  "cook_time": 40,
  "servings": 4,
  "difficulty": "Mudah"
}
```

The API assigns the logged-in user as author, generates the slug, and leaves
the recipe unapproved until an Admin reviews it. `category` is a category ID;
it can be omitted for an uncategorized recipe. To upload an image, send the
request as `multipart/form-data`.

### Bookmark or review a recipe (Member)

Create a bookmark with `POST /api/bookmarks/`:

```json
{
  "recipe": 42
}
```

Write a rating and comment with `POST /api/reviews/`:

```json
{
  "recipe": 42,
  "rating": 5,
  "comment": "Easy to follow and delicious."
}
```

The authenticated account is recorded automatically; clients cannot choose a
different bookmark or review owner.

## API route guide

All API routes are under `/api/`. List endpoints are paginated (20 results per
page by default).

| Route | Access | Purpose |
| --- | --- | --- |
| `/api/recipes/` | Public read; Creator/Admin write | Search, list, create, and filter recipes |
| `/api/recipes/{id}/` | Public read for approved recipes; Creator owner/Admin write | View or manage a recipe |
| `/api/categories/` | Public read; Admin write | Browse and manage recipe categories |
| `/api/ingredients/` | Public read; Admin write | Browse and manage ingredients |
| `/api/bookmarks/` | Authenticated | List and manage your saved recipes |
| `/api/reviews/` | Authenticated | Read and write recipe ratings and comments |
| `/api/recipe-ingredients/` | Creator/Admin | Manage recipe ingredient rows |
| `/api/steps/` | Creator/Admin | Manage recipe steps |
| `/api/users/` | Admin | Manage accounts and roles |
| `/api/auth/register/` | Public | Create a Member account |
| `/api/auth/login/` | Public | Obtain an API token |
| `/api/auth/logout/` | Authenticated | Invalidate your API token |
| `/api/health/` | Public | Check API and database availability |

For example, the recipe API supports search, category (ID or slug), difficulty,
prep/cook-time ranges, and ordering:

```text
/api/recipes/?search=chicken
/api/recipes/?category=dinner&max_prep_time=30&ordering=-created_at
/api/recipes/?difficulty=Mudah&min_cook_time=15
```

Search checks recipe titles, descriptions, category names, and ingredient
names. Ordering is available for fields such as `created_at`, `title`,
`prep_time`, `cook_time`, and `difficulty`.

## Backend developer playbook

The backend owner is responsible for keeping the API correct, secure, reliable,
and straightforward for the frontend team to consume. For SeGizi, that work
breaks down as follows.

### Database and data integrity

- Maintain the recipe, ingredient, category, user profile, bookmark, and review
  models in `backend/recipes/models.py`.
- Make schema changes through Django migrations. Review generated migrations
  before applying them, and back up production data before high-impact changes.
- Keep constraints such as unique category slugs and one bookmark per
  user/recipe pair in the database, not just in frontend code.
- Add indexes only when query patterns or database measurements show they are
  needed.

Typical schema-change workflow:

```powershell
python .\backend\manage.py makemigrations
python .\backend\manage.py migrate
python .\backend\manage.py makemigrations --check --dry-run
```

### Business logic and API contracts

- Keep recipe visibility, creator ownership, admin moderation, and
  bookmark/review rules enforced on the server.
- Validate request data and return predictable status codes and response
  shapes. Never rely on the client to supply an author, user, slug, or approval
  decision that the server controls.
- Document route, permission, and payload changes here so frontend development
  can proceed against a stable contract.
- Run the API tests when changing permissions or workflows:

```powershell
python .\backend\manage.py test recipes
```

### Security

- Use the API token returned at registration or login in the
  `Authorization: Token <token>` header. Keep tokens private and log out to
  invalidate them.
- Keep authorization checks in view permissions and queryset scoping. Test
  both allowed and denied access for Guest, Member, Creator, and Admin roles.
- Settings are environment-driven. For local development, `DJANGO_DEBUG`
  defaults to `True`; a random temporary key is generated if no key is set.
  `.env.example` is only a local template and contains placeholder values.
- In production, set `DJANGO_DEBUG=False`, provide a generated
  `DJANGO_SECRET_KEY` and explicit `DJANGO_ALLOWED_HOSTS`, database credentials,
  and a shared `CACHE_URL`. The settings reject missing production essentials.
  Store these values in the hosting provider's secret manager, not in Git.
- CORS is restricted to the configured origins. Set
  `CORS_ALLOWED_ORIGINS` and `CSRF_TRUSTED_ORIGINS` to the actual frontend
  origins. HTTPS redirect, secure cookies, HSTS, content-type and frame
  protections are configured for non-debug mode; validate proxy/TLS settings
  for the selected deployment before enabling HSTS preload or subdomains.
- Redis backs throttling when `CACHE_URL` is configured. Local debug mode uses
  an in-process cache when no Redis URL is configured.

### Server and infrastructure

- `runserver` is for local development. For deployment, run the WSGI
  application with a production server such as Gunicorn, and configure MySQL,
  Redis (if used), persistent media storage, process supervision, and health
  checks for the hosting environment.
- WhiteNoise serves collected static assets in non-debug mode. Uploaded recipe
  images use Django's configured media storage; production should use durable,
  access-controlled storage appropriate to the hosting provider.
- This repository does not provision a public cloud deployment, domain, TLS
  reverse proxy/certificate, object storage, centralized monitoring, or alert
  delivery. Configure and verify these for the chosen hosting provider before
  exposing the service to the internet. Provision and operate the application
  using the process and hosting tools selected for your environment.

### Debugging and performance

- Start with `manage.py check`, focused tests, and clear reproduction steps.
- Inspect database queries and response times before optimizing. The recipe
  viewsets already use related-object loading and pagination; preserve these
  patterns, query indexes, and tests that bound recipe-list queries. Redis is
  used for shared throttling/cache state when configured; add broader response
  caching only when measurements and invalidation rules justify it.
- Avoid returning private or unapproved data while optimizing querysets.
- Add regression tests for fixed bugs, especially authorization and visibility
  cases.

### Deployment and maintenance

- Review dependency updates in `backend/requirements.txt` and run the test suite
  before upgrading.
- GitHub Actions in `.github/workflows/backend.yml` runs Django checks,
  migration consistency, API tests against MySQL, and a Python dependency audit
  on pushes and pull requests. Configure branch protection in GitHub if these
  checks must be required before merge.
- Back up the database before production migrations. The PowerShell tools read
  the root `.env` (or existing process environment variables), create
  SHA-256-verified SQL dumps, and require confirmation before database restore:

  ```powershell
  .\scripts\backup_mysql.ps1
  .\scripts\restore_mysql.ps1 -BackupFile .\backups\db_e-resep_YYYYMMDD_HHMMSS.sql
  ```

- The database backup scripts connect to MySQL using `DB_HOST` and `DB_PORT`.
  Back up uploaded media using the selected storage provider's backup
  mechanism. Coordinate database and media recovery to the same backup point.
  SQL backups are not encrypted; restrict access and encrypt them before
  copying to off-site storage.
- Apply migrations as an explicit deployment step and verify health afterward.
  Console logs and health checks are included; centralized monitoring, alerting,
  scheduled/off-site backup retention, and a tested recovery objective remain
  deployment responsibilities.

### Team collaboration

- Coordinate API changes with frontend work before changing field names,
  permissions, or response formats.
- Keep pull requests focused and include migration notes, test results, and
  example request/response changes.
- Do not commit the local virtual environment, database files, uploaded media,
  or secrets; the root `.gitignore` excludes these local artifacts.
- Use the pull request template for migration, test, API-contract, and security
  notes. Coordinate API changes with frontend contributors before merging.

## Development notes

- Start commands from the repository root so the paths above resolve correctly.
- The root `venv/` is local and ignored by Git; recreate it on another machine
  with the setup steps above.
- The `frontend/` directory is intentionally empty and ready for a future
  client application.
- The `.env.example` defaults are for local development only. Before
  deployment, provide production secrets and connection URLs, disable debug,
  set allowed hosts and trusted CORS/CSRF origins, and serve the API behind a
  correctly configured HTTPS endpoint.
