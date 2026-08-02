/**
 * Cliente HTTP base para chamadas à API.
 * Base URL vazia = mesmo origem; em dev o Vite faz proxy de /api.
 * Autenticação via cookie HttpOnly (credentials: include).
 */

const baseURL = import.meta.env.VITE_API_BASE_URL ?? ''

/** Erro de API — `code` vem preenchido quando o backend usa o formato
 * `detail: { code, message }` (erros de validação de negócio com código estável). */
export class ApiError extends Error {
  code?: string

  constructor(message: string, code?: string) {
    super(message)
    this.name = 'ApiError'
    this.code = code
  }
}

function parseErrorBody(text: string, fallback: string): ApiError {
  try {
    const json = JSON.parse(text) as {
      detail?: string | unknown[] | { code?: string; message?: string }
    }
    const detail = json.detail
    if (Array.isArray(detail)) {
      const message = detail.map((d: unknown) => (d as { msg?: string }).msg ?? String(d)).join(', ')
      return new ApiError(message || fallback)
    }
    if (detail && typeof detail === 'object') {
      const d = detail as { code?: string; message?: string }
      return new ApiError(d.message || fallback, d.code)
    }
    return new ApiError((detail as string) || fallback)
  } catch {
    return new ApiError(text || fallback)
  }
}

export async function apiRequest<T>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = path.startsWith('http') ? path : `${baseURL}${path}`
  const res = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    credentials: 'include',
  })
  if (!res.ok) {
    const text = await res.text()
    throw parseErrorBody(text, res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function get<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: 'GET' })
}

/** Upload multipart; não define Content-Type (o browser define o boundary). */
export async function postFormData<T>(path: string, formData: FormData): Promise<T> {
  const url = path.startsWith('http') ? path : `${baseURL}${path}`
  const res = await fetch(url, {
    method: 'POST',
    body: formData,
    credentials: 'include',
  })
  if (!res.ok) {
    const text = await res.text()
    throw parseErrorBody(text, res.statusText)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined })
}

export function put<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, { method: 'PUT', body: body ? JSON.stringify(body) : undefined })
}

export function patch<T>(path: string, body?: unknown): Promise<T> {
  return apiRequest<T>(path, { method: 'PATCH', body: body ? JSON.stringify(body) : undefined })
}

export function del<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: 'DELETE' })
}
