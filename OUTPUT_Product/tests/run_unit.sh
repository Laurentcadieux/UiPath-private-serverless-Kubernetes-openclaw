#!/usr/bin/env bash
# Run unit tests
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "${SCRIPT_DIR}/.."

echo "Running UiPath Private Serverless K8s tests..."
python3 -m pytest tests/ -v "$@"
