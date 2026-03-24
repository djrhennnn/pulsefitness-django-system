# PulseFitness — Fixed Django Project

## Quick Start

1. **Install Django** (if not already installed):
   ```
   pip install django
   ```

2. **Run the setup script** (creates DB, migrations, sample trainers, admin user):
   ```
   cd group7
   python setup.py
   ```

3. **Start the server**:
   ```
   python manage.py runserver
   ```

4. **Open your browser**: http://127.0.0.1:8000/

---

## Accounts

| Role   | Email              | Password   | URL              |
|--------|--------------------|------------|------------------|
| Admin  | admin@pulse.com    | admin1234  | /admin-panel/    |
| Member | (register on site) | (your own) | /dashboard/      |

---

## Pages & URLs

| URL              | View                 | Who can access   |
|------------------|----------------------|------------------|
| `/`              | Landing page         | Everyone         |
| `/register/`     | Registration (POST)  | Guests           |
| `/login/`        | Login (POST)         | Guests           |
| `/logout/`       | Logout               | Logged-in users  |
| `/dashboard/`    | Member dashboard     | Members          |
| `/trainer/`      | Trainer dashboard    | Staff            |
| `/admin-panel/`  | Admin dashboard      | Staff            |
| `/django-admin/` | Django built-in admin| Superusers       |

---

## What was fixed

1. **`views.py`** — broken template path, missing views (`lenux`, `register`, `admin_dashboard`, `trainer_dashboard`), bad `urllib` import, nonexistent `view_records` redirect
2. **`fitness/urls.py`** — referenced `views.lenux` (didn't exist); now has all routes
3. **`pulse/urls.py`** — never included fitness app URLs; fixed
4. **`models.py`** — was storing plaintext passwords; replaced with `UserProfile` (linked to Django's `User`), `Trainer`, and `BookingRequest` models
5. **Static paths** — templates used `testdevtt/images/` instead of `fitness/images/`
6. **Login/Register** — was pure front-end JS with no backend; now uses Django form POSTs
7. **Pages connected** — landing → register/login → member dashboard → trainer/admin dashboard, all linked
8. **All dashboard features functional** — BMI calculator saves to DB, trainer booking posts to Django, workout generator works, profile updates saved via AJAX
