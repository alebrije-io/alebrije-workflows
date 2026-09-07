#!/usr/bin/env bash
# audit-no-hardcoded-creds.sh — Step 0 of every run_prepush.sh in the fleet:
# the three "reglas inquebrantables" scans (hardcoded credentials, `gh secret
# set GH_TOKEN`, Syncthing sync-conflict files). Exit 0 = clean, 1 = violation,
# 2 = the audit itself could not run (a scan that cannot read the tree is not
# passing, it is absent).
#
# CANONICAL COPY: alebrije-infra/scripts/audit-no-hardcoded-creds.sh. Every
# other repo carries a BYTE-IDENTICAL replica at its root and runs it as
# `bash ./audit-no-hardcoded-creds.sh`. alebrije-infra's run_prepush.sh runs
# scripts/test-audit-no-hardcoded-creds.sh (fixtures for every rule below) and
# scripts/audit-creds-sync.sh --check (fails on any replica that drifts, is
# missing, or is not wired into its run_prepush.sh). Never edit a replica:
# edit this file, run the self-test, then `bash scripts/audit-creds-sync.sh`.
#
# Origin: DEBT-FLOTA-STEP0-AUDIT-CREDS-14-REPOS-SIN-EL-Y-6-VARIANTES-CON-
# VOCABULARIO-DESALINEADO (fleet TECHNICAL-DEBT.md, 2026-09-06). 16 repos ran
# six diverging variants of this file and 16 ran none. Base of this version:
# alebrije-mod-rewards-go/audit-no-hardcoded-creds.sh (closing-quote rule and
# the [2/3]/[3/3] scans, kept as they were); `grep -i` on the credential scan
# from alebrije-svc-notifications-ex's variant (2026-08-17: `PASSWORD:` /
# `SECRET =` / `API_KEY:` in SCREAMING_SNAKE passed the case-sensitive regex
# silently); the placeholder vocabulary is scripts/placeholder-policy.sh's,
# copied verbatim below and asserted equal by the self-test.
#
# What changed versus the six variants, each measured over the 31 fleet repos
# on 2026-09-06 before writing this:
#  - The exclusion is judged on the extracted VALUE, never on the whole line or
#    the path. The old `grep -ivE '(test-|placeholder|<[a-z]|...)'` over the
#    line let `alebrije_dev_2024` (incident 2026-04-17) pass whenever any word
#    of the list appeared anywhere in the line. Of the old terms, `ci-test`,
#    `ephemeral`, `change-me`, `setdefault`, `.env.example`, `Mix.env == :test`,
#    `/dev.exs:` and `/test.exs:` saved 0 lines fleet-wide; they are gone.
#  - Test files and test directories are OUT of the credential scan. Measured:
#    427 of the 433 literals that no rule below excuses live in 154 test files
#    (fixtures with fake passwords, tokens and refresh tokens). Those files are
#    judged by detect-secrets against the committed .secrets.baseline
#    (scripts/check-secrets-baseline.sh, run by 26 of the 32 prepushes; the
#    incident conftest of 2026-04-17 was caught by exactly that scanner). The
#    repos without a baseline are DEBT-FLOTA-REPOS-SIN-BASELINE.
#  - `grep` exit codes are honoured: 1 = no match (clean), anything >= 2 =
#    abort with exit 2. The old `|| true` made an unreadable tree look clean.
#  - On FAIL the value is never printed — only `path:line: key = <N chars>`.
#    The old `echo "$HARDCODED" | head -10` printed the credential it found and
#    hid every finding after the tenth.
#
# Exclusions on the VALUE (any one of them excuses the literal):
#  (a) it matches PLACEHOLDER_PATTERN (same vocabulary the Vault seeders use to
#      refuse a placeholder, so a value the seeder would reject cannot be a
#      real credential either);
#  (b) it contains `$`, `{{` or `#{` — shell/Helm/Elixir expansion, resolved at
#      runtime, not a literal;
#  (c) it starts with `alebrije/data/`, `/vault/secrets/` or `secret/` — a
#      Vault path, i.e. WHERE the secret lives, not the secret;
#  (d) the keyword is `secret` or `token` AND the value is a digit-free
#      identifier (`^[A-Za-z][A-Za-z_-]*$`): the Secret NAME a Helm
#      `existingSecret:` points at, a wire-name constant such as
#      `credKeySigningSecret` holding the JSON key signing_secret.
#      `password` and `api_key` never get this excuse. `alebrije_dev_2024` has
#      digits and still fails.
# Not an exclusion: a `test`/`fake`/`sandbox` marker inside the value.
# MercadoPago `TEST-...` and Stripe `sk_test_...` are real sandbox credentials.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

