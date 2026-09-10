"""
Makes src/data_generation/incremental/ and ml/ importable as plain
modules in tests, matching how they're actually imported everywhere else
in this project (flat imports, not package-relative).
"""

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT / "src" / "data_generation" / "incremental"))
sys.path.insert(0, str(REPO_ROOT / "ml"))