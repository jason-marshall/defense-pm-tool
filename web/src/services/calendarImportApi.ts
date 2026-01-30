/**
 * API service for calendar import functionality.
 */

import { apiClient } from "@/api/client";
import type {
  CalendarImportPreviewResponse,
  CalendarImportResponse,
} from "@/types/calendarImport";

/**
 * Preview calendar import from MS Project XML.
 * Shows what calendars will be imported and resource mappings.
 */
export async function previewCalendarImport(
  programId: string,
  file: File,
  startDate: string,
  endDate: string
): Promise<CalendarImportPreviewResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<CalendarImportPreviewResponse>(
    `/calendars/import/preview?program_id=${programId}&start_date=${startDate}&end_date=${endDate}`,
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
 * Import calendars from MS Project XML and apply to resources.
 * Creates calendar templates and generates calendar entries.
 */
export async function importCalendars(
  programId: string,
  file: File,
  startDate: string,
  endDate: string
): Promise<CalendarImportResponse> {
  const formData = new FormData();
  formData.append("file", file);

  const response = await apiClient.post<CalendarImportResponse>(
    `/calendars/import?program_id=${programId}&start_date=${startDate}&end_date=${endDate}`,
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
 * Validate calendar import file before upload.
 * Returns error message if invalid, null if valid.
 */
export function validateCalendarFile(file: File): string | null {
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

export const calendarImportApi = {
  preview: previewCalendarImport,
  import: importCalendars,
  validate: validateCalendarFile,
};
