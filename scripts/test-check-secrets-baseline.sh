#!/usr/bin/env bash
# test-check-secrets-baseline.sh — self-test for scripts/check-secrets-baseline.sh.
#
# Same reason as test-tz-lint-guard.sh / test-check-no-token-persistence.sh:
# a guard whose detection quietly breaks reopens the whole class with no
# signal, so every escape path it closes is fixtured here and run from
# run_prepush.sh before the guard itself judges the repo.
#
# Fixtures are throw-away git repos under mktemp; every "secret" is random and
# never appears in the guard's output (asserted). Needs detect-secrets and git.
#
# Cases:
#   1. baseline in sync, all entries audited                      → exit 0
#   2. baseline present but entries not audited (no is_secret)    → exit 1 UNAUDITED
#   3. an entry marked is_secret=true                             → exit 1 REAL
#   4. new literal committed after the baseline                   → exit 1 NEW, value not printed
#   5. same literal, line moved                                   → exit 1 MOVED (line drift only)
#   6. finding removed from tree, still in baseline               → exit 1 GONE
#   7. uncommitted literal in the working tree                    → exit 0 (HEAD is judged, not the worktree)
#   8. `${DB_PASSWORD:-<literal>}`, `${..._ENCRYPTION_KEY:-<literal>}`   → exit 1 DEFAULT, value not printed
#   9. placeholder / `$var` / key-id / public-key / key-name defaults → exit 0
#  10. no committed baseline                                      → exit 2, never created
#  11. missing argument / not a git repo / no commits             → exit 2
#  12. detect-secrets binary missing                              → exit 2
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GUARD="${SCRIPT_DIR}/check-secrets-baseline.sh"

PASS=0
FAIL=0
TESTS_RUN=0
ok()   { echo "  ✓ $1"; PASS=$((PASS + 1)); }
fail() { echo "  ✗ $1" >&2; FAIL=$((FAIL + 1)); }
run_case() { TESTS_RUN=$((TESTS_RUN + 1)); echo "Case $TESTS_RUN: $1"; }

FIXTURE_DIR=""
cleanup() { [ -n "$FIXTURE_DIR" ] && [ -d "$FIXTURE_DIR" ] && rm -rf "$FIXTURE_DIR" || true; }
trap cleanup EXIT

rand32() { head -c 300 /dev/urandom | base64 | tr -dc 'A-Za-z0-9' | cut -c1-32; }
SECRET_A="$(rand32)"
SECRET_B="$(rand32)"
SECRET_C="$(rand32)"

new_fixture() {
  cleanup
  FIXTURE_DIR="$(mktemp -d)"
  git -C "$FIXTURE_DIR" init -q
}
commit_all() {
  git -C "$FIXTURE_DIR" add -A
  git -C "$FIXTURE_DIR" -c user.name=fixture -c user.email=fixture@example.invalid \
    commit -q --allow-empty -m "fixture: $1"
}
# Baseline the fixture's current tree the way the guard expects it: same flags,
# then mark every entry as an audited false positive (is_secret: false).
make_baseline() {
  (cd "$FIXTURE_DIR" && detect-secrets scan --all-files \
      --exclude-files ".secrets.baseline" --exclude-files ".git/.*" > .secrets.baseline)
  python3 - "$FIXTURE_DIR/.secrets.baseline" <<'PY'
import json, sys
p = sys.argv[1]
d = json.load(open(p))
for es in d["results"].values():
    for e in es:
        e["is_secret"] = False
json.dump(d, open(p, "w"), indent=2)
PY
}
# run_guard <expected_exit> <label> [needle ...]  — every needle must appear in the output
run_guard() {
  local expected="$1" label="$2"; shift 2
  local out rc=0
  out=$(bash "$GUARD" "$FIXTURE_DIR" 2>&1) || rc=$?
  if [ "$rc" -ne "$expected" ]; then
    fail "$label — expected exit $expected, got $rc"; echo "$out" | sed 's/^/      /' >&2; return
  fi
  local n
  for n in "$@"; do
    if ! grep -qF -- "$n" <<<"$out"; then
      fail "$label — output lacks '$n'"; echo "$out" | sed 's/^/      /' >&2; return
    fi
  done
  local s
  for s in "$SECRET_A" "$SECRET_B" "$SECRET_C"; do
    if grep -qF -- "$s" <<<"$out"; then fail "$label — output leaks a fixture secret"; return; fi
  done
  ok "$label"
}

