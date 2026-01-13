/**
 * EVMS Projections display component (EAC, ETC, VAC, TCPI).
 */

import type { EVMSSummary } from "@/services/evmsApi";

export interface ProjectionCardProps {
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

function formatIndex(value: string | null): string {
  if (!value) return "N/A";
  const num = parseFloat(value);
  if (isNaN(num)) return value;
  return num.toFixed(2);
}

function getVACClass(value: string | null): string {
  if (!value) return "";
  const num = parseFloat(value);
  if (num >= 0) return "positive";
  return "negative";
}

export function ProjectionCard({ summary }: ProjectionCardProps) {
  return (
    <div className="evms-section">
      <div className="evms-section-header">
        <h3>Projections & Estimates</h3>
      </div>

      <div className="evms-projections-grid">
        <div className="evms-projection-card">
          <div className="evms-projection-label">Estimate at Completion (EAC)</div>
          <div className="evms-projection-value">
            {formatCurrency(summary.estimateAtCompletion)}
          </div>
        </div>

        <div className="evms-projection-card">
          <div className="evms-projection-label">Estimate to Complete (ETC)</div>
          <div className="evms-projection-value">
            {formatCurrency(summary.estimateToComplete)}
          </div>
        </div>

        <div className="evms-projection-card">
          <div className="evms-projection-label">Variance at Completion (VAC)</div>
          <div className={`evms-projection-value ${getVACClass(summary.varianceAtCompletion)}`}>
            {formatCurrency(summary.varianceAtCompletion)}
          </div>
        </div>

        <div className="evms-projection-card">
          <div className="evms-projection-label">TCPI (to BAC)</div>
          <div className="evms-projection-value">
            {formatIndex(summary.tcpiBac)}
          </div>
        </div>

        <div className="evms-projection-card">
          <div className="evms-projection-label">TCPI (to EAC)</div>
          <div className="evms-projection-value">
            {formatIndex(summary.tcpiEac)}
          </div>
        </div>

        <div className="evms-projection-card">
          <div className="evms-projection-label">Budget at Completion</div>
          <div className="evms-projection-value">
            {formatCurrency(summary.budgetAtCompletion)}
          </div>
        </div>
      </div>

      {/* TCPI Interpretation */}
      <TCPIInterpretation tcpiBac={summary.tcpiBac} />
    </div>
  );
}

interface TCPIInterpretationProps {
  tcpiBac: string | null;
}

function TCPIInterpretation({ tcpiBac }: TCPIInterpretationProps) {
  if (!tcpiBac) return null;

  const bacNum = parseFloat(tcpiBac);
  if (isNaN(bacNum)) return null;

  let interpretation = "";

  if (bacNum > 1.1) {
    interpretation =
      "TCPI to BAC > 1.1: Meeting original budget is very difficult. Consider EAC-based target.";
  } else if (bacNum > 1.0) {
    interpretation =
      "TCPI to BAC > 1.0: Need improved efficiency to meet original budget.";
  } else {
    interpretation = "TCPI to BAC <= 1.0: On track to meet or beat original budget.";
  }

  if (!interpretation) return null;

  return (
    <div
      style={{
        marginTop: "12px",
        padding: "12px",
        background: "#fff8e1",
        borderRadius: "4px",
        fontSize: "13px",
        color: "#5d4037",
      }}
    >
      <strong>Interpretation:</strong> {interpretation}
    </div>
  );
}
