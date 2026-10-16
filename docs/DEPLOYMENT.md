# Deployment guide

Target: **Vercel** for both the web app and the Django API (two projects from this one repo) plus **Neon** for Postgres. All free, no card needed.

> Vercel deploys `main`. When `dev` is ready: `git checkout main && git merge --ff-only dev && git push`.

## 1. Neon (database, 2 min)

1. neon.tech → sign in with GitHub → **New project**, Postgres only.
2. **Connect** → turn **Connection pooling off** → **Copy snippet**. This is `DATABASE_URL`.

## 2. Vercel project #1: the API (5 min)

1. vercel.com → sign in with GitHub → **Add New… → Project** → import `weather-aware-truck-routing`.
2. **Project name:** `wtr-api` (any name). **Root Directory:** `backend`. Framework preset is detected as Django.
3. **Environment Variables:**

   | Key | Value |
   |---|---|
   | `MAPBOX_ACCESS_TOKEN` | your Mapbox token |
   | `DATABASE_URL` | the Neon string |
   | `DJANGO_SECRET_KEY` | output of `python3 -c "import secrets; print(secrets.token_urlsafe(50))"` |
   | `DJANGO_DEBUG` | `false` |

4. **Deploy.** The build installs from `pyproject.toml`, runs migrations through `scripts/vercel_build.py`, and runs `collectstatic`.
5. Open `https://<api-domain>/api/health/` and check it returns `{"status":"ok", ...}`.

## 3. Vercel project #2: the web app (3 min)

1. **Add New… → Project** → import the same repo again.
2. **Project name:** `weather-aware-truck-routing` (this becomes the public URL). **Root Directory:** `frontend`. Preset: Vite.
3. **Environment Variables:** `VITE_API_BASE_URL` = `https://<api-domain>` (no trailing slash).
4. **Deploy**, then open the URL and plan a trip.

CORS already allows any `https://*.vercel.app` origin, so no extra step is needed. To lock it down to one origin, set `CORS_ALLOWED_ORIGINS` on the API project and `CORS_ALLOWED_ORIGIN_REGEXES` to an empty value.

## How the API runs on Vercel

- Vercel detects `manage.py` and serves `config.wsgi:application` (also pinned in `pyproject.toml` under `[tool.vercel]`) as one Vercel Function with a 60 s limit (`backend/vercel.json`).
- `[tool.vercel.scripts] build` runs `scripts/vercel_build.py`, which applies migrations when `DATABASE_URL` is set and skips otherwise.
- Hostnames Vercel injects (`VERCEL_URL`, `VERCEL_PROJECT_PRODUCTION_URL`) are added to `ALLOWED_HOSTS` automatically; `/api/health/` answers before host validation so platform probes never get a 400.
- Caches are per function instance (in-memory). That's fine at this scale; swap `CACHES` for Redis/Upstash if traffic grows.
- There is no cold-start sleep like on container free tiers; the first request after idle takes ~1 s to boot Python.

## Environment variables reference

| Variable | Project | Notes |
|---|---|---|
| `MAPBOX_ACCESS_TOKEN` | API | Restrict the token to your domains in the Mapbox dashboard. |
| `DATABASE_URL` | API | Neon direct (non-pooled) connection string. |
| `DJANGO_SECRET_KEY` | API | Any long random string. |
| `DJANGO_DEBUG` | API | `false` in production. |
| `CORS_ALLOWED_ORIGINS` | API (optional) | Explicit origins, comma separated. |
| `DB_CONN_MAX_AGE` | API (optional) | Seconds to reuse a DB connection; default 60. |
| `VITE_API_BASE_URL` | Web | The API project's URL. |
| `VITE_MAP_STYLE_URL` | Web (optional) | Any MapLibre style URL; defaults to CARTO Positron. |

## Other hosts

`backend/Dockerfile` builds a production image (gunicorn, migrations on start, health check) that runs on any container host such as Render, Fly.io or Railway, with the same environment variables.
