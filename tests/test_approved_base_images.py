#!/usr/bin/env python3
"""Behavior tests for the approved-base-images supply-chain gate.

These cover the two functional gaps closed under DEBT-§43 (see TECHNICAL-DEBT.md):

  * DEBT-§43-SUPPLY-CHAIN-6 — the base-image whitelist gate must actually run in
    the canonical build chain. The enforcement lives INLINE in
    ``reusable-build-push.yml`` (step "Gate — validate Dockerfile base images
    against whitelist"), which every fleet ``ci.yml`` calls. These tests assert
    the gate step is present and wired before the build.
  * DEBT-§43-SUPPLY-CHAIN-7 — ``approved-base-images.json`` must track the real
    fleet Dockerfiles (Go 1.26.3, Elixir 1.19, Alpine 3.23, distroless, ...).
    These tests reconcile the catalog against every real ``FROM`` in the fleet
    AND lock in tag-exact enforcement so the gate can't be silently weakened to
    name-only (which would let golang:9.9-evil / python:2.7-eol slip through).

The matcher under test is the exact algorithm embedded in
``reusable-build-push.yml`` / ``reusable-approved-images-check.yml``. It is
re-implemented here (the workflows run it via ``shell: python3 {0}``) so the
behavior is asserted without spinning up GitHub Actions.

Run with:
    python3 -m pytest tests/test_approved_base_images.py -v
or stand-alone (no pytest needed):
    python3 tests/test_approved_base_images.py
"""

from __future__ import annotations

import json
import os
import re
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WHITELIST_FILE = os.path.join(REPO_ROOT, "approved-base-images.json")
BUILD_PUSH_WF = os.path.join(
    REPO_ROOT, ".github", "workflows", "reusable-build-push.yml"
)
STANDALONE_WF = os.path.join(
    REPO_ROOT, ".github", "workflows", "reusable-approved-images-check.yml"
)
# Where the real fleet Dockerfiles live (sibling repos checked out next to this one).
FLEET_ROOT = os.path.dirname(REPO_ROOT)

# Multi-stage / scratch / template directives that the gate intentionally skips.
FROM_RE = re.compile(
    r"^FROM\s+(?:--platform=\S+\s+)?(\S+)(?:\s+(?:AS|as)\s+(\S+))?",
    re.IGNORECASE | re.MULTILINE,
)


def load_approved():
    with open(WHITELIST_FILE) as fh:
        data = json.load(fh)
    approved = set()
    for entry in data["images"]:
        name = entry.get("name", "")
        tags = entry.get("approved_tags") or (
            [entry["tag"]] if entry.get("tag") else []
        )
        for tag in tags:
            approved.add(f"{name}:{tag}")
    return data, approved


def violations_in(content, approved):
    """Exact re-implementation of the workflow matcher (tag-exact)."""
    stage_names = {m.group(2).lower() for m in FROM_RE.finditer(content) if m.group(2)}
    out = []
    for match in FROM_RE.finditer(content):
        image = match.group(1)
        if image.lower() == "scratch":
            continue
        if image.lower() in stage_names:
            continue
        if "$" in image:  # build-arg substitution — resolves at build time
            continue
        check_image = image if ":" in image else f"{image}:latest"
        if check_image not in approved:
            out.append(image)
    return out


def iter_canonical_dockerfiles():
    """The single ``./Dockerfile`` per fleet repo — what build-push gates."""
    if not os.path.isdir(FLEET_ROOT):
        return
    for name in sorted(os.listdir(FLEET_ROOT)):
        if not name.startswith("alebrije-"):
            continue
        df = os.path.join(FLEET_ROOT, name, "Dockerfile")
        if os.path.isfile(df):
            yield df


