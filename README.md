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
- PyMuPDF
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
├── machines/
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── services.py
│   ├── views.py
│   ├── urls.py
│   ├── tests.py
│   └── test_task8.py
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

## System Architecture

The machine manual management module follows this workflow:

```text
Administrator
      |
      v
Machine Registration
      |
      v
Manual PDF Upload
      |
      v
PDF Validation
      |
      v
PyMuPDF Text Extraction
      |
      v
Page-wise Text Processing
      |
      v
Text Chunking
      |
      v
Chunk Records in Database
```

The Django application handles API requests, PyMuPDF extracts text from uploaded PDF manuals, and PostgreSQL stores machine, manual and extracted chunk information.

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
pip install django djangorestframework psycopg2-binary python-dotenv pymupdf
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

## Machine and Manual Management

The `machines` application manages machine details, uploaded PDF manuals and extracted text.

### Database Models

- **Machine:** Stores machine name and model.
- **Manual:** Stores the manual name, revision, PDF file, associated machine and upload details.
- **Chunk:** Stores extracted manual text along with its original PDF page number.

### PDF Upload and Text Extraction

Administrators can upload PDF manuals through:

`POST /api/manuals/upload/`

The upload process performs the following operations:

1. Validates the uploaded PDF file.
2. Checks the file extension, PDF signature and file size.
3. Checks for duplicate manual revisions.
4. Extracts text from each PDF page using PyMuPDF.
5. Splits extracted text into smaller chunks.
6. Stores the chunks in the database with their corresponding page numbers.

### PDF Text Extraction

PyMuPDF is used to open the uploaded PDF and extract text page by page.

Example extraction logic:

```python
with manual.file.open("rb") as uploaded_pdf:
    pdf_content = uploaded_pdf.read()

with pymupdf.open(
    stream=pdf_content,
    filetype="pdf"
) as pdf:
    for page_number, page in enumerate(pdf, start=1):
        page_text = page.get_text("text").strip()

        if page_text:
            page_chunks = split_text_into_chunks(page_text)
```

The page numbering starts at 1 using `enumerate(pdf, start=1)`. This ensures that the original PDF page number is stored correctly instead of using zero-based indexing.

### Text Chunking

Extracted text is divided into smaller chunks to make it easier to process and retrieve relevant information.

| Parameter | Value |
|---|---|
| Chunk size | 250 words |
| Chunk overlap | 30 words |
| Page numbering | Starts from 1 |

**Chunk overlap:** The last 30 words of a chunk are repeated at the beginning of the next chunk. This helps preserve context between consecutive chunks.

Example chunking logic:

```python
CHUNK_SIZE = 250
CHUNK_OVERLAP = 30

def split_text_into_chunks(
    text,
    chunk_size=CHUNK_SIZE,
    overlap=CHUNK_OVERLAP
):
    words = text.split()

    if not words:
        return []

    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("Invalid chunk overlap.")

    chunks = []
    start = 0

    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunks.append(" ".join(words[start:end]))

        if end == len(words):
            break

        start = end - overlap

    return chunks
```

Each generated chunk retains the page number from which its text was extracted.

### Error Handling

The upload process handles:

- Invalid or corrupted PDF files.
- PDFs with no extractable text.
- Duplicate manual revisions.
- Missing required upload details.
- File size and file type validation.

Readable error messages are returned when an upload fails.

### Protected PDF Viewing

Uploaded manuals can be accessed through a protected PDF endpoint:

`GET /api/manuals/<manual_id>/pdf/`

Only authenticated users with an authorized role can view the source PDF.

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

Run the machine application tests:

```bash
python manage.py test machines
```

The machine tests cover:

1. Machine and manual creation.
2. PDF upload and validation.
3. Page-wise PDF text extraction.
4. Correct page number preservation.
5. Text chunking and overlap.
6. Corrupted and empty PDF handling.
7. Protected PDF viewing and role permissions.

## Current Development Status

- Django project and PostgreSQL setup completed.
- Role groups and demo accounts created.
- Login and logout APIs implemented.
- Role-based dashboards implemented.
- Permission classes and automated tests implemented.
- Machine and manual management implemented.
- PDF text extraction and chunking implemented.
- Protected PDF viewing implemented.
- Automated three-page PDF page-number test implemented.

## Team Development

Each team member develops their assigned module and integrates it into the shared project repository.