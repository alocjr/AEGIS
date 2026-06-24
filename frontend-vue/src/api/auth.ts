import { post, apiRequest } from './client'

export interface LoginPayload {
  email: string
  password: string
}

export interface ForgotPasswordPayload {
  email: string
}

export interface ResetPasswordPayload {
  token: string
  new_password: string
}

export interface AuthUser {
  id: string
  name: string
  email: string
  is_admin: boolean
  /** Trilhas (course_slug) em que o aluno tem progresso. Só presente quando carregado por /me. */
  course_slugs?: string[]
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: AuthUser
}

export interface GenericMessageResponse {
  message: string
}

const TOKEN_KEY = 'valorian4future_token'

export function getStoredToken(): string | null {
  return localStorage.getItem(TOKEN_KEY)
}

export function setStoredToken(token: string): void {
  localStorage.setItem(TOKEN_KEY, token)
}

export function clearStoredToken(): void {
  localStorage.removeItem(TOKEN_KEY)
}

export function login(payload: LoginPayload): Promise<AuthResponse> {
  return post<AuthResponse>('/api/auth/login', payload)
}

export function fetchMe(): Promise<AuthUser> {
  const token = getStoredToken()
  if (!token) return Promise.reject(new Error('No token'))
  return apiRequest<AuthUser>('/api/auth/me', {
    headers: { Authorization: `Bearer ${token}` },
  })
}

export function forgotPassword(payload: ForgotPasswordPayload): Promise<GenericMessageResponse> {
  return post<GenericMessageResponse>('/api/auth/forgot-password', payload)
}

export function resetPassword(payload: ResetPasswordPayload): Promise<GenericMessageResponse> {
  return post<GenericMessageResponse>('/api/auth/reset-password', payload)
}