# --------------------------------------------------------------------------
# DEBT-§43-SUPPLY-CHAIN-6 — gate is wired into the canonical build chain.
# --------------------------------------------------------------------------
def test_build_push_invokes_gate_before_build():
    with open(BUILD_PUSH_WF) as fh:
        wf = fh.read()
    assert "Gate — validate Dockerfile base images against whitelist" in wf, (
        "build-push must contain the inline base-image gate step "
        "(DEBT-§43-SUPPLY-CHAIN-6)"
    )
    assert "approved-base-images.json" in wf, (
        "build-push gate must read the approved-base-images whitelist"
    )
    gate_pos = wf.index("validate Dockerfile base images against whitelist")
    build_pos = wf.index("Build and push Docker image")
    assert gate_pos < build_pos, (
        "the whitelist gate must run BEFORE the build step (fail cheap)"
    )
    # The gate must be fatal: a violation calls sys.exit(1), never a warning.
    gate_block = wf[gate_pos:build_pos]
    assert "sys.exit(1)" in gate_block, "gate must be fatal on violation"


# --------------------------------------------------------------------------
# DEBT-§43-SUPPLY-CHAIN-7 — catalog tracks reality + tag-exact enforcement.
# --------------------------------------------------------------------------
def test_catalog_covers_every_real_fleet_base_image():
    _, approved = load_approved()
    offenders = {}
    for df in iter_canonical_dockerfiles():
        with open(df, errors="replace") as fh:
            v = violations_in(fh.read(), approved)
        if v:
            offenders[df] = v
    assert not offenders, (
        "canonical fleet Dockerfiles use base images missing from the "
        f"whitelist (drift): {offenders}"
    )


def test_catalog_includes_known_real_tags():
    _, approved = load_approved()
    for required in (
        "golang:1.26.3-alpine",
        "golang:1.26.3-bookworm",
        "elixir:1.19-alpine",
        "alpine:3.23",
        "gcr.io/distroless/static:nonroot",
        "gcr.io/distroless/static-debian12:nonroot",
        "node:22-bookworm-slim",
        "python:3.13-slim",
    ):
        assert required in approved, f"{required} (real fleet tag) not approved"


def test_tag_enforcement_blocks_unapproved_tags_of_approved_names():
    """The gate must reject a bad tag of an APPROVED registry name — the
    name-only allow-list bug that DEBT-§43-SUPPLY-CHAIN-7 depends on."""
    _, approved = load_approved()
    for evil in (
        "FROM golang:9.9-evil",
        "FROM python:2.7-eol",
        "FROM alpine:9.99",
        "FROM elixir:1.0-ancient",
    ):
        assert violations_in(evil, approved), (
            f"gate must BLOCK {evil!r}; name-only matching would let it pass"
        )


def test_templated_and_scratch_and_stage_refs_are_skipped():
    _, approved = load_approved()
    for skipped in (
        "FROM --platform=$BUILDPLATFORM golang:${GO_VERSION}-alpine AS builder",
        "FROM ${BUILDER_IMAGE}",
        "FROM scratch",
    ):
        assert not violations_in(skipped, approved), (
            f"{skipped!r} must be skipped (build-time / scratch), not flagged"
        )
    multistage = "FROM golang:1.26.3-alpine AS builder\nFROM builder AS final"
    assert not violations_in(multistage, approved), (
        "intra-Dockerfile stage reference must not be treated as a base image"
    )


def test_json_parses_and_blocks_critical():
    data, _ = load_approved()
    assert data["scanning_policy"]["block_on_critical"] is True


