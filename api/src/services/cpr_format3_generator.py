"""CPR Format 3 (Baseline) report generator.

Generates time-phased Performance Measurement Baseline reports
per DFARS requirements for contract performance reporting.

CPR Format 3 shows:
- Time-phased BCWS (planned values by period)
- Time-phased BCWP (earned values by period)
- Time-phased ACWP (actual costs by period)
- Cumulative curves for trend analysis
- BAC tracking against baseline
"""

from collections.abc import Sequence
from datetime import date, timedelta
from decimal import Decimal
from typing import Any, Protocol

from src.schemas.cpr_format3 import CPRFormat3Report, TimePhaseRow
from src.services.evms import EVMSCalculator


class ProgramProtocol(Protocol):
    """Protocol for program-like objects."""

    name: str
    code: str
    contract_number: str | None
    budget_at_completion: Decimal | None


class BaselineProtocol(Protocol):
    """Protocol for baseline-like objects."""

    name: str
    version: int
    total_bac: Decimal
    scheduled_finish: date | None
    created_at: Any  # datetime


class EVMSPeriodProtocol(Protocol):
    """Protocol for EVMS period-like objects."""

    period_name: str
    period_start: date
    period_end: date
    bcws: Decimal | None
    bcwp: Decimal | None
    acwp: Decimal | None


