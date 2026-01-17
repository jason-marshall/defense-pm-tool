"""Unit tests for S-curve export service."""

from decimal import Decimal

from src.services.scurve_export import (
    ExportFormat,
    SCurveExportConfig,
    SCurveExporter,
)


class TestExportFormat:
    """Tests for ExportFormat enum."""

    def test_png_format(self):
        """Should have PNG format."""
        assert ExportFormat.PNG.value == "png"

    def test_svg_format(self):
        """Should have SVG format."""
        assert ExportFormat.SVG.value == "svg"


class TestSCurveExportConfig:
    """Tests for SCurveExportConfig dataclass."""

    def test_default_values(self):
        """Should have correct default values."""
        config = SCurveExportConfig()

        assert config.width == 12
        assert config.height == 8
        assert config.dpi == 150
        assert config.title == "S-Curve Analysis"
        assert config.show_legend is True
        assert config.show_grid is True
        assert config.show_confidence_bands is True
        assert config.confidence_alpha == 0.2
        assert config.font_size == 10
        assert config.line_width == 2.0

    def test_default_colors(self):
        """Should have correct default colors."""
        config = SCurveExportConfig()

        assert config.colors["bcws"] == "#2196F3"  # Blue
        assert config.colors["bcwp"] == "#4CAF50"  # Green
        assert config.colors["acwp"] == "#F44336"  # Red
        assert config.colors["eac"] == "#FF9800"  # Orange
        assert config.colors["confidence_band"] == "#9C27B0"  # Purple

    def test_custom_values(self):
        """Should accept custom values."""
        config = SCurveExportConfig(
            width=16,
            height=10,
            dpi=300,
            title="Custom Title",
            show_legend=False,
        )

        assert config.width == 16
        assert config.height == 10
        assert config.dpi == 300
        assert config.title == "Custom Title"
        assert config.show_legend is False


class TestSCurveExporterPNG:
    """Tests for PNG export functionality."""

    def test_export_png_empty_data(self):
        """Should handle empty data gracefully."""
        exporter = SCurveExporter()
        data = {"data_points": []}

        result = exporter.export_png(data)

        assert isinstance(result, bytes)
        assert len(result) > 0
        # PNG files start with specific magic bytes
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_export_png_with_data(self):
        """Should export PNG with valid data."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {
                    "period": 1,
                    "bcws_cumulative": "1000.00",
                    "bcwp_cumulative": "900.00",
                    "acwp_cumulative": "950.00",
                },
                {
                    "period": 2,
                    "bcws_cumulative": "2000.00",
                    "bcwp_cumulative": "1800.00",
                    "acwp_cumulative": "1900.00",
                },
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)
        assert len(result) > 0
        assert result[:8] == b"\x89PNG\r\n\x1a\n"

    def test_export_png_with_decimal_values(self):
        """Should handle Decimal values."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {
                    "period": 1,
                    "bcws_cumulative": Decimal("1000.00"),
                    "bcwp_cumulative": Decimal("900.00"),
                    "acwp_cumulative": Decimal("950.00"),
                },
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_png_custom_config(self):
        """Should respect custom configuration."""
        exporter = SCurveExporter()
        config = SCurveExportConfig(
            width=8,
            height=6,
            dpi=100,
            title="Custom Chart",
        )
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000},
            ]
        }

        result = exporter.export_png(data, config)

        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_export_png_with_eac_range(self):
        """Should include confidence bands when EAC range is present."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000, "bcwp_cumulative": 900},
                {"period": 2, "bcws_cumulative": 2000, "bcwp_cumulative": 1800},
            ],
            "eac_range": {
                "p10": "9500.00",
                "p50": "10000.00",
                "p90": "10500.00",
            },
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)
        assert len(result) > 0


class TestSCurveExporterSVG:
    """Tests for SVG export functionality."""

    def test_export_svg_empty_data(self):
        """Should handle empty data gracefully."""
        exporter = SCurveExporter()
        data = {"data_points": []}

        result = exporter.export_svg(data)

        assert isinstance(result, bytes)
        assert len(result) > 0
        # SVG files should contain SVG tag
        assert b"<svg" in result

    def test_export_svg_with_data(self):
        """Should export SVG with valid data."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {
                    "period": 1,
                    "bcws_cumulative": "1000.00",
                    "bcwp_cumulative": "900.00",
                    "acwp_cumulative": "950.00",
                },
                {
                    "period": 2,
                    "bcws_cumulative": "2000.00",
                    "bcwp_cumulative": "1800.00",
                    "acwp_cumulative": "1900.00",
                },
            ]
        }

        result = exporter.export_svg(data)

        assert isinstance(result, bytes)
        assert b"<svg" in result

    def test_export_svg_custom_title(self):
        """Should include custom title in SVG."""
        exporter = SCurveExporter()
        config = SCurveExportConfig(title="My Custom S-Curve")
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000},
            ]
        }

        result = exporter.export_svg(data, config)

        assert isinstance(result, bytes)
        assert b"My Custom S-Curve" in result


