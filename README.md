# Manual Assistant

Manual Assistant is a web application that helps factory engineers find answers from machine manuals. Engineers select a machine and ask questions in plain English. The system retrieves relevant information from that machine's manuals and provides answers with manual names, revisions, page numbers, and source references.

If the manuals do not contain enough information, the system responds with **"Not enough information"** instead of guessing.

## Features

- Role-based login for Administrators, Engineers, and Supervisors.
- Administrator-only machine registration and PDF manual uploads.
- PDF text extraction and page-wise storage.
- Machine-specific document retrieval.
- AI-generated answers grounded in manual content.
- Source citations with manual revision and page number.
- Insufficient-evidence detection.
- Engineer-specific question history.
- Supervisor access to all engineers' question history.
- Read-only history with status filtering.
- Automated permission and retrieval tests.

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python 3.11+ |
| Backend | Django 5.2 |
| API | Django REST Framework |
| Database | PostgreSQL |
| PDF processing | PyMuPDF |
| Vector database | ChromaDB |
| Embedding model | Sentence-Transformers |
| Embedding model name | all-MiniLM-L6-v2 |
| AI answer generation | Anthropic API |
| Frontend | HTML, CSS, JavaScript, Bootstrap 5 |
| Testing | Django test runner |

## Project Structure

```text
ManualAssistant/
|
|-- accounts/              Authentication, roles and permissions
|-- machines/              Machine and manual management
|-- retrieval/             Search, answering and question history
|-- config/                Django project configuration
|-- templates/             Login and dashboard templates
|-- rehearsal/             Sample PDFs and practice questions
|
|-- .env.example           Environment variable template
|-- .gitignore
|-- requirements.txt
|-- manage.py
|-- README.md
```

The following are generated or private local resources and are not committed to Git:

- `.env`
- `.venv/`
- `media/`
- `chroma_db/`

## User Roles and Permissions

The application supports three roles.

| Feature | Administrator | Engineer | Supervisor |
|---|---|---|---|
| Login | Yes | Yes | Yes |
| View machine list | Yes | Yes | Yes |
| Add machines | Yes | No | No |
| View uploaded manuals | Yes | No | No |
| Upload manuals | Yes | No | No |
| View source PDFs | Yes | Yes | Yes |
| Ask questions | No | Yes | No |
| View question history | No | Own history | All engineers' history |
| Filter question history | No | Yes | Yes |

Permissions are enforced on the backend using custom Django REST Framework permission classes:

- `IsAdministrator`
- `IsEngineer`
- `IsSupervisor`

## Setup Instructions

### 1. Clone the repository

```bash
git clone https://github.com/Sanika1356/ManualAssistant.git
cd ManualAssistant
```

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

Activate it in Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```powershell
pip install -r requirements.txt
```

### 4. Create the PostgreSQL database

Create a database named:

```sql
CREATE DATABASE manual_assistant_db;
```

Make sure PostgreSQL is running.

### 5. Configure environment variables

Create a private `.env` file using the provided template:

```powershell
Copy-Item .env.example .env
```

Configure the following variables in `.env`:

| Variable | Purpose |
|---|---|
| `DB_NAME` | PostgreSQL database name |
| `DB_USER` | PostgreSQL username |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host, normally localhost |
| `DB_PORT` | PostgreSQL port, normally 5432 |
| `DJANGO_SECRET_KEY` | Django secret key |
| `ANTHROPIC_API_KEY` | Anthropic API key |
| `LLM_MODEL` | AI model name |
| `RAG_MIN_SCORE` | Minimum retrieval score |

Additional retrieval settings can be configured using `RAG_EMBEDDING_BACKEND`, `RAG_EMBEDDING_MODEL`, `RAG_TOP_K`, and `LLM_TIMEOUT_SECONDS`.

**Important:** Never commit `.env` or share passwords, secret keys, or API keys.

### Render deployment

