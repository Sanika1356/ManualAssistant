# Manual Assistant

A web application that helps factory engineers find answers in machine manuals. Engineers ask a question in plain English, and the system answers only from the manuals of the selected machine, showing the manual, revision and page where the answer was found. When the manuals do not contain the answer, the system says so instead of guessing.

## Contents

1. [Project Overview](#project-overview)
2. [Technology Stack](#technology-stack)
3. [Project Structure](#project-structure)
4. [System Architecture](#system-architecture)
5. [Setup Instructions](#setup-instructions)
6. [Demo Accounts](#demo-accounts)
7. [API Reference](#api-reference)
8. [Role-Based Access Control](#role-based-access-control)
9. [Machine and Manual Management](#machine-and-manual-management)
10. [Retrieval and Answering](#retrieval-and-answering)
11. [Running Tests](#running-tests)
12. [Current Development Status](#current-development-status)
13. [Team Development](#team-development)

## Project Overview

Manual Assistant is developed using Python and Django. It provides role-based access for three types of users:

- **Administrator:** Manages users, roles, machines and manuals.
- **Engineer:** Asks questions about machine manuals and finds technical solutions.
- **Supervisor:** Monitors engineer questions and reviews activity history.

| Module | Purpose |
|---|---|
| Accounts and roles | Login, logout, role groups and permission checks |
| Machines and manuals | Machine registration, PDF upload, text extraction and chunking |
| Retrieval and answering | Searching a machine's manuals, answering with sources, and saving every question |

## Technology Stack

| Area | Technology |
|---|---|
| Language | Python 3.11 or newer |
| Backend | Django 5.2, Django REST Framework |
| Database | PostgreSQL |
| PDF reading | PyMuPDF |
| Search index | ChromaDB |
| Text embeddings | Sentence-Transformers (`all-MiniLM-L6-v2`) |
| Answer generation | Anthropic API |
| Frontend | HTML, CSS, JavaScript, Bootstrap 5 |
| Testing | Django test runner |

## Project Structure

```text
ManualAssistant/
│
├── accounts/                     Login, roles and permissions
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
├── machines/                     Machines, manuals and extracted text
│   ├── migrations/
│   ├── models.py
│   ├── serializers.py
│   ├── services.py
│   ├── views.py
│   ├── urls.py
│   ├── tests.py
│   └── test_task8.py
│
├── retrieval/                    Search, answering and saved questions
│   ├── migrations/
│   ├── management/
│   │   └── commands/
│   │       ├── ask.py
│   │       ├── evaluate_practice.py
│   │       └── reindex.py
│   ├── embeddings.py             Converts text to vectors
│   ├── vectorstore.py            ChromaDB storage and search
│   ├── services.py               Question answering steps
│   ├── llm.py                    Connection to the AI model
│   ├── models.py                 Question and QuestionSource
│   ├── serializers.py
│   ├── views.py
│   ├── urls.py
│   ├── signals.py
│   ├── admin.py
│   └── tests.py
│
├── rehearsal/                    Sample data for practice
│   ├── pdfs/
│   ├── make_rehearsal_pdfs.py
│   └── practice_questions.json
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
├── .env.example                  Template for the private .env file
├── requirements.txt
├── manage.py
└── README.md
```

The `chroma_db/` folder (the search index) and the `.env` file are created locally and are not stored in Git.

## System Architecture

### Manual upload

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
PyMuPDF Text Extraction (page by page)
      |
      v
Text Chunking
      |
      v
Chunk Records in PostgreSQL
      |
      v
Chunks added to the ChromaDB search index
```

### Asking a question

```text
Engineer selects a machine and types a question
                    |
                    v
Question is converted into a vector
                    |
                    v
ChromaDB search, limited to the selected machine
                    |
                    v
Safety check in PostgreSQL: every passage must belong to that machine
                    |
                    v
Best match score below RAG_MIN_SCORE?
        yes --> "Not enough information"  (the AI is not called)
        no
                    |
                    v
AI receives only the numbered passages and strict rules
                    |
                    v
AI replied NOT_ENOUGH_INFORMATION?
        yes --> "Not enough information"
        no
                    |
                    v
Question, answer and source passages are saved
                    |
                    v
Answer is shown with manual name, revision, page number and a link to the PDF page
```

## Setup Instructions

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd ManualAssistant
```

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
```

For Windows PowerShell:

```powershell
.\.venv\Scripts\Activate.ps1
```

For macOS or Linux:

```bash
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Create the PostgreSQL database

```sql
CREATE DATABASE manual_assistant_db;
```

### 5. Create the `.env` file

Copy the template and fill in your own values:

```bash
copy .env.example .env        # Windows
cp .env.example .env          # macOS or Linux
```

| Variable | Purpose |
|---|---|
| `DB_NAME` | PostgreSQL database name (`manual_assistant_db`) |
| `DB_USER` | PostgreSQL user |
| `DB_PASSWORD` | PostgreSQL password |
| `DB_HOST` | Database host, normally `localhost` |
| `DB_PORT` | Database port, normally `5432` |
| `DJANGO_SECRET_KEY` | Secret key. Generate one with `python -c "import secrets; print(secrets.token_urlsafe(50))"` |
| `ANTHROPIC_API_KEY` | Key for the AI service used to write answers |
| `LLM_MODEL` | AI model name, default `claude-haiku-5-5` |
| `RAG_MIN_SCORE` | Minimum search score before the AI is asked (see [Retrieval and Answering](#retrieval-and-answering)) |

Write each value without spaces around `=` and without quotation marks. **Never commit the `.env` file or share the API key.**

### 6. Apply migrations

```bash
python manage.py migrate
```

### 7. Create demo accounts

```bash
python manage.py seed_demo
```

### 8. Download the search model (once, requires internet)

```bash
python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"
```

The first run can take several minutes.

### 9. Start the development server

```bash
python manage.py runserver
```

Open: http://127.0.0.1:8000/login/

### 10. Build the search index (only after cloning with an existing database)

If manuals already exist in the database but the `chroma_db/` folder is missing, rebuild the index:

```bash
python manage.py reindex
```

## Demo Accounts

| Role | Username | Password |
|---|---|---|
| Administrator | admin_demo | AdminDemo@123 |
| Engineer | engineer_demo | EngineerDemo@123 |
| Supervisor | supervisor_demo | SupervisorDemo@123 |

**Note:** These credentials are for local development and demonstration only. Never use them in production.

## API Reference

| Method | Endpoint | Allowed role | Description |
|---|---|---|---|
| GET | `/api/csrf/` | Anyone | Obtain the CSRF cookie |
| POST | `/api/login/` | Anyone | User login |
| GET | `/api/me/` | Logged-in user | Logged-in user details and role |
| POST | `/api/logout/` | Logged-in user | User logout |
| GET, POST | `/api/machines/` | Administrator | List or register machines |
| GET | `/api/manuals/` | Administrator | List uploaded manuals |
| POST | `/api/manuals/upload/` | Administrator | Upload a manual PDF |
| GET | `/api/manuals/<manual_id>/pdf/` | Administrator, Engineer, Supervisor | View the source PDF (add `#page=N` to open a specific page) |
| POST | `/api/ask/` | Engineer | Ask a question about one machine |

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

Administrators can upload PDF manuals through `POST /api/manuals/upload/`.

The upload process performs the following operations:

1. Validates the uploaded PDF file.
2. Checks the file extension, PDF signature and file size.
3. Checks for duplicate manual revisions.
4. Extracts text from each PDF page using PyMuPDF.
5. Splits extracted text into smaller chunks.
6. Stores the chunks in the database with their corresponding page numbers.
7. Adds the chunks to the search index.

If the manual cannot be added to the search index, the upload is cancelled and a readable error is returned.

### PDF Text Extraction

PyMuPDF is used to open the uploaded PDF and extract text page by page.

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

Page numbering starts at 1 using `enumerate(pdf, start=1)`, so the original PDF page number is stored instead of a zero-based index.

### Text Chunking

Extracted text is divided into smaller chunks to make it easier to process and retrieve relevant information.

| Parameter | Value |
|---|---|
| Chunk size | 250 words |
| Chunk overlap | 30 words |
| Page numbering | Starts from 1 |

**Chunk overlap:** The last 30 words of a chunk are repeated at the beginning of the next chunk. This helps preserve context between consecutive chunks.

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

Each generated chunk keeps the page number from which its text was extracted.

### Error Handling

The upload process handles:

- Invalid or corrupted PDF files.
- PDFs with no extractable text.
- Duplicate manual revisions.
- Missing required upload details.
- File size and file type validation.
- Failures while adding the manual to the search index.

Readable error messages are returned when an upload fails.

### Protected PDF Viewing

Uploaded manuals can be opened through `GET /api/manuals/<manual_id>/pdf/`. Only authenticated users with an authorised role can view the source PDF.

## Retrieval and Answering

The `retrieval` application finds the relevant passages in a machine's manuals, asks the AI model to answer from them, and saves every question with its answer and sources.

### The "Not Enough Information" Rule

There are two separate checks:

1. **Score check.** Every passage receives a similarity score. If the best score is below `RAG_MIN_SCORE`, the question is treated as unanswerable and the AI is not called.
2. **AI check.** The AI is told to reply `NOT_ENOUGH_INFORMATION` unless the passages clearly contain the answer.

Both checks give the same saved result: `answered = false`. Supervisors can filter on this value to find unanswered questions.

### Keeping Machines Separate

- Every stored passage is tagged with its `machine_id`.
- Every search filters by `machine_id` inside the search itself, not afterwards.
- Results are checked again against the database before use.
- The AI prompt is built only from passages of the selected machine.

### Saved Questions

| Model | Stores |
|---|---|
| `Question` | User, machine, question text, answer, whether it was answered, time |
| `QuestionSource` | Each passage used: manual name, revision, page number, passage text and score |

The passage details are copied into `QuestionSource`, so question history remains correct even if a manual is deleted later.

### Ask API

`POST /api/ask/` (Engineer only)

Request:

```json
{
  "machine": 1,
  "question": "What temperature should I bake lasagna at?"
}
```

Response (`201 Created`):

```json
{
  "id": 12,
  "username": "engineer_demo",
  "machine_id": 1,
  "machine_name": "Kitchen A",
  "machine_model": "Convection Oven",
  "text": "What temperature should I bake lasagna at?",
  "answer": "Bake at 180 degrees Celsius for 45 minutes [1].",
  "answered": true,
  "created_at": "2026-11-01T10:30:00Z",
  "sources": [
    {
      "passage_number": 1,
      "manual_id": 1,
      "manual_name": "Kitchen A Recipe Book",
      "revision": "1.0",
      "page_number": 1,
      "text": "Lasagna. Preheat the Kitchen A convection oven to 180 degrees Celsius...",
      "score": 0.62,
      "pdf_url": "/api/manuals/1/pdf/#page=1"
    }
  ]
}
```

When there is no answer, `answered` is `false`, `answer` is "Not enough information in the manuals for this machine.", and `sources` is empty.

| Status | Meaning |
|---|---|
| 201 | Question saved (answered or not) |
| 400 | Empty question, question over 1000 characters, or missing or unknown machine |
| 403 | The user is not an Engineer |
| 503 | The AI service or search is unavailable. Nothing is saved |

### Settings

| Setting | Default | Purpose |
|---|---|---|
| `ANTHROPIC_API_KEY` | none | Key for the AI service |
| `LLM_MODEL` | `claude-haiku-5-5` | AI model used to write answers |
| `RAG_MIN_SCORE` | `0.30` | Minimum match score needed to try answering |
| `RAG_TOP_K` | `4` | Number of passages sent to the AI |
| `RAG_EMBEDDING_MODEL` | `all-MiniLM-L6-v2` | Model used to convert text to vectors |

### Management Commands

```bash
python manage.py reindex                       # rebuild the search index from the database
python manage.py ask 1 "your question"         # ask a question from the terminal
python manage.py evaluate_practice             # run the practice questions and suggest RAG_MIN_SCORE
python manage.py evaluate_practice --with-llm  # same, but also call the AI model
```

### Practice Data and Threshold Tuning

The `rehearsal/` folder contains sample data:

- `pdfs/`: three small manuals for two machines, Kitchen A and Kitchen B.
- `practice_questions.json`: 15 questions (5 answerable, 5 that only the other machine can answer, 5 unrelated).
- `make_rehearsal_pdfs.py`: recreates the sample PDFs.

To tune the threshold:

1. Upload the three PDFs as an Administrator (Kitchen A with two manuals, Kitchen B with one).
2. Run `python manage.py evaluate_practice`.
3. Set `RAG_MIN_SCORE` in `.env` between the highest score of an unrelated question and the lowest score of an answerable one.

**Sample result.** Unrelated questions scored up to about 0.14 and answerable questions scored from about 0.34, so a value near 0.25 separates them. Questions about topics that sound similar in both machines (for example, baking temperatures) can still score above the threshold. These are handled by the second check, where the AI replies that the passages do not contain the answer.

## Running Tests

Run all tests:

```bash
python manage.py test
```

Run the tests of one application:

```bash
python manage.py test accounts
python manage.py test machines
python manage.py test retrieval
```

### Account tests

1. Users with the correct role are allowed.
2. Users with a different role are denied.
3. Anonymous users are denied.
4. Users without an assigned role are denied.

### Machine tests

1. Machine and manual creation.
2. PDF upload and validation.
3. Page-wise PDF text extraction.
4. Correct page number preservation.
5. Text chunking and overlap.
6. Corrupted and empty PDF handling.
7. Protected PDF viewing and role permissions.

### Retrieval tests

1. Only Engineers can ask questions.
2. Text from another machine is never retrieved or sent to the AI.
3. Questions with no answer are refused without calling the AI.
4. Answered questions are saved with their sources, revision and page number.
5. Empty or invalid questions return a clear error.
6. If the AI service is unavailable, nothing is saved and a clear message is returned.
7. Uploading a manual makes it searchable with correct page numbers.
8. Deleting a manual removes it from search, and saved history still displays correctly.

The automated tests use a small built-in search method and a simulated AI, so they need no model download and no API key.

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
- Search index with machine-limited retrieval implemented.
- "Not enough information" rule implemented.
- AI answering with source passages and the `/api/ask/` endpoint implemented.
- Saving of questions, answers and sources implemented.
- Automated wrong-machine test implemented.

## Team Development

Each team member develops their assigned module and integrates it into the shared project repository.
