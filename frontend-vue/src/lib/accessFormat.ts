/** Formatação compartilhada pelas telas que exibem contagem de acesso (dashboard e gestão). */

const numberFmt = new Intl.NumberFormat('pt-BR')

export function formatCount(value: number): string {
  return numberFmt.format(value)
}

export function formatLastAccess(iso: string | null): string {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleDateString('pt-BR', {
      day: '2-digit',
      month: 'short',
      hour: '2-digit',
      minute: '2-digit',
    })
  } catch {
    return '—'
  }
}
