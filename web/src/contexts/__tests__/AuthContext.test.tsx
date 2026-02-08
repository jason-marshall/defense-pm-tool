import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, waitFor, act } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { BrowserRouter } from "react-router-dom";
import { AuthProvider, useAuth } from "../AuthContext";

// Mock authApi
vi.mock("@/services/authApi", () => ({
  login: vi.fn(),
  register: vi.fn(),
  refreshToken: vi.fn(),
  getCurrentUser: vi.fn(),
}));

import * as authApi from "@/services/authApi";

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

// Test component that exposes auth state
function AuthStateDisplay() {
  const { user, isAuthenticated, isLoading, login, logout } = useAuth();

  return (
    <div>
      <span data-testid="loading">{String(isLoading)}</span>
      <span data-testid="authenticated">{String(isAuthenticated)}</span>
      <span data-testid="user">{user ? user.full_name : "none"}</span>
      <button onClick={() => login({ email: "test@example.com", password: "pass" })}>
        Login
      </button>
      <button onClick={logout}>Logout</button>
    </div>
  );
}

function renderWithAuth() {
  return render(
    <BrowserRouter>
      <AuthProvider>
        <AuthStateDisplay />
      </AuthProvider>
    </BrowserRouter>
  );
}

describe("AuthContext", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    localStorage.clear();
  });

  it("should show loading state initially when token exists", async () => {
    localStorage.setItem("access_token", "existing-token");
    vi.mocked(authApi.getCurrentUser).mockImplementation(
      () => new Promise(() => {}) // Never resolves - stays loading
    );

    renderWithAuth();

    expect(screen.getByTestId("loading").textContent).toBe("true");
  });

  it("should be unauthenticated when no token exists", async () => {
    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("false");
    expect(screen.getByTestId("user").textContent).toBe("none");
  });

  it("should authenticate on mount when valid token exists", async () => {
    localStorage.setItem("access_token", "existing-token");
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("true");
    expect(screen.getByTestId("user").textContent).toBe("Test User");
  });

  it("should clear token when getCurrentUser fails on mount", async () => {
    localStorage.setItem("access_token", "expired-token");
    vi.mocked(authApi.getCurrentUser).mockRejectedValue(new Error("Unauthorized"));

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });
    expect(screen.getByTestId("authenticated").textContent).toBe("false");
    expect(localStorage.getItem("access_token")).toBeNull();
  });

  it("should login successfully", async () => {
    vi.mocked(authApi.login).mockResolvedValue(mockTokens);
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId("loading").textContent).toBe("false");
    });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByText("Login"));
    });

    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("true");
    });
    expect(screen.getByTestId("user").textContent).toBe("Test User");
    expect(localStorage.getItem("access_token")).toBe("mock-access-token");
  });

  it("should logout successfully", async () => {
    localStorage.setItem("access_token", "existing-token");
    vi.mocked(authApi.getCurrentUser).mockResolvedValue(mockUser);

    renderWithAuth();

    await waitFor(() => {
      expect(screen.getByTestId("authenticated").textContent).toBe("true");
    });

    const user = userEvent.setup();
    await act(async () => {
      await user.click(screen.getByText("Logout"));
    });

    expect(screen.getByTestId("authenticated").textContent).toBe("false");
    expect(screen.getByTestId("user").textContent).toBe("none");
    expect(localStorage.getItem("access_token")).toBeNull();
  });

  it("should throw when useAuth is used outside AuthProvider", () => {
    // Suppress console.error for this test
    const spy = vi.spyOn(console, "error").mockImplementation(() => {});

    function BadComponent() {
      useAuth();
      return null;
    }

    expect(() => render(<BadComponent />)).toThrow(
      "useAuth must be used within an AuthProvider"
    );

    spy.mockRestore();
  });
});
