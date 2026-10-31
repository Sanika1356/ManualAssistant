# Manual Assistant

A web-based application that helps engineers find answers from machine manuals using AI-powered question answering.

## Project Overview

Manual Assistant is developed using Python and Django. It provides role-based access for three types of users:

- **Administrator:** Manages users, roles, machines and manuals.
- **Engineer:** Asks questions about machine manuals and finds technical solutions.
- **Supervisor:** Monitors engineer questions and reviews activity history.

## Technology Stack

- Python 3.11
- Django 5.2
- Django REST Framework
- PostgreSQL
- HTML, CSS, JavaScript
- Bootstrap 5

## Project Structure

```text
ManualAssistant/
│
├── accounts/
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       └── seed_demo.py
│   ├── permissions.py
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   └── tests.py
│
├── config/
│   ├── settings.py
│   └── urls.py
│
├── templates/
│   └── accounts/
│       ├── login.html
│       └── dashboard.html
│
├── manage.py
└── README.md
```

## Setup Instructions

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ManualAssistant
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

### 3. Activate the virtual environment

For Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 4. Install dependencies

```bash
pip install django djangorestframework psycopg2-binary python-dotenv
```

### 5. Create the PostgreSQL database

Create a PostgreSQL database named:

```sql
CREATE DATABASE manual_assistant_db;
```

Configure your PostgreSQL connection in `config/settings.py` using your local database credentials.

### 6. Apply migrations

```bash
python manage.py migrate
```

### 7. Create demo accounts

```bash
python manage.py seed_demo
```

### 8. Start the development server

```bash
python manage.py runserver
```

Open:

http://127.0.0.1:8000/login/

## Demo Accounts

| Role | Username | Password |
|---|---|---|
| Administrator | admin_demo | AdminDemo@123 |
| Engineer | engineer_demo | EngineerDemo@123 |
| Supervisor | supervisor_demo | SupervisorDemo@123 |

**Note:** These credentials are for local development and demonstration only. Never use them in production.

## Authentication API

| Method | Endpoint | Description |
|---|---|---|
| POST | `/api/login/` | User login |
| GET | `/api/me/` | Get logged-in user details and role |
| POST | `/api/logout/` | User logout |
| GET | `/api/csrf/` | Obtain CSRF cookie |

## Role-Based Access Control

The application uses Django Groups to manage roles:

- Administrator
- Engineer
- Supervisor

Custom Django REST Framework permission classes enforce role-based access:

- `IsAdministrator`
- `IsEngineer`
- `IsSupervisor`

Access is checked on the backend, not just by hiding dashboard buttons.

## Running Tests

Run the account application tests:

```bash
python manage.py test accounts
```

The current permission tests verify:

1. Users with the correct role are allowed.
2. Users with a different role are denied.
3. Anonymous users are denied.
4. Users without an assigned role are denied.

## Current Development Status

- Django project and PostgreSQL setup completed.
- Role groups and demo accounts created.
- Login and logout APIs implemented.
- Role-based dashboards implemented.
- Permission classes and automated tests implemented.
- Integration with machine manuals and AI retrieval is under development.

## Team Development

Each team member develops their assigned module and integrates it into the shared project repository.