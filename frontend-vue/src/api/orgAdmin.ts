/** @deprecated Importe de `@/api/organizationMembers`. */
export type { OrganizationMember } from './organizationMembers'
export {
  listOrgMembers,
  createOrgMember,
  updateOrgMember,
  deleteOrgMember,
} from './organizationMembers'

/** @deprecated Use `OrganizationMember`. */
export type OrgMember = import('./organizationMembers').OrganizationMember
