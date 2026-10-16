"""
Vercel build hook: apply database migrations before the new deployment goes live.

Skipped when DATABASE_URL is not configured (e.g. preview builds without a
database), so the build never fails just because a database is absent.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path


def main() -> int:
    if not os.environ.get("DATABASE_URL"):
        print("vercel_build: DATABASE_URL not set; skipping migrations.")
        return 0

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

    import django
    from django.core.management import call_command

    django.setup()
    print("vercel_build: applying migrations...")
    call_command("migrate", interactive=False, verbosity=1)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
