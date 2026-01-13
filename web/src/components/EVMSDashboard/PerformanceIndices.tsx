/**
 * Performance indices (CPI, SPI) display component.
 */

import type { EVMSSummary } from "@/services/evmsApi";

export interface PerformanceIndicesProps {
  summary: EVMSSummary;
}

function formatIndex(value: string | null): string {
  if (!value) return "N/A";
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return num.toFixed(2);
}

function getIndexClass(value: string | null): "good" | "warning" | "bad" {
  if (!value) return "warning";
  const num = parseFloat(value);
  if (num >= 1.0) return "good";
  if (num >= 0.9) return "warning";
  return "bad";
}

function getBarWidth(value: string | null): number {
  if (!value) return 0;
  const num = parseFloat(value);
  // Cap at 150% for display purposes
  return Math.min(num * 100, 150);
}

function getIndexDescription(type: "cpi" | "spi", value: string | null): string {
  if (!value) return "No data available";
  const num = parseFloat(value);

  if (type === "cpi") {
    if (num >= 1.0) return "Under budget - efficient cost performance";
    if (num >= 0.9) return "Slightly over budget - monitor closely";
    return "Over budget - corrective action needed";
  } else {
    if (num >= 1.0) return "Ahead of schedule - good progress";
    if (num >= 0.9) return "Slightly behind schedule - monitor closely";
    return "Behind schedule - corrective action needed";
  }
}

export function PerformanceIndices({ summary }: PerformanceIndicesProps) {
  const cpiClass = getIndexClass(summary.cpi);
  const spiClass = getIndexClass(summary.spi);

  return (
    <div className="evms-section">
      <div className="evms-section-header">
        <h3>Performance Indices</h3>
        <OverallStatus cpi={summary.cpi} spi={summary.spi} />
      </div>

      <div className="evms-indices-row">
        {/* Cost Performance Index */}
        <div className="evms-index-card">
          <div className="evms-index-header">
            <span className="evms-index-name">Cost Performance Index (CPI)</span>
            <span className={`evms-index-value ${cpiClass}`}>
              {formatIndex(summary.cpi)}
            </span>
          </div>
          <div className="evms-index-bar">
            <div
              className={`evms-index-bar-fill ${cpiClass}`}
              style={{ width: `${Math.min(getBarWidth(summary.cpi), 100)}%` }}
            />
          </div>
          <div className="evms-index-description">
            {getIndexDescription("cpi", summary.cpi)}
          </div>
        </div>

        {/* Schedule Performance Index */}
        <div className="evms-index-card">
          <div className="evms-index-header">
            <span className="evms-index-name">Schedule Performance Index (SPI)</span>
            <span className={`evms-index-value ${spiClass}`}>
              {formatIndex(summary.spi)}
            </span>
          </div>
          <div className="evms-index-bar">
            <div
              className={`evms-index-bar-fill ${spiClass}`}
              style={{ width: `${Math.min(getBarWidth(summary.spi), 100)}%` }}
            />
          </div>
          <div className="evms-index-description">
            {getIndexDescription("spi", summary.spi)}
          </div>
        </div>
      </div>
    </div>
  );
}

interface OverallStatusProps {
  cpi: string | null;
  spi: string | null;
}

function OverallStatus({ cpi, spi }: OverallStatusProps) {
  const cpiNum = cpi ? parseFloat(cpi) : null;
  const spiNum = spi ? parseFloat(spi) : null;

  let status: "on-track" | "at-risk" | "behind" = "on-track";
  let label = "On Track";

  if (cpiNum === null || spiNum === null) {
    status = "at-risk";
    label = "No Data";
  } else if (cpiNum < 0.9 || spiNum < 0.9) {
    status = "behind";
    label = "Behind";
  } else if (cpiNum < 1.0 || spiNum < 1.0) {
    status = "at-risk";
    label = "At Risk";
  }

  return (
    <span className={`evms-status-badge ${status}`}>
      <span className="evms-status-dot" />
      {label}
    </span>
  );
}
