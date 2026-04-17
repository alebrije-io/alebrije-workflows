#!/usr/bin/env python3
"""Frontend ↔ backend contract audit.

Compares URL patterns invoked by every TypeScript client in
``alebrije-frontend/src/lib/api/*.ts`` against the routes declared by the
matching backend (Python FastAPI, Elixir Phoenix, Go chi).

Design notes
------------

*   The extractor is regex-based and intentionally dumb. Tree-sitter would
    catch more exotic forms, but at the cost of tying the tool to the
    specific versions of each framework. Regex keeps the helper portable
    across CI runners and dev machines.
*   Path-parameter syntax is normalised before comparison. FE uses ``:var``
    (when written as template strings on purpose) or interpolated
    ``${var}``. FastAPI and Phoenix declare ``{var}`` or ``:var``. All of
    these collapse to ``:param`` for matching, so a backend route
    ``/accounts/{user_id}`` and a frontend call
    ``/accounts/${userId}`` read as identical.
*   Query strings never count as path. ``?foo=1`` is trimmed off before
    the URL enters the comparison set.
*   Prefixes are inferred per-module. The workspace uses a mix of
    ``/api/v1/<mod>`` and ``/api/v1/mod/<mod>`` depending on when the
    module was born. Each module entry in ``MODULES`` pins its canonical
    prefix so we do not get false-positives from a ``/api/v1/rewards``
    backend seemingly disagreeing with the default ``/api/v1/mod/rewards``
    frontend.

Outputs
-------

Two formats are produced on every run:

1.  A JSON report (``--json`` writes it to stdout; otherwise it lands
    next to the markdown summary as ``.audit-report.json``).
2.  A markdown file at ``CONTRACT_AUDIT.md`` in the alebrije workspace
    root, suitable for review in a PR.

Usage
-----

::

    python3 scripts/fe_be_audit.py              # full audit, writes MD
    python3 scripts/fe_be_audit.py --module rewards
    python3 scripts/fe_be_audit.py --strict     # exit 1 on any mismatch
    python3 scripts/fe_be_audit.py --json       # print JSON to stdout
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# ── Workspace layout ────────────────────────────────────────────────────────

WORKSPACE = Path(__file__).resolve().parent.parent
FRONTEND_API_DIR = WORKSPACE / "alebrije-frontend" / "src" / "lib" / "api"


# Each module entry maps:
#   fe_files   — the *.ts clients that live under this module
#   fe_prefix  — the URL prefix the frontend prepends (via createModuleClient)
#   backend    — the on-disk location of the matching service
#   kind       — 'python' | 'elixir' | 'go'
#
# ``fe_prefix`` is the ground truth used to normalise both sides. The FE
# client's path parts are stitched back onto this prefix, and backend
# routes are expected to start with the same prefix.
MODULES: dict[str, dict] = {
    # NOTE: modules whose FE uses the default ``/api/v1/mod/<x>`` prefix
    # and ALSO prepends ``/<x>/`` to each call (catalog, campaigns,
    # agenda, agentic, etc.) map to backend routes at ``/api/v1/<x>/...``.
    # The gateway strips the ``/mod/<x>`` hop, so ``backend_prefix`` is
    # ``/api/v1`` for all of them — the second ``/<x>/`` segment in the
    # FE path carries the module name for the backend.
    "agenda": {
        "fe_files": ["agenda.ts"],
        "fe_prefix": "/api/v1/mod/agenda",
        "backend_prefix": "/api/v1",
        "backend": "alebrije-mod-agenda-ex",
        "kind": "elixir",
    },
    "agentic": {
        "fe_files": ["agentic.ts", "ai.ts"],
        "fe_prefix": "/api/v1/mod/agentic",
        "backend_prefix": "/api/v1",
        "backend": "alebrije-mod-agentic",
        "kind": "python",
    },
    "cadences": {
        "fe_files": ["cadences.ts"],
        "fe_prefix": "/api/v1/mod/cadences",
        "backend_prefix": "/api/v1",
        "backend": "alebrije-mod-cadences-ex",
        "kind": "elixir",
    },
    "campaigns": {
        "fe_files": ["campaigns.ts"],
        "fe_prefix": "/api/v1/mod/campaigns",
        "backend_prefix": "/api/v1",
        "backend": "alebrije-mod-campaigns-ex",
        "kind": "elixir",
    },
    "catalog": {
        "fe_files": ["catalog.ts"],
        "fe_prefix": "/api/v1/mod/catalog",
        # Catalog FE calls look like ``api.get("/catalog/items")`` on top
        # of the default ``/api/v1/mod/catalog`` prefix. The gateway
        # strips ``/mod/catalog`` before forwarding, so the service sees
        # ``/api/v1/catalog/items``. We anchor comparisons at ``/api/v1``
        # and rely on the FE path carrying the ``/catalog/`` segment.
        "backend_prefix": "/api/v1",
        "backend": "alebrije-mod-catalog-go",
        "kind": "go",
    },
    "control-medico": {
        "fe_files": ["control-medico.ts"],
        "fe_prefix": "/api/v1/mod/control-medico",
        "backend_prefix": "/api/v1",
        "backend": "alebrije-mod-control-medico",
        "kind": "python",
    },
    "crm": {
        "fe_files": ["crm.ts"],
        "fe_prefix": "/api/v1/crm",
        "backend_prefix": "/api/v1/crm",
        "backend": "alebrije-mod-crm-go",
        "kind": "go",
    },
    "field-ops": {
        "fe_files": ["field-ops.ts"],
        "fe_prefix": "/api/v1/field-ops",
        "backend_prefix": "/api/v1/field-ops",
        "backend": "alebrije-mod-field-ops-ex",
        "kind": "elixir",
    },
    "notifications": {
        "fe_files": [
            "notifications.ts",
            "notifications-admin.ts",
            "notification-preferences.ts",
        ],
        "fe_prefix": "/api/v1/notifications",
        "backend_prefix": "/api/v1/notifications",
        "backend": "alebrije-svc-notifications-ex",
        "kind": "elixir",
    },
    "omnichannel": {
        "fe_files": ["omnichannel.ts"],
        "fe_prefix": "/api/v1/mod/omnichannel",
        "backend_prefix": "/api/v1",
        "backend": "alebrije-svc-omnichannel-ex",
        "kind": "elixir",
    },
    "payments": {
        "fe_files": ["payments.ts"],
        "fe_prefix": "/api/v1/payments",
        "backend_prefix": "/api/v1/payments",
        "backend": "alebrije-mod-payments-go",
        "kind": "go",
    },
    "planificador": {
        "fe_files": [
            "planificador.ts",
            "planificador-card-extras.ts",
            "planificador-organization.ts",
        ],
        "fe_prefix": "/api/v1/planificador",
        "backend_prefix": "/api/v1/planificador",
        "backend": "alebrije-mod-planificador-ex",
        "kind": "elixir",
    },
    "proyectos": {
        "fe_files": ["proyectos.ts"],
        "fe_prefix": "/api/v1/mod/proyectos",
        "backend_prefix": "/api/v1",
        "backend": "alebrije-mod-proyectos-go",
        "kind": "go",
    },
    "rewards": {
        "fe_files": ["rewards.ts"],
        "fe_prefix": "/api/v1/rewards",
        "backend_prefix": "/api/v1/rewards",
        "backend": "alebrije-mod-rewards-go",
        "kind": "go",
    },
}

# These FE clients are tracked separately because they hit multiple
# backends (auth, feature flags) or don't map cleanly to one service.
STANDALONE_FE = {
    # file name → placeholder module label
    "feature-flags-api.ts": "auth",
    "sagas.ts": "auth",
    "settings.ts": "auth",
    "toronja.ts": "toronja",
}

# ── Path normalisation ──────────────────────────────────────────────────────

# ``{var}`` (FastAPI / Phoenix occasionally) or ``:var`` (chi, Phoenix) or
# ``${var}`` (FE template literal) all normalise to ``:param``.
PARAM_PATTERNS = [
    re.compile(r"\$\{[^}]+\}"),  # FE template literal — apply first so the
                                 # trailing ``}`` doesn't get consumed by
                                 # the generic ``{...}`` pattern below.
    re.compile(r"\{[^}]+\}"),    # FastAPI / chi verbose form
    re.compile(r":[A-Za-z_][A-Za-z0-9_]*"),  # chi / Phoenix
]


def normalise_path(path: str) -> str:
    """Return a canonical form with path params collapsed to ``:param``."""

    if not path:
        return ""

    # Trim query + hash.
    path = path.split("?", 1)[0].split("#", 1)[0]

    # Strip trailing slash except for bare root.
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]

    for pat in PARAM_PATTERNS:
        path = pat.sub(":param", path)

    return path


# ── Frontend extractor ──────────────────────────────────────────────────────

# Matches api.get("/foo/${bar}"), api.post('/foo/bar', body), etc.
# The call form is restricted to the verbs that appear in base.ts.
FE_CALL_RE = re.compile(
    r"""
    \bapi\s*\.\s*(?P<verb>get|post|put|patch|delete)\s*<[^>]*>?\s*\(\s*   # api.verb<T>(
    (?P<quote>["'`])                                                      # opening quote
    (?P<path>[^"'`]+)                                                     # the URL
    (?P=quote)                                                            # matching quote
    """,
    re.VERBOSE,
)

# When the FE file assigns `const client = createModuleClient(...)` the
# call prefix is `client.get(...)`. Same for `export const api =`. The
# extractor greedily matches any identifier followed by `.get/.post/etc`
# but still requires the call to live near a `createModuleClient`
# declaration in the same file to avoid noise.
FE_CLIENT_CALL_RE = re.compile(
    r"""
    \b(?P<client>[A-Za-z_][A-Za-z0-9_]*)\s*\.\s*(?P<verb>get|post|put|patch|delete)
    (?:\s*<[^>]*>)?              # optional generic type argument
    \s*\(\s*
    (?P<quote>["'`])
    (?P<path>[^"'`]+)
    (?P=quote)
    """,
    re.VERBOSE,
)


def extract_frontend(path: Path) -> list[tuple[str, str]]:
    """Return a list of ``(verb, url)`` tuples found in the given TS file."""

    try:
        text = path.read_text(encoding="utf-8")
    except OSError:
        return []

    # Discover the client identifiers used in this file. Anything assigned
    # to createModuleClient(...) is fair game.
    client_names: set[str] = set()
    for match in re.finditer(
        r"""(?:const|let|var|export\s+const)\s+([A-Za-z_][A-Za-z0-9_]*)\s*(?::\s*[^=]+)?=\s*createModuleClient\b""",
        text,
    ):
        client_names.add(match.group(1))
    if not client_names:
        client_names.add("api")  # sensible default

    calls: list[tuple[str, str]] = []
    for m in FE_CLIENT_CALL_RE.finditer(text):
        if m.group("client") not in client_names:
            continue
        verb = m.group("verb").upper()
        url = m.group("path").strip()
        if not url.startswith("/"):
            continue  # relative-looking strings in comments, URL pieces, etc.

        # Chop off anything from the first unbalanced ``${`` — template
        # literals that build a query string or conditional suffix like
        # ``/campaigns${query ? "?"+query : ""}`` confuse the tokenizer;
        # dropping the suffix is safer than emitting a bogus path.
        if "${" in url:
            opens = url.count("${")
            closes = url.count("}")
            if opens > closes:
                url = url[: url.index("${")]
                if not url.endswith("/"):
                    url = url.rstrip("/")
        # Same for raw query strings accidentally left in.
        url = url.split("?", 1)[0]

        if not url or not url.startswith("/"):
            continue
        calls.append((verb, url))
    return calls


# ── Backend extractors ──────────────────────────────────────────────────────

# FastAPI: @router.get("/foo")
FASTAPI_ROUTE_RE = re.compile(
    r"""@router\s*\.\s*(?P<verb>get|post|put|patch|delete)\s*\(\s*(?P<quote>["'])(?P<path>[^"']+)(?P=quote)""",
    re.VERBOSE,
)
FASTAPI_PREFIX_RE = re.compile(
    r"""APIRouter\s*\(\s*(?:[^)]*?\bprefix\s*=\s*(?P<quote>["'])(?P<prefix>[^"']*)(?P=quote))""",
    re.VERBOSE,
)
FASTAPI_INCLUDE_RE = re.compile(
    r"""include_router\s*\(\s*(?P<name>[A-Za-z_][A-Za-z0-9_]*)[^)]*?(?:prefix\s*=\s*(?P<quote>["'])(?P<prefix>[^"']*)(?P=quote))?""",
    re.VERBOSE | re.DOTALL,
)

# chi: ``r.Get("/foo", h.bar)``. The path literal must start with ``/``
# and the call must be followed by a ``,`` and a handler reference —
# never a bare ``)`` (which would match ``r.URL.Query().Get("page")``
# with a single argument). A handler always has another comma-separated
# argument after the path string.
CHI_ROUTE_RE = re.compile(
    r"""(?<![A-Za-z0-9_.])(?P<recv>[A-Za-z_][A-Za-z0-9_]{0,10})\s*\.\s*(?P<verb>Get|Post|Put|Patch|Delete)\s*\(\s*(?P<quote>["'])(?P<path>/[^"']*)(?P=quote)\s*,"""
)

# Phoenix router macros: get "/foo", Controller, :action
PHOENIX_ROUTE_RE = re.compile(
    r"""^\s*(?P<verb>get|post|put|patch|delete)\s+(?P<quote>["'])(?P<path>[^"']+)(?P=quote)""",
    re.MULTILINE,
)
PHOENIX_SCOPE_RE = re.compile(
    r"""scope\s+(?P<quote>["'])(?P<scope>[^"']+)(?P=quote)"""
)


def collect_python_routes(backend_dir: Path, prefix_hint: str) -> list[tuple[str, str]]:
    """Walk a FastAPI module and collect all registered endpoints.

    ``prefix_hint`` is used as a default when no ``include_router(prefix=…)``
    call can be found for a given router.
    """

    api_dir = backend_dir / "app" / "api" / "v1"
    if not api_dir.exists():
        return []

    main_py = backend_dir / "app" / "main.py"
    # Figure out per-router prefix overrides from main.py include_router calls.
    include_prefixes: dict[str, str] = {}
    if main_py.exists():
        main_src = main_py.read_text(encoding="utf-8", errors="replace")
        for m in FASTAPI_INCLUDE_RE.finditer(main_src):
            include_prefixes[m.group("name")] = m.group("prefix") or ""

    routes: list[tuple[str, str]] = []
    for py_file in sorted(api_dir.glob("*.py")):
        if py_file.name.startswith("__"):
            continue
        text = py_file.read_text(encoding="utf-8", errors="replace")

        # The router prefix either lives on APIRouter(prefix=...) or is
        # supplied by main.py's include_router call. The include-based form
        # wins when both exist — that's how FastAPI itself resolves it.
        router_prefix = ""
        local = FASTAPI_PREFIX_RE.search(text)
        if local:
            router_prefix = local.group("prefix") or ""

        # Look up the module alias used in main.py's include call. FastAPI
        # conventions import as e.g. `from app.api.v1.agenda import router
        # as agenda_router`, so we probe a few name variants.
        stem = py_file.stem
        for alias in (f"{stem}_router", "router", stem):
            if alias in include_prefixes:
                extra = include_prefixes[alias]
                # If the local router already carried a /api/v1/foo prefix,
                # the include prefix is usually a /api/v1 that the local
                # already encodes — don't double it.
                if extra and not router_prefix.startswith(extra):
                    router_prefix = extra + router_prefix
                break

        if not router_prefix:
            router_prefix = prefix_hint

        for m in FASTAPI_ROUTE_RE.finditer(text):
            verb = m.group("verb").upper()
            path = m.group("path")
            full = (router_prefix + path) if not path.startswith(router_prefix) else path
            routes.append((verb, full))

    return routes


def collect_go_routes(backend_dir: Path) -> list[tuple[str, str]]:
    """Collect chi routes from a Go service.

    chi routers use ``r.Get("/foo", handler)`` plus ``r.Route("/prefix", …)``
    for scoping. The scoping form is rare in this workspace — most
    services mount everything flat under ``/api/v1/<mod>`` at the top
    level — but we still honour a single level of ``Route`` wrapping by
    reading the literal string argument.

    The returned paths include the ``/api/v1`` prefix set up by the
    top-level ``Route("/api/v1", …)`` call in each router.go.
    """

    handler_dir = backend_dir / "internal" / "handler"
    if not handler_dir.exists():
        return []

    # First, inspect router.go to figure out the outer mount prefix.
    # The repeated idiom is ``r.Route("/api/v1", func(api chi.Router) {
    # h.Mount(api) })`` — handler files in sibling files then call
    # ``r.Post("/rewards/...")`` on the already-scoped router. We can't
    # track scopes across files with a stack, so we record the outer
    # prefix and prepend it whenever a route path doesn't already start
    # with ``/api/``.
    outer_prefix = ""
    router_go = handler_dir / "router.go"
    if router_go.exists():
        router_src = router_go.read_text(encoding="utf-8", errors="replace")
        m = re.search(
            r"""\.Route\s*\(\s*(?P<quote>["'])(?P<prefix>/api/[^"']*)(?P=quote)""",
            router_src,
        )
        if m:
            outer_prefix = m.group("prefix")
    if not outer_prefix:
        outer_prefix = "/api/v1"

    routes: list[tuple[str, str]] = []
    for go_file in sorted(handler_dir.glob("*.go")):
        if go_file.name.endswith("_test.go"):
            continue
        text = go_file.read_text(encoding="utf-8", errors="replace")
        is_router = go_file.name == "router.go"

        # Track nested ``Route("/prefix", func(c chi.Router) { ... })``
        # scopes in every file. For sibling handler files the outer
        # ``/api/v1`` scope is inherited from router.go — we emulate it
        # by adding `outer_prefix` to any path that doesn't already
        # start with ``/api/`` after in-file scopes are applied.
        scope_stack: list[str] = []
        brace_depth_for_scope: list[int] = []
        current_depth = 0

        for line in text.splitlines():
            route_intro = re.search(
                r"""\.Route\s*\(\s*(?P<quote>["'])(?P<prefix>/[^"']*)(?P=quote)""",
                line,
            )
            if route_intro:
                scope_stack.append(route_intro.group("prefix"))
                brace_depth_for_scope.append(current_depth)

            current_depth += line.count("{") - line.count("}")
            while brace_depth_for_scope and current_depth <= brace_depth_for_scope[-1]:
                brace_depth_for_scope.pop()
                scope_stack.pop()

            for m in CHI_ROUTE_RE.finditer(line):
                verb = m.group("verb").upper()
                path = m.group("path")
                if path in {"/", "/health", "/metrics"}:
                    continue
                in_file_prefix = "".join(scope_stack)
                stitched = in_file_prefix + path
                if stitched.startswith("/api/"):
                    full = stitched
                elif is_router:
                    full = stitched
                else:
                    full = outer_prefix + stitched
                routes.append((verb, full))
    return routes


def collect_elixir_routes(backend_dir: Path) -> list[tuple[str, str]]:
    """Collect Phoenix routes from lib/<app>_web/router.ex."""

    matches = list((backend_dir / "lib").glob("*/router.ex"))
    if not matches:
        return []

    routes: list[tuple[str, str]] = []
    for router_path in matches:
        text = router_path.read_text(encoding="utf-8", errors="replace")

        # Walk the file tracking the current scope. Whenever we hit a
        # ``scope "/foo"`` we push onto a stack and apply it to subsequent
        # route declarations. A crude line-based state machine is enough
        # for the way routes are laid out in this workspace — nested
        # scopes use ``scope "/x" do`` … ``end`` blocks.
        scope_stack: list[str] = []
        for line in text.splitlines():
            stripped = line.strip()
            sm = PHOENIX_SCOPE_RE.search(stripped)
            if sm and stripped.startswith("scope"):
                scope_stack.append(sm.group("scope"))
                continue
            if stripped == "end" and scope_stack:
                scope_stack.pop()
                continue
            rm = PHOENIX_ROUTE_RE.match(line)
            if rm:
                verb = rm.group("verb").upper()
                path = rm.group("path")
                full = "".join(scope_stack) + path
                routes.append((verb, full))
    return routes


# ── Audit core ──────────────────────────────────────────────────────────────


@dataclass
class ModuleReport:
    module: str
    fe_endpoints: list[tuple[str, str]] = field(default_factory=list)
    be_endpoints: list[tuple[str, str]] = field(default_factory=list)
    matched: list[tuple[str, str]] = field(default_factory=list)
    fe_only: list[tuple[str, str]] = field(default_factory=list)
    be_only: list[tuple[str, str]] = field(default_factory=list)
    backend_missing: bool = False

    def to_dict(self) -> dict:
        def pairs(xs):
            return [{"method": v, "path": p} for v, p in xs]

        return {
            "module": self.module,
            "fe_endpoints": pairs(self.fe_endpoints),
            "be_endpoints": pairs(self.be_endpoints),
            "matched": pairs(self.matched),
            "fe_only": pairs(self.fe_only),
            "be_only": pairs(self.be_only),
            "backend_missing": self.backend_missing,
        }


def audit_module(name: str, cfg: dict) -> ModuleReport:
    report = ModuleReport(module=name)
    fe_prefix = cfg["fe_prefix"]
    # Some FE clients still use the legacy /api/v1/mod/<name> URL because
    # the gateway rewrites that to /api/v1/<name> before it hits the
    # backend. We canonicalise both sides by projecting onto the backend
    # prefix during comparison.
    backend_prefix = cfg.get("backend_prefix", fe_prefix)

    # ── Frontend ─────────────────────────────────────────────────────────
    for fname in cfg["fe_files"]:
        file_path = FRONTEND_API_DIR / fname
        if not file_path.exists():
            continue
        for verb, url in extract_frontend(file_path):
            # FE calls are relative to the client prefix. The `base.ts`
            # factory prepends it before firing the request; swap it for
            # the backend prefix so the route format matches.
            full = backend_prefix + url
            report.fe_endpoints.append((verb, normalise_path(full)))

    # Dedup.
    report.fe_endpoints = sorted(set(report.fe_endpoints))

    # ── Backend ──────────────────────────────────────────────────────────
    backend_dir = WORKSPACE / cfg["backend"]
    if not backend_dir.exists():
        report.backend_missing = True
        return report

    kind = cfg["kind"]
    if kind == "python":
        routes = collect_python_routes(backend_dir, cfg.get("backend_prefix", ""))
    elif kind == "go":
        routes = collect_go_routes(backend_dir)
    elif kind == "elixir":
        routes = collect_elixir_routes(backend_dir)
    else:
        routes = []

    # Health / metrics endpoints are infrastructure probes, not part of
    # the API contract the frontend cares about — drop them before the
    # diff so the ``BE-only`` column stays readable.
    def is_probe(path: str) -> bool:
        p = path.split("?", 1)[0]
        return (
            p == "/health"
            or p.startswith("/health/")
            or p == "/metrics"
            or p.startswith("/metrics/")
        )

    normalised = sorted(
        {(v, normalise_path(p)) for v, p in routes if not is_probe(p)}
    )
    report.be_endpoints = normalised

    fe_set = set(report.fe_endpoints)
    be_set = set(report.be_endpoints)

    report.matched = sorted(fe_set & be_set)
    report.fe_only = sorted(fe_set - be_set)
    report.be_only = sorted(be_set - fe_set)

    return report


# ── Output renderers ────────────────────────────────────────────────────────


def render_markdown(reports: list[ModuleReport]) -> str:
    today = date.today().isoformat()
    out = [f"# Frontend ↔ Backend Contract Audit — {today}", ""]
    out.append("## Summary")
    out.append("")
    out.append("| Module | FE endpoints | BE routes | Match | FE only | BE only | Backend |")
    out.append("|---|---:|---:|---:|---:|---:|---|")

    for r in sorted(reports, key=lambda r: r.module):
        be_status = "missing" if r.backend_missing else "present"
        out.append(
            f"| {r.module} | {len(r.fe_endpoints)} | {len(r.be_endpoints)} | "
            f"{len(r.matched)} | {len(r.fe_only)} | {len(r.be_only)} | {be_status} |"
        )

    out.append("")
    out.append("## Mismatches by module")
    out.append("")

    any_mismatch = False
    for r in sorted(reports, key=lambda r: r.module):
        if not r.fe_only and not r.be_only and not r.backend_missing:
            continue
        any_mismatch = True
        out.append(f"### {r.module}")
        out.append("")
        if r.backend_missing:
            out.append(f"Backend directory missing on disk. FE ships {len(r.fe_endpoints)} endpoints with no counterpart.")
            out.append("")
            for verb, path in r.fe_endpoints:
                out.append(f"- FE: `{verb} {path}`")
            out.append("")
            continue
        if r.fe_only:
            out.append("**Frontend-only (calls endpoints that don't exist):**")
            out.append("")
            for verb, path in r.fe_only:
                out.append(f"- `{verb} {path}`")
            out.append("")
        if r.be_only:
            out.append("**Backend-only (not consumed yet):**")
            out.append("")
            for verb, path in r.be_only:
                out.append(f"- `{verb} {path}`")
            out.append("")

    if not any_mismatch:
        out.append("No mismatches detected. Every frontend call hits a defined backend route.")
        out.append("")

    out.append("## Recommendation")
    out.append("")
    top_drift = sorted(
        reports,
        key=lambda r: (len(r.fe_only) * 2 + len(r.be_only)),
        reverse=True,
    )[:3]
    if top_drift and any(len(r.fe_only) or len(r.be_only) for r in top_drift):
        out.append("Address the three highest-drift modules first:")
        out.append("")
        for r in top_drift:
            if not r.fe_only and not r.be_only:
                continue
            out.append(
                f"- `{r.module}`: {len(r.fe_only)} FE-only, {len(r.be_only)} BE-only"
            )
    else:
        out.append("Keep the audit wired into CI so any new drift fails the PR that introduced it.")

    return "\n".join(out) + "\n"


def render_json(reports: list[ModuleReport]) -> str:
    payload = {
        "generated_at": date.today().isoformat(),
        "modules": [r.to_dict() for r in sorted(reports, key=lambda r: r.module)],
        "totals": {
            "fe_endpoints": sum(len(r.fe_endpoints) for r in reports),
            "be_endpoints": sum(len(r.be_endpoints) for r in reports),
            "matched": sum(len(r.matched) for r in reports),
            "fe_only": sum(len(r.fe_only) for r in reports),
            "be_only": sum(len(r.be_only) for r in reports),
        },
    }
    return json.dumps(payload, indent=2, ensure_ascii=False)


# ── CLI ─────────────────────────────────────────────────────────────────────


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Audit FE↔BE API contract drift.")
    parser.add_argument("--module", help="Limit audit to one module name")
    parser.add_argument("--strict", action="store_true", help="Exit 1 if any mismatch")
    parser.add_argument("--json", action="store_true", help="Print JSON to stdout")
    parser.add_argument(
        "--markdown-out",
        default=str(WORKSPACE / "CONTRACT_AUDIT.md"),
        help="Where to write the markdown summary",
    )
    args = parser.parse_args(argv)

    selected = MODULES
    if args.module:
        if args.module not in MODULES:
            print(f"unknown module: {args.module}", file=sys.stderr)
            print(f"available: {', '.join(sorted(MODULES))}", file=sys.stderr)
            return 2
        selected = {args.module: MODULES[args.module]}

    reports = [audit_module(name, cfg) for name, cfg in selected.items()]

    if args.json:
        print(render_json(reports))
    else:
        md = render_markdown(reports)
        Path(args.markdown_out).write_text(md, encoding="utf-8")
        json_path = Path(args.markdown_out).with_suffix(".audit-report.json")
        json_path.write_text(render_json(reports), encoding="utf-8")
        # Console-friendly line per module.
        print(f"audit → {args.markdown_out}")
        for r in sorted(reports, key=lambda r: r.module):
            flag = ""
            if r.fe_only or r.be_only:
                flag = f" (fe_only={len(r.fe_only)}, be_only={len(r.be_only)})"
            if r.backend_missing:
                flag = " (backend missing)"
            print(
                f"  {r.module:20s} fe={len(r.fe_endpoints):3d} be={len(r.be_endpoints):3d} "
                f"match={len(r.matched):3d}{flag}"
            )

    if args.strict:
        for r in reports:
            if r.fe_only or r.backend_missing:
                return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
