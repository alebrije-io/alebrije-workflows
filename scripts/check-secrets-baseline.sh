#!/usr/bin/env bash
# check-secrets-baseline.sh — fail-closed secret gate over the COMMITTED tree.
#
# Origin (DEBT-INFRA-PREPUSH-SECRETS-SCAN-STAGED-ONLY, 2026-09-05): Phase 1 of
# run_prepush.sh ran a home-made regex over `git diff --cached` — which is EMPTY
# at pre-push time — so it printed "no obvious credentials in staged files" on
# every push while ~25 dev/test credentials sat in tracked files
# (DEBT-INFRA-TRACKED-DEV-SECRETS-LITERAL, cleaned in a944fe6). A gate that
# looks at nothing is not green; it is not running.
#
# What this does instead:
#   1. Extracts HEAD (`git archive`) into a temp dir and runs detect-secrets over
#      it with --all-files: exactly the tree a push ships, never the working
#      tree (uncommitted edits can neither hide nor fake a finding). In a
#      non-git dir detect-secrets without --all-files may silently scan nothing,
#      hence the explicit flag.
#   2. Compares the scan with the committed .secrets.baseline using the SAME
#      semantics as .github/workflows/secret-scanning-baseline-check.yml and
#      svc-auth's Step 2b (decision 40fcc61): every field except `is_secret`
#      (type, hashed_secret, line_number, is_verified). Local and CI can never
#      disagree on what "drift" means.
#   3. Requires every baseline entry to be AUDITED (`is_secret: false`). An
#      entry marked true (a real secret) or never audited fails the gate: a
#      baseline is a list of reviewed false positives, not a parking lot.
#   4. Scans tracked text files for `${SECRET_LIKE_VAR:-literal}` shell defaults
#      — a literal credential smuggled in as a fallback (the pattern behind
#      sync-local-to-prod-schema / verify-local-prod-parity before a944fe6).
#      Defaults that are empty, `$…`, `<placeholder>` or carry a placeholder
#      marker (test/stub/dummy/placeholder/fake/example/sample/changeme/
#      replace/todo/fixme/xxx/not-a-real) pass; variables whose suffix names
#      a non-secret (_FIELD, _NAME, _PATH, _TTL, _ID, …) are skipped.
#
# NEVER auto-creates or refreshes the baseline: a gate that heals itself on
# retry is not a gate. On drift, review each finding, then — deliberately —
#     detect-secrets scan --baseline .secrets.baseline   # in-place, keeps audit flags
#     detect-secrets audit .secrets.baseline             # mark new entries
# and commit the result separately. Never `scan … > .secrets.baseline` on an
# existing baseline: it rewrites the file and drops every is_secret flag.
#
# Usage:
#   bash check-secrets-baseline.sh <repo_dir>
#   CHECK_SECRETS_DETECT_BIN=<path>   override the detect-secrets binary (tests)
#
# Output never contains a secret value nor its hash: findings are printed as
# `<verdict> path:line [detector]` only.
#
# Exit 0 = baseline in sync, all entries audited, no literal defaults.
# Exit 1 = drift / unaudited or real entry / literal default found.
# Exit 2 = usage, tooling or scan error. A broken scan is NOT a pass.
set -euo pipefail

REPO="${1:-}"
if [ -z "$REPO" ]; then
  echo "usage: bash check-secrets-baseline.sh <repo_dir>" >&2
  exit 2
fi
if ! git -C "$REPO" rev-parse --verify --quiet HEAD >/dev/null 2>&1; then
  echo "check-secrets-baseline: '$REPO' is not a git repo with a HEAD commit" >&2
  exit 2
fi
DS_BIN="${CHECK_SECRETS_DETECT_BIN:-detect-secrets}"
if ! command -v "$DS_BIN" >/dev/null 2>&1; then
  echo "check-secrets-baseline: detect-secrets not found (looked for '$DS_BIN')." >&2
  echo "  install: pip install 'detect-secrets==1.5.0'   (or: brew install detect-secrets)" >&2
  exit 2
