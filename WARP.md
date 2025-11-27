# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Commands

### Environment & Installation

- Create virtual environment (recommended):
  - Windows (PowerShell):
    ```bash
    python -m venv venv
    venv\Scripts\activate
    ```
  - macOS/Linux:
    ```bash
    python -m venv venv
    source venv/bin/activate
    ```
- Install dependencies:
  ```bash
  pip install -r requirements.txt
  ```

### Running the Application

There are two primary entrypoints; prefer `run.py` for local development because it performs explicit DB checks before starting the server.

- Run via main app module (simple):
  ```bash
  python app.py
  ```

- Run via helper script (with DB initialization and clearer logs):
  ```bash
  python run.py
  ```

Environment variables that influence runtime (usually loaded from `.env` / `config.env`):
- `SECRET_KEY` – Flask secret key
- `DATABASE_URL` – SQLAlchemy URL for MySQL (defaults to MySQL connection built from DB_HOST, DB_USER, DB_PASS, DB_NAME, DB_PORT)
- `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG` – honored by `run.py`
- `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, `DB_PORT` – used by `config/database.py` for direct SQLAlchemy engine access (MySQL-style connection string)

### Database Setup & Migration Utilities

The application auto-creates tables on first run via SQLAlchemy in `app.py`/`run.py`, but there are several helper scripts for seeding and schema evolution, typically run as plain Python scripts:

- Initialize DB schema (alternate path that uses the low-level engine):
  ```bash
  python -c "from config.database import init_db; init_db()"
  ```

- One-off migration/utility scripts (run as needed):
  ```bash
  # Example patterns; inspect individual scripts before running them
  python migrate_database.py
  python migrate_add_deadline_to_scholarships.py
  python migrate_add_is_active.py
  python migrate_awards_table.py
  python migrate_credentials_status.py
  python migrate_extend_scholarships_fields.py
  python migrate_update_scholarships_counts.py
  python migrate_add_scholarship_application_files.py
  python migrate_add_remarks_table.py
  python migrate_schedule.py

  python create_admin.py
  python create_uc_admin.py
  python create_scholarships_table.py
  python setup_upload_directories.py
  python list_providers.py
  python check_provider.py
  python view_database.py
  ```

These scripts generally assume a configured MySQL database via `config.env`/`.env` (see `config/database.py` and `README.md`).

### Tests & Linting

There is no dedicated test or lint configuration in this repo (no `tests/` package, no `pytest.ini`, `tox.ini`, or linter config). If you need tests or linting:
- Prefer `pytest` for new tests (create a `tests/` directory and `test_*.py` files).
- Choose a linter/formatter explicitly (e.g., `flake8`, `black`) and add the configuration and commands when introducing them.

Until such tooling exists, there are no canonical "run tests"/"lint" commands for this project.

## High-Level Architecture

### Overview

This is a monolithic Flask application implementing the "Scholarsphere" scholarship portal. It uses:
- Flask with `flask_sqlalchemy` and `flask_login` for web/views and authentication.
- A hybrid data access pattern mixing:
  - SQLAlchemy ORM models defined in `app.py` (`User`, `Award`, `Credential`, `Scholarship`, `ScholarshipApplication`, `Notification`, `Schedule`).
  - Raw SQL executed via the SQLAlchemy engine/session from within blueprints (especially in the `students` and `auth` modules).
- Role-based dashboards and flows for three roles: **student**, **provider**, and **admin**.

The repo uses MySQL as the database backend. Configuration is managed via `config.env` and `config/database.py`. All database connections use Flask-SQLAlchemy with MySQL (PyMySQL driver). The application is configured to use MySQL exclusively.

### Entry Points & App Lifecycle

- `app.py`
  - Defines the Flask application instance `app` and the SQLAlchemy `db` and `login_manager`.
  - Declares core ORM models (`User`, `Award`, `Credential`, `Scholarship`, `ScholarshipApplication`, `Notification`, `Schedule`).
  - Registers blueprints:
    - `auth_bp` from `auth.routes` (prefix `/auth`).
    - `admin_bp` from `admin.routes` (prefix `/admin`).
    - `students_bp` from `students.routes` (prefix `/students`).
    - `provider_bp` from `provider.routes` (prefix `/provider`).
  - Configures Jinja filters (e.g., `safe_strftime`) and error handlers (404/500).
  - On import / app creation, runs `db.create_all()` inside `app.app_context()`, so initial table creation is implicit when the app starts.
  - Defines a small set of routes directly (`/`, `/login`, `/signup`, `/logout`) for basic entry points.

- `run.py`
  - Wraps the app in a more explicit CLI-like interface, handling:
    - Database initialization via `create_tables()` (calls `db.create_all()` again).
    - Reading `FLASK_HOST`, `FLASK_PORT`, `FLASK_DEBUG` from env.
    - Printing user-facing URLs (home, login, signup) and simple startup diagnostics.
  - Call `python run.py` when you want a clear startup sequence with console messages.

### Configuration & Database Layer

- `.env` / `config.env`
  - Loaded via `python-dotenv` in `app.py` and `config/database.py`.
  - Expected to contain:
    - `SECRET_KEY`
    - `DATABASE_URL` (MySQL connection string, or will be built from individual DB_* variables)
    - MySQL-specific variables: `DB_HOST`, `DB_USER`, `DB_PASS`, `DB_NAME`, `DB_PORT`.

- `config/database.py`
  - Defines a lower-level SQLAlchemy `engine`, `SessionLocal`, and `Base` targeting a MySQL DB using `PyMySQL`.
  - Exposes `get_db()` (generator for sessions) and `init_db()` (create all tables for models inheriting from `Base`).
  - This is used primarily by migration/utility scripts and **not** by the main Flask app (which uses `flask_sqlalchemy`'s `db`).

Because of this dual setup, DB-related changes may need to be updated in both the ORM model definitions (in `app.py`) and any raw SQL/migration script logic.

### Blueprints & Role-Specific Modules

Each major role has its own blueprint that handles both HTML pages and JSON APIs.

#### `auth` module (`auth/routes.py`)

- Blueprint: `auth_bp` with routes under `/auth`.
- Responsibilities:
  - Authentication (login/logout/signup) and redirecting users based on role.
  - Uses raw SQL via the app's SQLAlchemy engine to query the `users` table directly.
  - Defines an internal lightweight `User` class (subclassing `UserMixin`) to map raw query results to login sessions, separate from the ORM `User` model in `app.py`.

Important implementation detail: this blueprint bypasses the ORM for performance/decoupling reasons; changes to the `users` table schema must be reflected in its hand-written SQL and the positional indexing used when constructing `User` objects.

#### `students` module (`students/routes.py`)

- Blueprint: `students_bp` with routes under `/students`.
- Key responsibilities:
  - Student dashboard (`/dashboard`) aggregating metrics on:
    - Credentials count.
    - Scholarship applications (total, approved).
    - Upcoming scholarship deadlines (this month/next month).
  - CRUD for credentials and awards (upload/view/delete) under `/credentials`, `/awards`, `upload-*`, `delete-*`, `view-*` endpoints.
  - Applying to scholarships (`/apply-scholarship/<int:scholarship_id>`) including linking selected credentials via the `scholarship_application_files` table.
    - Business rule: a student may apply again to the same scholarship if their previous application was **rejected** (the previous record is soft-deactivated before creating a new one).
  - Viewing and withdrawing applications, including associated schedules and provider remarks.
  - Notifications APIs under `/api/notifications*` for listing and marking notifications as read.
  - Profile management (profile info + profile photo upload).

Patterns and architecture notes:
- Data access is predominantly **raw SQL** using `current_app.extensions['sqlalchemy']` plus `db.text(...)`.
- The module uses explicit role checks (`current_user.role == 'student'`) and returns JSON errors or redirects for unauthorized access.
- File uploads are stored under `static/uploads/...` with per-type subdirectories and unique filenames composed of a UUID and user ID.
- Date handling often involves coercing various date formats (strings, timestamps) into `datetime` for template consumption.
- `CredentialMatcher` (from `credential_matcher.py`) is used to map scholarship requirement codes to student credentials for smarter selection UX.

This blueprint is a good reference for how the front-end templates expect data to be shaped (e.g., dictionary keys in `applications_data`, `scholarships_data`, etc.).

#### `provider` module (`provider/routes.py`)

- Blueprint: `provider_bp` with routes under `/provider`.
- Responsibilities (based on the available code and templates):
  - Provider dashboard (`/dashboard`) summarizing:
    - Active/draft scholarships.
    - Application counts, pending reviews, recent reviews.
  - Scholarship management UI under `/scholarships` and related routes.
  - Application review workflows (scheduling, remarks, approval/rejection) and provider-side documents.

Implementation details:
- Uses Flask-SQLAlchemy (`current_app.extensions['sqlalchemy']`) for all database operations, connecting to MySQL database configured in `config.env`.
- All database access is standardized on MySQL via SQLAlchemy.

#### `admin` module (`admin/routes.py`)

- Blueprint: `admin_bp` with routes under `/admin`.
- Responsibilities (inferred from templates):
  - Admin dashboard and reports (`/dashboard`, `/reports`).
  - User and provider management (`/users`, `/providers`).
  - Scholarship/application oversight (`/scholarships`, `/applications`).

The implementation mirrors the provider module’s style: raw SQL via SQLAlchemy and role checks for `role == 'admin'`. When extending admin features, follow existing patterns for data loading and template context structure.

### Templates & Static Assets

- `templates/`
  - `base.html` – shared layout and navigation; individual pages (for each role) extend this.
  - `index.html` – landing page.
  - `auth/` – login and signup forms (`login.html`, `signup.html`).
  - `students/` – student dashboard, profile, credentials, awards, applications, scholarships.
  - `provider/` – provider dashboard, scholarships, applications, schedules, documents, remarks, profile.
  - `admin/` – admin dashboards for users, providers, scholarships, reports.
  - `errors/404.html`, `errors/500.html` – custom error pages used by error handlers in `app.py`.

- `static/`
  - `css/main.css`, `css/auth.css` – global and auth-specific styling.
  - `js/main.js`, `js/auth.js` – general UI and login/signup logic.
  - `images/uc-logo.png` – branding.
  - `uploads/` – runtime file uploads for profile pictures, credentials, awards.

The front-end expects specific JSON structures from the API routes (especially in `students` and `provider` blueprints); when adjusting APIs, verify the JS code in `static/js` and the associated templates.

### Supporting Scripts & Utilities

- Migration/utility scripts at the repo root (`migrate_*.py`, `create_*.py`, `setup_upload_directories.py`, `view_database.py`, etc.) are designed to be run manually and generally:
  - Import `config.database` and/or `app`.
  - Execute schema changes or data fixes via raw SQL or SQLAlchemy.

If you extend the schema or add new tables, consider following the existing pattern of small, focused migration scripts rather than a full migration framework. Ensure that both:
- ORM models in `app.py`, and
- Any raw SQL used throughout the blueprints

stay consistent with your changes.

## Guidance for Future Warp Agents

- When modifying authentication or user-related logic, ensure consistency between:
  - The ORM `User` model in `app.py`.
  - The raw SQL and ad-hoc `User` class in `auth/routes.py`.
- Database backend:
  - The application uses MySQL exclusively via Flask-SQLAlchemy.
  - All routes and scripts use SQLAlchemy for database access.
  - Migration scripts (`migrate_*.py`) have been updated to work with MySQL.
- For new functionality, prefer:
  - Adding routes to the appropriate blueprint (`auth`, `students`, `provider`, `admin`).
  - Extending templates under the corresponding subdirectory.
  - Using the existing JSON/HTML response shapes as a reference to maintain front-end compatibility.