class TestSCurveExporterDataExtraction:
    """Tests for data extraction functionality."""

    def test_extract_bcws_with_cumulative_key(self):
        """Should extract BCWS using cumulative key."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000},
                {"period": 2, "bcws_cumulative": 2000},
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)

    def test_extract_bcws_with_planned_value_key(self):
        """Should extract BCWS using planned_value key as fallback."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "planned_value": 1000},
                {"period": 2, "planned_value": 2000},
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)

    def test_extract_mixed_types(self):
        """Should handle mixed numeric types."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {
                    "period": 1,
                    "bcws_cumulative": 1000,  # int
                    "bcwp_cumulative": "1100.50",  # str
                    "acwp_cumulative": Decimal("1050.25"),  # Decimal
                },
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)


class TestSCurveExporterConfidenceBands:
    """Tests for confidence band plotting."""

    def test_plot_with_eac_range_percentiles(self):
        """Should plot EAC range percentiles."""
        exporter = SCurveExporter()
        config = SCurveExportConfig(show_confidence_bands=True)
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000},
                {"period": 2, "bcws_cumulative": 2000},
            ],
            "eac_range": {
                "p10": 9000,
                "p50": 10000,
                "p90": 11000,
            },
        }

        result = exporter.export_png(data, config)

        assert isinstance(result, bytes)

    def test_skip_confidence_bands_when_disabled(self):
        """Should skip confidence bands when disabled."""
        exporter = SCurveExporter()
        config = SCurveExportConfig(show_confidence_bands=False)
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000},
            ],
            "eac_range": {
                "p10": 9000,
                "p50": 10000,
                "p90": 11000,
            },
        }

        result = exporter.export_png(data, config)

        assert isinstance(result, bytes)

    def test_plot_time_series_confidence_bands(self):
        """Should plot time-series confidence bands."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000},
                {"period": 2, "bcws_cumulative": 2000},
            ],
            "confidence_bands": [
                {"period": 3, "lower": 2500, "upper": 3500},
                {"period": 4, "lower": 3500, "upper": 4500},
            ],
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)


class TestSCurveExporterEACForecast:
    """Tests for EAC forecast line plotting."""

    def test_plot_eac_forecast(self):
        """Should plot EAC forecast line."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000},
                {"period": 2, "bcws_cumulative": 2000},
            ],
            "eac_forecast": [
                {"period": 3, "eac": 2500},
                {"period": 4, "eac": 3000},
            ],
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)


class TestSCurveExporterEdgeCases:
    """Tests for edge cases and error handling."""

    def test_none_data(self):
        """Should handle None values in data points."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 1000, "bcwp_cumulative": None},
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)

    def test_missing_keys(self):
        """Should handle missing keys in data points."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1},  # No metric keys
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)

    def test_invalid_string_value(self):
        """Should skip invalid string values."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": "not a number"},
            ]
        }

        # Should not raise an exception
        result = exporter.export_png(data)
        assert isinstance(result, bytes)

    def test_zero_values(self):
        """Should handle zero values."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": 0, "bcwp_cumulative": 0, "acwp_cumulative": 0},
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)

    def test_negative_values(self):
        """Should handle negative values (e.g., cost variances)."""
        exporter = SCurveExporter()
        data = {
            "data_points": [
                {"period": 1, "bcws_cumulative": -100},
            ]
        }

        result = exporter.export_png(data)

        assert isinstance(result, bytes)


class TestSCurveExporterIntegration:
    """Integration tests for complete export workflow."""

    def test_full_scurve_export_workflow(self):
        """Test complete S-curve export with all data types."""
        exporter = SCurveExporter()
        config = SCurveExportConfig(
            title="Program Alpha - EV Analysis",
            show_confidence_bands=True,
            show_legend=True,
            show_grid=True,
        )

        data = {
            "program_id": "test-program-123",
            "bac": "10000000.00",
            "data_points": [
                {
                    "period_number": 1,
                    "period_date": "2025-01-31",
                    "bcws_cumulative": "500000.00",
                    "bcwp_cumulative": "450000.00",
                    "acwp_cumulative": "480000.00",
                },
                {
                    "period_number": 2,
                    "period_date": "2025-02-28",
                    "bcws_cumulative": "1000000.00",
                    "bcwp_cumulative": "900000.00",
                    "acwp_cumulative": "950000.00",
                },
                {
                    "period_number": 3,
                    "period_date": "2025-03-31",
                    "bcws_cumulative": "1500000.00",
                    "bcwp_cumulative": "1400000.00",
                    "acwp_cumulative": "1450000.00",
                },
            ],
            "eac_range": {
                "p10": "9800000.00",
                "p50": "10200000.00",
                "p90": "10800000.00",
            },
        }

        # Export as PNG
        png_result = exporter.export_png(data, config)
        assert isinstance(png_result, bytes)
        assert len(png_result) > 1000  # Should be a non-trivial image
        assert png_result[:8] == b"\x89PNG\r\n\x1a\n"

        # Export as SVG
        svg_result = exporter.export_svg(data, config)
        assert isinstance(svg_result, bytes)
        assert b"<svg" in svg_result
        assert b"Program Alpha" in svg_result

    def test_export_multiple_formats_same_data(self):
        """Same data should produce valid output in both formats."""
        exporter = SCurveExporter()
        data = {"data_points": [{"period": i, "bcws_cumulative": i * 1000} for i in range(1, 11)]}

        png_result = exporter.export_png(data)
        svg_result = exporter.export_svg(data)

        # Both should produce valid output
        assert png_result[:8] == b"\x89PNG\r\n\x1a\n"
        assert b"<svg" in svg_result

        # SVG should be larger (text-based)
        assert len(svg_result) > len(png_result) / 10  # Just a sanity check