For a Render web service, attach a Render PostgreSQL database and set
`DATABASE_URL` to that database's **Internal Database URL** (or link the
database's connection-string environment variable to the web service).
Also set `DJANGO_SECRET_KEY` to a private generated value. The application
accepts `DATABASE_URL` on Render and keeps the `DB_*` variables for local use.

Use `pip install -r requirements.txt` as the build command and
`bash render_start.sh` as the start command. The startup script applies pending
migrations before launching Gunicorn. After the first deployment, create the
intended application user(s) in the Render database; the optional local demo
account command is for demonstrations only and its preset credentials are not
suitable for a public production service. For a non-production demo, run
`python manage.py seed_demo` once using the Render Shell after deployment.

### 6. Apply database migrations

```powershell
python manage.py migrate
```

### 7. Create demo accounts

```powershell
python manage.py seed_demo
```

This command creates or updates the four demo accounts and assigns their correct roles.

### 8. Download the embedding model

Run this once on each laptop:

```powershell
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

An internet connection is required for the initial download.

### 9. Start the development server

```powershell
python manage.py runserver
```

Open the application:

http://127.0.0.1:8000/login/

## Demo Accounts

| Role | Username | Password |
|---|---|---|
| Administrator | `admin_demo` | `AdminDemo@123` |
| Engineer | `engineer_demo` | `EngineerDemo@123` |
| Engineer | `engineer2_demo` | `Engineer2Demo@123` |
| Supervisor | `supervisor_demo` | `SupervisorDemo@123` |

These accounts are intended only for local development and demonstrations. Use secure individual credentials in a production environment.

## API Reference

All API endpoints are prefixed with `/api/`.

### Authentication APIs

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/api/csrf/` | Anyone | Obtain CSRF cookie |
| POST | `/api/login/` | Anyone | Login |
| GET | `/api/me/` | Authenticated users | Get current user and role |
| POST | `/api/logout/` | Authenticated users | Logout |

### Machine and Manual APIs

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| GET | `/api/machines/` | All authenticated roles | List machines |
| POST | `/api/machines/` | Administrator | Register a machine |
| GET | `/api/manuals/` | Administrator | List uploaded manuals |
| POST | `/api/manuals/upload/` | Administrator | Upload a PDF manual |
| GET | `/api/manuals/<manual_id>/pdf/` | All three roles | View a source PDF |

### Question and History APIs

| Method | Endpoint | Access | Purpose |
|---|---|---|---|
| POST | `/api/ask/` | Engineer | Ask a machine-related question |
| GET | `/api/history/` | Engineer, Supervisor | View question history |

### History API

The History API is read-only.

- Engineers can view only their own questions.
- Supervisors can view questions from all engineers.
- Administrators cannot access the History API.
- Other HTTP methods are not allowed.

Filter history using the `status` query parameter.

**Answered questions:**

```text
GET /api/history/?status=answered
```

**Questions with insufficient evidence:**

```text
GET /api/history/?status=insufficient_evidence
```

Supported status values:

| Status | Meaning |
|---|---|
| `answered` | The system found sufficient evidence and generated an answer |
| `insufficient_evidence` | The manuals did not contain enough information |

An invalid status value returns HTTP 400.

### Ask API Example

Endpoint:

```text
POST /api/ask/
```

Example request:

```json
{
  "machine": 1,
  "question": "What temperature should I use?"
}
```

The response contains:

- Question ID and username.
- Machine ID, name and model.
- Question text and generated answer.
- `status` and `answered` fields.
- Creation timestamp.
- Source manual, revision, page number and passage.
- PDF URL for opening the cited page.

The `status` field is either `answered` or `insufficient_evidence`. The `answered` field is a Boolean compatibility property derived from the status.

## Machine and Manual Management

Administrators can register machines and upload PDF manuals.

The upload process:

1. Validates the PDF file.
2. Checks the file extension and PDF signature.
3. Enforces a maximum file size of 25 MB.
4. Prevents duplicate manual revisions for the same machine.
5. Extracts text page by page using PyMuPDF.
6. Splits extracted text into smaller chunks.
7. Stores chunks and page numbers in PostgreSQL.
8. Adds the extracted chunks to ChromaDB.

