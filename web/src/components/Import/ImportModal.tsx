/**
 * Import Modal component for MS Project XML file import workflow.
 * Supports drag-and-drop upload, preview, and import confirmation.
 */

import { useCallback, useState, useRef, DragEvent, ChangeEvent } from "react";
import {
  previewMSProjectImport,
  importMSProject,
  validateImportFile,
  getErrorMessage,
} from "@/services/importApi";
import type {
  ImportState,
  ImportPreviewResponse,
  ImportResultResponse,
} from "@/types/import";
import "./ImportModal.css";

export interface ImportModalProps {
  programId: string;
  programName?: string;
  isOpen: boolean;
  onClose: () => void;
  onImportComplete?: (result: ImportResultResponse) => void;
}

export function ImportModal({
  programId,
  programName,
  isOpen,
  onClose,
  onImportComplete,
}: ImportModalProps) {
  const [state, setState] = useState<ImportState>("idle");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<ImportPreviewResponse | null>(null);
  const [result, setResult] = useState<ImportResultResponse | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const resetState = useCallback(() => {
    setState("idle");
    setFile(null);
    setPreview(null);
    setResult(null);
    setError(null);
    setIsDragOver(false);
  }, []);

  const handleClose = useCallback(() => {
    resetState();
    onClose();
  }, [resetState, onClose]);

  const handleFileSelect = useCallback(
    async (selectedFile: File) => {
      const validationError = validateImportFile(selectedFile);
      if (validationError) {
        setError(validationError);
        setState("error");
        return;
      }

      setFile(selectedFile);
      setError(null);
      setState("uploading");

      try {
        const previewResult = await previewMSProjectImport(
          programId,
          selectedFile
        );
        setPreview(previewResult);
        setState("preview");
      } catch (err) {
        setError(getErrorMessage(err));
        setState("error");
      }
    },
    [programId]
  );

  const handleDragOver = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(true);
  }, []);

  const handleDragLeave = useCallback((e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback(
    (e: DragEvent<HTMLDivElement>) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);

      const droppedFile = e.dataTransfer.files[0];
      if (droppedFile) {
        handleFileSelect(droppedFile);
      }
    },
    [handleFileSelect]
  );

  const handleFileInputChange = useCallback(
    (e: ChangeEvent<HTMLInputElement>) => {
      const selectedFile = e.target.files?.[0];
      if (selectedFile) {
        handleFileSelect(selectedFile);
      }
    },
    [handleFileSelect]
  );

  const handleBrowseClick = useCallback(() => {
    fileInputRef.current?.click();
  }, []);

  const handleRemoveFile = useCallback(() => {
    resetState();
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  }, [resetState]);

  const handleImport = useCallback(async () => {
    if (!file) return;

    setState("importing");
    setError(null);

    try {
      const importResult = await importMSProject(programId, file);
      setResult(importResult);
      setState("success");
      onImportComplete?.(importResult);
    } catch (err) {
      setError(getErrorMessage(err));
      setState("error");
    }
  }, [file, programId, onImportComplete]);

  const formatFileSize = (bytes: number): string => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  };

  const formatDate = (dateStr: string): string => {
    return new Date(dateStr).toLocaleDateString("en-US", {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  };

  const formatDuration = (hours: number): string => {
    if (hours === 0) return "0h";
    const days = Math.floor(hours / 8);
    const remainingHours = hours % 8;
    if (days === 0) return `${remainingHours}h`;
    if (remainingHours === 0) return `${days}d`;
    return `${days}d ${remainingHours}h`;
  };

  if (!isOpen) return null;

  return (
    <div className="import-modal-overlay" onClick={handleClose}>
      <div className="import-modal" onClick={(e) => e.stopPropagation()}>
        <div className="import-modal-header">
          <h2>Import MS Project File</h2>
          <button className="import-modal-close" onClick={handleClose}>
            &times;
          </button>
        </div>

        <div className="import-modal-body">
          {programName && (
            <p style={{ marginTop: 0, color: "#666" }}>
              Importing into: <strong>{programName}</strong>
            </p>
          )}

          {/* File Drop Zone */}
          {(state === "idle" || state === "error") && (
            <>
              <div
                className={`import-dropzone ${isDragOver ? "dragover" : ""} ${file ? "has-file" : ""}`}
                onDragOver={handleDragOver}
                onDragLeave={handleDragLeave}
                onDrop={handleDrop}
                onClick={handleBrowseClick}
              >
                <div className="import-dropzone-icon">
                  {file ? "📄" : "📁"}
                </div>
                <h3>{file ? "File Selected" : "Drag & Drop MS Project XML"}</h3>
                <p>
                  {file
                    ? "Click to select a different file"
                    : "or click to browse"}
                </p>

                {file && (
                  <div className="import-dropzone-file">
                    <span className="import-dropzone-file-icon">📄</span>
                    <div className="import-dropzone-file-info">
                      <div className="import-dropzone-file-name">
                        {file.name}
                      </div>
                      <div className="import-dropzone-file-size">
                        {formatFileSize(file.size)}
                      </div>
                    </div>
                    <button
                      className="import-dropzone-remove"
                      onClick={(e) => {
                        e.stopPropagation();
                        handleRemoveFile();
                      }}
                    >
                      &times;
                    </button>
                  </div>
                )}

                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".xml"
                  style={{ display: "none" }}
                  onChange={handleFileInputChange}
                />
              </div>

              {state === "error" && error && (
                <div className="import-error">
                  <div className="import-error-icon">&#x26A0;</div>
                  <h3>Import Failed</h3>
                  <p>There was a problem with the file.</p>
                  <div className="import-error-message">{error}</div>
                </div>
              )}
            </>
          )}

          {/* Uploading State */}
          {state === "uploading" && (
            <div className="import-progress">
              <div className="import-progress-text">
                <span>Analyzing file...</span>
              </div>
              <div className="import-progress-bar">
                <div
                  className="import-progress-fill"
                  style={{ width: "100%", animation: "pulse 1.5s infinite" }}
                />
              </div>
              <div className="import-progress-status">
                Parsing MS Project XML structure
              </div>
            </div>
          )}

          {/* Preview State */}
          {state === "preview" && preview && (
            <div className="import-preview">
              <div className="import-preview-header">
                <h3>Preview Import</h3>
                <span className="import-preview-badge">
                  {preview.taskCount} tasks found
                </span>
              </div>

              <div className="import-preview-info">
                <div className="import-preview-info-item">
                  <div className="import-preview-info-label">Project Name</div>
                  <div className="import-preview-info-value">
                    {preview.projectName}
                  </div>
                </div>
                <div className="import-preview-info-item">
                  <div className="import-preview-info-label">Date Range</div>
                  <div className="import-preview-info-value">
                    {formatDate(preview.startDate)} -{" "}
                    {formatDate(preview.finishDate)}
                  </div>
                </div>
              </div>

              {preview.tasks.length > 0 && (
                <div className="import-preview-tasks">
                  <h4>Sample Tasks (first 20)</h4>
                  <table className="import-preview-table">
                    <thead>
                      <tr>
                        <th>WBS</th>
                        <th>Task Name</th>
                        <th>Duration</th>
                        <th>Links</th>
                      </tr>
                    </thead>
                    <tbody>
                      {preview.tasks.map((task, index) => (
                        <tr key={index}>
                          <td>{task.wbs || "-"}</td>
                          <td>
                            {task.name}
                            {task.isMilestone && (
                              <span className="import-milestone-badge">
                                Milestone
                              </span>
                            )}
                          </td>
                          <td>{formatDuration(task.durationHours)}</td>
                          <td>{task.predecessors}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}

              {preview.warnings.length > 0 && (
                <div className="import-warnings">
                  <div className="import-warnings-header">
                    <span>&#x26A0;</span> Import Warnings
                  </div>
                  <ul className="import-warnings-list">
                    {preview.warnings.map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          )}

          {/* Importing State */}
          {state === "importing" && (
            <div className="import-progress">
              <div className="import-progress-text">
                <span>Importing data...</span>
              </div>
              <div className="import-progress-bar">
                <div
                  className="import-progress-fill"
                  style={{ width: "100%", animation: "pulse 1.5s infinite" }}
                />
              </div>
              <div className="import-progress-status">
                Creating activities, dependencies, and WBS elements
              </div>
            </div>
          )}

          {/* Success State */}
          {state === "success" && result && (
            <div className="import-success">
              <div className="import-success-icon">&#x2705;</div>
              <h3>Import Complete!</h3>
              <p>Your MS Project data has been successfully imported.</p>

              <div className="import-success-stats">
                <div className="import-success-stat">
                  <div className="import-success-stat-value">
                    {result.tasksImported}
                  </div>
                  <div className="import-success-stat-label">
                    Activities Created
                  </div>
                </div>
                <div className="import-success-stat">
                  <div className="import-success-stat-value">
                    {result.dependenciesImported}
                  </div>
                  <div className="import-success-stat-label">
                    Dependencies Linked
                  </div>
                </div>
                <div className="import-success-stat">
                  <div className="import-success-stat-value">
                    {result.wbsElementsCreated}
                  </div>
                  <div className="import-success-stat-label">
                    WBS Elements Added
                  </div>
                </div>
              </div>

              {result.warnings.length > 0 && (
                <div className="import-warnings">
                  <div className="import-warnings-header">
                    <span>&#x26A0;</span> Import Warnings ({result.warnings.length})
                  </div>
                  <ul className="import-warnings-list">
                    {result.warnings.slice(0, 5).map((warning, index) => (
                      <li key={index}>{warning}</li>
                    ))}
                    {result.warnings.length > 5 && (
                      <li>...and {result.warnings.length - 5} more warnings</li>
                    )}
                  </ul>
                </div>
              )}
            </div>
          )}
        </div>

        <div className="import-modal-footer">
          {state === "idle" && (
            <button className="import-btn import-btn-secondary" onClick={handleClose}>
              Cancel
            </button>
          )}

          {state === "preview" && (
            <>
              <button
                className="import-btn import-btn-secondary"
                onClick={handleRemoveFile}
              >
                Choose Different File
              </button>
              <button
                className="import-btn import-btn-primary"
                onClick={handleImport}
              >
                Import {preview?.taskCount} Tasks
              </button>
            </>
          )}

          {(state === "uploading" || state === "importing") && (
            <button className="import-btn import-btn-secondary" disabled>
              <span className="import-spinner" />
              {state === "uploading" ? "Analyzing..." : "Importing..."}
            </button>
          )}

          {state === "success" && (
            <button
              className="import-btn import-btn-success"
              onClick={handleClose}
            >
              Done
            </button>
          )}

          {state === "error" && (
            <>
              <button
                className="import-btn import-btn-secondary"
                onClick={handleClose}
              >
                Cancel
              </button>
              <button
                className="import-btn import-btn-primary"
                onClick={resetState}
              >
                Try Again
              </button>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
