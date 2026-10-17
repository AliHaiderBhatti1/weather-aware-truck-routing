import 'maplibre-gl/dist/maplibre-gl.css'
import './maplibreWorker'

import type { MapLayerMouseEvent } from 'maplibre-gl'
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import {
  Layer,
  Map,
  type MapRef,
  Marker,
  NavigationControl,
  ScaleControl,
  Source,
} from 'react-map-gl/maplibre'

import type { Checkpoint, PlannedRoute, TripPlan } from '@/lib/types'

import { CheckpointPopup } from './CheckpointPopup'
import {
  activeHourLayer,
  CHECKPOINTS,
  CHECKPOINTS_OTHER,
  ROUTES_HIT_LAYER,
  ROUTES_OTHER,
  ROUTES_OTHER_CASING,
  SEGMENTS,
  SEGMENTS_CASING,
  UNDERLAY_BEFORE_LAYER_ID,
} from './layers'
import { buildMapData } from './mapData'
import { RouteLabels } from './RouteLabels'

const MAP_STYLE =
  import.meta.env.VITE_MAP_STYLE_URL ||
  'https://basemaps.cartocdn.com/gl/positron-gl-style/style.json'

const US_VIEW = { longitude: -97, latitude: 39, zoom: 3.6 }
const FIT_PADDING = { top: 70, right: 70, bottom: 150, left: 70 }

interface MapViewProps {
  plan: TripPlan | null
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
  onCheckpointClick?: (hourIndex: number) => void
  activeHourIndex: number | null
  /**
   * Layers to draw beneath every route layer (e.g. the corridor heatmap).
   * Receives the id of the lowest route layer to pass as \`beforeId\`.
   */
  renderUnderlay?: (beforeId: string) => React.ReactNode
}

interface Hover {
  route: PlannedRoute
  checkpoint: Checkpoint
}

export function MapView({
  plan,
  selectedRouteId,
  onSelectRoute,
  onCheckpointClick,
  activeHourIndex,
  renderUnderlay,
}: MapViewProps) {
  const mapRef = useRef<MapRef>(null)
  const [hover, setHover] = useState<Hover | null>(null)
  const [cursor, setCursor] = useState<string>('grab')

  const data = useMemo(
    () => (plan ? buildMapData(plan, selectedRouteId) : null),
    [plan, selectedRouteId],
  )

  const fitToPlan = useCallback(() => {
    if (!plan || !mapRef.current) return
    const map = mapRef.current.getMap()
    const { clientWidth, clientHeight } = map.getContainer()
    if (clientWidth < 50 || clientHeight < 50) return // hidden; wait for the resize event
    const compact = clientWidth < 640
    mapRef.current.fitBounds(plan.bounds, {
      padding: compact ? { top: 40, right: 24, bottom: 120, left: 24 } : FIT_PADDING,
      duration: 900,
      maxZoom: 11,
    })
  }, [plan])

  useEffect(() => {
    fitToPlan()
  }, [fitToPlan])

  const findCheckpoint = useCallback(
    (event: MapLayerMouseEvent): Hover | null => {
      const feature = event.features?.find((f) => f.layer.id === CHECKPOINTS.id)
      if (!feature || !plan) return null
      const { routeId, index } = feature.properties as { routeId: string; index: number }
      const route = plan.routes.find((r) => r.id === routeId)
      const checkpoint = route?.checkpoints[index]
      return route && checkpoint ? { route, checkpoint } : null
    },
    [plan],
  )

  const onMouseMove = useCallback(
    (event: MapLayerMouseEvent) => {
      const hovered = findCheckpoint(event)
      setHover(hovered)
      setCursor(event.features?.length ? 'pointer' : 'grab')
    },
    [findCheckpoint],
  )

  const onClick = useCallback(
    (event: MapLayerMouseEvent) => {
      const feature = event.features?.[0]
      if (!feature) return
      const props = feature.properties as { routeId?: string; hourIndex?: number }
      if (props.routeId) onSelectRoute(props.routeId)
      if (feature.layer.id === CHECKPOINTS.id && typeof props.hourIndex === 'number') {
        onCheckpointClick?.(props.hourIndex)
      }
    },
    [onSelectRoute, onCheckpointClick],
  )

  const origin = plan?.request.origin
  const destination = plan?.request.destination

  return (
    <Map
      ref={mapRef}
      mapStyle={MAP_STYLE}
      initialViewState={US_VIEW}
      style={{ width: '100%', height: '100%' }}
      onLoad={fitToPlan}
      // The map can be hidden (phone tab) or resized after the fit; refit so the
      // trip is always framed when it becomes visible.
      onResize={fitToPlan}
      interactiveLayerIds={data ? [CHECKPOINTS.id!, ROUTES_HIT_LAYER.id!] : []}
      onMouseMove={onMouseMove}
      onMouseLeave={() => setHover(null)}
      onClick={onClick}
      cursor={cursor}
      attributionControl={{ compact: true }}
      reuseMaps
    >
      <NavigationControl position="top-right" showCompass={false} />
      <ScaleControl unit="imperial" position="bottom-right" />

      {data && (
        <>
          <Source id="routes" type="geojson" data={data.routes}>
            <Layer {...ROUTES_OTHER_CASING} />
            <Layer {...ROUTES_OTHER} />
            <Layer {...ROUTES_HIT_LAYER} />
          </Source>
          <Source id="segments" type="geojson" data={data.segments}>
            <Layer {...SEGMENTS_CASING} />
            <Layer {...SEGMENTS} />
          </Source>
          <Source id="checkpoints" type="geojson" data={data.checkpoints}>
            <Layer {...CHECKPOINTS_OTHER} />
            <Layer {...CHECKPOINTS} />
            <Layer {...activeHourLayer(activeHourIndex)} />
          </Source>
          {/* Rendered after the route sources so their layers exist when the
              underlay is inserted beneath the lowest of them. */}
          {renderUnderlay?.(UNDERLAY_BEFORE_LAYER_ID)}
        </>
      )}

      {plan && (
        <RouteLabels
          routes={plan.routes}
          selectedRouteId={selectedRouteId}
          onSelectRoute={onSelectRoute}
        />
      )}
      {origin && <EndpointMarker lon={origin.lon} lat={origin.lat} label="A" />}
      {destination && <EndpointMarker lon={destination.lon} lat={destination.lat} label="B" />}

      {hover && <CheckpointPopup route={hover.route} checkpoint={hover.checkpoint} />}
    </Map>
  )
}

function EndpointMarker({ lon, lat, label }: { lon: number; lat: number; label: string }) {
  return (
    <Marker longitude={lon} latitude={lat} anchor="bottom">
      <div className="flex flex-col items-center">
        <div className="flex h-7 w-7 items-center justify-center rounded-full border-2 border-white bg-slate-900 text-xs font-bold text-white shadow-md">
          {label}
        </div>
        <div className="-mt-0.5 h-2 w-2 rotate-45 bg-slate-900" />
      </div>
    </Marker>
  )
}
