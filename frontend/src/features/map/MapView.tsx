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
  isNotRoute,
  isRoute,
} from './layers'
import { buildPlanSources, buildSegments, resolveSelectedRouteId } from './mapData'
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

  // Route lines and checkpoints depend on the plan only, so they are uploaded
  // to the map once per plan. Selection is expressed with layer filters and
  // only the selected route's coloured segments are rebuilt when it changes.
  const sources = useMemo(() => (plan ? buildPlanSources(plan) : null), [plan])
  const segments = useMemo(
    () => (plan ? buildSegments(plan, selectedRouteId) : null),
    [plan, selectedRouteId],
  )
  const selectedId = plan ? resolveSelectedRouteId(plan, selectedRouteId) : null
  const selectionLayers = useMemo(
    () => ({
      routesOtherCasing: { ...ROUTES_OTHER_CASING, filter: isNotRoute(selectedId) },
      routesOther: { ...ROUTES_OTHER, filter: isNotRoute(selectedId) },
      checkpointsOther: { ...CHECKPOINTS_OTHER, filter: isNotRoute(selectedId) },
      checkpoints: { ...CHECKPOINTS, filter: isRoute(selectedId) },
    }),
    [selectedId],
  )
  const activeHour = useMemo(
    () => activeHourLayer(activeHourIndex, selectedId),
    [activeHourIndex, selectedId],
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
      interactiveLayerIds={sources ? [CHECKPOINTS.id!, ROUTES_HIT_LAYER.id!] : []}
      onMouseMove={onMouseMove}
      onMouseLeave={() => setHover(null)}
      onClick={onClick}
      cursor={cursor}
      attributionControl={{ compact: true }}
      reuseMaps
    >
      <NavigationControl position="top-right" showCompass={false} />
      <ScaleControl unit="imperial" position="bottom-right" />

      {sources && segments && (
        <>
          <Source id="routes" type="geojson" data={sources.routes}>
            <Layer {...selectionLayers.routesOtherCasing} />
            <Layer {...selectionLayers.routesOther} />
            <Layer {...ROUTES_HIT_LAYER} />
          </Source>
          <Source id="segments" type="geojson" data={segments}>
            <Layer {...SEGMENTS_CASING} />
            <Layer {...SEGMENTS} />
          </Source>
          <Source id="checkpoints" type="geojson" data={sources.checkpoints}>
            <Layer {...selectionLayers.checkpointsOther} />
            <Layer {...selectionLayers.checkpoints} />
            <Layer {...activeHour} />
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
