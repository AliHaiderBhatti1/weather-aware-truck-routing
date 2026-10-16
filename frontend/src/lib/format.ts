import { format, formatDistanceStrict } from 'date-fns'

export function formatDuration(seconds: number): string {
  const totalMinutes = Math.round(seconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours === 0) return `${minutes} min`
  return minutes === 0 ? `${hours} h` : `${hours} h ${minutes} min`
}

export function formatMiles(miles: number, digits = 0): string {
  return `${miles.toLocaleString(undefined, { maximumFractionDigits: digits })} mi`
}

export function formatPounds(lb: number): string {
  return `${lb.toLocaleString()} lb`
}

export function formatClock(iso: string): string {
  return format(new Date(iso), 'h:mm a')
}

export function formatDayTime(iso: string): string {
  return format(new Date(iso), 'EEE MMM d, h:mm a')
}

export function formatOffset(fromIso: string, toIso: string): string {
  return formatDistanceStrict(new Date(toIso), new Date(fromIso), { addSuffix: false })
}

export function formatInchesPerHour(value: number): string {
  return `${value.toFixed(2)} in/hr`
}

/** Convert a Date to the `datetime-local` input format in the browser's zone. */
export function toDateTimeLocal(date: Date): string {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`
}
