import { post, get } from './client'

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
  email_verified?: boolean
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

export function login(payload: LoginPayload): Promise<AuthResponse> {
  return post<AuthResponse>('/api/auth/login', payload)
}

export function logoutApi(): Promise<GenericMessageResponse> {
  return post<GenericMessageResponse>('/api/auth/logout')
}

export function fetchMe(): Promise<AuthUser> {
  return get<AuthUser>('/api/auth/me')
}

export function forgotPassword(payload: ForgotPasswordPayload): Promise<GenericMessageResponse> {
  return post<GenericMessageResponse>('/api/auth/forgot-password', payload)
}

export function resetPassword(payload: ResetPasswordPayload): Promise<GenericMessageResponse> {
  return post<GenericMessageResponse>('/api/auth/reset-password', payload)
}

export function verifyEmail(token: string): Promise<GenericMessageResponse> {
  return post<GenericMessageResponse>('/api/auth/verify-email', { token })
}

export function resendVerification(): Promise<GenericMessageResponse> {
  return post<GenericMessageResponse>('/api/auth/resend-verification')
}
