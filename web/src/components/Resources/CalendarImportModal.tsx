/**
 * Calendar Import Modal component for MS Project calendar import workflow.
 * Supports file upload, preview, and import confirmation.
 */

import { useCallback, useState, useRef, ChangeEvent } from "react";
import { Upload, Calendar, AlertTriangle, Check, X } from "lucide-react";
import {
  previewCalendarImport,
  importCalendars,
  validateCalendarFile,
} from "@/services/calendarImportApi";
import { useToast } from "@/components/Toast";
import type { CalendarImportPreviewResponse } from "@/types/calendarImport";
import "./CalendarImportModal.css";

type ImportStep = "upload" | "preview" | "importing" | "success" | "error";

export interface CalendarImportModalProps {
  programId: string;
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
}

export function CalendarImportModal({
  programId,
  isOpen,
  onClose,
  onSuccess,
}: CalendarImportModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [startDate, setStartDate] = useState("");
  const [endDate, setEndDate] = useState("");
  const [preview, setPreview] = useState<CalendarImportPreviewResponse | null>(
    null
  );
  const [step, setStep] = useState<ImportStep>("upload");
  const [error, setError] = useState<string | null>(null);
  const [importResult, setImportResult] = useState<{
    templates: number;
    resources: number;
    entries: number;
  } | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const toast = useToast();

  const resetState = useCallback(() => {
    setFile(null);
    setStartDate("");
    setEndDate("");
    setPreview(null);
    setStep("upload");
    setError(null);
    setImportResult(null);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [resetState, onClose]);

  const handleFileSelect = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        const validationError = validateCalendarFile(selectedFile);
        if (validationError) {
          toast.error(validationError);
          return;
        }
        setFile(selectedFile);
      }
    },
    [toast]
  );

  const handlePreview = useCallback(async () => {
    if (!file || !startDate || !endDate) {
      toast.error("Please fill in all fields");
      return;
    }

    if (new Date(endDate) < new Date(startDate)) {
      toast.error("End date must be after start date");
      return;
    }

    setStep("importing");
    setError(null);

    try {
      const previewResult = await previewCalendarImport(
        programId,
        file,
        startDate,
        endDate
      );
      setPreview(previewResult);
      setStep("preview");
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Preview failed";
      setError(errorMessage);
      setStep("error");
    }
  }, [file, startDate, endDate, programId, toast]);

  const handleImport = useCallback(async () => {
    if (!file) return;

    setStep("importing");
    setError(null);

    try {
      const result = await importCalendars(programId, file, startDate, endDate);
      setImportResult({
        templates: result.templates_created,
        resources: result.resources_updated,
        entries: result.calendar_entries_created,
      });
      setStep("success");
      toast.success(
        `Imported: ${result.templates_created} templates, ` +
          `${result.resources_updated} resources, ` +
          `${result.calendar_entries_created} calendar entries`
      );
    } catch (err: unknown) {
      const errorMessage =
        err instanceof Error ? err.message : "Import failed";
      setError(errorMessage);
      setStep("error");
    }
  }, [file, startDate, endDate, programId, toast]);

  const handleDone = useCallback(() => {
    onSuccess();
    handleClose();
  }, [onSuccess, handleClose]);

  if (!isOpen) return null;

  return (
    <div className="calendar-import-modal-overlay" onClick={handleClose}>
      <div
        className="calendar-import-modal"
        onClick={(e) => e.stopPropagation()}
      >
        <div className="calendar-import-modal-header">
          <h2>
            <Calendar className="calendar-import-header-icon" />
            Import Resource Calendars
          </h2>
          <button className="calendar-import-modal-close" onClick={handleClose} aria-label="Close">
            <X size={20} />
          </button>
        </div>

        <div className="calendar-import-modal-body">
          {/* Upload Step */}
          {step === "upload" && (
            <div className="calendar-import-upload">
              <div className="calendar-import-field">
                <label>MS Project XML File</label>
                <div
                  className="calendar-import-dropzone"
                  onClick={() => fileInputRef.current?.click()}
                >
                  <input
                    ref={fileInputRef}
                    type="file"
                    accept=".xml"
                    onChange={handleFileSelect}
                    style={{ display: "none" }}
                  />
                  <Upload className="calendar-import-upload-icon" />
                  <p>
                    {file ? file.name : "Click to select MS Project XML file"}
                  </p>
                </div>
              </div>

              <div className="calendar-import-dates">
                <div className="calendar-import-field">
                  <label>Start Date</label>
                  <input
                    type="date"
                    value={startDate}
                    onChange={(e) => setStartDate(e.target.value)}
                    className="calendar-import-input"
                  />
                </div>
                <div className="calendar-import-field">
                  <label>End Date</label>
                  <input
                    type="date"
                    value={endDate}
                    onChange={(e) => setEndDate(e.target.value)}
                    className="calendar-import-input"
                  />
                </div>
              </div>

              <button
                onClick={handlePreview}
                disabled={!file || !startDate || !endDate}
                className="calendar-import-btn calendar-import-btn-primary"
              >
                Preview Import
              </button>
            </div>
          )}

          {/* Preview Step */}
          {step === "preview" && preview && (
            <div className="calendar-import-preview">
              <div className="calendar-import-summary">
                <h3>Import Summary</h3>
                <ul>
                  <li>{preview.calendars.length} calendar(s) found</li>
                  <li>{preview.resource_mappings.length} resource mapping(s)</li>
                  <li>{preview.total_holidays} holiday(s)</li>
                  <li>
                    Date range: {preview.date_range_start} to{" "}
                    {preview.date_range_end}
                  </li>
                </ul>
              </div>

              {preview.warnings.length > 0 && (
                <div className="calendar-import-warnings">
                  <div className="calendar-import-warnings-header">
                    <AlertTriangle size={16} />
                    <span>Warnings</span>
                  </div>
                  <ul>
                    {preview.warnings.map((w, i) => (
                      <li key={i}>{w}</li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="calendar-import-mappings">
                <h4>Resource Mappings</h4>
                <div className="calendar-import-mappings-list">
                  {preview.resource_mappings.map((mapping, i) => (
                    <div key={i} className="calendar-import-mapping-item">
                      <span className="calendar-import-mapping-source">
                        {mapping.ms_project_resource}
                      </span>
                      <span className="calendar-import-mapping-arrow">→</span>
                      <span className="calendar-import-mapping-target">
                        {mapping.matched_resource_id ? (
                          <>
                            <Check
                              size={14}
                              className="calendar-import-check"
                            />
                            {mapping.matched_resource_name}
                          </>
                        ) : (
                          <span className="calendar-import-no-match">
                            No match
                          </span>
                        )}
                      </span>
                    </div>
                  ))}
                </div>
              </div>

              <div className="calendar-import-actions">
                <button
                  onClick={() => setStep("upload")}
                  className="calendar-import-btn calendar-import-btn-secondary"
                >
                  Back
                </button>
                <button
                  onClick={handleImport}
                  className="calendar-import-btn calendar-import-btn-success"
                >
                  Import Calendars
                </button>
              </div>
            </div>
          )}

          {/* Importing Step */}
          {step === "importing" && (
            <div className="calendar-import-loading">
              <div className="calendar-import-spinner" />
              <p>Importing calendars...</p>
            </div>
          )}

          {/* Success Step */}
          {step === "success" && importResult && (
            <div className="calendar-import-success">
              <div className="calendar-import-success-icon">✓</div>
              <h3>Import Complete!</h3>
              <div className="calendar-import-success-stats">
                <div className="calendar-import-stat">
                  <div className="calendar-import-stat-value">
                    {importResult.templates}
                  </div>
                  <div className="calendar-import-stat-label">Templates</div>
                </div>
                <div className="calendar-import-stat">
                  <div className="calendar-import-stat-value">
                    {importResult.resources}
                  </div>
                  <div className="calendar-import-stat-label">Resources</div>
                </div>
                <div className="calendar-import-stat">
                  <div className="calendar-import-stat-value">
                    {importResult.entries}
                  </div>
                  <div className="calendar-import-stat-label">
                    Calendar Entries
                  </div>
                </div>
              </div>
              <button
                onClick={handleDone}
                className="calendar-import-btn calendar-import-btn-primary"
              >
                Done
              </button>
            </div>
          )}

          {/* Error Step */}
          {step === "error" && (
            <div className="calendar-import-error">
              <div className="calendar-import-error-icon">!</div>
              <h3>Import Failed</h3>
              <p>{error}</p>
              <div className="calendar-import-actions">
                <button
                  onClick={handleClose}
                  className="calendar-import-btn calendar-import-btn-secondary"
                >
                  Cancel
                </button>
                <button
                  onClick={resetState}
                  className="calendar-import-btn calendar-import-btn-primary"
                >
                  Try Again
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
