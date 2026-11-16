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
├── venv/                # Local Python environment; do not commit
├── .gitignore
└── README.md
```

The current application is the Django REST API. No React or other frontend has
been scaffolded yet.

## Requirements

- Python compatible with Django 5.2
- MySQL, with a database and account configured for the backend
- Windows PowerShell for the commands below (Command Prompt alternatives are
  included where useful)

The backend dependencies are listed in `backend/requirements.txt`. Django is
constrained to the 5.2 series to remain compatible with the project's MySQL 8.0
server.

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

### 3. Configure MySQL

The default database configuration is in `backend/config/settings.py`:

- Database: `db_e-resep`
- Host: `localhost`
- Port: `3306`
- User: `root`

Create the database if it does not already exist:

```sql
CREATE DATABASE `db_e-resep`
  CHARACTER SET utf8mb4
  COLLATE utf8mb4_unicode_ci;
```

Update the database name, user, and password in `backend/config/settings.py` to
match your local MySQL setup before continuing.

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

## Development notes

- Start commands from the repository root so the paths above resolve correctly.
- The root `venv/` is local and ignored by Git; recreate it on another machine
  with the setup steps above.
- The `frontend/` directory is intentionally empty and ready for a future
  client application.
- The current settings are for local development. Before deployment, move
  secrets and database credentials out of source, set `DEBUG = False`, configure
  `ALLOWED_HOSTS`, restrict CORS to trusted origins, and serve the API over
  HTTPS.