class CPRFormat3Generator:
    """Generate CPR Format 3 (Baseline) report.

    Shows time-phased PMB with actual performance overlay.
    Enables trend analysis by comparing planned vs actual
    values across multiple reporting periods.

    Example usage:
        generator = CPRFormat3Generator(
            program=program,
            baseline=baseline,
            periods=evms_periods,
        )
        report = generator.generate()
    """

    def __init__(
        self,
        program: ProgramProtocol,
        baseline: BaselineProtocol,
        periods: Sequence[EVMSPeriodProtocol],
    ) -> None:
        """Initialize CPR Format 3 generator.

        Args:
            program: Program object with name, code, budget info
            baseline: Baseline object with PMB data
            periods: List of EVMS period objects with performance data
        """
        self.program = program
        self.baseline = baseline
        self.periods = sorted(periods, key=lambda p: p.period_start)

    def generate(self) -> CPRFormat3Report:
        """Generate the CPR Format 3 report.

        Returns:
            Complete CPRFormat3Report with all time-phased data
        """
        # Build time-phase rows
        time_phase_rows = self._build_time_phase_rows()

        # Get latest period for summary
        latest_period = self.periods[-1] if self.periods else None

        # Calculate summary metrics from cumulative values
        if time_phase_rows:
            last_row = time_phase_rows[-1]
            total_bcws = last_row.cumulative_bcws
            total_bcwp = last_row.cumulative_bcwp
            total_acwp = last_row.cumulative_acwp
        else:
            total_bcws = Decimal("0")
            total_bcwp = Decimal("0")
            total_acwp = Decimal("0")

        total_sv = total_bcwp - total_bcws
        total_cv = total_bcwp - total_acwp

        # Get BAC from baseline or program
        bac = self.baseline.total_bac
        if not bac or bac == 0:
            bac = self.program.budget_at_completion or Decimal("0")

        # Calculate performance indices
        cpi = EVMSCalculator.calculate_cpi(total_bcwp, total_acwp)
        spi = EVMSCalculator.calculate_spi(total_bcwp, total_bcws)

        # Calculate EAC/ETC/VAC
        eac = EVMSCalculator.calculate_eac(bac, total_acwp, total_bcwp, "cpi")
        if eac is None:
            eac = bac

        etc = EVMSCalculator.calculate_etc(eac, total_acwp)
        vac = EVMSCalculator.calculate_vac(bac, eac)

        # Calculate TCPI
        tcpi = EVMSCalculator.calculate_tcpi(bac, total_bcwp, total_acwp, "bac")

        # Percent metrics
        if bac > 0:
            percent_complete = (total_bcwp / bac * 100).quantize(Decimal("0.01"))
            percent_spent = (total_acwp / bac * 100).quantize(Decimal("0.01"))
        else:
            percent_complete = Decimal("0")
            percent_spent = Decimal("0")

        # Schedule variance in days
        baseline_finish = self.baseline.scheduled_finish
        forecast_finish = self._calculate_forecast_finish(spi)
        schedule_variance_days = 0
        if baseline_finish and forecast_finish:
            schedule_variance_days = (forecast_finish - baseline_finish).days

        return CPRFormat3Report(
            program_name=self.program.name,
            program_code=self.program.code,
            contract_number=self.program.contract_number,
            baseline_name=self.baseline.name,
            baseline_version=self.baseline.version,
            report_date=date.today(),
            bac=bac,
            current_period=latest_period.period_name if latest_period else "",
            percent_complete=percent_complete,
            percent_spent=percent_spent,
            total_bcws=total_bcws,
            total_bcwp=total_bcwp,
            total_acwp=total_acwp,
            total_sv=total_sv,
            total_cv=total_cv,
            eac=eac,
            etc=etc,
            vac=vac,
            cpi=cpi,
            spi=spi,
            tcpi=tcpi,
            time_phase_rows=time_phase_rows,
            baseline_finish_date=baseline_finish,
            forecast_finish_date=forecast_finish,
            schedule_variance_days=schedule_variance_days,
        )

    def _build_time_phase_rows(self) -> list[TimePhaseRow]:
        """Build time-phased rows from EVMS periods.

        Returns:
            List of TimePhaseRow objects with cumulative calculations
        """
        rows: list[TimePhaseRow] = []
        cumulative_bcws = Decimal("0")
        cumulative_bcwp = Decimal("0")
        cumulative_acwp = Decimal("0")

        for period in self.periods:
            bcws = period.bcws or Decimal("0")
            bcwp = period.bcwp or Decimal("0")
            acwp = period.acwp or Decimal("0")

            cumulative_bcws += bcws
            cumulative_bcwp += bcwp
            cumulative_acwp += acwp

            sv = bcwp - bcws
            cv = bcwp - acwp

            rows.append(
                TimePhaseRow(
                    period_name=period.period_name,
                    period_start=period.period_start,
                    period_end=period.period_end,
                    bcws=bcws,
                    bcwp=bcwp,
                    acwp=acwp,
                    cumulative_bcws=cumulative_bcws,
                    cumulative_bcwp=cumulative_bcwp,
                    cumulative_acwp=cumulative_acwp,
                    sv=sv,
                    cv=cv,
                )
            )

        return rows

    def _calculate_forecast_finish(self, spi: Decimal | None) -> date | None:
        """Calculate forecast finish date based on SPI.

        Uses schedule performance index to project when the project
        will actually complete based on current performance.

        Args:
            spi: Schedule Performance Index (BCWP/BCWS)

        Returns:
            Forecast finish date, or None if cannot be calculated
        """
        if not spi or spi <= 0:
            return None

        baseline_finish = self.baseline.scheduled_finish
        baseline_start = self._get_baseline_start()

        if not baseline_finish or not baseline_start:
            return None

        # Original duration in days
        original_duration = (baseline_finish - baseline_start).days

        if original_duration <= 0:
            return None

        # Adjusted duration based on SPI
        # If SPI < 1, project is behind schedule and will take longer
        # If SPI > 1, project is ahead of schedule and may finish early
        adjusted_duration = int(original_duration / float(spi))

        return baseline_start + timedelta(days=adjusted_duration)

    def _get_baseline_start(self) -> date | None:
        """Get the baseline start date.

        Returns:
            Start date from baseline creation or first period
        """
        # Try to get from baseline creation date
        if self.baseline.created_at:
            if hasattr(self.baseline.created_at, "date"):
                created_date: date = self.baseline.created_at.date()
                return created_date
            if isinstance(self.baseline.created_at, date):
                return self.baseline.created_at
            return None

        # Fall back to first period start
        if self.periods:
            return self.periods[0].period_start

        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert generated report to dictionary format.

        Convenience method for API responses.

        Returns:
            Dictionary representation of the report
        """
        report = self.generate()

        return {
            "program_name": report.program_name,
            "program_code": report.program_code,
            "contract_number": report.contract_number,
            "baseline_name": report.baseline_name,
            "baseline_version": report.baseline_version,
            "report_date": report.report_date.isoformat(),
            "summary": {
                "bac": str(report.bac),
                "eac": str(report.eac),
                "etc": str(report.etc),
                "vac": str(report.vac),
                "percent_complete": str(report.percent_complete),
                "percent_spent": str(report.percent_spent),
                "cpi": str(report.cpi) if report.cpi else None,
                "spi": str(report.spi) if report.spi else None,
                "tcpi": str(report.tcpi) if report.tcpi else None,
                "status_color": report.status_color,
            },
            "cumulative": {
                "bcws": str(report.total_bcws),
                "bcwp": str(report.total_bcwp),
                "acwp": str(report.total_acwp),
                "sv": str(report.total_sv),
                "cv": str(report.total_cv),
            },
            "schedule": {
                "baseline_finish": report.baseline_finish_date.isoformat()
                if report.baseline_finish_date
                else None,
                "forecast_finish": report.forecast_finish_date.isoformat()
                if report.forecast_finish_date
                else None,
                "variance_days": report.schedule_variance_days,
                "is_behind_schedule": report.is_behind_schedule,
            },
            "time_phase_data": [
                {
                    "period": row.period_name,
                    "start": row.period_start.isoformat(),
                    "end": row.period_end.isoformat(),
                    "bcws": str(row.bcws),
                    "bcwp": str(row.bcwp),
                    "acwp": str(row.acwp),
                    "cumulative_bcws": str(row.cumulative_bcws),
                    "cumulative_bcwp": str(row.cumulative_bcwp),
                    "cumulative_acwp": str(row.cumulative_acwp),
                    "sv": str(row.sv),
                    "cv": str(row.cv),
                    "spi": str(row.spi) if row.spi else None,
                    "cpi": str(row.cpi) if row.cpi else None,
                }
                for row in report.time_phase_rows
            ],
        }
