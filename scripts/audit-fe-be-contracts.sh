#!/usr/bin/env bash
# audit-fe-be-contracts.sh
#
# Thin shell wrapper around scripts/fe_be_audit.py. Every heavy lift is
# done in Python — the script exists mainly so the tool shows up with the
# rest of the workspace utilities (bump-version.sh, check-all-ci.sh, …)
# and can be invoked without remembering the Python path.
#
# Usage:
#   scripts/audit-fe-be-contracts.sh                    # full audit
#   scripts/audit-fe-be-contracts.sh --module rewards   # one module only
#   scripts/audit-fe-be-contracts.sh --strict           # CI mode, non-zero exit
#   scripts/audit-fe-be-contracts.sh --json             # machine-readable output
#
# The audit writes CONTRACT_AUDIT.md at the workspace root and a JSON
# twin alongside it (CONTRACT_AUDIT.audit-report.json) unless --json is
# passed, in which case the JSON lands on stdout for piping into jq.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
HELPER="$SCRIPT_DIR/fe_be_audit.py"

if [[ ! -f "$HELPER" ]]; then
  echo "audit: missing helper at $HELPER" >&2
  exit 2
fi

# Pick the first usable python3. The helper depends on the standard
# library only — no pip install required.
PYTHON_BIN="${PYTHON:-python3}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
  echo "audit: $PYTHON_BIN not found on PATH" >&2
  exit 2
fi

exec "$PYTHON_BIN" "$HELPER" "$@"
