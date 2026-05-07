#!/bin/bash
# parse-semver.sh — Semantic Version parser helper
#
# This file defines parsing utilities for semver 2.0.0 validation
# Source this script from other scripts: source parse-semver.sh

# parse_semver <version-string>
# Extracts major, minor, patch from a version string
# Sets MAJOR, MINOR, PATCH global variables
# Returns 0 on success, 1 on invalid version
parse_semver() {
  local version="$1"

  # Regex: major.minor.patch with optional pre-release and metadata
  if [[ $version =~ ^([0-9]+)\.([0-9]+)\.([0-9]+)(-[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?(\+[0-9A-Za-z-]+(\.[0-9A-Za-z-]+)*)?$ ]]; then
    MAJOR="${BASH_REMATCH[1]}"
    MINOR="${BASH_REMATCH[2]}"
    PATCH="${BASH_REMATCH[3]}"
    PRERELEASE="${BASH_REMATCH[4]:-}"
    METADATA="${BASH_REMATCH[6]:-}"
    return 0
  else
    echo "Invalid semver format: $version" >&2
    return 1
  fi
}

# is_valid_semver <version-string>
# Returns 0 if version is valid semver, 1 otherwise
is_valid_semver() {
  local version="$1"
  if [[ $version =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    return 0
  else
    return 1
  fi
}

# compare_versions <v1> <v2>
# Returns:
#   0 if v1 == v2
#   1 if v1 > v2
#   -1 if v1 < v2
compare_versions() {
  local v1="$1"
  local v2="$2"

  parse_semver "$v1" || return 2
  local major1="$MAJOR" minor1="$MINOR" patch1="$PATCH"

  parse_semver "$v2" || return 2
  local major2="$MAJOR" minor2="$MINOR" patch2="$PATCH"

  if (( major1 > major2 )); then
    echo 1
  elif (( major1 < major2 )); then
    echo -1
  elif (( minor1 > minor2 )); then
    echo 1
  elif (( minor1 < minor2 )); then
    echo -1
  elif (( patch1 > patch2 )); then
    echo 1
  elif (( patch1 < patch2 )); then
    echo -1
  else
    echo 0
  fi
}