fi
if ! command -v python3 >/dev/null 2>&1; then
  echo "check-secrets-baseline: python3 is required" >&2
  exit 2
fi

WORK="$(mktemp -d)"
cleanup() { rm -rf "$WORK"; }
trap cleanup EXIT

# 1. The committed tree, and only the committed tree.
TREE="$WORK/tree"
mkdir -p "$TREE"
if ! git -C "$REPO" archive --format=tar HEAD | tar -x -C "$TREE"; then
  echo "check-secrets-baseline: git archive HEAD failed" >&2
  exit 2
fi
TRACKED=$(git -C "$REPO" ls-tree -r --name-only HEAD | wc -l | tr -d ' ')
EXTRACTED=$(cd "$TREE" && find . -type f | wc -l | tr -d ' ')
if [ "$TRACKED" -eq 0 ] || [ "$TRACKED" -ne "$EXTRACTED" ]; then
  echo "check-secrets-baseline: HEAD has $TRACKED tracked files but $EXTRACTED were extracted — refusing to judge a partial tree" >&2
  exit 2
fi
if [ ! -f "$TREE/.secrets.baseline" ]; then
  echo "❌ check-secrets-baseline: no committed .secrets.baseline in HEAD." >&2
  echo "   The gate cannot run without one and will NOT create it. Create it once, on purpose:" >&2
  echo "     detect-secrets scan --exclude-files '.secrets.baseline' --exclude-files '.git/.*' > .secrets.baseline" >&2
  echo "     detect-secrets audit .secrets.baseline     # review EVERY entry; only false positives may stay" >&2
  echo "   then commit it." >&2
  exit 2
fi

# 2. Fresh scan, same flags as the CI workflow (plus --all-files: the archive is not a git repo).
CURRENT="$WORK/current.json"
if ! (cd "$TREE" && "$DS_BIN" scan --all-files \
        --exclude-files ".secrets.baseline" --exclude-files ".git/.*" > "$CURRENT" 2> "$WORK/scan.err"); then
  echo "check-secrets-baseline: detect-secrets scan failed:" >&2
  sed 's/^/    /' "$WORK/scan.err" >&2
  exit 2
fi
DS_VERSION="$("$DS_BIN" --version 2>/dev/null | head -1 || true)"

RC=0
set +e
python3 - "$TREE/.secrets.baseline" "$CURRENT" "$DS_VERSION" <<'PY'
import json, sys, collections

base_p, cur_p, ds_version = sys.argv[1], sys.argv[2], sys.argv[3]
try:
    with open(base_p) as fh:
        base = json.load(fh)
    with open(cur_p) as fh:
        cur = json.load(fh)
except (OSError, ValueError) as exc:  # unreadable baseline / scan output → not a pass
    print(f"check-secrets-baseline: cannot read baseline or scan output: {exc}", file=sys.stderr)
    sys.exit(2)

if base.get("version") and ds_version and base["version"] != ds_version:
    print(f"  ℹ️  baseline generated with detect-secrets {base['version']}, scanning with {ds_version}")

def strip(results):
    return {f: [{k: v for k, v in e.items() if k != "is_secret"} for e in es] for f, es in results.items()}

old_full = base.get("results", {})
old, new = strip(old_full), strip(cur.get("results", {}))
failed = False

# 3. Audit discipline: every baseline entry must be a reviewed false positive.
real = [(f, e["line_number"], e["type"]) for f, es in old_full.items() for e in es if e.get("is_secret") is True]
unaudited = [(f, e["line_number"], e["type"]) for f, es in old_full.items() for e in es if "is_secret" not in e]
if real:
    failed = True
    print(f"❌ {len(real)} baseline entr{'y is' if len(real)==1 else 'ies are'} marked is_secret=true — a real secret in the tree:")
    for f, ln, t in real:
        print(f"     REAL     {f}:{ln} [{t}]")
