/**
 * API service for authentication endpoints.
 */

import { apiClient } from "@/api/client";

export interface User {
  id: string;
  email: string;
  full_name: string;
  role: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name: string;
}

export interface TokenPairResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

/**
 * Login with email and password.
 */
export async function login(credentials: LoginRequest): Promise<TokenPairResponse> {
  const response = await apiClient.post<TokenPairResponse>("/auth/login", credentials);
  return response.data;
}

/**
 * Register a new user account.
 */
export async function register(data: RegisterRequest): Promise<User> {
  const response = await apiClient.post<User>("/auth/register", data);
  return response.data;
}

/**
 * Refresh the access token using a refresh token.
 */
export async function refreshToken(refresh_token: string): Promise<TokenPairResponse> {
  const response = await apiClient.post<TokenPairResponse>("/auth/refresh", {
    refresh_token,
  });
  return response.data;
}

/**
 * Get the currently authenticated user's profile.
 */
export async function getCurrentUser(): Promise<User> {
  const response = await apiClient.get<User>("/auth/me");
  return response.data;
}
