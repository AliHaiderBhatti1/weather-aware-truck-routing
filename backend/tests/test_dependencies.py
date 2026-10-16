"""pyproject.toml (used by Vercel/uv) and requirements.txt (used by Docker) must agree."""

import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _requirements(name: str) -> set[str]:
    lines = (ROOT / name).read_text().splitlines()
    return {line.strip() for line in lines if line.strip() and not line.startswith(("#", "-r"))}


def test_runtime_dependencies_match() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert set(pyproject["project"]["dependencies"]) == _requirements("requirements.txt")


def test_dev_dependencies_match() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text())
    assert set(pyproject["dependency-groups"]["dev"]) == _requirements("requirements-dev.txt")
