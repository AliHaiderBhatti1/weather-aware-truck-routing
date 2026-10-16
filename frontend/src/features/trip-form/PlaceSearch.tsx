import { useQuery } from '@tanstack/react-query'
import { Loader2, MapPin, X } from 'lucide-react'
import { useEffect, useId, useRef, useState } from 'react'

import { inputClassName } from '@/components/ui'
import { api } from '@/lib/api'
import { cn } from '@/lib/cn'
import type { Place } from '@/lib/types'

import type { PlaceValue } from './schema'

interface PlaceSearchProps {
  id?: string
  value: PlaceValue | null
  onChange: (place: PlaceValue | null) => void
  placeholder?: string
  invalid?: boolean
  autoFocus?: boolean
}

function useDebounced<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value)
  useEffect(() => {
    const handle = window.setTimeout(() => setDebounced(value), delay)
    return () => window.clearTimeout(handle)
  }, [value, delay])
  return debounced
}

/** Autocomplete combobox backed by the geocode endpoint. */
export function PlaceSearch({
  id,
  value,
  onChange,
  placeholder = 'City, address or ZIP',
  invalid,
  autoFocus,
}: PlaceSearchProps) {
  const listId = useId()
  const [text, setText] = useState(value?.full_name ?? '')
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState(0)
  const containerRef = useRef<HTMLDivElement>(null)
  const query = useDebounced(text.trim(), 250)

  // Keep the input in sync when the value is set from outside (e.g. "swap").
  // Adjusting state during render is the React-sanctioned way to derive from props.
  const [syncedValue, setSyncedValue] = useState(value)
  if (value !== syncedValue) {
    setSyncedValue(value)
    if (value) setText(value.full_name)
  }

  const suggestions = useQuery({
    queryKey: ['geocode', query],
    queryFn: ({ signal }) => api.geocode(query, signal),
    enabled: open && query.length >= 2 && query !== value?.full_name,
    staleTime: 5 * 60 * 1000,
    placeholderData: (previous) => previous,
  })

  const items: Place[] = suggestions.data ?? []
  const showList = open && query.length >= 2 && query !== value?.full_name

  useEffect(() => {
    const onPointerDown = (event: PointerEvent) => {
      if (!containerRef.current?.contains(event.target as Node)) setOpen(false)
    }
    document.addEventListener('pointerdown', onPointerDown)
    return () => document.removeEventListener('pointerdown', onPointerDown)
  }, [])

  const select = (place: Place) => {
    onChange({ name: place.name, full_name: place.full_name, lat: place.lat, lon: place.lon })
    setText(place.full_name)
    setOpen(false)
  }

  const clear = () => {
    onChange(null)
    setText('')
    setOpen(false)
  }

  return (
    <div ref={containerRef} className="relative">
      <div className="relative">
        <MapPin
          className="pointer-events-none absolute top-1/2 left-3 h-4 w-4 -translate-y-1/2 text-slate-400"
          aria-hidden
        />
        <input
          id={id}
          type="text"
          role="combobox"
          aria-expanded={showList}
          aria-controls={listId}
          aria-autocomplete="list"
          aria-invalid={invalid || undefined}
          autoComplete="off"
          autoFocus={autoFocus}
          className={cn(inputClassName, 'pr-9 pl-9')}
          placeholder={placeholder}
          value={text}
          onChange={(event) => {
            setText(event.target.value)
            setOpen(true)
            setActive(0)
            if (value) onChange(null)
          }}
          onFocus={() => setOpen(true)}
          onKeyDown={(event) => {
            if (!showList || items.length === 0) return
            if (event.key === 'ArrowDown') {
              event.preventDefault()
              setActive((index) => (index + 1) % items.length)
            } else if (event.key === 'ArrowUp') {
              event.preventDefault()
              setActive((index) => (index - 1 + items.length) % items.length)
            } else if (event.key === 'Enter') {
              event.preventDefault()
              select(items[active])
            } else if (event.key === 'Escape') {
              setOpen(false)
            }
          }}
        />
        {suggestions.isFetching ? (
          <Loader2
            className="absolute top-1/2 right-3 h-4 w-4 -translate-y-1/2 animate-spin text-slate-400"
            aria-hidden
          />
        ) : text ? (
          <button
            type="button"
            onClick={clear}
            aria-label="Clear"
            className="absolute top-1/2 right-2 flex h-6 w-6 -translate-y-1/2 items-center justify-center rounded-md text-slate-400 hover:bg-slate-100 hover:text-slate-600"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        ) : null}
      </div>

      {showList && (
        <ul
          id={listId}
          role="listbox"
          className="shadow-panel absolute z-30 mt-1 max-h-64 w-full overflow-auto rounded-lg border border-slate-200 bg-white py-1"
        >
          {items.length === 0 ? (
            <li className="px-3 py-2 text-sm text-slate-500">
              {suggestions.isFetching
                ? 'Searching…'
                : suggestions.isError
                  ? 'Search failed. Try again.'
                  : 'No matches.'}
            </li>
          ) : (
            items.map((place, index) => (
              <li
                key={`${place.lat},${place.lon},${place.full_name}`}
                role="option"
                aria-selected={index === active}
                onMouseEnter={() => setActive(index)}
                onMouseDown={(event) => event.preventDefault()}
                onClick={() => select(place)}
                className={cn(
                  'cursor-pointer px-3 py-2 text-sm',
                  index === active ? 'bg-slate-100' : 'hover:bg-slate-50',
                )}
              >
                <div className="font-medium text-slate-900">{place.name}</div>
                <div className="truncate text-xs text-slate-500">{place.full_name}</div>
              </li>
            ))
          )}
        </ul>
      )}
    </div>
  )
}
