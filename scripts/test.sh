#!/usr/bin/env bash
set -euo pipefail

# Always run from project root
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Virtualenv detection (optional, safe)
if [[ -d ".venv" ]]; then
  source .venv/bin/activate
elif [[ -d "venv" ]]; then
  source venv/bin/activate
fi

# Ensure pytest exists
command -v pytest >/dev/null 2>&1 || {
  echo "pytest not found. Install with: pip install pytest"
  exit 1
}

export PYTHONPATH="$ROOT_DIR${PYTHONPATH:+:$PYTHONPATH}"

# Run all tests
pytest \
  --strict-markers \
  --strict-config \
  --disable-warnings \
  -ra