# ── 1. in sync ───────────────────────────────────────────────────────────────
run_case "baseline in sync, audited"
new_fixture
mkdir -p "$FIXTURE_DIR/app"
printf 'db_password = "%s"\n' "$SECRET_A" > "$FIXTURE_DIR/app/settings.py"
printf '# clean file\n' > "$FIXTURE_DIR/README.md"
commit_all "code"
make_baseline
commit_all "baseline"
run_guard 0 "in sync" "baseline in sync" "no literal defaults"

# ── 2. unaudited ─────────────────────────────────────────────────────────────
run_case "baseline entries not audited"
python3 - "$FIXTURE_DIR/.secrets.baseline" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
for es in d["results"].values():
    for e in es: e.pop("is_secret", None)
json.dump(d, open(p, "w"), indent=2)
PY
commit_all "unaudited baseline"
run_guard 1 "unaudited entry fails" "UNAUDITED" "app/settings.py:1"

# ── 3. is_secret=true ────────────────────────────────────────────────────────
run_case "baseline entry marked is_secret=true"
python3 - "$FIXTURE_DIR/.secrets.baseline" <<'PY'
import json, sys
p = sys.argv[1]; d = json.load(open(p))
for es in d["results"].values():
    for e in es: e["is_secret"] = True
json.dump(d, open(p, "w"), indent=2)
PY
commit_all "real-secret baseline"
run_guard 1 "is_secret=true fails" "REAL" "app/settings.py:1"

# ── 4. new literal after baseline ────────────────────────────────────────────
run_case "new literal committed after the baseline"
make_baseline
commit_all "baseline again"
printf 'api_key = "%s"\n' "$SECRET_B" > "$FIXTURE_DIR/app/client.py"
commit_all "leak"
run_guard 1 "new finding fails" "drift vs .secrets.baseline" "NEW" "app/client.py:1"

# ── 5. moved line ────────────────────────────────────────────────────────────
run_case "same literal, line moved"
rm -f "$FIXTURE_DIR/app/client.py"
commit_all "remove leak"
make_baseline
commit_all "baseline"
printf '\n\n' | cat - "$FIXTURE_DIR/app/settings.py" > "$FIXTURE_DIR/app/settings.tmp"
mv "$FIXTURE_DIR/app/settings.tmp" "$FIXTURE_DIR/app/settings.py"
commit_all "shift lines"
run_guard 1 "line drift fails" "MOVED" "app/settings.py: line 1 → 3" "Line drift only"

# ── 6. gone ──────────────────────────────────────────────────────────────────
run_case "finding removed from tree, still in baseline"
printf '# nothing here\n' > "$FIXTURE_DIR/app/settings.py"
commit_all "clean settings"
run_guard 1 "gone finding fails" "GONE" "app/settings.py"

# ── 7. worktree only ─────────────────────────────────────────────────────────
run_case "uncommitted literal in the working tree"
make_baseline
commit_all "baseline"
printf 'password = "%s"\n' "$SECRET_C" > "$FIXTURE_DIR/app/untracked.py"
run_guard 0 "worktree is not judged" "baseline in sync"
rm -f "$FIXTURE_DIR/app/untracked.py"

# ── 8. literal default ───────────────────────────────────────────────────────
run_case "\${DB_PASSWORD:-literal} and \${GATEWAY_ENCRYPTION_KEY:-literal} defaults"
mkdir -p "$FIXTURE_DIR/scripts"
printf '#!/usr/bin/env bash\nexport DB_PASSWORD="${DB_PASSWORD:-%s}"\nexport GATEWAY_ENCRYPTION_KEY="${GATEWAY_ENCRYPTION_KEY:-dev-%s}"\n' \
  "$SECRET_C" "$SECRET_B" > "$FIXTURE_DIR/scripts/run.sh"
