/**
 * Cliente HTTP base para chamadas à API.
 * Base URL vazia = mesmo origem; em dev o Vite faz proxy de /api.
 * Requisições autenticadas: inclui Bearer token quando disponível.
 */

const baseURL = import.meta.env.VITE_API_BASE_URL ?? ''
const TOKEN_KEY = 'valorian4future_token'

function authHeaders(): Record<string, string> {
  const token = typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null
  if (!token) return {}
  return { Authorization: `Bearer ${token}` }
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
      ...authHeaders(),
      ...options.headers,
    },
    credentials: 'include',
  })
  if (!res.ok) {
    const text = await res.text()
    let detail: string
    try {
      const json = JSON.parse(text) as { detail?: string | unknown[] }
      detail = Array.isArray(json.detail)
        ? json.detail.map((d: unknown) => (d as { msg?: string }).msg ?? String(d)).join(', ')
        : (json.detail as string) ?? text
    } catch {
      detail = text || res.statusText
    }
    throw new Error(detail)
  }
  if (res.status === 204) return undefined as T
  return res.json() as Promise<T>
}

export function get<T>(path: string): Promise<T> {
  return apiRequest<T>(path, { method: 'GET' })
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
