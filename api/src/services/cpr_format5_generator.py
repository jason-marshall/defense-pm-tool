"""CPR Format 5 (EVMS) report generator.

Generates detailed EVMS report with variance analysis per DFARS requirements.

CPR Format 5 provides:
- Monthly/quarterly BCWS, BCWP, ACWP data
- Variance percentages and trends
- Management Reserve (MR) changes
- Estimate at Completion (EAC) analysis with 6 methods
- Narrative variance explanations for significant variances
"""

from datetime import date
from decimal import Decimal

import structlog

from src.models.evms_period import EVMSPeriod
from src.models.management_reserve_log import ManagementReserveLog
from src.models.program import Program
from src.models.variance_explanation import VarianceExplanation as VarianceExplanationModel
from src.schemas.cpr_format5 import (
    CPRFormat5Report,
    EACAnalysis,
    Format5ExportConfig,
    Format5PeriodRow,
    ManagementReserveRow,
    VarianceExplanation,
)
from src.services.evms import EVMSCalculator

logger = structlog.get_logger(__name__)


class CPRFormat5Generator:
    """Generate CPR Format 5 (EVMS) report.

    Implements full CPR Format 5 report generation with:
    - Time-phased BCWS/BCWP/ACWP data
    - All 6 EAC calculation methods per GL 27
    - Variance explanations from repository
    - Management Reserve tracking

    Example usage:
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            config=Format5ExportConfig(periods_to_include=12),
            variance_explanations=explanations,
            mr_logs=mr_logs,
        )
        report = generator.generate()
    """

    def __init__(
        self,
        program: Program,
        periods: list[EVMSPeriod],
        config: Format5ExportConfig | None = None,
        variance_explanations: list[VarianceExplanationModel] | None = None,
        mr_logs: list[ManagementReserveLog] | None = None,
        manager_etc: Decimal | None = None,
    ) -> None:
        """Initialize CPR Format 5 generator.

        Args:
            program: Program to generate report for
            periods: List of EVMS periods (will be sorted by date)
            config: Optional export configuration
            variance_explanations: Optional list of variance explanations
            mr_logs: Optional list of management reserve log entries
            manager_etc: Optional manager's estimate to complete (for independent EAC)
        """
        self.program = program
        self.periods = sorted(periods, key=lambda p: p.period_start)
        self.config = config or Format5ExportConfig()
        self.variance_explanations_data = variance_explanations or []
        self.mr_logs = mr_logs or []
        self.manager_etc = manager_etc

    def generate(self) -> CPRFormat5Report:
        """Generate the CPR Format 5 report.

        Returns:
            Complete CPRFormat5Report dataclass with all sections
        """
        logger.info(
            "generating_cpr_format5",
            program_id=str(self.program.id),
            program_code=self.program.code,
            period_count=len(self.periods),
        )

        # Build period rows
        period_rows = self._build_period_rows()

        # Get latest period for summary metrics
        latest = self.periods[-1] if self.periods else None

        # Calculate summary metrics
        bac = self.program.budget_at_completion or Decimal("0")

        if latest:
            cumulative_bcwp = latest.cumulative_bcwp
            cumulative_acwp = latest.cumulative_acwp
            cumulative_bcws = latest.cumulative_bcws

            cpi = EVMSCalculator.calculate_cpi(cumulative_bcwp, cumulative_acwp)
            spi = EVMSCalculator.calculate_spi(cumulative_bcwp, cumulative_bcws)

            eac = EVMSCalculator.calculate_eac(bac, cumulative_acwp, cumulative_bcwp, "cpi")
            etc = (eac - cumulative_acwp) if eac else Decimal("0")
            vac = (bac - eac) if eac else Decimal("0")

            tcpi = EVMSCalculator.calculate_tcpi(bac, cumulative_bcwp, cumulative_acwp, "bac")

            percent_complete = (cumulative_bcwp / bac * 100) if bac > 0 else Decimal("0")
            percent_spent = (cumulative_acwp / bac * 100) if bac > 0 else Decimal("0")
        else:
            cpi = spi = tcpi = None
            eac = bac
            etc = bac
            vac = Decimal("0")
            percent_complete = percent_spent = Decimal("0")

        # Build EAC analysis with all 6 methods
        eac_analysis = self._build_eac_analysis(latest, bac) if latest else None

        # Build variance explanations from provided data
        variance_explanations = self._build_variance_explanations()

        # Build MR rows from provided data
        mr_rows = self._build_mr_rows()

        # Get current MR from latest log entry
        current_mr = Decimal("0")
        if self.mr_logs:
            latest_mr = self.mr_logs[-1]
            current_mr = latest_mr.ending_mr

        report = CPRFormat5Report(
            program_name=self.program.name,
            program_code=self.program.code,
            contract_number=self.program.contract_number,
            report_date=date.today(),
            reporting_period=latest.period_name if latest else "",
            bac=bac,
            current_eac=eac or bac,
            current_etc=etc,
            current_vac=vac,
            cumulative_cpi=cpi,
            cumulative_spi=spi,
            cumulative_tcpi=tcpi,
            percent_complete=percent_complete.quantize(Decimal("0.01")),
            percent_spent=percent_spent.quantize(Decimal("0.01")),
            period_rows=period_rows,
            mr_rows=mr_rows,
            current_mr=current_mr,
            variance_explanations=variance_explanations,
            eac_analysis=eac_analysis,
            generated_at=date.today(),
        )

        logger.info(
            "cpr_format5_generated",
            program_code=self.program.code,
            period_rows=len(period_rows),
            variance_explanations=len(variance_explanations),
            mr_rows=len(mr_rows),
        )

        return report

    def _build_period_rows(self) -> list[Format5PeriodRow]:
        """Build period rows for Format 5 report.

        Returns:
            List of Format5PeriodRow for included periods
        """
        rows = []
        periods_to_process = self.periods[-self.config.periods_to_include :]

        # Track previous period for calculating period-only values
        prev_cumulative_bcws = Decimal("0")
        prev_cumulative_bcwp = Decimal("0")
        prev_cumulative_acwp = Decimal("0")

        # If we're starting mid-stream, get the prior period's cumulatives
        if len(self.periods) > self.config.periods_to_include:
            prior_period = self.periods[-(self.config.periods_to_include + 1)]
            prev_cumulative_bcws = prior_period.cumulative_bcws
            prev_cumulative_bcwp = prior_period.cumulative_bcwp
            prev_cumulative_acwp = prior_period.cumulative_acwp

        bac = self.program.budget_at_completion or Decimal("0")

        for period in periods_to_process:
            # Calculate period-only values
            period_bcws = period.cumulative_bcws - prev_cumulative_bcws
            period_bcwp = period.cumulative_bcwp - prev_cumulative_bcwp
            period_acwp = period.cumulative_acwp - prev_cumulative_acwp

            # Period variances
            period_sv = period_bcwp - period_bcws
            period_cv = period_bcwp - period_acwp

            # Cumulative variances
            cumulative_sv = period.cumulative_bcwp - period.cumulative_bcws
            cumulative_cv = period.cumulative_bcwp - period.cumulative_acwp

            # Calculate variance percentages (relative to cumulative BCWS)
            if period.cumulative_bcws > 0:
                sv_percent = (cumulative_sv / period.cumulative_bcws * 100).quantize(
                    Decimal("0.01")
                )
                cv_percent = (cumulative_cv / period.cumulative_bcws * 100).quantize(
                    Decimal("0.01")
                )
            else:
                sv_percent = Decimal("0")
                cv_percent = Decimal("0")

            # Calculate forecasts
            eac = (
                EVMSCalculator.calculate_eac(
                    bac, period.cumulative_acwp, period.cumulative_bcwp, "cpi"
                )
                or bac
            )

            tcpi = EVMSCalculator.calculate_tcpi(
                bac, period.cumulative_bcwp, period.cumulative_acwp, "bac"
            )

            rows.append(
                Format5PeriodRow(
                    period_name=period.period_name,
                    period_start=period.period_start,
                    period_end=period.period_end,
                    bcws=period_bcws,
                    bcwp=period_bcwp,
                    acwp=period_acwp,
                    cumulative_bcws=period.cumulative_bcws,
                    cumulative_bcwp=period.cumulative_bcwp,
                    cumulative_acwp=period.cumulative_acwp,
                    period_sv=period_sv,
                    period_cv=period_cv,
                    cumulative_sv=cumulative_sv,
                    cumulative_cv=cumulative_cv,
                    sv_percent=sv_percent,
                    cv_percent=cv_percent,
                    spi=period.spi,
                    cpi=period.cpi,
                    eac=eac,
                    etc=eac - period.cumulative_acwp,
                    vac=bac - eac,
                    tcpi=tcpi,
                )
            )

            # Update previous cumulatives for next iteration
            prev_cumulative_bcws = period.cumulative_bcws
            prev_cumulative_bcwp = period.cumulative_bcwp
            prev_cumulative_acwp = period.cumulative_acwp

        return rows

    def _build_eac_analysis(self, latest_period: EVMSPeriod, bac: Decimal) -> EACAnalysis:
        """Build EAC analysis with all 6 estimation methods.

        Per EVMS GL 27, multiple EAC methods should be compared:
        1. CPI: BAC / CPI
        2. SPI: BAC / SPI
        3. Composite: ACWP + (BAC - BCWP) / (CPI * SPI)
        4. Typical: ACWP + (BAC - BCWP)
        5. Atypical/Mathematical: ACWP + (BAC - BCWP) / CPI
        6. Management: Bottom-up estimate from program manager

        Args:
            latest_period: Most recent EVMS period
            bac: Budget at Completion

        Returns:
            EACAnalysis with all 6 EAC methods
        """
        bcwp = latest_period.cumulative_bcwp
        acwp = latest_period.cumulative_acwp
        bcws = latest_period.cumulative_bcws

        # Calculate indices
        cpi = (bcwp / acwp) if acwp > 0 else Decimal("1")
        spi = (bcwp / bcws) if bcws > 0 else Decimal("1")

        # Remaining work
        remaining = bac - bcwp

        # 1. EAC using CPI method: BAC / CPI
        eac_cpi = (bac / cpi).quantize(Decimal("0.01")) if cpi > 0 else bac

        # 2. EAC using SPI method: BAC / SPI
        eac_spi = (bac / spi).quantize(Decimal("0.01")) if spi > 0 else None

        # 3. EAC Composite/Comprehensive: ACWP + (BAC - BCWP) / (CPI * SPI)
        if cpi > 0 and spi > 0:
            efficiency_factor = cpi * spi
            eac_composite = (acwp + (remaining / efficiency_factor)).quantize(Decimal("0.01"))
        else:
            eac_composite = bac

        # 4. EAC Typical: ACWP + (BAC - BCWP)
        eac_typical = (acwp + remaining).quantize(Decimal("0.01"))

        # 5. EAC Atypical/Mathematical: ACWP + (BAC - BCWP) / CPI
        eac_atypical = (acwp + (remaining / cpi)).quantize(Decimal("0.01")) if cpi > 0 else bac

        # 6. EAC Management: Use manager's ETC if provided, otherwise None
        eac_management = None
        if self.manager_etc is not None:
            eac_management = (acwp + self.manager_etc).quantize(Decimal("0.01"))

        # Collect valid EAC values for comparison
        valid_eacs = [eac_cpi, eac_composite, eac_typical, eac_atypical]
        if eac_spi is not None:
            valid_eacs.append(eac_spi)
        if eac_management is not None:
            valid_eacs.append(eac_management)

        # Calculate range and average
        eac_range_low = min(valid_eacs)
        eac_range_high = max(valid_eacs)
        eac_sum = sum(valid_eacs, Decimal("0"))
        eac_average = (eac_sum / len(valid_eacs)).quantize(Decimal("0.01"))

        # Select EAC and rationale
        # Default logic: Use CPI method as primary, but consider composite for troubled projects
        if cpi < Decimal("0.90") and spi < Decimal("0.90"):
            # Significant cost and schedule issues - use composite
            eac_selected = eac_composite
            selection_rationale = (
                "Composite method selected due to significant cost and schedule issues "
                f"(CPI={cpi:.2f}, SPI={spi:.2f})"
            )
        elif cpi < Decimal("0.95"):
            # Cost issues expected to continue - use CPI method
            eac_selected = eac_cpi
            selection_rationale = (
                f"CPI method selected - historical cost efficiency (CPI={cpi:.2f}) "
                "expected to continue"
            )
        else:
            # Normal performance - use CPI method
            eac_selected = eac_cpi
            selection_rationale = (
                "CPI method selected per standard practice - "
                "program performing within acceptable parameters"
            )

        return EACAnalysis(
            eac_cpi=eac_cpi,
            eac_spi=eac_spi,
            eac_composite=eac_composite,
            eac_typical=eac_typical,
            eac_atypical=eac_atypical,
            eac_management=eac_management,
            eac_selected=eac_selected,
            selection_rationale=selection_rationale,
            eac_range_low=eac_range_low,
            eac_range_high=eac_range_high,
            eac_average=eac_average,
        )

    def _build_variance_explanations(self) -> list[VarianceExplanation]:
        """Build variance explanations from provided model data.

        Converts VarianceExplanation model instances to schema dataclasses,
        filtering by the configured threshold.

        Returns:
            List of VarianceExplanation schema objects
        """
        if not self.config.include_explanations:
            return []

        explanations = []
        threshold = abs(self.config.variance_threshold_percent)

        for ve in self.variance_explanations_data:
            # Only include if variance exceeds threshold
            if abs(ve.variance_percent) >= threshold:
                # Get WBS info if available
                wbs_code = ""
                wbs_name = ""
                if ve.wbs is not None:
                    wbs_code = ve.wbs.wbs_code
                    wbs_name = ve.wbs.name

                explanations.append(
                    VarianceExplanation(
                        wbs_code=wbs_code,
                        wbs_name=wbs_name,
                        variance_type=ve.variance_type,
                        variance_amount=ve.variance_amount,
                        variance_percent=ve.variance_percent,
                        explanation=ve.explanation,
                        corrective_action=ve.corrective_action,
                        expected_resolution_date=ve.expected_resolution,
                    )
                )

        # Sort by variance percent (absolute value, descending)
        explanations.sort(key=lambda x: abs(x.variance_percent), reverse=True)

        return explanations

    def _build_mr_rows(self) -> list[ManagementReserveRow]:
        """Build Management Reserve tracking rows from log data.

        Converts ManagementReserveLog model instances to schema dataclasses.

        Returns:
            List of ManagementReserveRow schema objects
        """
        if not self.config.include_mr:
            return []

        rows = []

        for log in self.mr_logs:
            # Get period name if available
            period_name = ""
            if log.period is not None:
                period_name = log.period.period_name

            rows.append(
                ManagementReserveRow(
                    period_name=period_name,
                    beginning_mr=log.beginning_mr,
                    changes_in=log.changes_in,
                    changes_out=log.changes_out,
                    ending_mr=log.ending_mr,
                    reason=log.reason,
                )
            )

        return rows


def generate_format5_report(
    program: Program,
    periods: list[EVMSPeriod],
    config: Format5ExportConfig | None = None,
    variance_explanations: list[VarianceExplanationModel] | None = None,
    mr_logs: list[ManagementReserveLog] | None = None,
    manager_etc: Decimal | None = None,
) -> CPRFormat5Report:
    """Convenience function to generate CPR Format 5 report.

    Args:
        program: Program to generate report for
        periods: List of EVMS periods
        config: Optional export configuration
        variance_explanations: Optional list of variance explanations
        mr_logs: Optional list of management reserve log entries
        manager_etc: Optional manager's estimate to complete

    Returns:
        Generated CPRFormat5Report
    """
    generator = CPRFormat5Generator(
        program=program,
        periods=periods,
        config=config,
        variance_explanations=variance_explanations,
        mr_logs=mr_logs,
        manager_etc=manager_etc,
    )
    return generator.generate()
