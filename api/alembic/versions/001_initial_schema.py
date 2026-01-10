"""Initial schema for Defense PM Tool.

Revision ID: 001
Revises: None
Create Date: 2026-01-08

Description:
    Creates the initial database schema including:
    - PostgreSQL extensions (uuid-ossp, ltree)
    - Enum types for user roles, program status, constraints, dependencies
    - Core tables: users, programs, wbs_elements, activities, dependencies
    - All indexes and constraints
    - Seeds initial admin user

This migration establishes the foundation for:
- User authentication and RBAC
- Program/project management
- Work Breakdown Structure (WBS) with ltree hierarchy
- Activity scheduling with CPM support
- Activity dependencies for critical path calculations
"""

from typing import Sequence, Union
from uuid import uuid4

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# Revision identifiers, used by Alembic.
revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Upgrade database schema.

    Creates all tables and seeds initial data.
    Operations are ordered to respect foreign key dependencies.
    """
    # =========================================================================
    # STEP 1: Enable PostgreSQL Extensions
    # =========================================================================
    # uuid-ossp: Provides UUID generation functions
    op.execute("CREATE EXTENSION IF NOT EXISTS \"uuid-ossp\"")

    # ltree: Provides hierarchical data type for WBS paths
    op.execute("CREATE EXTENSION IF NOT EXISTS ltree")

    # =========================================================================
    # STEP 2: Create Enum Types
    # =========================================================================
    # User role enum for RBAC (hierarchical permissions)
    user_role = postgresql.ENUM(
        "viewer",
        "analyst",
        "scheduler",
        "program_manager",
        "admin",
        name="user_role",
        create_type=False,
    )
    op.execute(
        "CREATE TYPE user_role AS ENUM "
        "('viewer', 'analyst', 'scheduler', 'program_manager', 'admin')"
    )

    # Program lifecycle status enum
    op.execute(
        "CREATE TYPE program_status AS ENUM "
        "('planning', 'active', 'complete', 'on_hold')"
    )

    # Activity scheduling constraint types (CPM)
    op.execute(
        "CREATE TYPE constraint_type AS ENUM "
        "('asap', 'alap', 'snet', 'snlt', 'fnet', 'fnlt')"
    )

    # Dependency types for activity relationships
    op.execute(
        "CREATE TYPE dependency_type AS ENUM "
        "('FS', 'SS', 'FF', 'SF')"
    )

    # =========================================================================
    # STEP 3: Create Users Table
    # =========================================================================
    op.create_table(
        "users",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            comment="Unique identifier (UUID v4)",
        ),
        # User credentials
        sa.Column(
            "email",
            sa.String(255),
            nullable=False,
            unique=True,
            comment="Unique email address for login",
        ),
        sa.Column(
            "hashed_password",
            sa.String(255),
            nullable=False,
            comment="Bcrypt hash of user password",
        ),
        # Profile
        sa.Column(
            "full_name",
            sa.String(255),
            nullable=False,
            comment="User's display name",
        ),
        # Account status
        sa.Column(
            "is_active",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("true"),
            comment="Whether the user account is active",
        ),
        # Role for authorization
        sa.Column(
            "role",
            postgresql.ENUM(
                "viewer", "analyst", "scheduler", "program_manager", "admin",
                name="user_role",
                create_type=False,
            ),
            nullable=False,
            server_default="viewer",
            comment="User role for access control",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Timestamp when record was created",
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
            comment="Timestamp when record was last updated",
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Timestamp when record was soft-deleted (null = active)",
        ),
        comment="User accounts for authentication and authorization",
    )

    # Users indexes
    op.create_index("ix_users_email", "users", ["email"], unique=True)
    op.create_index("ix_users_is_active", "users", ["is_active"])
    op.create_index("ix_users_role", "users", ["role"])
    op.create_index("ix_users_deleted_at", "users", ["deleted_at"])
    op.create_index(
        "ix_users_active_role",
        "users",
        ["is_active", "role"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index(
        "ix_users_email_lower",
        "users",
        [sa.text("LOWER(email)")],
        unique=True,
    )

    # =========================================================================
    # STEP 4: Create Programs Table
    # =========================================================================
    op.create_table(
        "programs",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            comment="Unique identifier (UUID v4)",
        ),
        # Unique program code
        sa.Column(
            "code",
            sa.String(50),
            nullable=False,
            unique=True,
            comment="Unique program code identifier",
        ),
        # Basic information
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Display name of the program",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Detailed description of the program",
        ),
        sa.Column(
            "contract_number",
            sa.String(100),
            nullable=True,
            unique=True,
            comment="Associated contract identifier",
        ),
        # Schedule dates
        sa.Column(
            "start_date",
            sa.Date,
            nullable=False,
            comment="Planned program start date",
        ),
        sa.Column(
            "end_date",
            sa.Date,
            nullable=False,
            comment="Planned program end date",
        ),
        # Status
        sa.Column(
            "status",
            postgresql.ENUM(
                "planning", "active", "complete", "on_hold",
                name="program_status",
                create_type=False,
            ),
            nullable=False,
            server_default="planning",
            comment="Current program lifecycle status",
        ),
        # Owner FK
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="RESTRICT"),
            nullable=False,
            comment="FK to user who owns this program",
        ),
        # Budget
        sa.Column(
            "budget_at_completion",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0.00",
            comment="Total authorized budget (BAC)",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        comment="Defense programs/projects",
    )

    # Programs indexes
    op.create_index("ix_programs_code", "programs", ["code"], unique=True)
    op.create_index("ix_programs_name", "programs", ["name"])
    op.create_index("ix_programs_contract_number", "programs", ["contract_number"])
    op.create_index("ix_programs_start_date", "programs", ["start_date"])
    op.create_index("ix_programs_end_date", "programs", ["end_date"])
    op.create_index("ix_programs_status", "programs", ["status"])
    op.create_index("ix_programs_owner_id", "programs", ["owner_id"])
    op.create_index("ix_programs_deleted_at", "programs", ["deleted_at"])
    op.create_index(
        "ix_programs_status_active",
        "programs",
        ["status", "owner_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    op.create_index("ix_programs_dates", "programs", ["start_date", "end_date"])

    # =========================================================================
    # STEP 5: Create WBS Elements Table
    # =========================================================================
    op.create_table(
        "wbs_elements",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            comment="Unique identifier (UUID v4)",
        ),
        # Foreign keys
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to parent program",
        ),
        sa.Column(
            "parent_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wbs_elements.id", ondelete="CASCADE"),
            nullable=True,
            comment="FK to parent WBS element (null for root)",
        ),
        # Basic information
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Display name of the WBS element",
        ),
        sa.Column(
            "wbs_code",
            sa.String(50),
            nullable=False,
            comment="Unique code within program (e.g., 1.2.3)",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Detailed description of the WBS element",
        ),
        # Hierarchy using ltree
        sa.Column(
            "path",
            postgresql.LTREE,
            nullable=False,
            comment="ltree path for hierarchy queries",
        ),
        sa.Column(
            "level",
            sa.Integer,
            nullable=False,
            server_default="1",
            comment="Depth in hierarchy (1 = root)",
        ),
        # EVMS control account
        sa.Column(
            "is_control_account",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="Whether this is an EVMS control account",
        ),
        # Budget
        sa.Column(
            "budget_at_completion",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0.00",
            comment="Allocated budget (BAC) for this element",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        comment="Work Breakdown Structure elements with hierarchy",
    )

    # WBS indexes
    op.create_index("ix_wbs_elements_program_id", "wbs_elements", ["program_id"])
    op.create_index("ix_wbs_elements_parent_id", "wbs_elements", ["parent_id"])
    op.create_index("ix_wbs_elements_is_control_account", "wbs_elements", ["is_control_account"])
    op.create_index("ix_wbs_elements_deleted_at", "wbs_elements", ["deleted_at"])
    op.create_index(
        "ix_wbs_elements_program_code",
        "wbs_elements",
        ["program_id", "wbs_code"],
        unique=True,
        postgresql_where=sa.text("deleted_at IS NULL"),
    )
    # GiST index on ltree path for efficient hierarchy queries
    op.create_index(
        "ix_wbs_elements_path_gist",
        "wbs_elements",
        ["path"],
        postgresql_using="gist",
    )
    op.create_index(
        "ix_wbs_elements_control_accounts",
        "wbs_elements",
        ["program_id", "is_control_account"],
        postgresql_where=sa.text("is_control_account = true AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_wbs_elements_program_level",
        "wbs_elements",
        ["program_id", "level"],
    )

    # =========================================================================
    # STEP 6: Create Activities Table
    # =========================================================================
    op.create_table(
        "activities",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            comment="Unique identifier (UUID v4)",
        ),
        # Foreign key to Program (for direct program queries)
        sa.Column(
            "program_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("programs.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to parent program",
        ),
        # Foreign key to WBS
        sa.Column(
            "wbs_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("wbs_elements.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to parent WBS element",
        ),
        # Unique activity code within program
        sa.Column(
            "code",
            sa.String(50),
            nullable=False,
            comment="Unique activity code within program",
        ),
        # Basic information
        sa.Column(
            "name",
            sa.String(255),
            nullable=False,
            comment="Activity name/description",
        ),
        sa.Column(
            "description",
            sa.Text,
            nullable=True,
            comment="Detailed description",
        ),
        # Duration
        sa.Column(
            "duration",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Duration in working days",
        ),
        # Planned dates
        sa.Column(
            "planned_start",
            sa.Date,
            nullable=True,
            comment="Baseline planned start date",
        ),
        sa.Column(
            "planned_finish",
            sa.Date,
            nullable=True,
            comment="Baseline planned finish date",
        ),
        # Actual dates
        sa.Column(
            "actual_start",
            sa.Date,
            nullable=True,
            comment="Actual start date",
        ),
        sa.Column(
            "actual_finish",
            sa.Date,
            nullable=True,
            comment="Actual finish date",
        ),
        # CPM calculated dates (forward pass)
        sa.Column(
            "early_start",
            sa.Date,
            nullable=True,
            comment="Early start from CPM forward pass",
        ),
        sa.Column(
            "early_finish",
            sa.Date,
            nullable=True,
            comment="Early finish from CPM forward pass",
        ),
        # CPM calculated dates (backward pass)
        sa.Column(
            "late_start",
            sa.Date,
            nullable=True,
            comment="Late start from CPM backward pass",
        ),
        sa.Column(
            "late_finish",
            sa.Date,
            nullable=True,
            comment="Late finish from CPM backward pass",
        ),
        # Float values
        sa.Column(
            "total_float",
            sa.Integer,
            nullable=True,
            comment="Total float in days (LS - ES)",
        ),
        sa.Column(
            "free_float",
            sa.Integer,
            nullable=True,
            comment="Free float in days",
        ),
        # Critical path flag
        sa.Column(
            "is_critical",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="True if on critical path (total_float = 0)",
        ),
        # Scheduling constraint
        sa.Column(
            "constraint_type",
            postgresql.ENUM(
                "asap", "alap", "snet", "snlt", "fnet", "fnlt",
                name="constraint_type",
                create_type=False,
            ),
            nullable=False,
            server_default="asap",
            comment="Scheduling constraint type",
        ),
        sa.Column(
            "constraint_date",
            sa.Date,
            nullable=True,
            comment="Date for scheduling constraint",
        ),
        # Progress
        sa.Column(
            "percent_complete",
            sa.Numeric(precision=5, scale=2),
            nullable=False,
            server_default="0.00",
            comment="Progress percentage (0-100)",
        ),
        # Milestone flag
        sa.Column(
            "is_milestone",
            sa.Boolean,
            nullable=False,
            server_default=sa.text("false"),
            comment="True if this is a milestone (duration=0)",
        ),
        # EVMS cost tracking
        sa.Column(
            "budgeted_cost",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0.00",
            comment="Budgeted cost (BCWS at completion)",
        ),
        sa.Column(
            "actual_cost",
            sa.Numeric(precision=15, scale=2),
            nullable=False,
            server_default="0.00",
            comment="Actual cost incurred (ACWP)",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Check constraints
        sa.CheckConstraint(
            "percent_complete >= 0 AND percent_complete <= 100",
            name="ck_activities_percent_complete",
        ),
        sa.CheckConstraint(
            "duration >= 0",
            name="ck_activities_duration",
        ),
        # Unique constraint: activity code must be unique within a program
        sa.UniqueConstraint(
            "program_id",
            "code",
            name="uq_activities_program_code",
        ),
        comment="Schedule activities with CPM support",
    )

    # Activities indexes
    op.create_index("ix_activities_program_id", "activities", ["program_id"])
    op.create_index("ix_activities_wbs_id", "activities", ["wbs_id"])
    op.create_index("ix_activities_code", "activities", ["code"])
    op.create_index("ix_activities_name", "activities", ["name"])
    op.create_index("ix_activities_planned_start", "activities", ["planned_start"])
    op.create_index("ix_activities_planned_finish", "activities", ["planned_finish"])
    op.create_index("ix_activities_actual_start", "activities", ["actual_start"])
    op.create_index("ix_activities_actual_finish", "activities", ["actual_finish"])
    op.create_index("ix_activities_total_float", "activities", ["total_float"])
    op.create_index("ix_activities_is_critical", "activities", ["is_critical"])
    op.create_index("ix_activities_is_milestone", "activities", ["is_milestone"])
    op.create_index("ix_activities_deleted_at", "activities", ["deleted_at"])
    op.create_index(
        "ix_activities_critical",
        "activities",
        ["program_id", "is_critical"],
        postgresql_where=sa.text("is_critical = true AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_activities_milestones",
        "activities",
        ["wbs_id", "is_milestone"],
        postgresql_where=sa.text("is_milestone = true AND deleted_at IS NULL"),
    )
    op.create_index(
        "ix_activities_dates",
        "activities",
        ["early_start", "early_finish"],
    )
    op.create_index(
        "ix_activities_incomplete",
        "activities",
        ["wbs_id", "percent_complete"],
        postgresql_where=sa.text("percent_complete < 100 AND deleted_at IS NULL"),
    )

    # =========================================================================
    # STEP 7: Create Dependencies Table
    # =========================================================================
    op.create_table(
        "dependencies",
        # Primary key
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("uuid_generate_v4()"),
            comment="Unique identifier (UUID v4)",
        ),
        # Foreign keys to activities
        sa.Column(
            "predecessor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to predecessor activity",
        ),
        sa.Column(
            "successor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("activities.id", ondelete="CASCADE"),
            nullable=False,
            comment="FK to successor activity",
        ),
        # Dependency type
        sa.Column(
            "dependency_type",
            postgresql.ENUM(
                "FS", "SS", "FF", "SF",
                name="dependency_type",
                create_type=False,
            ),
            nullable=False,
            server_default="FS",
            comment="Type of dependency (FS, SS, FF, SF)",
        ),
        # Lag/lead
        sa.Column(
            "lag",
            sa.Integer,
            nullable=False,
            server_default="0",
            comment="Lag (positive) or lead (negative) in working days",
        ),
        # Timestamps
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "deleted_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        # Unique constraint: only one dependency between any two activities
        sa.UniqueConstraint(
            "predecessor_id",
            "successor_id",
            name="uq_dependencies_predecessor_successor",
        ),
        comment="Activity dependencies for CPM scheduling",
    )

    # Dependencies indexes
    op.create_index("ix_dependencies_predecessor_id", "dependencies", ["predecessor_id"])
    op.create_index("ix_dependencies_successor_id", "dependencies", ["successor_id"])
    op.create_index("ix_dependencies_deleted_at", "dependencies", ["deleted_at"])
    op.create_index(
        "ix_dependencies_activities",
        "dependencies",
        ["predecessor_id", "successor_id"],
    )
    op.create_index(
        "ix_dependencies_active",
        "dependencies",
        ["predecessor_id", "successor_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )

    # =========================================================================
    # STEP 8: Seed Initial Admin User
    # =========================================================================
    # Password hash for "changeme" using bcrypt
    # Generated with: import bcrypt; bcrypt.hashpw(b"changeme", bcrypt.gensalt()).decode()
    admin_password_hash = "$2b$12$LQv3c1yqBWVHxkd0LHAkCOYz6TtxMQJqhN8/X4ooP5GwBJlF0sKLi"

    op.execute(
        f"""
        INSERT INTO users (id, email, hashed_password, full_name, is_active, role)
        VALUES (
            uuid_generate_v4(),
            'admin@example.com',
            '{admin_password_hash}',
            'System Administrator',
            true,
            'admin'
        )
        """
    )


def downgrade() -> None:
    """
    Downgrade database schema.

    Drops all tables and types in reverse order of creation.
    Data will be lost - use with caution!
    """
    # =========================================================================
    # STEP 1: Drop Tables (reverse order to respect FK dependencies)
    # =========================================================================
    op.drop_table("dependencies")
    op.drop_table("activities")
    op.drop_table("wbs_elements")
    op.drop_table("programs")
    op.drop_table("users")

    # =========================================================================
    # STEP 2: Drop Enum Types
    # =========================================================================
    op.execute("DROP TYPE IF EXISTS dependency_type")
    op.execute("DROP TYPE IF EXISTS constraint_type")
    op.execute("DROP TYPE IF EXISTS program_status")
    op.execute("DROP TYPE IF EXISTS user_role")

    # =========================================================================
    # STEP 3: Note on Extensions
    # =========================================================================
    # We don't drop uuid-ossp and ltree extensions as they may be used
    # by other schemas or applications in the same database.
    # If you need to drop them, uncomment the following:
    # op.execute('DROP EXTENSION IF EXISTS ltree')
    # op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')