commit_all "default"
make_baseline
commit_all "baseline"
run_guard 1 "literal defaults fail" "2 literal defaults on secret-like variables" "DEFAULT" "scripts/run.sh:2" "DB_PASSWORD" "default of 32 chars" \
  "scripts/run.sh:3" "GATEWAY_ENCRYPTION_KEY" "default of 36 chars"

# ── 9. acceptable defaults ───────────────────────────────────────────────────
run_case "placeholder, non-secret suffix and \$var defaults pass"
cat > "$FIXTURE_DIR/scripts/run.sh" <<'SH'
#!/usr/bin/env bash
export DB_PASSWORD="${DB_PASSWORD:-changeme}"
export API_TOKEN="${API_TOKEN:-<your-token>}"
export SECRET_FIELD="${SECRET_FIELD:-api_key}"
export VAULT_TOKEN_TTL="${VAULT_TOKEN_TTL:-24h}"
export JWT_SECRET="${JWT_SECRET:-$OTHER_SECRET}"
export SMTP_PASSWORD="${SMTP_PASSWORD:-}"
export OPENAI_API_KEY="${OPENAI_API_KEY:-sk-test-placeholder}"
export JWT_KEY_ID="${JWT_KEY_ID:-kid-2026-09}"
export JWT_PUBLIC_KEY="${JWT_PUBLIC_KEY:-/etc/keys/jwt.pub}"
export KEYCLOAK_URL="${KEYCLOAK_URL:-http://keycloak:8080}"
export VAULT_TRANSIT_KEY="${VAULT_TRANSIT_KEY:-payments-webhook-hmac}"
export LLM_PROVIDER_KEY="${LLM_PROVIDER_KEY:-anthropic}"
export SERVICE_TYPE_KEY="${SERVICE_TYPE_KEY:-conversational_bot}"
SH
commit_all "ok defaults"
make_baseline
commit_all "baseline"
run_guard 0 "acceptable defaults pass" "no literal defaults on secret-like variables"

# ── 10. no baseline ──────────────────────────────────────────────────────────
run_case "no committed baseline"
git -C "$FIXTURE_DIR" rm -q .secrets.baseline
commit_all "drop baseline"
run_guard 2 "missing baseline is exit 2" "no committed .secrets.baseline"
if [ -e "$FIXTURE_DIR/.secrets.baseline" ]; then fail "guard created a baseline"; else ok "guard did not create a baseline"; fi

# ── 11. usage errors ─────────────────────────────────────────────────────────
run_case "error — missing argument / not a git repo / repo without commits"
rc=0; out=$(bash "$GUARD" 2>&1) || rc=$?
if [ "$rc" -eq 2 ]; then ok "error: missing argument"; else fail "expected exit 2 without argument, got $rc"; fi
NOTGIT="$(mktemp -d)"
rc=0; out=$(bash "$GUARD" "$NOTGIT" 2>&1) || rc=$?
if [ "$rc" -eq 2 ]; then ok "error: not a git repo"; else fail "expected exit 2 for non-git dir, got $rc"; fi
rm -rf "$NOTGIT"
new_fixture
rc=0; out=$(bash "$GUARD" "$FIXTURE_DIR" 2>&1) || rc=$?
if [ "$rc" -eq 2 ]; then ok "error: git repo with no commits"; else fail "expected exit 2 for repo without commits, got $rc"; fi

# ── 12. tool missing ─────────────────────────────────────────────────────────
run_case "detect-secrets binary missing"
printf '# x\n' > "$FIXTURE_DIR/README.md"
commit_all "init"
rc=0; out=$(CHECK_SECRETS_DETECT_BIN=/nonexistent/detect-secrets bash "$GUARD" "$FIXTURE_DIR" 2>&1) || rc=$?
if [ "$rc" -eq 2 ] && grep -q "detect-secrets not found" <<<"$out"; then ok "error: tool missing is exit 2"; else fail "expected exit 2 + message when detect-secrets is missing, got $rc"; fi

echo ""
echo "check-secrets-baseline self-test: $PASS passed, $FAIL failed, $TESTS_RUN cases"
[ "$FAIL" -eq 0 ]
