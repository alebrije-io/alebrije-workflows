#!/usr/bin/env bash
# verify-action-pins.sh — every `uses: owner/repo[/path]@<sha>` under .github must be a
# 40-hex SHA that EXISTS in github.com/owner/repo.
#
# Why: from 2026-05-07 (f835f51) to 2026-09-03 this repo carried 212 pins whose commits did not
# exist upstream (e.g. actions/checkout@692d26c9…, actions/setup-python@f677139b…). Every consumer
# job died in "Set up job" with "Unable to resolve action". validate-self only checked the pin's
# SHAPE (hex chars), so fabricated SHAs — and one 41-char SHA — passed for four months.
#
# Fail-closed: a pin that cannot be verified (404/422, no network, no token) counts as unresolved.
# Usage: scripts/verify-action-pins.sh [repo-root]   (needs `gh` authenticated; CI uses github.token)
set -euo pipefail
root="${1:-.}"
pins=$(grep -rhoE 'uses: *[A-Za-z0-9_.-]+/[A-Za-z0-9_./-]+@[0-9a-f]{7,}' "$root/.github" | sed -E 's/uses: *//' | sort -u)
fail=0
n=0
while read -r ref; do
  [ -z "$ref" ] && continue
  n=$((n + 1))
  repo=$(printf '%s' "${ref%@*}" | cut -d/ -f1-2)
  sha=${ref##*@}
  if [ "${#sha}" -ne 40 ]; then
    echo "::error::$ref — SHA must be exactly 40 hex chars (got ${#sha})"
    fail=1
    continue
  fi
  if ! gh api "repos/$repo/commits/$sha" --jq '.sha' >/dev/null 2>&1; then
    echo "::error::$ref — commit does not exist in github.com/$repo (or could not be verified)"
    fail=1
  fi
done <<< "$pins"
if [ "$fail" -ne 0 ]; then
  echo "::error::unresolvable action pins found ($n distinct pins checked)"
  exit 1
fi
echo "✓ $n distinct action pins resolve upstream"
