# P4 – Ask & History Module

## Project: ManualAssistant

### 1. Overview

The Ask & History module is responsible for allowing engineers to ask questions about machine manuals and access their previous questions and answers.

It is part of the ManualAssistant Django application, which helps users access information from machine manuals.

### 2. Responsibilities

The P4 module covers:

- Accepting questions from authenticated engineers.
- Integrating with the question-answering functionality provided by P3.
- Displaying generated answers to users.
- Maintaining a history of questions and answers.
- Allowing engineers to view their own question history.
- Allowing supervisors to view all users' question history in read-only mode.

### 3. Role-Based Access

| Role | Permissions |
|---|---|
| Administrator | Upload machine manuals |
| Engineer | Ask questions and view own history |
| Supervisor | View all question history (read-only) |

### 4. Technology Stack

- Python
- Django 5.2.18
- Django REST Framework 3.18.3
- PostgreSQL
- HTML, CSS, Bootstrap and JavaScript

### 5. Integration

The module uses the existing authentication and role-management functionality.

Existing authentication endpoints:

- `POST /api/login/`
- `GET /api/me/`
- `POST /api/logout/`

The Ask functionality will integrate with P3's question-answering implementation. The exact integration interface will be documented after coordination with P3.

### 6. Database

The project uses PostgreSQL as its database.

The question history functionality will maintain records of questions, generated answers, the user who asked each question, and relevant manual/source information where available.

### 7. Current Development Status

- Django project environment configured.
- PostgreSQL database connected.
- Existing database migrations applied.
- Existing login page loads successfully on localhost.
- P4 question-answering integration and history functionality require implementation and testing.

### 8. Running the Project

Activate the virtual environment, install project dependencies, configure the environment variables, and run:

```bash
python manage.py migrate
python manage.py runserver
```

Open the application at:

`http://127.0.0.1:8000/login/`

**Note:** This document describes the P4 module scope and current development status. Update the implementation details and API endpoints after completing integration and testing.
