# Defense Program Management Tool

A comprehensive defense program management system built with modern web technologies.

## Overview

The Defense PM Tool is a full-stack application designed to streamline the management of defense programs, projects, and resources. It provides a robust platform for tracking program milestones, managing budgets, coordinating teams, and ensuring compliance with defense standards.

### Key Features

- **Program Management**: Track multiple defense programs with hierarchical organization
- **Project Tracking**: Monitor project milestones, deliverables, and timelines
- **Resource Management**: Allocate and track resources across programs
- **Budget Tracking**: Real-time budget monitoring and forecasting
- **Compliance Management**: Ensure adherence to defense regulations and standards
- **Reporting**: Generate comprehensive reports and analytics
- **Role-Based Access Control**: Secure access with granular permissions

## Architecture

This is a monorepo project with the following structure:

```
defense-pm-tool/
├── api/                    # FastAPI backend (Python 3.11+)
│   ├── src/
│   │   ├── models/        # SQLAlchemy ORM models
│   │   ├── schemas/       # Pydantic validation schemas
│   │   ├── repositories/  # Data access layer
│   │   ├── services/      # Business logic
│   │   ├── api/v1/        # API route handlers
│   │   └── core/          # Auth, database, exceptions
│   ├── tests/             # API tests
│   └── alembic/           # Database migrations
├── web/                    # React frontend (TypeScript)
├── shared/                 # Shared types and constants
└── docs/                   # Documentation
```

### Technology Stack

#### Backend
- **FastAPI**: Modern, fast web framework for building APIs
- **SQLAlchemy**: Powerful ORM with async support
- **PostgreSQL**: Production-grade relational database
- **Alembic**: Database migration management
- **Pydantic**: Data validation using Python type hints
- **JWT**: Secure authentication and authorization

#### Frontend (Planned)
- **React**: Component-based UI library
- **TypeScript**: Type-safe JavaScript
- **Vite**: Fast build tool and dev server
- **TanStack Query**: Data fetching and caching
- **TailwindCSS**: Utility-first CSS framework

### Design Patterns

- **Repository Pattern**: Clean separation of data access logic
- **Service Pattern**: Encapsulated business logic
- **Dependency Injection**: Loosely coupled components
- **Clean Architecture**: Clear boundaries between layers

## Prerequisites

- Python 3.11 or higher
- PostgreSQL 14 or higher
- Node.js 18+ (for frontend, when implemented)
- Docker and Docker Compose (optional, for containerized deployment)

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd defense-pm-tool
```

### 2. Environment Configuration

Copy the example environment file and configure it:

```bash
cp .env.example .env
```

Edit `.env` and update the following variables:
- `DATABASE_URL`: Your PostgreSQL connection string
- `SECRET_KEY`: Generate a secure key (e.g., `openssl rand -hex 32`)
- Other configuration as needed

### 3. Backend Setup

#### Option A: Using Python Virtual Environment

```bash
cd api

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Linux/macOS:
source venv/bin/activate
# On Windows:
# venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Or using pyproject.toml
pip install -e ".[dev]"
```

#### Option B: Using Docker Compose

```bash
# Start all services (API + PostgreSQL)
docker-compose up -d
```

### 4. Database Setup

```bash
cd api

# Run database migrations
alembic upgrade head

# Optional: Seed initial data
# python scripts/seed_data.py
```

### 5. Run the Development Server

```bash
cd api

# Run with uvicorn
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at:
- API: http://localhost:8000
- API Documentation: http://localhost:8000/docs
- Alternative Documentation: http://localhost:8000/redoc

### 6. Running Tests

```bash
cd api

# Run all tests
pytest

# Run with coverage
pytest --cov=src --cov-report=html

# Run specific test file
pytest tests/test_main.py

# Run with verbose output
pytest -v
```

### 7. Code Quality

```bash
cd api

# Linting with ruff
ruff check src/

# Auto-fix issues
ruff check --fix src/

# Type checking with mypy
mypy src/

# Format code
ruff format src/
```

## Development Workflow

1. **Feature Development**
   - Create a feature branch: `git checkout -b feature/your-feature`
   - Write code following the established patterns
   - Write tests for new functionality
   - Ensure all tests pass and code quality checks succeed

2. **Database Changes**
   - Modify models in `api/src/models/`
   - Generate migration: `alembic revision --autogenerate -m "description"`
   - Review and edit the migration file
   - Apply migration: `alembic upgrade head`

3. **Code Review**
   - Ensure all tests pass
   - Run linters and type checkers
   - Submit pull request with clear description

## Project Structure Details

### API Layer (`api/src/api/`)
Route handlers that receive HTTP requests, validate input, call services, and return responses.

### Service Layer (`api/src/services/`)
Business logic that orchestrates operations, enforces business rules, and coordinates between repositories.

### Repository Layer (`api/src/repositories/`)
Data access layer that interacts with the database through SQLAlchemy ORM.

### Models (`api/src/models/`)
SQLAlchemy ORM models representing database tables and relationships.

### Schemas (`api/src/schemas/`)
Pydantic models for request validation and response serialization.

### Core (`api/src/core/`)
Shared utilities including authentication, database connection, exceptions, and dependencies.

## Configuration

All configuration is managed through environment variables using `pydantic-settings`.

Key configuration files:
- `.env`: Local environment variables (not committed)
- `.env.example`: Template for required environment variables
- `api/src/config.py`: Application settings and configuration

## Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Add users table"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history

# View current version
alembic current
```

## API Documentation

Once the server is running, interactive API documentation is available at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Deployment

### Docker Deployment

```bash
# Build and run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

### Production Checklist

- [ ] Set `ENV=production` in environment
- [ ] Generate strong `SECRET_KEY`
- [ ] Configure production database
- [ ] Set up SSL/TLS certificates
- [ ] Configure CORS for production domains
- [ ] Set up logging and monitoring
- [ ] Enable backup strategy for database
- [ ] Review and update security settings
- [ ] Set up CI/CD pipeline

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Write/update tests
5. Ensure all tests pass
6. Submit a pull request

## Security

- All passwords are hashed using bcrypt
- JWT tokens for authentication
- SQL injection prevention through ORM
- CORS configuration for frontend access
- Environment-based configuration
- Input validation using Pydantic

## License

[Specify your license here]

## Support

For questions or issues, please contact [your contact information] or open an issue in the repository.

## Roadmap

### Phase 1: Core Backend (Current)
- [x] Project structure and boilerplate
- [ ] User authentication and authorization
- [ ] Program management endpoints
- [ ] Project tracking endpoints
- [ ] Basic reporting

### Phase 2: Advanced Backend
- [ ] Budget management
- [ ] Resource allocation
- [ ] Document management
- [ ] Audit logging
- [ ] Advanced reporting and analytics

### Phase 3: Frontend Development
- [ ] React application setup
- [ ] Authentication UI
- [ ] Program management interface
- [ ] Project tracking dashboard
- [ ] Reporting interface

### Phase 4: Integration & Deployment
- [ ] End-to-end testing
- [ ] Performance optimization
- [ ] Production deployment
- [ ] Monitoring and logging
- [ ] Documentation completion
