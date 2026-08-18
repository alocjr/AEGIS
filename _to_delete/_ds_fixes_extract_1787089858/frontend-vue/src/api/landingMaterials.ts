import { get } from './client'

export interface PublicLandingMaterial {
  id: string
  title: string
  description: string
  material_url: string
  summary_url: string
  audio_url: string | null
  order: number
}

export function fetchPublicLandingMaterials(): Promise<PublicLandingMaterial[]> {
  return get<PublicLandingMaterial[]>('/api/public/landing-materials')
}
