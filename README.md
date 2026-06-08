# SPARSH — Student Performance Analysis, Records & Scholastic History

A web-based Internal Exam / Result Analysis application for schools. Built for KVS (Kendriya Vidyalaya Sangathan) schools to analyze, compare, and archive student performance data across academic years.

## Features

- **Excel Import** — Bulk import student results from standardized Excel sheets
- **Student Search** — Look up any student by admission number, class, or roll number
- **Result Dashboard** — View current exam results with subject-wise breakdown
- **Historical Report Cards** — Upload, archive, and view previous years' PDF report cards inline
- **Google Drive Storage** — All uploaded PDFs are stored securely in the admin's Google Drive via OAuth 2.0
- **Role-Based Access** — Admin, Teacher, and Principal roles with appropriate permissions
- **Academic Year Management** — Manage multiple academic years, classes, sections, and exams

## Technology Stack

| Layer     | Technology                   |
|-----------|------------------------------|
| Backend   | Python FastAPI               |
| Database  | SQLite (dev) / PostgreSQL (prod) |
| Frontend  | Bootstrap 5 + Vanilla JS    |
| Storage   | Google Drive (OAuth 2.0)     |
| Deploy    | Render                       |

## Project Structure

```
/backend         → FastAPI application
  /app
    /api         → Route handlers (endpoints)
    /core        → Config, security, encryption
    /db          → Database engine, session, seed
    /models      → SQLAlchemy ORM models
    /schemas     → Pydantic validation DTOs
    /services    → Business logic & external integrations
  /alembic       → Database migration scripts
/frontend        → Bootstrap 5 static frontend
  /css           → Stylesheets
  /js            → JavaScript modules
/docs            → Setup guides & documentation
/sample-files    → Sample Excel and PDF files for testing
```

## Local Development Setup

### Prerequisites

- Python 3.11+
- Git

### Quick Start (Windows)

```bash
git clone https://github.com/<your-username>/SPARSH-student-progress-tracker.git
cd SPARSH-student-progress-tracker
```

Run the automated installer:
```bash
install_requirements.bat
```

Or set up manually:

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
# Edit .env with your secret key and database URL
alembic upgrade head
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### Verify

- Dashboard: [http://127.0.0.1:8000/dashboard.html](http://127.0.0.1:8000/dashboard.html)
- API Docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- Default login: `admin` / `admin123`

## Environment Variables

| Variable                       | Required | Description                              |
|--------------------------------|----------|------------------------------------------|
| `SECRET_KEY`                   | Yes      | JWT signing key                          |
| `DATABASE_URL`                 | Yes      | Database connection string               |
| `FERNET_SECRET_KEY`            | Yes      | Encryption key for OAuth token storage   |
| `STORAGE_PROVIDER`             | No       | `google_drive` (default)                 |
| `GOOGLE_CLIENT_ID`             | No       | Google OAuth Client ID                   |
| `GOOGLE_CLIENT_SECRET`         | No       | Google OAuth Client Secret               |
| `GOOGLE_REDIRECT_URI`          | No       | OAuth callback URL                       |

See [`.env.example`](backend/.env.example) for a full template.

## Google Drive Setup

For detailed instructions on setting up Google Drive integration:
- **Developers:** See [`docs/developer_oauth_setup.md`](docs/developer_oauth_setup.md)
- **Admins:** See [`docs/admin_storage_guide.md`](docs/admin_storage_guide.md)

## License

This project is developed for educational purposes.
