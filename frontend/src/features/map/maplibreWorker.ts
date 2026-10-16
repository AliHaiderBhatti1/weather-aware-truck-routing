/**
 * MapLibre 6 resolves its web worker from a runtime-built URL that bundlers
 * cannot see, so production builds would request a file that was never
 * emitted (and SPA hosts answer with index.html). Importing the worker with
 * `?url` makes Vite emit it as a hashed asset, and `setWorkerUrl` points
 * MapLibre at it. Must run before the first map is created.
 */
import { setWorkerUrl } from 'maplibre-gl'
import workerUrl from 'maplibre-gl/dist/maplibre-gl-worker.mjs?url'

setWorkerUrl(workerUrl)
