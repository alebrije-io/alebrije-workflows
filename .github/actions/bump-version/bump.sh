#!/bin/bash
# bump.sh — Polyglot version bumper supporting GO, Python, Elixir, TypeScript
#
# Usage:
#   ./bump.sh <language> <current-version> <bump-type> [version-file]
#
# Example:
#   ./bump.sh go 1.2.3 minor
#   ./bump.sh python 0.9.5 patch setup.py

set -euo pipefail

LANGUAGE="${1:-}"
CURRENT_VERSION="${2:-}"
BUMP_TYPE="${3:-}"
VERSION_FILE="${4:-VERSION}"

if [[ -z "$LANGUAGE" || -z "$CURRENT_VERSION" || -z "$BUMP_TYPE" ]]; then
  echo "Usage: $0 <language> <current-version> <bump-type> [version-file]"
  echo "Languages: go | python | elixir | ts | docker"
  exit 1
fi

# Source parse helper
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/parse-semver.sh"

# Parse current version
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT_VERSION"
MAJOR="${MAJOR:-0}"
MINOR="${MINOR:-0}"
PATCH="${PATCH:-0}"

# Calculate new version
case "$BUMP_TYPE" in
  major)
    NEW_VERSION="$((MAJOR + 1)).0.0"
    ;;
  minor)
    NEW_VERSION="$MAJOR.$((MINOR + 1)).0"
    ;;
  patch)
    NEW_VERSION="$MAJOR.$MINOR.$((PATCH + 1))"
    ;;
  none)
    NEW_VERSION="$CURRENT_VERSION"
    ;;
  *)
    echo "Invalid bump type: $BUMP_TYPE"
    exit 1
    ;;
esac

# Update language-specific files
case "$LANGUAGE" in
  go)
    # Go: VERSION file (root or version.go constant)
    if [[ -f "version.go" ]]; then
      # Update version.go const Version = "..."
      perl -pi -e "s/const Version = \"[^\"]*\"/const Version = \"$NEW_VERSION\"/" version.go
    else
      echo "$NEW_VERSION" > "$VERSION_FILE"
    fi
    ;;

  python)
    # Python: setup.py, setup.cfg, pyproject.toml, or VERSION file
    if [[ -f "setup.py" ]]; then
      perl -pi -e "s/version=['\"].*['\"]/version=\"$NEW_VERSION\"/" setup.py
    elif [[ -f "pyproject.toml" ]]; then
      perl -pi -e "s/^version = ['\"].*['\"]/version = \"$NEW_VERSION\"/" pyproject.toml
    elif [[ -f "setup.cfg" ]]; then
      perl -pi -e "s/^version = .*/version = $NEW_VERSION/" setup.cfg
    else
      echo "$NEW_VERSION" > "$VERSION_FILE"
    fi
    ;;

  elixir)
    # Elixir: mix.exs project() version field
    if [[ -f "mix.exs" ]]; then
      perl -pi -e "s/@version \"[^\"]*\"/@version \"$NEW_VERSION\"/" mix.exs
    else
      echo "$NEW_VERSION" > "$VERSION_FILE"
    fi
    ;;

  ts)
    # TypeScript/Node: package.json version field
    if [[ -f "package.json" ]]; then
      # Use Python for robust JSON parsing
      python3 << PYSCRIPT
import json, sys
with open("package.json") as f:
    data = json.load(f)
data["version"] = "$NEW_VERSION"
with open("package.json", "w") as f:
    json.dump(data, f, indent=2)
PYSCRIPT
    else
      echo "$NEW_VERSION" > "$VERSION_FILE"
    fi
    ;;

  docker)
    # Docker: VERSION file only (no standard Dockerfile versioning)
    echo "$NEW_VERSION" > "$VERSION_FILE"
    ;;

  *)
    echo "Unsupported language: $LANGUAGE"
    exit 1
    ;;
esac

echo "$NEW_VERSION"
