# Defense Program Management Tool

Schedule optimization and EVMS analysis for defense program management.

## Tech Stack

- **Backend**: Python 3.11+ / FastAPI / SQLAlchemy 2.0
- **Frontend**: React 18 / TypeScript / TailwindCSS
- **Database**: PostgreSQL 15 with ltree extension
- **Cache**: Redis 7
- **Architecture**: Modular Monolith

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20 LTS
- Docker Desktop
- Git

### Setup

1. Clone the repository
```bash
   git clone https://github.com/your-org/defense-pm-tool.git
   cd defense-pm-tool
```

2. Copy environment file
```bash
   cp .env.example .env
```

3. Start databases
```bash
   docker-compose up -d
```

4. Setup backend
```bash
   cd api
   python -m venv venv
   .\venv\Scripts\activate  # Windows
   python -m pip install -r requirements.txt
   alembic upgrade head
   uvicorn src.main:app --reload
```

5. Setup frontend
```bash
   cd web
   npm install
   npm run dev
```

## Development

See [CLAUDE.md](CLAUDE.md) for coding standards and workflows.

## Documentation

- [Architecture](docs/architecture.md)
- [API Reference](docs/api.md)
- [CPM Algorithm](docs/cpm-algorithm.md)

## License

Proprietary - All rights reserved