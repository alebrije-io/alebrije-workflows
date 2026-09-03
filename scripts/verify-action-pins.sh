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
#
# Two probes, because the REST API alone is not enough: an org with an IP allow list
# (aquasecurity, seen 2026-09-03) answers HTTP 403 to AUTHENTICATED calls from GitHub-hosted
# runner IPs even though the commit exists. Anonymous fetch-by-SHA over git — the same thing
# actions/checkout does — is not subject to that list and gives a definitive answer:
# "not our ref" / "Repository not found" mean the pin is fabricated.
set -euo pipefail
root="${1:-.}"
ATTEMPTS=3
scratch=$(mktemp -d)
trap 'rm -rf -- "${scratch:?}"' EXIT
git -C "$scratch" init -q --bare

# git_probe OWNER/REPO SHA -> exit 0 if the commit is fetchable anonymously from github.com.
git_probe() {
  GIT_TERMINAL_PROMPT=0 git -C "$scratch" -c credential.helper= -c http.extraheader= -c protocol.version=2 \
    fetch --quiet --no-tags --depth=1 --filter=blob:none "https://github.com/$1.git" "$2"
}

# resolve OWNER/REPO SHA -> 0 exists; 1 upstream says it does not exist (definitive);
# 2 could not be verified (network, rate limit, 5xx) after $ATTEMPTS tries. On 1 and 2 the
# probe's own message is printed so the log says WHY, not just that it failed.
resolve() {
  local out attempt
  for attempt in $(seq 1 "$ATTEMPTS"); do
    if out=$(gh api "repos/$1/commits/$2" --jq '.sha' 2>&1); then
      return 0
    fi
    case "$out" in
      *"HTTP 404"*|*"HTTP 422"*) printf '%s' "gh: ${out##*gh: }"; return 1 ;;
    esac
    # 403 (IP allow list), 401, 5xx, rate limit, no network: ask git instead of guessing.
    if out=$(git_probe "$1" "$2" 2>&1); then
      return 0
    fi
    case "$out" in
      *"not our ref"*|*"Repository not found"*) printf '%s' "$out" | tail -1; return 1 ;;
    esac
    sleep $((attempt * 3))
  done
  printf '%s' "$out" | tail -1
  return 2
}
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
  # `$?` inside an `if !` body is the negation's status (always 0), so capture rc explicitly.
  rc=0
  msg=$(resolve "$repo" "$sha") || rc=$?
  case "$rc" in
    0) ;;
    1) echo "::error::$ref — commit does not exist in github.com/$repo ($msg)"; fail=1 ;;
    *) echo "::error::$ref — could not be verified after $ATTEMPTS attempts ($msg)"; fail=1 ;;
  esac
done <<< "$pins"
if [ "$fail" -ne 0 ]; then
  echo "::error::unresolvable action pins found ($n distinct pins checked)"
  exit 1
fi
echo "✓ $n distinct action pins resolve upstream"
