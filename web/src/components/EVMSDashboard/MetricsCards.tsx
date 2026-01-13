/**
 * EVMS Metrics summary cards component.
 */

import type { EVMSSummary } from "@/services/evmsApi";

export interface MetricsCardsProps {
  summary: EVMSSummary;
}

function formatCurrency(value: string | null): string {
  if (!value) return "N/A";
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(num);
}

function formatPercent(value: string | null): string {
  if (!value) return "N/A";
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return `${num.toFixed(1)}%`;
}

function getVarianceClass(value: string | null): string {
  if (!value) return "neutral";
  const num = parseFloat(value);
  if (num > 0) return "positive";
  if (num < 0) return "negative";
  return "neutral";
}

export function MetricsCards({ summary }: MetricsCardsProps) {
  return (
    <div className="evms-metrics-grid">
      <div className="evms-metric-card neutral">
        <div className="evms-metric-label">Budget at Completion (BAC)</div>
        <div className="evms-metric-value">
          {formatCurrency(summary.budgetAtCompletion)}
        </div>
        <div className="evms-metric-sublabel">Total authorized budget</div>
      </div>

      <div className="evms-metric-card neutral">
        <div className="evms-metric-label">Planned Value (BCWS)</div>
        <div className="evms-metric-value">
          {formatCurrency(summary.cumulativeBcws)}
        </div>
        <div className="evms-metric-sublabel">Budgeted Cost of Work Scheduled</div>
      </div>

      <div className="evms-metric-card neutral">
        <div className="evms-metric-label">Earned Value (BCWP)</div>
        <div className="evms-metric-value">
          {formatCurrency(summary.cumulativeBcwp)}
        </div>
        <div className="evms-metric-sublabel">Budgeted Cost of Work Performed</div>
      </div>

      <div className="evms-metric-card neutral">
        <div className="evms-metric-label">Actual Cost (ACWP)</div>
        <div className="evms-metric-value">
          {formatCurrency(summary.cumulativeAcwp)}
        </div>
        <div className="evms-metric-sublabel">Actual Cost of Work Performed</div>
      </div>

      <div className={`evms-metric-card ${getVarianceClass(summary.costVariance)}`}>
        <div className="evms-metric-label">Cost Variance (CV)</div>
        <div className={`evms-metric-value ${getVarianceClass(summary.costVariance)}`}>
          {formatCurrency(summary.costVariance)}
        </div>
        <div className="evms-metric-sublabel">BCWP - ACWP</div>
      </div>

      <div className={`evms-metric-card ${getVarianceClass(summary.scheduleVariance)}`}>
        <div className="evms-metric-label">Schedule Variance (SV)</div>
        <div className={`evms-metric-value ${getVarianceClass(summary.scheduleVariance)}`}>
          {formatCurrency(summary.scheduleVariance)}
        </div>
        <div className="evms-metric-sublabel">BCWP - BCWS</div>
      </div>

      <div className="evms-metric-card neutral">
        <div className="evms-metric-label">% Complete</div>
        <div className="evms-metric-value">
          {formatPercent(summary.percentComplete)}
        </div>
        <div className="evms-metric-sublabel">Work completed</div>
      </div>

      <div className="evms-metric-card neutral">
        <div className="evms-metric-label">% Spent</div>
        <div className="evms-metric-value">
          {formatPercent(summary.percentSpent)}
        </div>
        <div className="evms-metric-sublabel">Budget consumed</div>
      </div>
    </div>
  );
}
