/**
 * Cliente HTTP base para chamadas à API.
 * Base URL vazia = mesmo origem; em dev o Vite faz proxy de /api.
 * Autenticação via cookie HttpOnly (credentials: include).
 */

const baseURL = import.meta.env.VITE_API_BASE_URL ?? ''

/** Rotas em que 401 é esperado (sonda de sessão, login inválido) — não redirecionam. */
const AUTH_PROBE_PATHS = new Set(['/api/auth/me', '/api/auth/login', '/api/auth/logout'])

/** Erro de API — `code` vem preenchido quando o backend usa o formato
 * `detail: { code, message }` (erros de validação de negócio com código estável). */
export class ApiError extends Error {
  code?: string
  status?: number

  constructor(message: string, code?: string, status?: number) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.status = status
  }
}

function parseErrorBody(text: string, fallback: string, status?: number): ApiError {
  try {
    const json = JSON.parse(text) as {
      detail?: string | unknown[] | { code?: string; message?: string }
    }
    const detail = json.detail
    if (Array.isArray(detail)) {
      const message = detail.map((d: unknown) => (d as { msg?: string }).msg ?? String(d)).join(', ')
      return new ApiError(message || fallback, undefined, status)
    }
    if (detail && typeof detail === 'object') {
      const d = detail as { code?: string; message?: string }
      return new ApiError(d.message || fallback, d.code, status)
    }
    return new ApiError((detail as string) || fallback, undefined, status)
  } catch {
    return new ApiError(text || fallback, undefined, status)
  }
}

function requestPathname(url: string): string {
  if (url.startsWith('http')) {
    try {
      return new URL(url).pathname
    } catch {
      return url
    }
  }
  return url.split('?')[0] ?? url
}

function shouldRedirectToUnauthorized(url: string): boolean {
  return !AUTH_PROBE_PATHS.has(requestPathname(url))
}

async function redirectToUnauthorizedPage(): Promise<void> {
  if (typeof window === 'undefined') return
  if (window.location.pathname === '/401') return
  try {
    await fetch(`${baseURL}/api/auth/logout`, { method: 'POST', credentials: 'include' })
  } catch {
    // Cookie inválido ou rede; a navegação para /401 segue mesmo assim.
  }
  window.location.assign('/401')
}

async function throwIfNotOk(res: Response, url: string): Promise<void> {
  if (res.ok) return
  const text = await res.text()
  if (res.status === 401 && shouldRedirectToUnauthorized(url)) {
    await redirectToUnauthorizedPage()
  }
  throw parseErrorBody(text, res.statusText, res.status)
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
  await throwIfNotOk(res, url)
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
  await throwIfNotOk(res, url)
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
