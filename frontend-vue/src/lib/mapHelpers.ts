/** Utilitários do mapa estratégico (AR-02). */

export function clip(text: string, max: number): string {
  const value = (text || '').trim()
  return value.length <= max ? value : `${value.slice(0, max - 1).trimEnd()}…`
}

export function formatDate(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    })
  } catch {
    return iso
  }
}
