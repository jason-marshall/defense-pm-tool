import { describe, it, expect, vi, beforeEach } from "vitest";

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
  },
}));

import { apiClient } from "@/api/client";
import { login, register, refreshToken, getCurrentUser } from "../authApi";

const mockedGet = vi.mocked(apiClient.get);
const mockedPost = vi.mocked(apiClient.post);

const mockUser = {
  id: "user-001",
  email: "test@example.com",
  full_name: "Test User",
  role: "scheduler",
  is_active: true,
  created_at: "2026-01-01T00:00:00Z",
  updated_at: "2026-01-01T00:00:00Z",
};

const mockTokens = {
  access_token: "mock-access-token",
  refresh_token: "mock-refresh-token",
  token_type: "bearer",
  expires_in: 900,
};

describe("authApi", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("login", () => {
    it("should send login credentials and return tokens", async () => {
      mockedPost.mockResolvedValue({ data: mockTokens });

      const result = await login({
        email: "test@example.com",
        password: "password123",
      });

      expect(mockedPost).toHaveBeenCalledWith("/auth/login", {
        email: "test@example.com",
        password: "password123",
      });
      expect(result).toEqual(mockTokens);
    });
  });

  describe("register", () => {
    it("should send registration data and return user", async () => {
      mockedPost.mockResolvedValue({ data: mockUser });

      const result = await register({
        email: "test@example.com",
        password: "password123",
        full_name: "Test User",
      });

      expect(mockedPost).toHaveBeenCalledWith("/auth/register", {
        email: "test@example.com",
        password: "password123",
        full_name: "Test User",
      });
      expect(result).toEqual(mockUser);
    });
  });

  describe("refreshToken", () => {
    it("should send refresh token and return new tokens", async () => {
      mockedPost.mockResolvedValue({ data: mockTokens });

      const result = await refreshToken("old-refresh-token");

      expect(mockedPost).toHaveBeenCalledWith("/auth/refresh", {
        refresh_token: "old-refresh-token",
      });
      expect(result).toEqual(mockTokens);
    });
  });

  describe("getCurrentUser", () => {
    it("should fetch current user profile", async () => {
      mockedGet.mockResolvedValue({ data: mockUser });

      const result = await getCurrentUser();

      expect(mockedGet).toHaveBeenCalledWith("/auth/me");
      expect(result).toEqual(mockUser);
    });
  });
});
