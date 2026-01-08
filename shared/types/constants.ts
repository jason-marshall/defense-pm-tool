/**
 * Shared constants between frontend and backend.
 */

// Dependency types
export const DEPENDENCY_TYPES = {
  FS: "FS", // Finish-to-Start
  SS: "SS", // Start-to-Start
  FF: "FF", // Finish-to-Finish
  SF: "SF", // Start-to-Finish
} as const;

export type DependencyType = (typeof DEPENDENCY_TYPES)[keyof typeof DEPENDENCY_TYPES];

// EV Methods
export const EV_METHODS = {
  ZERO_HUNDRED: "0/100",
  FIFTY_FIFTY: "50/50",
  PERCENT_COMPLETE: "percent_complete",
  MILESTONE: "milestone",
} as const;

export type EVMethod = (typeof EV_METHODS)[keyof typeof EV_METHODS];

// Contract types
export const CONTRACT_TYPES = {
  FFP: "FFP", // Firm Fixed Price
  FPIF: "FPIF", // Fixed Price Incentive Firm
  CPFF: "CPFF", // Cost Plus Fixed Fee
  CPIF: "CPIF", // Cost Plus Incentive Fee
  CPAF: "CPAF", // Cost Plus Award Fee
  TM: "T&M", // Time and Materials
} as const;

export type ContractType = (typeof CONTRACT_TYPES)[keyof typeof CONTRACT_TYPES];

// WBS limits
export const MAX_WBS_DEPTH = 10;

// Performance thresholds
export const PERFORMANCE_THRESHOLDS = {
  CPI_CRITICAL: 0.9,
  CPI_WARNING: 0.95,
  SPI_CRITICAL: 0.9,
  SPI_WARNING: 0.95,
} as const;

// Pagination defaults
export const PAGINATION = {
  DEFAULT_PAGE_SIZE: 20,
  MAX_PAGE_SIZE: 100,
} as const;
