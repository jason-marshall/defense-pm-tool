"""Unit tests for EV Method Calculator.

Tests all EV calculation methods per EVMS standards.
"""

from decimal import Decimal

import pytest

from src.models.enums import EVMethod
from src.services.ev_methods import (
    EVCalculationInput,
    EVMethodCalculator,
    Milestone,
    get_ev_method_info,
    validate_milestone_weights,
)


class TestEVMethodEnum:
    """Tests for EVMethod enum."""

    def test_all_methods_have_display_names(self) -> None:
        """All EV methods should have display names."""
        for method in EVMethod:
            assert method.display_name is not None
            assert len(method.display_name) > 0

    def test_all_methods_have_descriptions(self) -> None:
        """All EV methods should have descriptions."""
        for method in EVMethod:
            assert method.description is not None
            assert len(method.description) > 0

    def test_milestone_weight_requires_milestones(self) -> None:
        """Milestone weight method should require milestones."""
        assert EVMethod.MILESTONE_WEIGHT.requires_milestones is True
        assert EVMethod.PERCENT_COMPLETE.requires_milestones is False

    def test_apportioned_requires_base_activity(self) -> None:
        """Apportioned method should require base activity."""
        assert EVMethod.APPORTIONED.requires_base_activity is True
        assert EVMethod.ZERO_HUNDRED.requires_base_activity is False


class TestZeroHundredMethod:
    """Tests for 0/100 EV method."""

    @pytest.fixture
    def calculator(self) -> EVMethodCalculator:
        """Create calculator instance."""
        return EVMethodCalculator()

    def test_zero_percent_when_not_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return 0 BCWP when not complete."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("5000.00"),
            percent_complete=Decimal("50.00"),
            is_started=True,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.ZERO_HUNDRED, input_data)

        assert result.bcwp == Decimal("0.00")
        assert result.earned_percent == Decimal("0.00")
        assert result.method_used == EVMethod.ZERO_HUNDRED

    def test_hundred_percent_when_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return full BAC when complete."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("10000.00"),
            percent_complete=Decimal("100.00"),
            is_started=True,
            is_completed=True,
        )

        result = calculator.calculate(EVMethod.ZERO_HUNDRED, input_data)

        assert result.bcwp == Decimal("10000.00")
        assert result.earned_percent == Decimal("100.00")

    def test_zero_when_not_started(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return 0 when not started."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("0.00"),
            percent_complete=Decimal("0.00"),
            is_started=False,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.ZERO_HUNDRED, input_data)

        assert result.bcwp == Decimal("0.00")


class TestFiftyFiftyMethod:
    """Tests for 50/50 EV method."""

    @pytest.fixture
    def calculator(self) -> EVMethodCalculator:
        """Create calculator instance."""
        return EVMethodCalculator()

    def test_zero_when_not_started(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return 0 when not started."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("0.00"),
            percent_complete=Decimal("0.00"),
            is_started=False,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.FIFTY_FIFTY, input_data)

        assert result.bcwp == Decimal("0.00")
        assert result.earned_percent == Decimal("0.00")

    def test_fifty_percent_when_started(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return 50% of BAC when started."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("5000.00"),
            percent_complete=Decimal("25.00"),
            is_started=True,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.FIFTY_FIFTY, input_data)

        assert result.bcwp == Decimal("5000.00")
        assert result.earned_percent == Decimal("50.00")

    def test_hundred_percent_when_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return full BAC when complete."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("10000.00"),
            percent_complete=Decimal("100.00"),
            is_started=True,
            is_completed=True,
        )

        result = calculator.calculate(EVMethod.FIFTY_FIFTY, input_data)

        assert result.bcwp == Decimal("10000.00")
        assert result.earned_percent == Decimal("100.00")


class TestPercentCompleteMethod:
    """Tests for percent complete EV method."""

    @pytest.fixture
    def calculator(self) -> EVMethodCalculator:
        """Create calculator instance."""
        return EVMethodCalculator()

    def test_zero_percent_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return 0 BCWP for 0% complete."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("0.00"),
            percent_complete=Decimal("0.00"),
            is_started=False,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.PERCENT_COMPLETE, input_data)

        assert result.bcwp == Decimal("0.00")
        assert result.earned_percent == Decimal("0.00")

    def test_partial_percent_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should calculate BCWP based on percent complete."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("5000.00"),
            percent_complete=Decimal("35.00"),
            is_started=True,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.PERCENT_COMPLETE, input_data)

        assert result.bcwp == Decimal("3500.00")
        assert result.earned_percent == Decimal("35.00")

    def test_hundred_percent_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return full BAC for 100% complete."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("10000.00"),
            percent_complete=Decimal("100.00"),
            is_started=True,
            is_completed=True,
        )

        result = calculator.calculate(EVMethod.PERCENT_COMPLETE, input_data)

        assert result.bcwp == Decimal("10000.00")
        assert result.earned_percent == Decimal("100.00")

    def test_fractional_percent(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should handle fractional percentages."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("5000.00"),
            percent_complete=Decimal("33.33"),
            is_started=True,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.PERCENT_COMPLETE, input_data)

        assert result.bcwp == Decimal("3333.00")


