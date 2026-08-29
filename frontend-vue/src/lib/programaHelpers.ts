/** Utilitários do programa de mentoria (AR-02). */
const ROMANOS = ['I', 'II', 'III', 'IV', 'V', 'VI', 'VII', 'VIII', 'IX', 'X', 'XI', 'XII', 'XIII', 'XIV', 'XV']

export function romano(n: number): string {
  return ROMANOS[n - 1] ?? String(n)
}

export function isExternalUrl(url?: string): boolean {
  return !!(url && (url.startsWith('http://') || url.startsWith('https://')))
}

export function parseMatItem(item: string): { tipo: string; nome: string } {
  const i = item.indexOf(':')
  if (i < 0) return { tipo: 'Material', nome: item.trim() }
  return { tipo: item.slice(0, i).trim(), nome: item.slice(i + 1).trim() }
}
