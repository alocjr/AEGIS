import { get } from './client'

export interface PublicLandingPrompt {
  id: string
  title: string
  description: string
  meta_label: string
  prompt_url: string
  order: number
}

export function fetchPublicLandingPrompts(): Promise<PublicLandingPrompt[]> {
  return get<PublicLandingPrompt[]>('/api/public/landing-prompts')
}
