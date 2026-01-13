/**
 * Main EVMS Dashboard component for displaying program earned value metrics.
 */

import { useEVMSSummary } from "@/hooks/useEVMSMetrics";
import { MetricsCards } from "./MetricsCards";
import { PerformanceIndices } from "./PerformanceIndices";
import { ProjectionCard } from "./ProjectionCard";
import "./EVMSDashboard.css";

export interface EVMSDashboardProps {
  programId: string;
  programName?: string;
}

export function EVMSDashboard({ programId, programName }: EVMSDashboardProps) {
  const { data: summary, isLoading, isError, error } = useEVMSSummary(programId);

  if (isLoading) {
    return (
      <div className="evms-dashboard">
        <div className="evms-dashboard-loading">Loading EVMS metrics...</div>
      </div>
    );
  }

  if (isError) {
    return (
      <div className="evms-dashboard">
        <div className="evms-dashboard-error">
          Error loading EVMS data: {(error as Error)?.message || "Unknown error"}
        </div>
      </div>
    );
  }

  if (!summary) {
    return (
      <div className="evms-dashboard">
        <div className="evms-no-data">
          <p>No EVMS data available for this program.</p>
          <p>Create an EVMS period and add performance data to get started.</p>
        </div>
      </div>
    );
  }

  const hasData =
    parseFloat(summary.cumulativeBcws) > 0 ||
    parseFloat(summary.cumulativeBcwp) > 0 ||
    parseFloat(summary.cumulativeAcwp) > 0;

  return (
    <div className="evms-dashboard">
      <div className="evms-dashboard-header">
        <h2>EVMS Dashboard</h2>
        <p>{programName || summary.programName}</p>
      </div>

      {!hasData ? (
        <div className="evms-no-data">
          <p>No EVMS period data has been recorded yet.</p>
          <p>Add period data to view earned value metrics and projections.</p>
        </div>
      ) : (
        <>
          {/* Key Metrics Overview */}
          <MetricsCards summary={summary} />

          {/* Performance Indices (CPI, SPI) */}
          <PerformanceIndices summary={summary} />

          {/* Progress Bar */}
          <ProgressSection summary={summary} />

          {/* Projections (EAC, ETC, VAC) */}
          <ProjectionCard summary={summary} />

          {/* Latest Period Info */}
          {summary.latestPeriod && (
            <LatestPeriodInfo period={summary.latestPeriod} />
          )}
        </>
      )}
    </div>
  );
}

interface ProgressSectionProps {
  summary: {
    percentComplete: string;
    percentSpent: string;
    budgetAtCompletion: string;
  };
}

function ProgressSection({ summary }: ProgressSectionProps) {
  const percentComplete = parseFloat(summary.percentComplete) || 0;
  const percentSpent = parseFloat(summary.percentSpent) || 0;

  return (
    <div className="evms-section">
      <div className="evms-section-header">
        <h3>Progress Overview</h3>
      </div>

      <div className="evms-progress-section">
        <div className="evms-progress-header">
          <span>Work Completion vs. Budget Consumption</span>
          <span>
            {percentComplete.toFixed(1)}% complete / {percentSpent.toFixed(1)}%
            spent
          </span>
        </div>

        <div className="evms-progress-bar-container">
          <div
            className="evms-progress-bar complete"
            style={{ width: `${Math.min(percentComplete, 100)}%` }}
          />
          {percentSpent > percentComplete && (
            <div
              className="evms-progress-bar spent"
              style={{ width: `${Math.min(percentSpent, 100)}%` }}
            />
          )}
        </div>

        <div className="evms-progress-labels">
          <span>0%</span>
          <span>25%</span>
          <span>50%</span>
          <span>75%</span>
          <span>100%</span>
        </div>

        {percentSpent > percentComplete && (
          <div
            style={{
              marginTop: "12px",
              padding: "8px 12px",
              background: "#fff3e0",
              borderRadius: "4px",
              fontSize: "13px",
              color: "#e65100",
            }}
          >
            Budget consumption ({percentSpent.toFixed(1)}%) exceeds work completion (
            {percentComplete.toFixed(1)}%). Cost overrun risk detected.
          </div>
        )}
      </div>
    </div>
  );
}

interface LatestPeriodInfoProps {
  period: {
    periodName: string;
    periodStart: string;
    periodEnd: string;
    status: string;
  };
}

function LatestPeriodInfo({ period }: LatestPeriodInfoProps) {
  const formatDate = (dateStr: string) => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  return (
    <div className="evms-section">
      <div className="evms-section-header">
        <h3>Latest Reporting Period</h3>
        <span
          style={{
            fontSize: "12px",
            padding: "4px 8px",
            background: "#e3f2fd",
            borderRadius: "4px",
            color: "#1565c0",
            textTransform: "capitalize",
          }}
        >
          {period.status}
        </span>
      </div>

      <div
        style={{
          display: "flex",
          gap: "24px",
          fontSize: "14px",
          color: "#666",
        }}
      >
        <div>
          <strong>Period:</strong> {period.periodName}
        </div>
        <div>
          <strong>From:</strong> {formatDate(period.periodStart)}
        </div>
        <div>
          <strong>To:</strong> {formatDate(period.periodEnd)}
        </div>
      </div>
    </div>
  );
}