if unaudited:
    failed = True
    print(f"❌ {len(unaudited)} baseline entr{'y is' if len(unaudited)==1 else 'ies are'} not audited (no is_secret flag):")
    for f, ln, t in unaudited[:40]:
        print(f"     UNAUDITED {f}:{ln} [{t}]")
    if len(unaudited) > 40:
        print(f"     … and {len(unaudited) - 40} more")
    print("   run `detect-secrets audit .secrets.baseline`, keep only false positives, commit.")

# 4. Drift, CI semantics: everything but is_secret.
if json.dumps(old, sort_keys=True) != json.dumps(new, sort_keys=True):
    failed = True
    key = lambda f, e: (f, e["type"], e["hashed_secret"])
    def index(res):
        d = collections.defaultdict(list)
        for f, es in res.items():
            for e in es:
                d[key(f, e)].append(e)
        return d
    oi, ni = index(old), index(new)
    added = [k for k in ni if k not in oi]
    gone = [k for k in oi if k not in ni]
    moved = [k for k in ni if k in oi and ni[k] != oi[k]]
    print("❌ detect-secrets: drift vs .secrets.baseline")
    for k in sorted(added):
        for e in ni[k]:
            print(f"     NEW      {k[0]}:{e['line_number']} [{k[1]}]  ← review before touching the baseline")
    for k in sorted(gone):
        for e in oi[k]:
            print(f"     GONE     {k[0]}:{e['line_number']} [{k[1]}]  (no longer matched)")
    for k in sorted(moved):
        ol = ",".join(str(e["line_number"]) for e in oi[k]); nl = ",".join(str(e["line_number"]) for e in ni[k])
        ov = any(e.get("is_verified") for e in oi[k]); nv = any(e.get("is_verified") for e in ni[k])
        extra = "  ⚠ is_verified changed" if ov != nv else ""
        print(f"     MOVED    {k[0]}: line {ol} → {nl} [{k[1]}]{extra}")
    if added:
        print("   New findings: a real secret must be removed from the tree and rotated; a false positive is")
        print("   added to the baseline ONLY after review (detect-secrets audit).")
    if moved and not added and not gone:
        print("   Line drift only (same files, same hashes). Refresh IN-PLACE, deliberately, and commit separately:")
    else:
        print("   After review, refresh IN-PLACE (keeps audit flags) and commit separately:")
    print("     detect-secrets scan --baseline .secrets.baseline && detect-secrets audit .secrets.baseline")
    print("   NO automatic refresh — a gate that heals itself on retry is not a gate.")
    print("   NEVER `scan … > .secrets.baseline` on an existing baseline: it drops every is_secret flag.")

if not failed:
    n = sum(len(v) for v in new.values())
    print(f"  baseline in sync: {n} audited false positive{'s' if n != 1 else ''} in {len(new)} files, 0 new, 0 gone")
sys.exit(1 if failed else 0)
PY
RC_BASE=$?
[ "$RC_BASE" -eq 2 ] && exit 2

# 5. Literal shell defaults on secret-like variables.
python3 - "$TREE" <<'PY'
import os, re, sys

tree = sys.argv[1]
SELF = {"scripts/check-secrets-baseline.sh", "scripts/test-check-secrets-baseline.sh", ".secrets.baseline"}
# Any `${VAR:-default}` is a candidate; the variable NAME decides whether it is
# secret-like, token by token (`_`-separated), so ENCRYPTION_KEY, SIGNING_KEY,
# DB_PASS or HMAC_SECRET all count while KEYCLOAK_URL does not (no `KEY` token).
DEFAULT = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*):-([^}]*)\}")
SECRET_TOKENS = {"PASSWORD", "PASSWD", "PWD", "PASS", "SECRET", "SECRETS", "TOKEN", "KEY", "KEYS",
                 "APIKEY", "SALT", "CREDENTIAL", "CREDENTIALS", "PRIVKEY"}
