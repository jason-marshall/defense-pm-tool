/**
 * Report viewer with format selector and PDF download.
 */

import { useState } from "react";
import { FileText, Download } from "lucide-react";
import { CPRFormat1 } from "./CPRFormat1";
import { CPRFormat3 } from "./CPRFormat3";
import { CPRFormat5 } from "./CPRFormat5";
import { ReportAuditTrail } from "./ReportAuditTrail";
import { downloadReportPDF } from "@/services/reportApi";
import { useToast } from "@/components/Toast";
import type { CPRFormat } from "@/types/report";

interface ReportViewerProps {
  programId: string;
}

export function ReportViewer({ programId }: ReportViewerProps) {
  const [activeFormat, setActiveFormat] = useState<CPRFormat | "audit">("format1");
  const [downloading, setDownloading] = useState(false);
  const toast = useToast();

  const handleDownloadPDF = async () => {
    if (activeFormat === "audit") return;
    setDownloading(true);
    try {
      const blob = await downloadReportPDF(programId, activeFormat);
      const url = window.URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `CPR_${activeFormat}_${programId}.pdf`;
      document.body.appendChild(a);
      a.click();
      window.URL.revokeObjectURL(url);
      document.body.removeChild(a);
      toast.success("PDF downloaded");
    } catch {
      toast.error("Failed to download PDF");
    } finally {
      setDownloading(false);
    }
  };

  const formats: { key: CPRFormat | "audit"; label: string }[] = [
    { key: "format1", label: "Format 1 (WBS)" },
    { key: "format3", label: "Format 3 (Baseline)" },
    { key: "format5", label: "Format 5 (Variance)" },
    { key: "audit", label: "Audit Trail" },
  ];

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-xl font-semibold flex items-center gap-2">
          <FileText size={20} /> CPR Reports
        </h2>
        {activeFormat !== "audit" && (
          <button
            onClick={handleDownloadPDF}
            disabled={downloading}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 text-sm disabled:opacity-50"
          >
            <Download size={16} />
            {downloading ? "Downloading..." : "Download PDF"}
          </button>
        )}
      </div>

      <div className="border-b border-gray-200 mb-4">
        <nav className="flex gap-0 -mb-px">
          {formats.map((f) => (
            <button
              key={f.key}
              onClick={() => setActiveFormat(f.key)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeFormat === f.key
                  ? "border-blue-600 text-blue-600"
                  : "border-transparent text-gray-500 hover:text-gray-700"
              }`}
            >
              {f.label}
            </button>
          ))}
        </nav>
      </div>

      {activeFormat === "format1" && <CPRFormat1 programId={programId} />}
      {activeFormat === "format3" && <CPRFormat3 programId={programId} />}
      {activeFormat === "format5" && <CPRFormat5 programId={programId} />}
      {activeFormat === "audit" && <ReportAuditTrail programId={programId} />}
    </div>
  );
}
