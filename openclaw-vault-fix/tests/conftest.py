import sys
from pathlib import Path

# Make `vaultfix` and `fix.py` importable from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