# A name that ends in a descriptor is metadata about the secret, not the secret.
NON_SECRET_SUFFIX = re.compile(
    r"(_FIELD|_NAME|_PATH|_FILE|_TTL|_URL|_URI|_ID|_LEN|_LENGTH|_HEADER|_MOUNT|_ENGINE|_ROLE|_ENV|_VERSION|_TYPE|_MODE|"
    r"_COUNT|_DAYS|_HOURS|_MINUTES|_SECONDS|_BYTES|_BITS|_ALG|_ALGORITHM|_ISSUER|_AUDIENCE|_PREFIX|_SUFFIX|_DIR|_CONTEXT|"
    r"_NAMESPACE|_NS|_REF|_KIND|_LABEL|_ENABLED|_REQUIRED|_MAX|_MIN|_LIMIT|_SIZE|_FORMAT|_SOURCE|_STORE|_BACKEND|_PROVIDER)$",
    re.I)
# `KEY` as *name of a key* or *dictionary key*, not key material. Demonstrated
# in this tree: VAULT_TRANSIT_KEY (transit key name), LLM_PROVIDER_KEY and
# SERVICE_TYPE_KEY (enum keys); the rest are the same class.
NAME_LIKE_KEY = re.compile(
    r"(TRANSIT|PROVIDER|TYPE|KV|MAP|DICT|INDEX|SORT|PARTITION|ROUTING|CACHE|LABEL|ANNOTATION|LOOKUP|PRIMARY|FOREIGN|"
    r"UNIQUE|CONFIG|SETTING|OPTION|FEATURE|PUBLIC|VERIFY|VERIFICATION|HOST)_KEYS?$", re.I)


def secret_like(var):
    tokens = set(var.upper().split("_"))
    if not tokens & SECRET_TOKENS:
        return False
    return not (NON_SECRET_SUFFIX.search(var) or NAME_LIKE_KEY.search(var))


PLACEHOLDER = re.compile(
    r"^(\s*$|\$|<)|(?i:test|stub|dummy|placeholder|fake|example|sample|changeme|change[-_]me|replace|todo|fixme|xxx|not[-_]a[-_]real)")

hits = []
for root, dirs, files in os.walk(tree):
    dirs[:] = [d for d in dirs if d != ".git"]
    for name in files:
        path = os.path.join(root, name)
        rel = os.path.relpath(path, tree)
        if rel in SELF:
            continue
        try:
            with open(path, "rb") as fh:
                data = fh.read()
        except OSError as exc:
            print(f"check-secrets-baseline: cannot read {rel}: {exc}", file=sys.stderr)
            sys.exit(2)
        if b"\0" in data[:8000]:
            continue  # binary
        for ln, line in enumerate(data.decode("utf-8", errors="replace").split("\n"), 1):
            for m in DEFAULT.finditer(line):
                var, default = m.group(1), m.group(2)
                if not secret_like(var) or PLACEHOLDER.search(default):
                    continue
                hits.append((rel, ln, var, len(default)))

if hits:
    print(f"❌ {len(hits)} literal default{'s' if len(hits) != 1 else ''} on secret-like variables (value never printed):")
    for rel, ln, var, n in sorted(hits):
        print(f"     DEFAULT  {rel}:{ln} ${{{var}:-…}} (default of {n} chars)")
    print("   A fallback credential is a credential in git. Use `${VAR:?message}` and read the value from .env/Vault;")
    print("   a deliberate non-secret placeholder must say so (e.g. `changeme`, `<value>`, `test-…`).")
    sys.exit(1)
print("  no literal defaults on secret-like variables")
sys.exit(0)
PY
RC_DEF=$?
set -e
[ "$RC_DEF" -eq 2 ] && exit 2
if [ "$RC_BASE" -ne 0 ] || [ "$RC_DEF" -ne 0 ]; then
  exit 1
fi
exit 0
