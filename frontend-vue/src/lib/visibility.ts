export type ArtifactVisibility = 'shared' | 'private'

export function normalizeVisibility(value: unknown): ArtifactVisibility {
  return value === 'private' ? 'private' : 'shared'
}
