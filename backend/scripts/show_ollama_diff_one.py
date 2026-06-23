"""Run clean diff for a single company (stdout only)."""

from __future__ import annotations

import sys

# Reuse main script logic for one company
if __name__ == "__main__":
    import show_ollama_diffs_clean as mod

    website = sys.argv[1] if len(sys.argv) > 1 else "http://onemarketmedia.com"
    mod.SAMPLES = [("One Market Media", website)]
    mod.main()
