import { del, get, patch, post } from './client'

/** Membro da organização — gestão pelo admin de organização (nome/email/telefone/senha
 * apenas; trilha/mentoria continua exclusiva do admin da plataforma em `api/admin.ts`). */
export interface OrgMember {
  id: string
  name: string
  email: string
  phone: string
  is_org_admin: boolean
  created_at: string | null
}

export function listOrgMembers(): Promise<{ items: OrgMember[] }> {
  return get<{ items: OrgMember[] }>('/api/org-admin/members')
}

export function createOrgMember(body: {
  name: string
  email: string
  password: string
  phone?: string
}): Promise<OrgMember> {
  return post<OrgMember>('/api/org-admin/members', body)
}

export function updateOrgMember(
  id: string,
  body: { name?: string; email?: string; password?: string; phone?: string }
): Promise<OrgMember> {
  return patch<OrgMember>(`/api/org-admin/members/${encodeURIComponent(id)}`, body)
}

export function deleteOrgMember(id: string): Promise<{ message: string; id: string }> {
  return del<{ message: string; id: string }>(`/api/org-admin/members/${encodeURIComponent(id)}`)
}
