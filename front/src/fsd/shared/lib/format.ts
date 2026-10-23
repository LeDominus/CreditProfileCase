const moneyFormatter = new Intl.NumberFormat('ru-RU', { maximumFractionDigits: 0 })

/** 3000000 → "3 000 000 ₽" */
export function formatMoney(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${moneyFormatter.format(Math.round(value))} ₽`
}

const rateFormatter = new Intl.NumberFormat('ru-RU', {
  minimumFractionDigits: 1,
  maximumFractionDigits: 1,
})

/** 16.5 → "16,5 %" */
export function formatRate(value: number | null | undefined): string {
  if (value == null) return '—'
  return `${rateFormatter.format(value)} %`
}

/** ISO datetime → "21.10.2026, 14:32" */
export function formatDateTime(value: string | null | undefined): string {
  if (!value) return '—'
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '—'
  return date.toLocaleString('ru-RU', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

/** 524288 → "512 КБ" */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} Б`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} КБ`
  return `${(bytes / (1024 * 1024)).toFixed(1)} МБ`
}
