# DEDC Survey Project

A FastAPI-based survey application with HTML templates, CSS, and JavaScript for managing surveys, questions, and responses.

Administrator login and logout are available at `/portal`. See
[Admin portal setup and Git collaboration](docs/admin-portal.md) for Docker MySQL
configuration, administrator credentials, routes, and the feature-branch workflow.

## Project Structure

```
DEDC/
├── app/                    # Core application code
│   ├── __init__.py
│   ├── main.py            # FastAPI app entry point, router & static files setup
│   ├── config.py          # Application settings & environment variables
│   ├── database.py        # SQLAlchemy engine, session, and Base model
│   ├── dependencies.py    # FastAPI dependencies (DB session)
│   │
│   ├── models/            # SQLAlchemy ORM models (Database tables)
│   │   ├── __init__.py
│   │   ├── survey.py      # Survey model (title, year)
│   │   ├── question.py    # Question model (linked to Survey)
│   │   ├── option.py      # Option model for multiple-choice questions
│   │   ├── response.py    # Response model (survey submission metadata)
│   │   └── answer.py      # Answer model (individual question answers)
│   │
│   ├── schemas/           # Pydantic schemas (Request/Response validation)
│   │   ├── __init__.py
│   │   ├── survey.py      # SurveyCreate, Survey schemas
│   │   ├── question.py    # QuestionCreate, Question, Option schemas
│   │   └── response.py    # ResponseCreate, Response, Answer schemas
│   │
│   ├── crud/              # Database CRUD operations
│   │   ├── __init__.py
│   │   ├── survey.py      # Survey CRUD functions
│   │   └── response.py    # Response CRUD functions
│   │
│   └── routers/           # API route handlers
│       ├── __init__.py
│       ├── surveys.py     # Survey API endpoints (/surveys)
│       ├── questions.py   # Question API endpoints (/questions)
│       ├── responses.py   # Response API endpoints (/responses)
│       └── web/           # Web UI route handlers
│           ├── __init__.py
│           └── views.py   # HTML page routes (/, /surveys, /survey/{id})
│
├── templates/             # Jinja2 HTML templates
│   ├── base.html          # Base template with navbar & common layout
│   ├── index.html         # Home page
│   ├── surveys.html       # Surveys listing page
│   └── survey_detail.html # Individual survey detail page
│
├── static/                # Static assets
│   ├── css/
│   │   └── style.css      # Main stylesheet
│   ├── js/
│   │   ├── main.js        # Common JavaScript
│   │   ├── surveys.js     # Surveys listing page logic
│   │   └── survey_detail.js # Survey detail page logic
│   └── img/               # Images (empty, add as needed)
│
├── alembic/               # Database migrations (Alembic)
├── tests/                 # Test files
├── pyproject.toml         # Project dependencies (managed by uv)
├── uv.lock                # Lock file for dependencies
├── requirements.txt       # Legacy requirements file
├── .env                   # Environment variables (not committed)
└── README.md              # This file
```

## Where to Write What

| Folder/File | Purpose | When to Add |
|-------------|---------|-------------|
| `app/models/` | SQLAlchemy models defining database tables and relationships. | Add new entities (e.g., User, Category) here. Always inherit from `Base`. |
| `app/schemas/` | Pydantic models for request/response validation and serialization. | Add schemas matching your models. Use `from_attributes = True` for ORM objects. |
| `app/crud/` | Reusable database operations (create, read, update, delete). | Add complex DB queries here. Keep routers thin by calling CRUD functions. |
| `app/routers/` | API endpoints. REST API routes go in root, web UI routes in `routers/web/`. | Add new API endpoints here. Group by resource (e.g., users.py). |
| `app/routers/web/views.py` | HTML page routes using Jinja2 templates. | Add routes to render new pages here. |
| `app/main.py` | App initialization, middleware, static files, and router registration. | Register new routers here with `app.include_router()`. |
| `app/config.py` | App configuration using Pydantic Settings. | Add new environment variables/settings here. |
| `app/dependencies.py` | Shared dependencies (DB session, auth, etc.). | Add reusable FastAPI dependencies here. |
| `templates/` | Jinja2 HTML templates. Extend `base.html` for consistency. | Create new `.html` files for pages. Use `{% block %}` for customization. |
| `static/css/` | Stylesheets. | Add component/page-specific CSS files here. Import/link in templates. |
| `static/js/` | Client-side JavaScript. | Add interactivity logic. Fetch data from API endpoints. |
| `static/img/` | Images, icons, logos. | Add static images here. |
| `alembic/` | Database migrations. | Generate with `alembic revision --autogenerate -m "message"`, apply with `alembic upgrade head`. |
| `tests/` | Unit/integration tests. | Add pytest tests for models, CRUD, routers. |

## Getting Started

### Prerequisites
- Python 3.10+
- [uv](https://docs.astral.sh/uv/) package manager

### Installation

1. Install dependencies:
```bash
uv sync
```

2. Set up environment variables:
```bash
cp .env.example .env  # if exists, or edit .env
```

3. Run database migrations (after setting up Alembic):
```bash
alembic upgrade head
```

### Running the Application

Development server:
```bash
uv run uvicorn app.main:app --reload
```

The app will be available at:
- **API Docs**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Web UI**: http://localhost:8000/

## API Endpoints

| Method | Endpoint | Description |
## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | Home page (HTML) |
| GET | `/surveys` | Surveys list page (HTML) |
| GET | `/survey/{id}` | Survey detail page (HTML) |
| GET | `/health` | Health check |
| POST | `/surveys/` | Create a survey |
| GET | `/surveys/ | Get all surveys (paginated) |
| GET | `/surveys/year/{year}` | Get surveys by year |
| GET | `/surveys/{id}` | Get a specific survey |
| DELETE | `/surveys/{id}` | Delete a survey |
| POST | `/questions/survey/{survey_id}` | Create question with options |
| GET | `/questions/survey/{survey_id}` | Get questions for a survey |
| POST | `/responses/ | Create a survey response (submit answers) |
| GET | `/responses/{id}` | Get a specific response |
| GET | `/responses/survey/{survey_id} | Get responses for a survey (paginated) |

## Development Tips

- **Models first**: Define ORM models in `app/models/`, then create corresponding schemas.
- **Keep separation**: API logic in routers, DB logic in CRUD, validation in schemas.
- **Templates**: Use `{% extends "base.html" %` and define blocks for page-specific content.
- **Static files**: Link CSS/JS using `url_for('static', path='/css/style.css')`.
-                    {url_for('static', path='/js/script.js')} }
