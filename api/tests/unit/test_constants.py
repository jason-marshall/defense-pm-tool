"""Tests for application constants."""

from src.core import constants


class TestWBSConstants:
    """Tests for WBS-related constants."""

    def test_max_wbs_depth(self):
        """MAX_WBS_DEPTH should be 10."""
        assert constants.MAX_WBS_DEPTH == 10

    def test_max_wbs_children(self):
        """MAX_WBS_CHILDREN should be 100."""
        assert constants.MAX_WBS_CHILDREN == 100

    def test_max_wbs_elements_per_program(self):
        """MAX_WBS_ELEMENTS_PER_PROGRAM should be 10000."""
        assert constants.MAX_WBS_ELEMENTS_PER_PROGRAM == 10000


class TestActivityConstants:
    """Tests for activity-related constants."""

    def test_max_activity_duration(self):
        """MAX_ACTIVITY_DURATION should be approximately 5 years."""
        assert constants.MAX_ACTIVITY_DURATION == 365 * 5

    def test_min_activity_duration(self):
        """MIN_ACTIVITY_DURATION should be 0 (for milestones)."""
        assert constants.MIN_ACTIVITY_DURATION == 0

    def test_max_activities_per_program(self):
        """MAX_ACTIVITIES_PER_PROGRAM should be 50000."""
        assert constants.MAX_ACTIVITIES_PER_PROGRAM == 50000

    def test_max_dependencies_per_program(self):
        """MAX_DEPENDENCIES_PER_PROGRAM should be 100000."""
        assert constants.MAX_DEPENDENCIES_PER_PROGRAM == 100000


class TestCPMConstants:
    """Tests for CPM-related constants."""

    def test_cpm_timeout(self):
        """CPM_CALCULATION_TIMEOUT should be 30 seconds."""
        assert constants.CPM_CALCULATION_TIMEOUT == 30

    def test_near_critical_threshold(self):
        """NEAR_CRITICAL_THRESHOLD should be 5 days."""
        assert constants.NEAR_CRITICAL_THRESHOLD == 5

    def test_critical_path_threshold(self):
        """CRITICAL_PATH_THRESHOLD should be 0."""
        assert constants.CRITICAL_PATH_THRESHOLD == 0


class TestPaginationConstants:
    """Tests for pagination constants."""

    def test_default_page_size(self):
        """DEFAULT_PAGE_SIZE should be 50."""
        assert constants.DEFAULT_PAGE_SIZE == 50

    def test_max_page_size(self):
        """MAX_PAGE_SIZE should be 200."""
        assert constants.MAX_PAGE_SIZE == 200

    def test_min_page_size(self):
        """MIN_PAGE_SIZE should be 1."""
        assert constants.MIN_PAGE_SIZE == 1


class TestEVMSConstants:
    """Tests for EVMS-related constants."""

    def test_cpi_thresholds(self):
        """CPI thresholds should be defined."""
        assert constants.CPI_GREEN_THRESHOLD == 0.95
        assert constants.CPI_YELLOW_THRESHOLD == 0.90

    def test_spi_thresholds(self):
        """SPI thresholds should be defined."""
        assert constants.SPI_GREEN_THRESHOLD == 0.95
        assert constants.SPI_YELLOW_THRESHOLD == 0.90

    def test_vac_warning_threshold(self):
        """VAC_WARNING_THRESHOLD should be 10%."""
        assert constants.VAC_WARNING_THRESHOLD == 0.10

    def test_eac_methods(self):
        """EAC calculation methods should be defined."""
        assert constants.EAC_METHOD_CPI == "cpi"
        assert constants.EAC_METHOD_COMPOSITE == "composite"
        assert constants.EAC_METHOD_MANAGER == "manager"


class TestValidationConstants:
    """Tests for validation constants."""

    def test_string_lengths(self):
        """String length constants should be defined."""
        assert constants.MAX_NAME_LENGTH == 255
        assert constants.MAX_DESCRIPTION_LENGTH == 5000
        assert constants.MAX_WBS_CODE_LENGTH == 50
        assert constants.MAX_EMAIL_LENGTH == 255

    def test_password_requirements(self):
        """Password requirements should be defined."""
        assert constants.MIN_PASSWORD_LENGTH == 8
        assert constants.MAX_PASSWORD_LENGTH == 128

    def test_numeric_precision(self):
        """Numeric precision constants should be defined."""
        assert constants.CURRENCY_PRECISION == 15
        assert constants.CURRENCY_SCALE == 2
        assert constants.PERCENT_PRECISION == 5
        assert constants.PERCENT_SCALE == 2


class TestRateLimitConstants:
    """Tests for rate limiting constants."""

    def test_rate_limits(self):
        """Rate limit constants should be defined."""
        assert constants.RATE_LIMIT_AUTHENTICATED == 100
        assert constants.RATE_LIMIT_ANONYMOUS == 20
        assert constants.RATE_LIMIT_CPM_CALCULATION == 10


class TestCacheConstants:
    """Tests for cache TTL constants."""

    def test_cache_ttls(self):
        """Cache TTL constants should be defined."""
        assert constants.CACHE_TTL_PROGRAM == 300
        assert constants.CACHE_TTL_WBS_TREE == 60
        assert constants.CACHE_TTL_CPM_RESULTS == 30
        assert constants.CACHE_TTL_USER_SESSION == 3600


class TestFileConstants:
    """Tests for file import/export constants."""

    def test_max_import_file_size(self):
        """MAX_IMPORT_FILE_SIZE should be 50 MB."""
        assert constants.MAX_IMPORT_FILE_SIZE == 50 * 1024 * 1024

    def test_supported_import_formats(self):
        """Supported import formats should include common types."""
        assert ".xml" in constants.SUPPORTED_IMPORT_FORMATS
        assert ".csv" in constants.SUPPORTED_IMPORT_FORMATS
        assert ".json" in constants.SUPPORTED_IMPORT_FORMATS

    def test_max_csv_import_rows(self):
        """MAX_CSV_IMPORT_ROWS should be 100000."""
        assert constants.MAX_CSV_IMPORT_ROWS == 100000


class TestDateTimeConstants:
    """Tests for date/time constants."""

    def test_working_time(self):
        """Working time constants should be defined."""
        assert constants.WORKING_DAYS_PER_WEEK == 5
        assert constants.WORKING_HOURS_PER_DAY == 8
        assert constants.DEFAULT_WORKING_DAYS == (0, 1, 2, 3, 4)

    def test_date_formats(self):
        """Date format strings should be defined."""
        assert constants.DATE_FORMAT_DISPLAY == "%Y-%m-%d"
        assert constants.DATETIME_FORMAT_DISPLAY == "%Y-%m-%d %H:%M:%S"
