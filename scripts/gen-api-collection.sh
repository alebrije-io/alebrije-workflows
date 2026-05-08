#!/bin/bash
# gen-api-collection.sh
# Generates an API collection JSON from the API gateway repository.

set -euo pipefail

API_REPO_PATH="${API_REPO_PATH:-../api-gateway-go}"
OUTPUT_FILE="${OUTPUT_FILE:-api-collection.json}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

usage() {
  cat <<HELP
Usage: gen-api-collection.sh [OPTIONS]

Generates an API collection JSON from API gateway repository definitions.

OPTIONS:
  -h, --help              Show this help message
  -r, --repo PATH         Path to API gateway repo (default: ../api-gateway-go)
  -o, --output FILE       Output file path (default: api-collection.json)

Environment Variables:
  API_REPO_PATH           Override API repository path
  OUTPUT_FILE             Override output file path

HELP
}

log_info() {
  echo "[INFO] $*" >&2
}

log_error() {
  echo "[ERROR] $*" >&2
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    -h|--help) usage; exit 0 ;;
    -r|--repo) API_REPO_PATH="$2"; shift 2 ;;
    -o|--output) OUTPUT_FILE="$2"; shift 2 ;;
    *) log_error "Unknown option: $1"; usage; exit 1 ;;
  esac
done

if [[ ! -d "$API_REPO_PATH" ]]; then
  log_error "API repository not found: $API_REPO_PATH"
  exit 1
fi

log_info "API Repository: $API_REPO_PATH"
log_info "Output File: $OUTPUT_FILE"

if ! python3 "$SCRIPT_DIR/gen_api_collection.py" --repo "$API_REPO_PATH" --output "$OUTPUT_FILE"; then
  log_error "Failed to generate API collection"
  exit 1
fi

if [[ ! -f "$OUTPUT_FILE" ]]; then
  log_error "Output file was not created: $OUTPUT_FILE"
  exit 1
fi

if ! python3 -m json.tool "$OUTPUT_FILE" > /dev/null 2>&1; then
  log_error "Generated file is not valid JSON"
  exit 1
fi

log_info "Successfully generated API collection: $OUTPUT_FILE"
exit 0
