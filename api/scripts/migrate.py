#!/usr/bin/env python3
"""Database migration helper script.

This script provides a convenient CLI interface for common Alembic
migration operations. It wraps Alembic commands with helpful defaults
and better error handling.

Usage:
    python scripts/migrate.py upgrade              # Upgrade to latest
    python scripts/migrate.py upgrade head         # Upgrade to latest (explicit)
    python scripts/migrate.py upgrade +1           # Upgrade one revision
    python scripts/migrate.py upgrade 001          # Upgrade to specific revision
    python scripts/migrate.py downgrade -1         # Downgrade one revision
    python scripts/migrate.py downgrade base       # Downgrade to empty database
    python scripts/migrate.py current              # Show current revision
    python scripts/migrate.py history              # Show migration history
    python scripts/migrate.py generate "message"   # Generate new migration

Environment Variables:
    DATABASE_URL: PostgreSQL connection string (required)

Examples:
    # Development workflow
    export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/defense_pm"
    python scripts/migrate.py upgrade

    # Generate a new migration after model changes
    python scripts/migrate.py generate "add user preferences table"

    # Rollback the last migration
    python scripts/migrate.py downgrade -1
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path


def get_project_root() -> Path:
    """Get the project root directory (api/)."""
    return Path(__file__).resolve().parent.parent


def run_alembic(args: list[str], check: bool = True) -> subprocess.CompletedProcess:
    """
    Run an Alembic command.

    Args:
        args: Command line arguments to pass to alembic
        check: Whether to raise on non-zero exit code

    Returns:
        CompletedProcess instance with stdout/stderr
    """
    project_root = get_project_root()

    # Ensure we're in the api directory for alembic.ini
    env = os.environ.copy()
    env["PYTHONPATH"] = str(project_root)

    cmd = ["alembic"] + args

    print(f"Running: {' '.join(cmd)}")
    print("-" * 60)

    result = subprocess.run(
        cmd,
        cwd=str(project_root),
        env=env,
        capture_output=False,  # Let output flow to console
        check=False,
    )

    if check and result.returncode != 0:
        print(f"\nError: Alembic command failed with exit code {result.returncode}")
        sys.exit(result.returncode)

    return result


def cmd_upgrade(args: argparse.Namespace) -> None:
    """
    Upgrade database schema.

    Applies pending migrations to bring the database up to the
    specified revision (default: head/latest).
    """
    revision = args.revision or "head"
    print(f"Upgrading database to revision: {revision}")
    print()
    run_alembic(["upgrade", revision])
    print()
    print("Upgrade complete!")


def cmd_downgrade(args: argparse.Namespace) -> None:
    """
    Downgrade database schema.

    Reverts migrations to bring the database down to the
    specified revision.
    """
    revision = args.revision
    if not revision:
        print("Error: Revision is required for downgrade")
        print("  Use '-1' to downgrade one revision")
        print("  Use 'base' to downgrade to empty database")
        sys.exit(1)

    # Safety confirmation for destructive operations
    if revision == "base":
        print("WARNING: This will drop ALL tables and data!")
        confirm = input("Type 'yes' to confirm: ")
        if confirm.lower() != "yes":
            print("Aborted.")
            sys.exit(0)

    print(f"Downgrading database to revision: {revision}")
    print()
    run_alembic(["downgrade", revision])
    print()
    print("Downgrade complete!")


def cmd_current(args: argparse.Namespace) -> None:
    """
    Show current database revision.

    Displays the current migration revision applied to the database.
    """
    print("Current database revision:")
    print()
    run_alembic(["current", "--verbose"])


def cmd_history(args: argparse.Namespace) -> None:
    """
    Show migration history.

    Lists all available migrations with their revision IDs
    and descriptions.
    """
    print("Migration history:")
    print()

    history_args = ["history"]
    if args.verbose:
        history_args.append("--verbose")
    if args.range:
        history_args.extend(["--rev-range", args.range])

    run_alembic(history_args)


def cmd_generate(args: argparse.Namespace) -> None:
    """
    Generate a new migration.

    Creates a new migration file by comparing the current database
    schema with the SQLAlchemy models (autogenerate).
    """
    message = args.message
    if not message:
        print("Error: Migration message is required")
        print("  Example: python scripts/migrate.py generate 'add user preferences'")
        sys.exit(1)

    print(f"Generating migration: {message}")
    print()

    gen_args = ["revision", "--autogenerate", "-m", message]
    run_alembic(gen_args)

    print()
    print("Migration generated! Review the file before applying.")


def cmd_heads(args: argparse.Namespace) -> None:
    """
    Show all head revisions.

    Useful when dealing with branched migrations.
    """
    print("Head revisions:")
    print()
    run_alembic(["heads", "--verbose"])


def cmd_branches(args: argparse.Namespace) -> None:
    """
    Show migration branches.

    Displays any branch points in the migration history.
    """
    print("Migration branches:")
    print()
    run_alembic(["branches", "--verbose"])


def cmd_stamp(args: argparse.Namespace) -> None:
    """
    Stamp database with revision without running migrations.

    Useful for marking a database as being at a certain revision
    when migrations were applied manually.
    """
    revision = args.revision
    if not revision:
        print("Error: Revision is required for stamp")
        sys.exit(1)

    print(f"Stamping database as revision: {revision}")
    print()
    run_alembic(["stamp", revision])
    print()
    print("Database stamped!")


def cmd_check(args: argparse.Namespace) -> None:
    """
    Check if database is up to date.

    Exits with code 0 if database is at head, 1 otherwise.
    """
    print("Checking database status...")
    print()
    result = run_alembic(["check"], check=False)

    if result.returncode == 0:
        print("Database is up to date!")
    else:
        print("Database has pending migrations.")
        sys.exit(1)


def main() -> None:
    """Main entry point for the migration script."""
    parser = argparse.ArgumentParser(
        description="Database migration helper for Defense PM Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s upgrade                  Upgrade to latest revision
  %(prog)s upgrade 001              Upgrade to revision 001
  %(prog)s upgrade +2               Upgrade 2 revisions
  %(prog)s downgrade -1             Downgrade 1 revision
  %(prog)s downgrade base           Downgrade to empty database
  %(prog)s current                  Show current revision
  %(prog)s history                  Show all migrations
  %(prog)s generate "add users"     Generate new migration
        """,
    )

    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        required=True,
    )

    # Upgrade command
    upgrade_parser = subparsers.add_parser(
        "upgrade",
        help="Upgrade database schema",
        description="Apply migrations to upgrade the database schema.",
    )
    upgrade_parser.add_argument(
        "revision",
        nargs="?",
        default="head",
        help="Target revision (default: head). Use +N for relative.",
    )
    upgrade_parser.set_defaults(func=cmd_upgrade)

    # Downgrade command
    downgrade_parser = subparsers.add_parser(
        "downgrade",
        help="Downgrade database schema",
        description="Revert migrations to downgrade the database schema.",
    )
    downgrade_parser.add_argument(
        "revision",
        help="Target revision. Use -N for relative, 'base' for empty.",
    )
    downgrade_parser.set_defaults(func=cmd_downgrade)

    # Current command
    current_parser = subparsers.add_parser(
        "current",
        help="Show current database revision",
    )
    current_parser.set_defaults(func=cmd_current)

    # History command
    history_parser = subparsers.add_parser(
        "history",
        help="Show migration history",
    )
    history_parser.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output",
    )
    history_parser.add_argument(
        "-r", "--range",
        help="Revision range (e.g., 'base:head', '001:003')",
    )
    history_parser.set_defaults(func=cmd_history)

    # Generate command
    generate_parser = subparsers.add_parser(
        "generate",
        help="Generate a new migration",
        description="Auto-generate a migration by comparing models to database.",
    )
    generate_parser.add_argument(
        "message",
        help="Migration description (e.g., 'add user preferences table')",
    )
    generate_parser.set_defaults(func=cmd_generate)

    # Heads command
    heads_parser = subparsers.add_parser(
        "heads",
        help="Show head revisions",
    )
    heads_parser.set_defaults(func=cmd_heads)

    # Branches command
    branches_parser = subparsers.add_parser(
        "branches",
        help="Show migration branches",
    )
    branches_parser.set_defaults(func=cmd_branches)

    # Stamp command
    stamp_parser = subparsers.add_parser(
        "stamp",
        help="Stamp database with revision",
        description="Mark database at revision without running migrations.",
    )
    stamp_parser.add_argument(
        "revision",
        help="Revision to stamp (e.g., 'head', '001')",
    )
    stamp_parser.set_defaults(func=cmd_stamp)

    # Check command
    check_parser = subparsers.add_parser(
        "check",
        help="Check if database is up to date",
    )
    check_parser.set_defaults(func=cmd_check)

    # Parse and execute
    args = parser.parse_args()

    # Check for DATABASE_URL
    if "DATABASE_URL" not in os.environ:
        print("Warning: DATABASE_URL environment variable not set")
        print("Alembic will use the value from src/config.py")
        print()

    # Run the command
    args.func(args)


if __name__ == "__main__":
    main()