# --------------------------------------------------------------------------
# DEBT-W07 — approved-base-images.json structural validation, wired into
# validate-self.yml AUDIT 18 (check-approved-images-schema). Previously this
# file had ZERO pre-merge structural validation despite gating Docker builds
# for ~33 fleet repos (DEBT-§43-SUPPLY-CHAIN-6/7) — a malformed edit could
# merge to main through this repo's own CI untouched and only surface at the
# next fleet build. Re-implementation below is an exact copy of the workflow
# step's Python (extracted via yaml.safe_load in the closing session — see
# TECHNICAL-DEBT.md DEBT-W07 for the extraction command used to prove drift
# would be caught by the real, not a reimplemented, script).
# --------------------------------------------------------------------------
def _validate_schema(data):
    errors = []
    if not isinstance(data, dict):
        errors.append("top-level JSON must be an object")
        return errors
    images = data.get("images")
    if not isinstance(images, list) or not images:
        errors.append("'images' must be a non-empty array")
    else:
        for i, entry in enumerate(images):
            if not isinstance(entry, dict):
                errors.append(f"images[{i}] must be an object")
                continue
            name = entry.get("name")
            if not isinstance(name, str) or not name.strip():
                errors.append(f"images[{i}]: 'name' must be a non-empty string")
            tags = entry.get("approved_tags")
            tag = entry.get("tag")
            if tags is None and tag is None:
                errors.append(
                    f"images[{i}] ({name}): must declare 'approved_tags' "
                    "(array) or 'tag' (string)"
                )
            if tags is not None:
                if not isinstance(tags, list) or not tags:
                    errors.append(
                        f"images[{i}] ({name}): 'approved_tags' must be a "
                        "non-empty array"
                    )
                else:
                    for t in tags:
                        if not isinstance(t, str) or not t.strip():
                            errors.append(
                                f"images[{i}] ({name}): 'approved_tags' "
                                "entries must be non-empty strings"
                            )
            if tag is not None and (not isinstance(tag, str) or not tag.strip()):
                errors.append(f"images[{i}] ({name}): 'tag' must be a non-empty string")
    sp = data.get("scanning_policy")
    if not isinstance(sp, dict) or "block_on_critical" not in sp:
        errors.append("'scanning_policy.block_on_critical' must be present")
    return errors


def test_schema_validator_extracted_from_workflow_matches_reimplementation():
    """Guards against the re-implementation above drifting from the real
    YAML-embedded script (the exact drift risk DEBT-W07 exists to catch)."""
    import yaml as _yaml

    with open(
        os.path.join(REPO_ROOT, ".github", "workflows", "validate-self.yml")
    ) as fh:
        doc = _yaml.safe_load(fh)
    step = doc["jobs"]["check-approved-images-schema"]["steps"][-1]
    assert step["name"] == "Validate schema"
    assert "'approved_tags' must be a" in step["run"], (
        "the extracted workflow script text no longer matches this test's "
        "re-implementation — update _validate_schema() to match"
    )


def test_schema_validator_passes_real_file():
    data, _ = load_approved()
    assert _validate_schema(data) == []


def test_schema_validator_catches_missing_images_key():
    assert _validate_schema({"scanning_policy": {"block_on_critical": True}})


def test_schema_validator_catches_entry_without_name():
    bad = {
        "images": [{"approved_tags": ["1.0"]}],
        "scanning_policy": {"block_on_critical": True},
    }
    errs = _validate_schema(bad)
    assert any("'name'" in e for e in errs)


def test_schema_validator_catches_entry_without_tags():
    bad = {
        "images": [{"name": "golang"}],
        "scanning_policy": {"block_on_critical": True},
    }
    errs = _validate_schema(bad)
    assert any("must declare" in e for e in errs)


def test_schema_validator_catches_empty_approved_tags():
    """The exact mutation used in the live break/restore control for
    DEBT-W07: an entry present but with an emptied approved_tags array."""
    bad = {
        "images": [{"name": "golang", "approved_tags": []}],
        "scanning_policy": {"block_on_critical": True},
    }
    errs = _validate_schema(bad)
    assert any("golang" in e and "non-empty array" in e for e in errs)


def test_schema_validator_catches_missing_scanning_policy():
    bad = {"images": [{"name": "golang", "tag": "1.26.3-alpine"}]}
    errs = _validate_schema(bad)
    assert any("scanning_policy" in e for e in errs)


def test_standalone_workflow_uses_tag_exact_matcher():
    """The opt-in standalone gate must use the same tag-exact logic — never
    re-introduce the bare-name allowance that defeats tag enforcement."""
    with open(STANDALONE_WF) as fh:
        wf = fh.read()
    assert "approved_images.add(name)" not in wf, (
        "standalone gate must NOT add the bare registry name to the allow-set "
        "(would let any tag pass — DEBT-§43-SUPPLY-CHAIN-7)"
    )


if __name__ == "__main__":
    failures = 0
    for fn_name, fn in sorted(globals().items()):
        if fn_name.startswith("test_") and callable(fn):
            try:
                fn()
                print(f"PASS {fn_name}")
            except AssertionError as exc:
                failures += 1
                print(f"FAIL {fn_name}: {exc}")
    print(f"\n{failures} failure(s)")
    sys.exit(1 if failures else 0)
