/**
 * AR-06: tipo e listagem unificados de membros da organização.
 * Dois endpoints no backend (governança vs. org-admin) expõem o mesmo domínio
 * com campos diferentes — normalizamos no cliente.
 */
import { del, get, patch, post } from './client'

export interface OrganizationMember {
  id: string
  name: string
  email?: string
  phone?: string
  is_org_admin: boolean
  created_at?: string | null
}

type GovernanceMemberResponse = {
  id: string
  name: string
  is_admin: boolean
}

function fromGovernance(raw: GovernanceMemberResponse): OrganizationMember {
  return {
    id: raw.id,
    name: raw.name,
    is_org_admin: Boolean(raw.is_admin),
  }
}

function fromOrgAdmin(raw: OrganizationMember): OrganizationMember {
  return {
    id: raw.id,
    name: raw.name,
    email: raw.email ?? '',
    phone: raw.phone ?? '',
    is_org_admin: Boolean(raw.is_org_admin),
    created_at: raw.created_at ?? null,
  }
}

/** Lista resumida — seletores RACI (governança). */
export function listOrganizationMembers(): Promise<{ items: OrganizationMember[] }> {
  return get<{ items: GovernanceMemberResponse[] }>('/api/governance/organization-members').then(
    (res) => ({
      items: res.items.map(fromGovernance),
    })
  )
}

/** Lista completa — gestão pelo admin de organização. */
export function listOrgMembers(): Promise<{ items: OrganizationMember[] }> {
  return get<{ items: OrganizationMember[] }>('/api/org-admin/members').then((res) => ({
    items: res.items.map(fromOrgAdmin),
  }))
}

export function createOrgMember(body: {
  name: string
  email: string
  password: string
  phone?: string
}): Promise<OrganizationMember> {
  return post<OrganizationMember>('/api/org-admin/members', body).then(fromOrgAdmin)
}

export function updateOrgMember(
  id: string,
  body: { name?: string; email?: string; password?: string; phone?: string }
): Promise<OrganizationMember> {
  return patch<OrganizationMember>(`/api/org-admin/members/${encodeURIComponent(id)}`, body).then(
    fromOrgAdmin
  )
}

export function deleteOrgMember(id: string): Promise<{ message: string; id: string }> {
  return del<{ message: string; id: string }>(`/api/org-admin/members/${encodeURIComponent(id)}`)
}
