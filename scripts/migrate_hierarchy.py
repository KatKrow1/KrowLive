"""Run hierarchy data migration (wrapper for backend script)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"


def main() -> None:
    script = BACKEND / "scripts" / "migrate_hierarchy.py"
    result = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(BACKEND),
        check=False,
    )
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
