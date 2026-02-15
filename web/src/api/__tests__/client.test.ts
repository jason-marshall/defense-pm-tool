import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import type { InternalAxiosRequestConfig } from "axios";

// Capture interceptor callbacks before importing the module
const requestFulfilled: Array<
  (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig
> = [];
const responseFulfilled: Array<(response: unknown) => unknown> = [];
const responseRejected: Array<(error: unknown) => unknown> = [];

vi.mock("axios", async () => {
  const actual = await vi.importActual<typeof import("axios")>("axios");
  return {
    ...actual,
    default: {
      ...actual.default,
      create: () => {
        const instance = {
          interceptors: {
            request: {
              use: (onFulfilled: (config: InternalAxiosRequestConfig) => InternalAxiosRequestConfig) => {
                requestFulfilled.push(onFulfilled);
              },
            },
            response: {
              use: (
                onFulfilled: (response: unknown) => unknown,
                onRejected: (error: unknown) => unknown
              ) => {
                responseFulfilled.push(onFulfilled);
                responseRejected.push(onRejected);
              },
            },
          },
          defaults: { headers: { common: {} } },
        };
        return instance;
      },
      isAxiosError: actual.default.isAxiosError,
    },
  };
});

// Must import after mock setup
const { apiClient, getErrorMessage } = await import("../client");

describe("apiClient", () => {
  const originalLocation = window.location;

  beforeEach(() => {
    localStorage.clear();
    // Mock window.location
    Object.defineProperty(window, "location", {
      writable: true,
      value: { ...originalLocation, pathname: "/dashboard", href: "" },
    });
  });

  afterEach(() => {
    Object.defineProperty(window, "location", {
      writable: true,
      value: originalLocation,
    });
  });

  describe("request interceptor", () => {
    it("adds Authorization header when token exists", () => {
      localStorage.setItem("access_token", "test-jwt-token");

      const config = {
        headers: {},
      } as InternalAxiosRequestConfig;

      const result = requestFulfilled[0](config);
      expect(result.headers.Authorization).toBe("Bearer test-jwt-token");
    });

    it("does not add Authorization header when no token", () => {
      const config = {
        headers: {},
      } as InternalAxiosRequestConfig;

      const result = requestFulfilled[0](config);
      expect(result.headers.Authorization).toBeUndefined();
    });
  });

  describe("response interceptor", () => {
    it("clears tokens and redirects on 401", async () => {
      localStorage.setItem("access_token", "expired-token");
      localStorage.setItem("refresh_token", "refresh-token");

      const error = {
        response: { status: 401 },
        isAxiosError: true,
      };

      await expect(responseRejected[0](error)).rejects.toEqual(error);

      expect(localStorage.getItem("access_token")).toBeNull();
      expect(localStorage.getItem("refresh_token")).toBeNull();
      expect(window.location.href).toBe("/login");
    });

    it("does not redirect when already on /login", async () => {
      Object.defineProperty(window, "location", {
        writable: true,
        value: { pathname: "/login", href: "/login" },
      });
      localStorage.setItem("access_token", "expired-token");

      const error = {
        response: { status: 401 },
        isAxiosError: true,
      };

      await expect(responseRejected[0](error)).rejects.toEqual(error);

      // Token should still be there since redirect was skipped
      expect(localStorage.getItem("access_token")).toBe("expired-token");
    });

    it("passes through responses unchanged", () => {
      const response = { data: { id: 1 }, status: 200 };
      expect(responseFulfilled[0](response)).toEqual(response);
    });
  });

  describe("apiClient instance", () => {
    it("is defined", () => {
      expect(apiClient).toBeDefined();
    });
  });
});

describe("getErrorMessage", () => {
  it("extracts detail from AxiosError response", () => {
    const error = {
      response: { data: { detail: "Not found", code: "NOT_FOUND" } },
      message: "Request failed with status code 404",
      isAxiosError: true,
      name: "AxiosError",
    };
    // Manually set up axios.isAxiosError to recognize this
    Object.defineProperty(error, "isAxiosError", { value: true });
    // getErrorMessage uses axios.isAxiosError which checks the isAxiosError property
    expect(getErrorMessage(error)).toBe("Not found");
  });

  it("falls back to error.message for AxiosError without detail", () => {
    const error = {
      response: { data: {} },
      message: "Network Error",
      isAxiosError: true,
      name: "AxiosError",
    };
    expect(getErrorMessage(error)).toBe("Network Error");
  });

  it("handles plain Error objects", () => {
    const error = new Error("Something went wrong");
    expect(getErrorMessage(error)).toBe("Something went wrong");
  });

  it("handles unknown error types", () => {
    expect(getErrorMessage("string error")).toBe(
      "An unexpected error occurred"
    );
    expect(getErrorMessage(42)).toBe("An unexpected error occurred");
    expect(getErrorMessage(null)).toBe("An unexpected error occurred");
  });
});
