from __future__ import annotations

from pathlib import Path


def load_project_dotenv() -> None:
    """Load `.env` from the repo root (next to pyproject.toml) if python-dotenv is installed."""
    here = Path(__file__).resolve()
    for d in [here, *here.parents]:
        env_path = d / ".env"
        if (d / "pyproject.toml").is_file():
            try:
                from dotenv import load_dotenv

                load_dotenv(env_path, override=False)
            except ImportError:
                pass
            return