die() { echo "AUDIT ERROR: $*" >&2; exit 2; }

# Root to scan: explicit argument (the self-test passes a fixture), else the
# git toplevel of the checkout this file lives in — the same answer for the
# canonical copy under scripts/ and for a replica at a repo root.
if [ $# -gt 1 ]; then die "usage: $0 [ROOT]"; fi
if [ $# -eq 1 ]; then
  ROOT="$1"
else
  ROOT="$(git -C "$SCRIPT_DIR" rev-parse --show-toplevel 2>/dev/null)" \
    || die "$SCRIPT_DIR is not inside a git checkout and no ROOT was given"
fi
[ -d "$ROOT" ] || die "ROOT is not a directory: $ROOT"
cd "$ROOT"

# SYNC-WITH: alebrije-infra/scripts/placeholder-policy.sh — copied verbatim;
# scripts/test-audit-no-hardcoded-creds.sh fails if the two lines differ.
PLACEHOLDER_PATTERN='REDACTED|placeholder|changeme|CHANGE_ME|REPLACE_WITH|<[A-Z]|test-placeholder|YOUR_|TODO_|FIXME|dummy|sample|xxxxx|not[-_]?set|example\.com'

# rc-strict `grep -q`: 0 = match, 1 = no match, anything else aborts the audit.
qgrep() {
  local rc=0
  printf '%s\n' "$1" | grep -qiE "$2" || rc=$?
  [ "$rc" -le 1 ] || die "grep -E '$2' exited $rc"
  return "$rc"
}

ERR="$(mktemp)"
trap 'rm -f "$ERR"' EXIT

FAIL=0

# ─────────────────────────────────────────────────────────────────────────────
echo "[AUDIT 1/3] Credenciales hardcoded (tests fuera: los juzga detect-secrets)"
# The value of a REAL hardcoded secret is always a CLOSED string literal
# ("value"). Requiring the closing quote keeps concatenations such as
# `"...password=" + dbPass` out (the open quote is followed by code, not by a
# value) — rewards-go's rationale, kept.
DQ='"'
SQ="'"
QUOTE="[${DQ}${SQ}]"
KEYWORD_RE="(password|secret|token|api_key)[[:space:]]*[:=][[:space:]]*${QUOTE}[^<${DQ}${SQ}][^${DQ}${SQ}]{7,}${QUOTE}"

rc=0
RAW="$(grep -rniE "$KEYWORD_RE" \
  --include='*.go' --include='*.py' --include='*.ts' --include='*.tsx' \
  --include='*.ex' --include='*.exs' --include='*.yaml' --include='*.yml' \
  --include='*.sh' \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv \
  --exclude-dir=.venv --exclude-dir=.venv313 --exclude-dir=deps \
  --exclude-dir=_build \
  --exclude-dir=test --exclude-dir=tests --exclude-dir=__tests__ \
  --exclude-dir=testdata \
  --exclude='*_test.go' --exclude='*_test.exs' --exclude='test_*.py' \
  --exclude='conftest.py' --exclude='*.test.ts' --exclude='*.test.tsx' \
  --exclude='*.spec.ts' --exclude='*.spec.tsx' \
  . 2>"$ERR")" || rc=$?
if [ "$rc" -ge 2 ]; then
  cat "$ERR" >&2
  die "grep exited $rc while scanning $ROOT"
fi

HITS=""
NHITS=0
while IFS= read -r hit; do
  [ -n "$hit" ] || continue
  loc="${hit%%:*}"
  rest="${hit#*:}"
  lineno="${rest%%:*}"
  content="${rest#*:}"
  # Every literal on the line is judged, not only the first one.
  while IFS= read -r match; do
    [ -n "$match" ] || continue
    kwraw="$(printf '%s' "$match" | sed -E 's/[[:space:]]*[:=].*$//')"
    kw="$(printf '%s' "$kwraw" | tr '[:upper:]' '[:lower:]')"
    val="$(printf '%s' "$match" | sed -E "s/^[^:=]*[:=][[:space:]]*${QUOTE}//; s/${QUOTE}\$//")"
    pre="${content%%"$match"*}"
    ident="$(printf '%s\n' "$pre" | sed -E 's/^.*[^A-Za-z0-9_.-]//')"
    if qgrep "$val" "$PLACEHOLDER_PATTERN"; then continue; fi                 # (a)
    case "$val" in *'$'*|*'{{'*|*'#{'*) continue ;; esac                        # (b)
    case "$val" in alebrije/data/*|/vault/secrets/*|secret/*) continue ;; esac  # (c)
    case "$kw" in
      secret|token) if qgrep "$val" '^[A-Za-z][A-Za-z_-]*$'; then continue; fi ;;  # (d)
    esac
    HITS="${HITS}  ${loc}:${lineno}: ${ident}${kwraw} = <${#val} chars>"$'\n'
    NHITS=$((NHITS + 1))
  done <<EOM
$(printf '%s\n' "$content" | grep -oiE "$KEYWORD_RE" || [ $? -eq 1 ] || die "grep -o exited $? on ${loc}:${lineno}")
EOM
done <<EOM
$RAW
EOM

if [ "$NHITS" -gt 0 ]; then
  echo "FAIL: $NHITS credencial(es) hardcoded (el valor no se imprime; sólo su longitud):"
  printf '%s' "$HITS"
  FAIL=1
fi

# ─────────────────────────────────────────────────────────────────────────────
echo "[AUDIT 2/3] gh secret set GH_TOKEN (regla Vault-only)"
rc=0
GH_RAW="$(grep -rn 'gh secret set GH_TOKEN' \
  --include='*.sh' --include='*.yml' --include='*.yaml' --include='*.md' \
  --exclude-dir=.git --exclude-dir=node_modules --exclude-dir=venv \
  --exclude-dir=.venv --exclude-dir=.venv313 --exclude-dir=deps \
  --exclude-dir=_build \
  . 2>"$ERR")" || rc=$?
if [ "$rc" -ge 2 ]; then
  cat "$ERR" >&2
  die "grep exited $rc while scanning $ROOT for gh secret set"
fi
# This audit and its self-test carry the string as their own needle.
rc=0
GH_VIOL="$(printf '%s\n' "$GH_RAW" | grep -v 'audit-no-hardcoded-creds' | grep -v '^$')" || rc=$?
[ "$rc" -le 1 ] || die "grep -v exited $rc"
if [ -n "$GH_VIOL" ]; then
  echo "FAIL: gh secret set GH_TOKEN encontrado (los secrets van a Vault, no a GitHub):"
  printf '%s\n' "$GH_VIOL" | sed 's/^/  /'
  FAIL=1
fi

# ─────────────────────────────────────────────────────────────────────────────
echo "[AUDIT 3/3] Syncthing sync-conflict files en source"
rc=0
CONFLICTS="$(find . \( -path ./.git -o -path ./node_modules -o -path ./venv \
  -o -path ./.venv -o -path ./.venv313 -o -path ./deps -o -path ./_build \) -prune \
  -o -name '*.sync-conflict-*' -print 2>"$ERR")" || rc=$?
if [ "$rc" -ne 0 ]; then
  cat "$ERR" >&2
  die "find exited $rc while scanning $ROOT for sync-conflict files"
fi
if [ -n "$CONFLICTS" ]; then
  echo "FAIL: archivos sync-conflict de Syncthing en el árbol (resolver y borrar):"
  printf '%s\n' "$CONFLICTS" | sed 's/^/  /'
  FAIL=1
fi

# ─────────────────────────────────────────────────────────────────────────────
if [ "$FAIL" = "1" ]; then
  echo "=== AUDIT FAILED ==="
  exit 1
fi
echo "=== AUDIT OK ==="