class TestMilestoneWeightMethod:
    """Tests for milestone weight EV method."""

    @pytest.fixture
    def calculator(self) -> EVMethodCalculator:
        """Create calculator instance."""
        return EVMethodCalculator()

    def test_no_milestones_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return 0 when no milestones complete."""
        milestones = [
            Milestone(name="Design", weight=Decimal("0.25"), is_complete=False),
            Milestone(name="Build", weight=Decimal("0.50"), is_complete=False),
            Milestone(name="Test", weight=Decimal("0.25"), is_complete=False),
        ]
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("0.00"),
            percent_complete=Decimal("0.00"),
            is_started=False,
            is_completed=False,
            milestones=milestones,
        )

        result = calculator.calculate(EVMethod.MILESTONE_WEIGHT, input_data)

        assert result.bcwp == Decimal("0.00")
        assert result.earned_percent == Decimal("0.00")

    def test_partial_milestones_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should calculate based on completed milestone weights."""
        milestones = [
            Milestone(name="Design", weight=Decimal("0.25"), is_complete=True),
            Milestone(name="Build", weight=Decimal("0.50"), is_complete=False),
            Milestone(name="Test", weight=Decimal("0.25"), is_complete=False),
        ]
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("2500.00"),
            percent_complete=Decimal("25.00"),
            is_started=True,
            is_completed=False,
            milestones=milestones,
        )

        result = calculator.calculate(EVMethod.MILESTONE_WEIGHT, input_data)

        assert result.bcwp == Decimal("2500.00")
        assert result.earned_percent == Decimal("25.00")

    def test_all_milestones_complete(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should return full BAC when all milestones complete."""
        milestones = [
            Milestone(name="Design", weight=Decimal("0.25"), is_complete=True),
            Milestone(name="Build", weight=Decimal("0.50"), is_complete=True),
            Milestone(name="Test", weight=Decimal("0.25"), is_complete=True),
        ]
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("10000.00"),
            percent_complete=Decimal("100.00"),
            is_started=True,
            is_completed=True,
            milestones=milestones,
        )

        result = calculator.calculate(EVMethod.MILESTONE_WEIGHT, input_data)

        assert result.bcwp == Decimal("10000.00")
        assert result.earned_percent == Decimal("100.00")

    def test_raises_without_milestones(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should raise error if milestones not provided."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("5000.00"),
            percent_complete=Decimal("50.00"),
            is_started=True,
            is_completed=False,
            milestones=None,
        )

        with pytest.raises(ValueError, match="milestone definitions"):
            calculator.calculate(EVMethod.MILESTONE_WEIGHT, input_data)


class TestLOEMethod:
    """Tests for Level of Effort EV method."""

    @pytest.fixture
    def calculator(self) -> EVMethodCalculator:
        """Create calculator instance."""
        return EVMethodCalculator()

    def test_bcwp_equals_bcws(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """LOE should always have BCWP = BCWS."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("5000.00"),
            percent_complete=Decimal("30.00"),  # Ignored for LOE
            is_started=True,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.LOE, input_data)

        assert result.bcwp == Decimal("5000.00")
        assert result.method_used == EVMethod.LOE

    def test_loe_earned_percent(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """LOE earned percent should be BCWS/BAC."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("7500.00"),
            percent_complete=Decimal("50.00"),
            is_started=True,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.LOE, input_data)

        assert result.bcwp == Decimal("7500.00")
        assert result.earned_percent == Decimal("75.00")

    def test_loe_zero_bcws(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """LOE should return 0 when BCWS is 0."""
        input_data = EVCalculationInput(
            bac=Decimal("10000.00"),
            bcws=Decimal("0.00"),
            percent_complete=Decimal("0.00"),
            is_started=False,
            is_completed=False,
        )

        result = calculator.calculate(EVMethod.LOE, input_data)

        assert result.bcwp == Decimal("0.00")


class TestApportionedMethod:
    """Tests for apportioned effort EV method."""

    @pytest.fixture
    def calculator(self) -> EVMethodCalculator:
        """Create calculator instance."""
        return EVMethodCalculator()

    def test_apportioned_calculation(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should calculate BCWP as factor * base_BCWP."""
        input_data = EVCalculationInput(
            bac=Decimal("2000.00"),
            bcws=Decimal("1000.00"),
            percent_complete=Decimal("0.00"),
            is_started=True,
            is_completed=False,
            base_bcwp=Decimal("5000.00"),
            apportionment_factor=Decimal("0.20"),
        )

        result = calculator.calculate(EVMethod.APPORTIONED, input_data)

        assert result.bcwp == Decimal("1000.00")
        assert result.method_used == EVMethod.APPORTIONED

    def test_raises_without_base_bcwp(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should raise error if base_bcwp not provided."""
        input_data = EVCalculationInput(
            bac=Decimal("2000.00"),
            bcws=Decimal("1000.00"),
            percent_complete=Decimal("0.00"),
            is_started=True,
            is_completed=False,
            apportionment_factor=Decimal("0.20"),
        )

        with pytest.raises(ValueError, match="base_bcwp"):
            calculator.calculate(EVMethod.APPORTIONED, input_data)

    def test_raises_without_factor(
        self,
        calculator: EVMethodCalculator,
    ) -> None:
        """Should raise error if factor not provided."""
        input_data = EVCalculationInput(
            bac=Decimal("2000.00"),
            bcws=Decimal("1000.00"),
            percent_complete=Decimal("0.00"),
            is_started=True,
            is_completed=False,
            base_bcwp=Decimal("5000.00"),
        )

        with pytest.raises(ValueError, match="apportionment_factor"):
            calculator.calculate(EVMethod.APPORTIONED, input_data)


class TestValidateMilestoneWeights:
    """Tests for milestone weight validation."""

    def test_valid_weights_sum_to_one(self) -> None:
        """Should return True when weights sum to 1.0."""
        milestones = [
            {"name": "Design", "weight": 0.25},
            {"name": "Build", "weight": 0.50},
            {"name": "Test", "weight": 0.25},
        ]

        assert validate_milestone_weights(milestones) is True

    def test_invalid_weights_under_one(self) -> None:
        """Should return False when weights sum to < 1.0."""
        milestones = [
            {"name": "Design", "weight": 0.25},
            {"name": "Build", "weight": 0.50},
        ]

        assert validate_milestone_weights(milestones) is False

    def test_invalid_weights_over_one(self) -> None:
        """Should return False when weights sum to > 1.0."""
        milestones = [
            {"name": "Design", "weight": 0.50},
            {"name": "Build", "weight": 0.60},
        ]

        assert validate_milestone_weights(milestones) is False

    def test_empty_milestones(self) -> None:
        """Should return False for empty list."""
        assert validate_milestone_weights([]) is False


class TestGetEVMethodInfo:
    """Tests for get_ev_method_info function."""

    def test_returns_all_methods(self) -> None:
        """Should return info for all EV methods."""
        info = get_ev_method_info()

        assert len(info) == len(EVMethod)

    def test_info_structure(self) -> None:
        """Each method info should have required keys."""
        info = get_ev_method_info()

        for method_info in info:
            assert "value" in method_info
            assert "display_name" in method_info
            assert "description" in method_info
            assert "recommended_duration" in method_info

    def test_info_values_match_enum(self) -> None:
        """Values should match enum values."""
        info = get_ev_method_info()
        values = {m["value"] for m in info}

        expected = {method.value for method in EVMethod}
        assert values == expected


class TestMilestoneFromDict:
    """Tests for Milestone.from_dict method."""

    def test_from_dict_complete(self) -> None:
        """Should create milestone from complete dict."""
        data = {
            "name": "Design Review",
            "weight": 0.25,
            "is_complete": True,
        }

        milestone = Milestone.from_dict(data)

        assert milestone.name == "Design Review"
        assert milestone.weight == Decimal("0.25")
        assert milestone.is_complete is True

    def test_from_dict_defaults(self) -> None:
        """Should use defaults for missing keys."""
        data = {"name": "Task", "weight": 0.5}

        milestone = Milestone.from_dict(data)

        assert milestone.name == "Task"
        assert milestone.weight == Decimal("0.5")
        assert milestone.is_complete is False

    def test_from_dict_empty(self) -> None:
        """Should handle empty dict."""
        milestone = Milestone.from_dict({})

        assert milestone.name == ""
        assert milestone.weight == Decimal("0")
        assert milestone.is_complete is False
