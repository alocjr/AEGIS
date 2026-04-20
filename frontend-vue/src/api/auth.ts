import { post, apiRequest } from './client'

export interface LoginPayload {
  email: string
  password: string
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
