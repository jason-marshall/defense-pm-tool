"""S-curve export service for PNG and SVG generation.

Provides chart export functionality for S-curve visualizations
with support for confidence bands and customizable styling.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from enum import Enum
from io import BytesIO
from typing import Any

import matplotlib

matplotlib.use("Agg")  # Non-interactive backend for server use
import matplotlib.pyplot as plt
import structlog
from matplotlib.axes import Axes
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter

logger = structlog.get_logger(__name__)


class ExportFormat(str, Enum):
    """Supported export formats."""

    PNG = "png"
    SVG = "svg"


@dataclass
class SCurveExportConfig:
    """Configuration for S-curve export."""

    width: int = 12
    height: int = 8
    dpi: int = 150
    title: str = "S-Curve Analysis"
    show_legend: bool = True
    show_grid: bool = True
    show_confidence_bands: bool = True
    confidence_alpha: float = 0.2
    font_size: int = 10
    line_width: float = 2.0
    colors: dict[str, str] = field(
        default_factory=lambda: {
            "bcws": "#2196F3",  # Blue - Planned Value
            "bcwp": "#4CAF50",  # Green - Earned Value
            "acwp": "#F44336",  # Red - Actual Cost
            "eac": "#FF9800",  # Orange - Estimate at Completion
            "confidence_band": "#9C27B0",  # Purple - Confidence bands
        }
    )


class SCurveExporter:
    """Export S-curve visualizations to PNG/SVG formats.

    Generates publication-quality S-curve charts with:
    - Planned Value (BCWS) line
    - Earned Value (BCWP) line
    - Actual Cost (ACWP) line
    - EAC forecast line
    - Confidence bands from Monte Carlo simulation

    Example usage:
        exporter = SCurveExporter()
        config = SCurveExportConfig(title="Program Alpha S-Curve")
        png_bytes = exporter.export_png(scurve_data, config)
    """

    def export_png(
        self,
        data: dict[str, Any],
        config: SCurveExportConfig | None = None,
    ) -> bytes:
        """Export S-curve as PNG image.

        Args:
            data: S-curve data with data_points and optional eac_range
            config: Export configuration options

        Returns:
            PNG image as bytes
        """
        config = config or SCurveExportConfig()
        fig = self._create_figure(data, config)

        buffer = BytesIO()
        fig.savefig(buffer, format="png", dpi=config.dpi, bbox_inches="tight")
        plt.close(fig)

        buffer.seek(0)
        logger.info("scurve_export_png", size=buffer.getbuffer().nbytes)
        return buffer.getvalue()

    def export_svg(
        self,
        data: dict[str, Any],
        config: SCurveExportConfig | None = None,
    ) -> bytes:
        """Export S-curve as SVG image.

        Args:
            data: S-curve data with data_points and optional eac_range
            config: Export configuration options

        Returns:
            SVG image as bytes
        """
        config = config or SCurveExportConfig()
        fig = self._create_figure(data, config)

        buffer = BytesIO()
        fig.savefig(buffer, format="svg", bbox_inches="tight")
        plt.close(fig)

        buffer.seek(0)
        logger.info("scurve_export_svg", size=buffer.getbuffer().nbytes)
        return buffer.getvalue()

    def _create_figure(
        self,
        data: dict[str, Any],
        config: SCurveExportConfig,
    ) -> Figure:
        """Create matplotlib figure from S-curve data.

        Args:
            data: S-curve data dictionary
            config: Export configuration

        Returns:
            Matplotlib Figure object
        """
        fig, ax = plt.subplots(figsize=(config.width, config.height))

        data_points = data.get("data_points", [])
        if not data_points:
            ax.text(
                0.5,
                0.5,
                "No data available",
                ha="center",
                va="center",
                transform=ax.transAxes,
                fontsize=config.font_size + 2,
            )
            return fig

        # Extract data series
        periods = [p.get("period", p.get("period_number", i)) for i, p in enumerate(data_points)]
        bcws = self._extract_values(data_points, "bcws_cumulative", "planned_value")
        bcwp = self._extract_values(data_points, "bcwp_cumulative", "earned_value")
        acwp = self._extract_values(data_points, "acwp_cumulative", "actual_cost")

        # Plot main lines
        if bcws:
            ax.plot(
                periods[: len(bcws)],
                bcws,
                label="Planned Value (BCWS)",
                color=config.colors["bcws"],
                linewidth=config.line_width,
                linestyle="--",
            )

        if bcwp:
            ax.plot(
                periods[: len(bcwp)],
                bcwp,
                label="Earned Value (BCWP)",
                color=config.colors["bcwp"],
                linewidth=config.line_width,
            )

        if acwp:
            ax.plot(
                periods[: len(acwp)],
                acwp,
                label="Actual Cost (ACWP)",
                color=config.colors["acwp"],
                linewidth=config.line_width,
            )

        # Plot EAC forecast line if available
        eac_data = data.get("eac_forecast", [])
        if eac_data:
            eac_periods = [p.get("period", i) for i, p in enumerate(eac_data)]
            eac_values = self._extract_values(eac_data, "eac", "forecast_value")
            if eac_values:
                ax.plot(
                    eac_periods[: len(eac_values)],
                    eac_values,
                    label="EAC Forecast",
                    color=config.colors["eac"],
                    linewidth=config.line_width,
                    linestyle=":",
                )

        # Plot confidence bands if available
        if config.show_confidence_bands:
            self._plot_confidence_bands(ax, data, config)

        # Styling
        ax.set_title(config.title, fontsize=config.font_size + 4, fontweight="bold")
        ax.set_xlabel("Period", fontsize=config.font_size)
        ax.set_ylabel("Value ($)", fontsize=config.font_size)

        if config.show_grid:
            ax.grid(True, alpha=0.3)

        if config.show_legend:
            ax.legend(loc="upper left", fontsize=config.font_size - 1)

        # Format y-axis with currency formatting
        ax.yaxis.set_major_formatter(FuncFormatter(lambda x, _: f"${x:,.0f}"))

        plt.tight_layout()
        return fig

    def _extract_values(
        self,
        data_points: list[dict[str, Any]],
        *keys: str,
    ) -> list[float]:
        """Extract numeric values from data points.

        Args:
            data_points: List of data point dictionaries
            keys: Keys to try in order

        Returns:
            List of float values
        """
        values = []
        for point in data_points:
            value = None
            for key in keys:
                if key in point and point[key] is not None:
                    value = point[key]
                    break

            if value is not None:
                if isinstance(value, Decimal):
                    values.append(float(value))
                elif isinstance(value, str):
                    try:
                        values.append(float(value))
                    except ValueError:
                        continue
                else:
                    values.append(float(value))
        return values

    def _plot_confidence_bands(
        self,
        ax: Axes,
        data: dict[str, Any],
        config: SCurveExportConfig,
    ) -> None:
        """Plot confidence bands from Monte Carlo simulation.

        Args:
            ax: Matplotlib axes
            data: S-curve data with eac_range
            config: Export configuration
        """
        eac_range = data.get("eac_range", {})
        if not eac_range:
            return

        # Check for percentile data
        p10 = eac_range.get("p10")
        p50 = eac_range.get("p50")
        p90 = eac_range.get("p90")

        if p10 is not None and p90 is not None:
            # Convert percentile values for plotting
            p10_val = float(p10) if isinstance(p10, (Decimal, str)) else p10
            p90_val = float(p90) if isinstance(p90, (Decimal, str)) else p90

            # Fill between P10 and P90
            ax.axhspan(
                p10_val,
                p90_val,
                alpha=config.confidence_alpha,
                color=config.colors["confidence_band"],
                label="P10-P90 Range",
            )

            # Mark P50 if available
            if p50 is not None:
                p50_val = float(p50) if isinstance(p50, (Decimal, str)) else p50
                ax.axhline(
                    y=p50_val,
                    color=config.colors["confidence_band"],
                    linestyle="--",
                    alpha=0.7,
                    linewidth=1,
                    label="P50 (Median)",
                )

        # Check for time-series confidence bands
        confidence_bands = data.get("confidence_bands", [])
        if confidence_bands:
            band_periods = []
            lower_bounds = []
            upper_bounds = []

            for band in confidence_bands:
                period = band.get("period")
                lower = band.get("lower", band.get("p10"))
                upper = band.get("upper", band.get("p90"))

                if period is not None and lower is not None and upper is not None:
                    band_periods.append(period)
                    lower_bounds.append(
                        float(lower) if isinstance(lower, (Decimal, str)) else lower
                    )
                    upper_bounds.append(
                        float(upper) if isinstance(upper, (Decimal, str)) else upper
                    )

            if band_periods:
                ax.fill_between(
                    band_periods,
                    lower_bounds,
                    upper_bounds,
                    alpha=config.confidence_alpha,
                    color=config.colors["confidence_band"],
                    label="Confidence Band",
                )


# Global exporter instance
scurve_exporter = SCurveExporter()
