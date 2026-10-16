import { zodResolver } from '@hookform/resolvers/zod'
import { ArrowDownUp, Route, Sparkles } from 'lucide-react'
import { useState } from 'react'
import { Controller, useForm } from 'react-hook-form'

import { Alert, Button, Field, inputClassName, SegmentedControl } from '@/components/ui'
import { ApiError } from '@/lib/api'
import { toDateTimeLocal } from '@/lib/format'
import type { TripPlanRequest } from '@/lib/types'

import { INTERVAL_OPTIONS, MAX_DAYS_AHEAD, tripFormSchema, type TripFormValues } from './schema'
import { toRequest } from './toRequest'
import { PlaceSearch } from './PlaceSearch'

interface TripFormProps {
  onSubmit: (request: TripPlanRequest) => void
  pending: boolean
  error: unknown
  defaultValues?: Partial<TripFormValues>
}

const EXAMPLE_TRIP: Pick<TripFormValues, 'origin' | 'destination' | 'loadWeightLb'> = {
  origin: {
    name: 'Denver',
    full_name: 'Denver, Colorado, United States',
    lat: 39.7392,
    lon: -104.9847,
  },
  destination: {
    name: 'Salt Lake City',
    full_name: 'Salt Lake City, Utah, United States',
    lat: 40.7608,
    lon: -111.891,
  },
  loadWeightLb: 42000,
}

function defaultDeparture(): string {
  const date = new Date(Date.now() + 60 * 60 * 1000)
  date.setMinutes(0, 0, 0)
  return toDateTimeLocal(date)
}

export function TripForm({ onSubmit, pending, error, defaultValues }: TripFormProps) {
  const form = useForm<TripFormValues>({
    resolver: zodResolver(tripFormSchema),
    defaultValues: {
      origin: null,
      destination: null,
      departure: defaultDeparture(),
      loadWeightLb: 40000,
      intervalMiles: 25,
      ...defaultValues,
    },
    mode: 'onSubmit',
    reValidateMode: 'onChange',
  })
  const { control, register, handleSubmit, formState, getValues, setValue } = form
  const errors = formState.errors

  const fillExample = () => {
    setValue('origin', EXAMPLE_TRIP.origin, { shouldValidate: true })
    setValue('destination', EXAMPLE_TRIP.destination, { shouldValidate: true })
    setValue('loadWeightLb', EXAMPLE_TRIP.loadWeightLb, { shouldValidate: true })
  }

  const swap = () => {
    const origin = getValues('origin')
    const destination = getValues('destination')
    setValue('origin', destination, { shouldValidate: formState.isSubmitted })
    setValue('destination', origin, { shouldValidate: formState.isSubmitted })
  }

  const [[minDeparture, maxDeparture]] = useState(() => {
    const now = Date.now()
    return [
      toDateTimeLocal(new Date(now - 60 * 60 * 1000)),
      toDateTimeLocal(new Date(now + MAX_DAYS_AHEAD * 86_400_000)),
    ] as const
  })

  return (
    <form
      noValidate
      onSubmit={handleSubmit((values) => onSubmit(toRequest(values)))}
      className="flex flex-col gap-4"
      aria-busy={pending}
    >
      <div className="flex flex-col gap-2">
        <Controller
          control={control}
          name="origin"
          render={({ field }) => (
            <Field label="Origin" htmlFor="origin" error={errors.origin?.message}>
              <PlaceSearch
                id="origin"
                value={field.value}
                onChange={field.onChange}
                invalid={Boolean(errors.origin)}
                placeholder="Where does the trip start?"
                autoFocus
              />
            </Field>
          )}
        />
        <div className="-my-1 flex justify-end pr-1">
          <button
            type="button"
            onClick={swap}
            aria-label="Swap origin and destination"
            className="flex h-7 w-7 items-center justify-center rounded-full border border-slate-200 bg-white text-slate-500 shadow-xs hover:bg-slate-50 hover:text-slate-800"
          >
            <ArrowDownUp className="h-3.5 w-3.5" />
          </button>
        </div>
        <Controller
          control={control}
          name="destination"
          render={({ field }) => (
            <Field label="Destination" htmlFor="destination" error={errors.destination?.message}>
              <PlaceSearch
                id="destination"
                value={field.value}
                onChange={field.onChange}
                invalid={Boolean(errors.destination)}
                placeholder="Where is the load going?"
              />
            </Field>
          )}
        />
      </div>

      <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
        <Field label="Departure" htmlFor="departure" error={errors.departure?.message}>
          <input
            id="departure"
            type="datetime-local"
            min={minDeparture}
            max={maxDeparture}
            step={300}
            aria-invalid={Boolean(errors.departure) || undefined}
            className={inputClassName}
            {...register('departure')}
          />
        </Field>
        <Field label="Load weight" htmlFor="load" error={errors.loadWeightLb?.message}>
          <div className="relative">
            <input
              id="load"
              type="number"
              inputMode="numeric"
              min={0}
              max={200000}
              step={500}
              aria-invalid={Boolean(errors.loadWeightLb) || undefined}
              className={`${inputClassName} pr-10`}
              {...register('loadWeightLb', { valueAsNumber: true })}
            />
            <span className="pointer-events-none absolute top-1/2 right-3 -translate-y-1/2 text-xs font-medium text-slate-400">
              lb
            </span>
          </div>
        </Field>
      </div>

      <Controller
        control={control}
        name="intervalMiles"
        render={({ field }) => (
          <Field
            label="Weather checkpoint every"
            hint="Shorter intervals sample more forecast points along each route."
          >
            <SegmentedControl
              ariaLabel="Checkpoint interval"
              value={field.value}
              onChange={field.onChange}
              options={INTERVAL_OPTIONS.map((miles) => ({ value: miles, label: `${miles} mi` }))}
            />
          </Field>
        )}
      />

      {error instanceof ApiError ? (
        <Alert tone="error" title={error.message}>
          {error.fieldMessages.length > 0 && (
            <ul className="mt-1 list-disc pl-4">
              {error.fieldMessages.map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
          )}
          {error.code === 'rate_limited' && (
            <p className="mt-1">
              Nothing is wrong with your trip; the forecast provider is throttling. Retry in a
              moment.
            </p>
          )}
        </Alert>
      ) : error ? (
        <Alert tone="error" title="Something went wrong while planning the trip." />
      ) : null}

      <Button type="submit" size="lg" loading={pending} leftIcon={<Route className="h-4 w-4" />}>
        {pending ? 'Planning routes…' : 'Plan routes'}
      </Button>
      <button
        type="button"
        onClick={fillExample}
        className="-mt-1 inline-flex items-center justify-center gap-1.5 text-xs font-medium text-slate-500 hover:text-slate-800"
      >
        <Sparkles className="h-3.5 w-3.5" /> Try an example: Denver → Salt Lake City, 42,000 lb
      </button>
    </form>
  )
}