The original PDF page number is preserved for accurate source citations.

## Retrieval and Answer Generation

The retrieval application uses machine-specific search to find relevant manual passages.

The workflow:

1. An Engineer selects a machine and submits a question.
2. The question is converted into an embedding.
3. ChromaDB searches the selected machine's manuals.
4. Retrieved passages are checked against PostgreSQL to ensure they belong to that machine.
5. The retrieval score is checked against `RAG_MIN_SCORE`.
6. If evidence is sufficient, the AI receives the relevant passages and generates an answer.
7. If evidence is insufficient, the system returns "Not enough information".
8. The question, answer, status and source details are saved.

### Machine Isolation

The system prevents information from one machine's manuals from being used to answer questions about another machine.

- Search is restricted to the selected machine.
- Retrieved passages are checked again against the database.
- Only passages belonging to the selected machine are passed to the AI.

### Question History

The `Question` model stores the user, machine, question, answer, status and creation time.

The `QuestionSource` model stores source passage details, including manual name, revision, page number, passage text and score.

## Practice Data

The `rehearsal/` folder contains sample materials:

- `pdfs/` — sample Kitchen A and Kitchen B manuals.
- `practice_questions.json` — practice questions.
- `practice_questions_real.json` — additional practice questions.
- `make_rehearsal_pdfs.py` — script to generate the sample PDFs.

These files can be used for demonstrations and retrieval testing.

## Useful Management Commands

```powershell
# Create or update demo accounts
python manage.py seed_demo

# Rebuild the ChromaDB index from stored manual chunks
python manage.py reindex

# Ask a question from the terminal
python manage.py ask 1 "your question"

# Evaluate practice questions
python manage.py evaluate_practice

# Evaluate practice questions with AI
python manage.py evaluate_practice --with-llm
```

If the database already contains manual chunks but the local `chroma_db/` index is missing, run the reindex command.

## Running Tests

Run the complete test suite:

```powershell
python manage.py test
```

Run tests for an individual application:

```powershell
python manage.py test accounts
python manage.py test machines
python manage.py test retrieval
```

The automated test suite covers:

- Authentication and role permissions.
- Machine list and creation permissions.
- Administrator-only manual management.
- PDF upload validation and text extraction.
- Page number preservation and text chunking.
- Engineer-only question submission.
- Machine-specific retrieval.
- Insufficient-evidence handling.
- Question and source history.
- Engineer and Supervisor history access.
- History status filtering.
- Anonymous access restrictions.
- Read-only API behaviour.

The integrated project test suite passed **63 tests** during release verification.

The test configuration uses an offline test embedding backend and simulated AI behaviour, so the automated tests do not require an API key or a model download.

## Backup and Release Notes

The project uses two separate types of backup:

1. **PostgreSQL database backup:** A custom-format dump of the database, created using `pg_dump`.
2. **Project ZIP backup:** A copy of the source code and sample rehearsal files.

The project ZIP excludes private environment files, virtual environments, Git metadata, IDE metadata, Python caches, and the separate database dump.

Uploaded PDF files stored in the local `media/` directory and the ChromaDB index are separate local resources. Back them up separately when they contain data that must be retained. The ChromaDB index can be rebuilt from stored manual chunks using `python manage.py reindex`.

## Development and Verification Status

The integrated project includes:

- Authentication and role management.
- Machine and manual management.
- PDF processing and text extraction.
- Machine-specific retrieval.
- AI-assisted question answering.
- Insufficient-evidence handling.
- Source citations.
- Role-based question history.
- Permission and API tests.

The final integration was tested on four team laptops. The full automated test suite passed, and the PostgreSQL and project ZIP backups were verified.

**Note:** This project is configured for local development and demonstration. Production deployment requires appropriate production security settings, credentials, hosting, and infrastructure configuration.
