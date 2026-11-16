import { ApiError, apiRequest } from "@/lib/api";

export interface AuthenticatedUser {
  id: string;
  email: string;
}

export interface LoginResponse {
  user: AuthenticatedUser;
}

export function login(email: string, password: string): Promise<LoginResponse> {
  return apiRequest<LoginResponse>("/auth/login/", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function logout(): Promise<void> {
  await apiRequest<{ detail: string }>("/auth/logout/", {
    method: "POST",
  });
}

export async function getCurrentUser(): Promise<AuthenticatedUser | null> {
  try {
    return await apiRequest<AuthenticatedUser>("/auth/me/");
  } catch (error) {
    if (error instanceof ApiError && error.status === 403) {
      return null;
    }
    throw error;
  }
}
