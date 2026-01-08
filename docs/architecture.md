# Architecture Overview

## System Architecture

The Defense PM Tool follows a **Modular Monolith** architecture with clear boundaries between modules.

```
┌─────────────────────────────────────────────────────────────────┐
│                        Frontend (React)                          │
│    ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│    │ Programs │  │Activities│  │  Gantt   │  │   EVMS   │      │
│    │   Page   │  │   Page   │  │  Chart   │  │Dashboard │      │
│    └──────────┘  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ REST API (JSON)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend (FastAPI)                            │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                      API Layer                             │  │
│  │    /programs    /activities    /dependencies    /schedule  │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                    Service Layer                           │  │
│  │   ┌──────────┐   ┌──────────┐   ┌──────────┐             │  │
│  │   │   CPM    │   │   EVMS   │   │  Import  │             │  │
│  │   │  Engine  │   │Calculator│   │  Export  │             │  │
│  │   └──────────┘   └──────────┘   └──────────┘             │  │
│  └───────────────────────────────────────────────────────────┘  │
│                              │                                   │
│  ┌───────────────────────────────────────────────────────────┐  │
│  │                  Repository Layer                          │  │
│  │   ProgramRepo  ActivityRepo  DependencyRepo  WBSRepo      │  │
│  └───────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ Async SQLAlchemy
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                  │
│   ┌──────────────┐           ┌──────────────┐                   │
│   │  PostgreSQL  │           │    Redis     │                   │
│   │   (Primary)  │           │   (Cache)    │                   │
│   └──────────────┘           └──────────────┘                   │
└─────────────────────────────────────────────────────────────────┘
```

## Module Boundaries

### Schedule Manager
- Program CRUD operations
- Activity management
- Dependency tracking
- WBS hierarchy

### CPM Engine
- Forward pass calculation
- Backward pass calculation
- Float calculation
- Critical path identification

### EVMS Calculator
- Earned value calculations
- Performance indices
- Forecasting
- Variance analysis

## Data Flow

1. **Request Flow**: Client → Router → Service → Repository → Database
2. **Response Flow**: Database → Repository → Service → Schema → Client

## Key Design Decisions

1. **Async First**: All I/O operations use async/await for better performance
2. **Repository Pattern**: Abstracts database operations from business logic
3. **Pydantic Validation**: Input validation at API boundary
4. **NetworkX for CPM**: Leverages proven graph algorithms
5. **Decimal for Money**: Avoids floating-point errors in financial calculations
