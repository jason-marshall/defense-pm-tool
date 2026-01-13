/**
 * API service for MS Project import functionality.
 */

import { apiClient, getErrorMessage } from "@/api/client";
import type { ImportPreviewResponse, ImportResultResponse } from "@/types/import";

/**
 * Preview an MS Project XML file without importing.
 * Returns task count, project info, and sample tasks.
 */
export async function previewMSProjectImport(
  programId: string,
  file: File
): Promise<ImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<ImportPreviewResponse>(
    `/import/msproject/${programId}?preview=true`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data;
}

/**
 * Import an MS Project XML file into a program.
 * Creates activities, dependencies, and WBS elements.
 */
export async function importMSProject(
  programId: string,
  file: File
): Promise<ImportResultResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<ImportResultResponse>(
    `/import/msproject/${programId}`,
    formData,
    {
      headers: {
        "Content-Type": "multipart/form-data",
      },
    }
  );
  return response.data;
}

/**
 * Validate file before upload.
 * Returns error message if invalid, null if valid.
 */
export function validateImportFile(file: File): string | null {
  // Check file extension
  if (!file.name.toLowerCase().endsWith(".xml")) {
    return "File must be an MS Project XML file (.xml)";
  }

  // Check file size (max 50MB)
  const maxSize = 50 * 1024 * 1024;
  if (file.size > maxSize) {
    return "File size exceeds 50MB limit";
  }

  // Check for empty file
  if (file.size === 0) {
    return "File is empty";
  }

  return null;
}

export { getErrorMessage };
