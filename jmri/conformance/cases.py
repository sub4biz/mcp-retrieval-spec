"""Built-in jMRI conformance cases — Core (MUST) + Full (SHOULD).

Each case is a small dataclass with an ``apply(adapter)`` callable. The
runner walks the case list, calls ``apply``, and records pass/fail/skip
plus evidence and any exception message.

Cases are intentionally small and named after the spec invariant they
enforce so a failing report points the maintainer straight at the
relevant SPEC.md section.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional

from .adapter import Adapter, AdapterError


@dataclass
class ConformanceCase:
    name: str                     # dotted path: "core.discover.returns_list"
    tier: str                     # "core" | "full"
    severity: str                 # "must" | "should"
    spec_ref: str                 # human pointer: "SPEC.md §discover()"
    apply: Callable[[Adapter], "CaseOutcome"]


@dataclass
class CaseOutcome:
    passed: bool
    evidence: dict
    error: Optional[str] = None


def _ok(**evidence: Any) -> CaseOutcome:
    return CaseOutcome(passed=True, evidence=evidence)


def _fail(error: str, **evidence: Any) -> CaseOutcome:
    return CaseOutcome(passed=False, evidence=evidence, error=error)


# ---------------------------------------------------------------------------
# Helpers shared across cases.
# ---------------------------------------------------------------------------

def _resolve_known_id(adapter: Adapter) -> Optional[str]:
    """If the adapter didn't pre-set a known symbol id, derive one from
    a generic search query. Returns None if even that fails."""
    if adapter.known_symbol_id:
        return adapter.known_symbol_id
    try:
        results = adapter.search("the", max_results=1)
    except AdapterError:
        return None
    if not results:
        return None
    first = results[0]
    if isinstance(first, dict):
        return first.get("id") or first.get("symbol_id") or first.get("section_id")
    return None


def _meta_of(payload: dict) -> dict:
    return payload.get("_meta") or {}


# ---------------------------------------------------------------------------
# jMRI-Core MUSTs.
# ---------------------------------------------------------------------------

def _case_discover_returns_list(adapter: Adapter) -> CaseOutcome:
    try:
        out = adapter.discover()
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    if not isinstance(out, list):
        return _fail("discover() must return a list", got_type=type(out).__name__)
    if not out:
        return _fail("discover() returned empty list — server has no indexed sources")
    return _ok(count=len(out))


def _case_discover_required_fields(adapter: Adapter) -> CaseOutcome:
    try:
        out = adapter.discover()
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    if not out:
        return _fail("no discover() entries to inspect")
    first = out[0]
    if not isinstance(first, dict):
        return _fail("discover() entry must be a dict", got_type=type(first).__name__)
    missing = [k for k in ("id", "name") if k not in first]
    if missing:
        return _fail(f"discover() entry missing required fields: {missing}",
                     entry_keys=sorted(first.keys()))
    return _ok(sample=first)


def _case_search_returns_stubs_only(adapter: Adapter) -> CaseOutcome:
    try:
        results = adapter.search("the", max_results=3)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    if not isinstance(results, list):
        return _fail("search() must return a list", got_type=type(results).__name__)
    # Any single very-large field probably means full content was inlined.
    for r in results:
        if not isinstance(r, dict):
            continue
        for key in ("source", "content", "body", "text"):
            v = r.get(key)
            if isinstance(v, str) and len(v) > 4000:
                return _fail(
                    f"search() result includes full content under '{key}' "
                    f"({len(v)} chars). Use retrieve() for content.",
                    sample_keys=list(r.keys()),
                )
    return _ok(count=len(results))


def _case_search_required_fields(adapter: Adapter) -> CaseOutcome:
    try:
        results = adapter.search("the", max_results=1)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    if not results:
        return _ok(note="empty result set is acceptable")
    first = results[0]
    if not isinstance(first, dict):
        return _fail("search() entry must be a dict", got_type=type(first).__name__)
    if "id" not in first and "symbol_id" not in first and "section_id" not in first:
        return _fail("search() result missing stable id field",
                     entry_keys=sorted(first.keys()))
    return _ok(sample=first)


def _case_search_respects_max_results(adapter: Adapter) -> CaseOutcome:
    try:
        results = adapter.search("the", max_results=2)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    if len(results) > 2:
        return _fail(f"max_results=2 returned {len(results)} entries")
    return _ok(returned=len(results))


def _case_retrieve_returns_content(adapter: Adapter) -> CaseOutcome:
    sym_id = _resolve_known_id(adapter)
    if not sym_id:
        return _fail("could not resolve any symbol id to test retrieve()")
    try:
        out = adapter.retrieve(sym_id)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    if not isinstance(out, dict):
        return _fail("retrieve() must return a dict", got_type=type(out).__name__)
    if not any(out.get(k) for k in ("source", "content", "body", "text")):
        return _fail("retrieve() returned no recognizable content field",
                     keys=sorted(out.keys()))
    return _ok(content_field=next(k for k in ("source", "content", "body", "text") if out.get(k)))


def _case_retrieve_has_meta(adapter: Adapter) -> CaseOutcome:
    sym_id = _resolve_known_id(adapter)
    if not sym_id:
        return _fail("could not resolve any symbol id to test retrieve()")
    try:
        out = adapter.retrieve(sym_id)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    meta = _meta_of(out)
    if not meta:
        return _fail("retrieve() response missing required _meta block",
                     top_level_keys=sorted(out.keys()))
    return _ok(meta_keys=sorted(meta.keys()))


def _case_retrieve_bad_id_returns_error(adapter: Adapter) -> CaseOutcome:
    bogus_id = "::definitely-not-a-real-symbol::"
    try:
        out = adapter.retrieve(bogus_id)
    except AdapterError:
        # Adapter-level failure is acceptable here; the spec just forbids
        # raw exceptions bubbling from a compliant server. Treat as pass —
        # the underlying server rejected the id, the adapter translated
        # the response into an exception path.
        return _ok(note="adapter raised; treating as structured rejection")
    if not isinstance(out, dict):
        return _fail("retrieve(bad_id) must still return a dict", got_type=type(out).__name__)
    if "error" not in out and "errors" not in out:
        return _fail("retrieve(bad_id) returned a non-error response",
                     keys=sorted(out.keys()))
    return _ok(error=out.get("error") or out.get("errors"))


def _case_metadata_returns_dict(adapter: Adapter) -> CaseOutcome:
    try:
        out = adapter.metadata(None)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    if not isinstance(out, dict):
        return _fail("metadata() must return a dict", got_type=type(out).__name__)
    return _ok(keys=sorted(out.keys()))


# ---------------------------------------------------------------------------
# jMRI-Full SHOULDs.
# ---------------------------------------------------------------------------

def _case_meta_tokens_saved_present(adapter: Adapter) -> CaseOutcome:
    sym_id = _resolve_known_id(adapter)
    if not sym_id:
        return _fail("could not resolve any symbol id")
    try:
        out = adapter.retrieve(sym_id)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    meta = _meta_of(out)
    if "tokens_saved" not in meta:
        return _fail("Full implementations SHOULD include _meta.tokens_saved")
    return _ok(tokens_saved=meta["tokens_saved"])


def _case_meta_tokens_saved_nonneg(adapter: Adapter) -> CaseOutcome:
    sym_id = _resolve_known_id(adapter)
    if not sym_id:
        return _fail("could not resolve any symbol id")
    try:
        out = adapter.retrieve(sym_id)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    meta = _meta_of(out)
    val = meta.get("tokens_saved")
    if val is None:
        return _fail("_meta.tokens_saved missing")
    if not isinstance(val, (int, float)) or val < 0:
        return _fail("_meta.tokens_saved must be a non-negative number",
                     value=val, value_type=type(val).__name__)
    return _ok(tokens_saved=val)


def _case_meta_elapsed_ms_present(adapter: Adapter) -> CaseOutcome:
    sym_id = _resolve_known_id(adapter)
    if not sym_id:
        return _fail("could not resolve any symbol id")
    try:
        out = adapter.retrieve(sym_id)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    meta = _meta_of(out)
    candidate = meta.get("elapsed_ms") or meta.get("timing_ms")
    if candidate is None:
        return _fail("Full implementations SHOULD include _meta.elapsed_ms or _meta.timing_ms")
    return _ok(elapsed_ms=candidate)


def _case_meta_retrieval_version_present(adapter: Adapter) -> CaseOutcome:
    sym_id = _resolve_known_id(adapter)
    if not sym_id:
        return _fail("could not resolve any symbol id")
    try:
        out = adapter.retrieve(sym_id)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    meta = _meta_of(out)
    if "retrieval_version" not in meta:
        return _fail("Full implementations SHOULD advertise _meta.retrieval_version (jMRI spec version)")
    return _ok(retrieval_version=meta["retrieval_version"])


def _case_search_deterministic_ids(adapter: Adapter) -> CaseOutcome:
    """Same query twice -> same id list. IDs MUST be stable (SPEC.md §Identifier Formats)."""
    try:
        first = adapter.search("the", max_results=5)
        second = adapter.search("the", max_results=5)
    except AdapterError as e:
        return _fail(f"adapter error: {e}")
    if len(first) != len(second):
        return _fail("repeated search returned different result counts",
                     first=len(first), second=len(second))
    extract = lambda r: (r.get("id") or r.get("symbol_id") or r.get("section_id")) if isinstance(r, dict) else None
    first_ids = [extract(r) for r in first]
    second_ids = [extract(r) for r in second]
    if first_ids != second_ids:
        return _fail("repeated search returned different id sequence",
                     first=first_ids, second=second_ids)
    return _ok(count=len(first_ids))


# ---------------------------------------------------------------------------
# Built-in case lists.
# ---------------------------------------------------------------------------

CORE_CASES: list[ConformanceCase] = [
    ConformanceCase(
        name="core.discover.returns_list",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §discover()",
        apply=_case_discover_returns_list,
    ),
    ConformanceCase(
        name="core.discover.required_fields",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §discover()",
        apply=_case_discover_required_fields,
    ),
    ConformanceCase(
        name="core.search.returns_stubs_only",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §search() (Results MUST NOT include full source content)",
        apply=_case_search_returns_stubs_only,
    ),
    ConformanceCase(
        name="core.search.required_fields",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §search() (Results MUST include a stable id)",
        apply=_case_search_required_fields,
    ),
    ConformanceCase(
        name="core.search.respects_max_results",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §search()",
        apply=_case_search_respects_max_results,
    ),
    ConformanceCase(
        name="core.retrieve.returns_content",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §retrieve()",
        apply=_case_retrieve_returns_content,
    ),
    ConformanceCase(
        name="core.retrieve.has_meta",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §Response Envelope",
        apply=_case_retrieve_has_meta,
    ),
    ConformanceCase(
        name="core.retrieve.bad_id_returns_error",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §Error Handling",
        apply=_case_retrieve_bad_id_returns_error,
    ),
    ConformanceCase(
        name="core.metadata.returns_dict",
        tier="core",
        severity="must",
        spec_ref="SPEC.md §metadata()",
        apply=_case_metadata_returns_dict,
    ),
]


FULL_CASES: list[ConformanceCase] = [
    ConformanceCase(
        name="full.meta.tokens_saved_present",
        tier="full",
        severity="should",
        spec_ref="SPEC.md §Response Envelope (Optional Fields)",
        apply=_case_meta_tokens_saved_present,
    ),
    ConformanceCase(
        name="full.meta.tokens_saved_nonneg",
        tier="full",
        severity="should",
        spec_ref="SPEC.md §Token Savings Calculation",
        apply=_case_meta_tokens_saved_nonneg,
    ),
    ConformanceCase(
        name="full.meta.elapsed_ms_present",
        tier="full",
        severity="should",
        spec_ref="SPEC.md §Response Envelope (Optional Fields)",
        apply=_case_meta_elapsed_ms_present,
    ),
    ConformanceCase(
        name="full.meta.retrieval_version_present",
        tier="full",
        severity="should",
        spec_ref="SPEC.md §Versioning",
        apply=_case_meta_retrieval_version_present,
    ),
    ConformanceCase(
        name="full.search.deterministic_ids",
        tier="full",
        severity="should",
        spec_ref="SPEC.md §Identifier Formats",
        apply=_case_search_deterministic_ids,
    ),
]
