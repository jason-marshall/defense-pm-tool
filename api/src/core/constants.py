"""Application-wide constants for the Defense PM Tool.

This module centralizes configuration constants used throughout the application.
These values define limits, thresholds, and default settings.

Categories:
- WBS Hierarchy: Depth limits for Work Breakdown Structure
- Scheduling: Activity and CPM calculation limits
- Pagination: Default and maximum page sizes
- EVMS: Earned Value Management thresholds
- Validation: Input validation limits
"""

from typing import Final

# =============================================================================
# WBS (Work Breakdown Structure) Constants
# =============================================================================

# Maximum depth for WBS hierarchy (root = level 1)
# 10 levels is typical for large defense programs (MIL-STD-881E compliant)
MAX_WBS_DEPTH: Final[int] = 10

# Maximum number of direct children per WBS element
MAX_WBS_CHILDREN: Final[int] = 100

# Maximum total WBS elements per program
MAX_WBS_ELEMENTS_PER_PROGRAM: Final[int] = 10000


# =============================================================================
# Activity & Scheduling Constants
# =============================================================================

# Maximum activity duration in working days (approximately 5 years)
# 260 working days per year (52 weeks * 5 days)
MAX_ACTIVITY_DURATION: Final[int] = 365 * 5  # 1825 days

# Minimum activity duration (0 = milestone)
MIN_ACTIVITY_DURATION: Final[int] = 0

# Maximum activities per program
MAX_ACTIVITIES_PER_PROGRAM: Final[int] = 50000

# Maximum dependencies per program
MAX_DEPENDENCIES_PER_PROGRAM: Final[int] = 100000


# =============================================================================
# CPM (Critical Path Method) Calculation Constants
# =============================================================================

# Timeout for CPM calculation in seconds
# Prevents runaway calculations on malformed schedules
CPM_CALCULATION_TIMEOUT: Final[int] = 30

# Near-critical threshold in days of total float
# Activities with float <= this value are considered near-critical
NEAR_CRITICAL_THRESHOLD: Final[int] = 5

# Critical path threshold (activities with this float are critical)
CRITICAL_PATH_THRESHOLD: Final[int] = 0

# Maximum iterations for schedule leveling
MAX_LEVELING_ITERATIONS: Final[int] = 1000


# =============================================================================
# Pagination Constants
# =============================================================================

# Default number of items per page
DEFAULT_PAGE_SIZE: Final[int] = 50

# Maximum items per page (to prevent performance issues)
MAX_PAGE_SIZE: Final[int] = 200

# Minimum items per page
MIN_PAGE_SIZE: Final[int] = 1

# Default starting page (1-indexed)
DEFAULT_PAGE: Final[int] = 1


# =============================================================================
# EVMS (Earned Value Management System) Constants
# =============================================================================

# Cost Performance Index (CPI) thresholds
CPI_GREEN_THRESHOLD: Final[float] = 0.95  # Good performance
CPI_YELLOW_THRESHOLD: Final[float] = 0.90  # Warning
# Below yellow = red (poor performance)

# Schedule Performance Index (SPI) thresholds
SPI_GREEN_THRESHOLD: Final[float] = 0.95  # On schedule
SPI_YELLOW_THRESHOLD: Final[float] = 0.90  # Behind schedule
# Below yellow = red (significantly behind)

# Variance at Completion (VAC) warning threshold
# Percentage of BAC that triggers variance warning
VAC_WARNING_THRESHOLD: Final[float] = 0.10  # 10% variance

# Estimate at Completion (EAC) calculation methods
EAC_METHOD_CPI: Final[str] = "cpi"  # EAC = BAC / CPI
EAC_METHOD_COMPOSITE: Final[str] = "composite"  # EAC = AC + (BAC - EV) / (CPI * SPI)
EAC_METHOD_MANAGER: Final[str] = "manager"  # Manual estimate


# =============================================================================
# Validation Constants
# =============================================================================

# Maximum string lengths
MAX_NAME_LENGTH: Final[int] = 255
MAX_DESCRIPTION_LENGTH: Final[int] = 5000
MAX_WBS_CODE_LENGTH: Final[int] = 50
MAX_CONTRACT_NUMBER_LENGTH: Final[int] = 100
MAX_EMAIL_LENGTH: Final[int] = 255

# Password requirements
MIN_PASSWORD_LENGTH: Final[int] = 8
MAX_PASSWORD_LENGTH: Final[int] = 128

# Numeric precision for financial values
CURRENCY_PRECISION: Final[int] = 15  # Total digits
CURRENCY_SCALE: Final[int] = 2  # Decimal places

# Percent complete precision
PERCENT_PRECISION: Final[int] = 5  # Total digits
PERCENT_SCALE: Final[int] = 2  # Decimal places


# =============================================================================
# API Rate Limiting Constants
# =============================================================================

# Requests per minute for authenticated users
RATE_LIMIT_AUTHENTICATED: Final[int] = 100

# Requests per minute for unauthenticated users
RATE_LIMIT_ANONYMOUS: Final[int] = 20

# Requests per minute for CPM calculation endpoints
RATE_LIMIT_CPM_CALCULATION: Final[int] = 10


# =============================================================================
# Cache Constants
# =============================================================================

# Cache TTL for program data (seconds)
CACHE_TTL_PROGRAM: Final[int] = 300  # 5 minutes

# Cache TTL for WBS tree (seconds)
CACHE_TTL_WBS_TREE: Final[int] = 60  # 1 minute

# Cache TTL for CPM results (seconds)
CACHE_TTL_CPM_RESULTS: Final[int] = 30  # 30 seconds

# Cache TTL for user session (seconds)
CACHE_TTL_USER_SESSION: Final[int] = 3600  # 1 hour


# =============================================================================
# File Import/Export Constants
# =============================================================================

# Maximum file size for imports (bytes)
MAX_IMPORT_FILE_SIZE: Final[int] = 50 * 1024 * 1024  # 50 MB

# Supported import formats
SUPPORTED_IMPORT_FORMATS: Final[tuple[str, ...]] = (
    ".xml",  # MS Project XML
    ".mpp",  # MS Project (via converter)
    ".csv",  # CSV import
    ".json",  # JSON import
)

# Maximum rows in CSV import
MAX_CSV_IMPORT_ROWS: Final[int] = 100000


# =============================================================================
# Date/Time Constants
# =============================================================================

# Working days per week (for schedule calculations)
WORKING_DAYS_PER_WEEK: Final[int] = 5

# Working hours per day
WORKING_HOURS_PER_DAY: Final[int] = 8

# Default working days (Monday=0 to Friday=4)
DEFAULT_WORKING_DAYS: Final[tuple[int, ...]] = (0, 1, 2, 3, 4)

# Date format for display
DATE_FORMAT_DISPLAY: Final[str] = "%Y-%m-%d"

# DateTime format for display
DATETIME_FORMAT_DISPLAY: Final[str] = "%Y-%m-%d %H:%M:%S"
