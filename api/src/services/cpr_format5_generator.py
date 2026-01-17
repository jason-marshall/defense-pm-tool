"""CPR Format 5 (EVMS) report generator.

Generates detailed EVMS report with variance analysis per DFARS requirements.
Full implementation in Week 9.

CPR Format 5 provides:
- Monthly/quarterly BCWS, BCWP, ACWP data
- Variance percentages and trends
- Management Reserve (MR) changes
- Estimate at Completion (EAC) analysis
- Narrative variance explanations for significant variances
"""

from datetime import date
from decimal import Decimal

import structlog

from src.models.evms_period import EVMSPeriod
from src.models.program import Program
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

    Note: This is the foundation/skeleton for Week 9 implementation.
    Full variance analysis and MR tracking will be added in Week 9.

    Example usage:
        generator = CPRFormat5Generator(
            program=program,
            periods=periods,
            config=Format5ExportConfig(periods_to_include=12),
        )
        report = generator.generate()
    """

    def __init__(
        self,
        program: Program,
        periods: list[EVMSPeriod],
        config: Format5ExportConfig | None = None,
    ) -> None:
        """Initialize CPR Format 5 generator.

        Args:
            program: Program to generate report for
            periods: List of EVMS periods (will be sorted by date)
            config: Optional export configuration
        """
        self.program = program
        self.periods = sorted(periods, key=lambda p: p.period_start)
        self.config = config or Format5ExportConfig()

    def generate(self) -> CPRFormat5Report:
        """Generate the CPR Format 5 report.

        Week 8: Returns skeleton with basic data.
        Week 9: Full implementation with variance analysis.

        Returns:
            Complete CPRFormat5Report dataclass
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

        # Build EAC analysis (comparing different methods)
        eac_analysis = self._build_eac_analysis(latest, bac) if latest else None

        # TODO Week 9: Add variance explanations
        variance_explanations = self._build_variance_explanations() if latest else []

        # TODO Week 9: Add MR tracking
        mr_rows = self._build_mr_rows()

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
            variance_explanations=variance_explanations,
            eac_analysis=eac_analysis,
            generated_at=date.today(),
        )

        logger.info(
            "cpr_format5_generated",
            program_code=self.program.code,
            period_rows=len(period_rows),
            variance_explanations=len(variance_explanations),
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
        """Build EAC analysis comparing different estimation methods.

        Args:
            latest_period: Most recent EVMS period
            bac: Budget at Completion

        Returns:
            EACAnalysis with different EAC methods
        """
        bcwp = latest_period.cumulative_bcwp
        acwp = latest_period.cumulative_acwp
        bcws = latest_period.cumulative_bcws

        # EAC using CPI method: BAC / CPI
        eac_cpi = EVMSCalculator.calculate_eac(bac, acwp, bcwp, "cpi") or bac

        # EAC using SPI x CPI method: ACWP + (BAC - BCWP) / (CPI x SPI)
        cpi = (bcwp / acwp) if acwp > 0 else Decimal("1")
        spi = (bcwp / bcws) if bcws > 0 else Decimal("1")

        if cpi > 0 and spi > 0:
            remaining = bac - bcwp
            eac_spi_cpi = acwp + (remaining / (cpi * spi))
        else:
            eac_spi_cpi = bac

        # Management estimate (placeholder - would come from separate input)
        # For now, use the CPI method as management estimate
        eac_management = eac_cpi

        return EACAnalysis(
            eac_cpi=eac_cpi.quantize(Decimal("0.01")),
            eac_spi_cpi=eac_spi_cpi.quantize(Decimal("0.01")),
            eac_management=eac_management.quantize(Decimal("0.01")),
            eac_selected=eac_cpi.quantize(Decimal("0.01")),
            selection_rationale="CPI method selected per standard practice",
        )

    def _build_variance_explanations(self) -> list[VarianceExplanation]:
        """Build variance explanations for significant variances.

        TODO Week 9: Full implementation with WBS-level variance analysis.

        Returns:
            List of variance explanations (empty for Week 8 skeleton)
        """
        # Placeholder for Week 9 implementation
        # Will analyze WBS-level variances and generate explanations
        # for items exceeding variance_threshold_percent
        return []

    def _build_mr_rows(self) -> list[ManagementReserveRow]:
        """Build Management Reserve tracking rows.

        TODO Week 9: Full implementation with MR change tracking.

        Returns:
            List of MR rows (empty for Week 8 skeleton)
        """
        # Placeholder for Week 9 implementation
        # Will track MR changes across periods
        return []


def generate_format5_report(
    program: Program,
    periods: list[EVMSPeriod],
    config: Format5ExportConfig | None = None,
) -> CPRFormat5Report:
    """Convenience function to generate CPR Format 5 report.

    Args:
        program: Program to generate report for
        periods: List of EVMS periods
        config: Optional export configuration

    Returns:
        Generated CPRFormat5Report
    """
    generator = CPRFormat5Generator(program, periods, config)
    return generator.generate()
