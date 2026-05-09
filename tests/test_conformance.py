"""Unit tests for the jmri.conformance suite — runner, cases, report."""

from __future__ import annotations

import json
from typing import Any

import pytest

from jmri.conformance import (
    Adapter,
    AdapterError,
    CORE_CASES,
    FULL_CASES,
    ConformanceCase,
    ConformanceReport,
    run_conformance,
)
from jmri.conformance.cases import CaseOutcome


# ---------------------------------------------------------------------------
# Mock-adapter helpers — build a fake server that returns scripted shapes.
# ---------------------------------------------------------------------------

def _good_full_adapter() -> Adapter:
    """Adapter that satisfies every Core MUST and every Full SHOULD."""
    sources = [{"id": "owner/repo", "name": "owner/repo", "index_version": 9}]
    deterministic_ids = ["owner/repo::foo#function", "owner/repo::bar#class"]

    def _discover():
        return list(sources)

    def _search(query, **opts):
        max_results = int(opts.get("max_results", 10))
        return [
            {"id": sid, "name": sid.split("::")[-1].split("#")[0], "score": 0.9}
            for sid in deterministic_ids[:max_results]
        ]

    def _retrieve(id, **opts):
        if id == "::definitely-not-a-real-symbol::":
            return {
                "error": {"code": "ID_NOT_FOUND", "message": f"no such id: {id}"},
                "_meta": {"tokens_saved": 0, "elapsed_ms": 0.1, "retrieval_version": "1.0.0"},
            }
        return {
            "id": id,
            "source": "def foo():\n    return 42\n",
            "_meta": {
                "tokens_saved": 1234,
                "elapsed_ms": 0.5,
                "retrieval_version": "1.0.0",
                "total_tokens_saved": 12_345_678,
            },
        }

    def _metadata(id=None):
        return {
            "server": "mock-jmri",
            "version": "1.0.0",
            "_meta": {"retrieval_version": "1.0.0"},
        }

    return Adapter(
        discover=_discover,
        search=_search,
        retrieve=_retrieve,
        metadata=_metadata,
        repo="owner/repo",
        server_label="mock-good",
    )


def _broken_core_adapter() -> Adapter:
    """Adapter that fails several Core MUSTs — for negative tests."""
    def _discover():
        return []                                 # empty -> fail
    def _search(query, **opts):
        # Returns full content inline — violates "stubs only".
        return [{
            "name": "huge",
            "source": "x" * 5000,                 # >4000 chars
        }]
    def _retrieve(id, **opts):
        return "raw-string"                       # not a dict -> fail
    def _metadata(id=None):
        return None                                # not a dict -> fail
    return Adapter(
        discover=_discover,
        search=_search,
        retrieve=_retrieve,
        metadata=_metadata,
        repo="owner/repo",
        server_label="mock-broken",
    )


# ---------------------------------------------------------------------------
# Runner.
# ---------------------------------------------------------------------------

class TestRunner:
    def test_full_pass(self):
        report = run_conformance(_good_full_adapter())
        assert report.core_compliant
        assert report.full_compliant
        assert "Full compliant" in report.verdict
        assert all(r.passed for r in report.results)

    def test_core_only_skips_full(self):
        report = run_conformance(_good_full_adapter(), include_full=False)
        assert report.core_total > 0
        assert report.full_total == 0
        assert report.core_compliant
        assert "Full not assessed" in report.verdict

    def test_broken_adapter_fails_loud(self):
        report = run_conformance(_broken_core_adapter())
        assert not report.core_compliant
        assert report.core_passed < report.core_total
        assert "NOT compliant" in report.verdict

    def test_runner_traps_unhandled_exceptions(self):
        def _explode():
            raise RuntimeError("boom")
        adapter = Adapter(
            discover=_explode,
            search=lambda q, **kw: [],
            retrieve=lambda id, **kw: {"_meta": {}, "source": ""},
            metadata=lambda id=None: {},
            repo="owner/repo",
        )
        report = run_conformance(adapter)
        # discover raised — cases that depend on discover should have
        # registered failure rather than crashing the run.
        names = {r.case_name for r in report.results}
        assert "core.discover.returns_list" in names
        assert all(isinstance(r.error, (str, type(None))) for r in report.results)


# ---------------------------------------------------------------------------
# Case-level coverage. We aren't re-asserting every assertion here — just
# spot-checking the cases that have non-trivial logic.
# ---------------------------------------------------------------------------

class TestCases:
    def _run_named_case(self, adapter: Adapter, case_name: str):
        case = next(c for c in (*CORE_CASES, *FULL_CASES) if c.name == case_name)
        return case.apply(adapter)

    def test_search_stubs_only_catches_inlined_content(self):
        outcome = self._run_named_case(_broken_core_adapter(), "core.search.returns_stubs_only")
        assert not outcome.passed
        assert "full content" in (outcome.error or "")

    def test_search_max_results_cap(self):
        adapter = _good_full_adapter()
        outcome = self._run_named_case(adapter, "core.search.respects_max_results")
        assert outcome.passed

    def test_retrieve_bad_id_passes_when_error_returned(self):
        outcome = self._run_named_case(_good_full_adapter(), "core.retrieve.bad_id_returns_error")
        assert outcome.passed

    def test_full_tokens_saved_must_be_nonneg(self):
        # Fake an adapter that returns a negative tokens_saved (illegal).
        adapter = _good_full_adapter()
        original = adapter.retrieve
        def _bad_retrieve(id, **kw):
            r = original(id, **kw)
            r["_meta"]["tokens_saved"] = -42
            return r
        adapter.retrieve = _bad_retrieve
        outcome = self._run_named_case(adapter, "full.meta.tokens_saved_nonneg")
        assert not outcome.passed
        assert "non-negative" in (outcome.error or "")

    def test_search_deterministic_ids(self):
        outcome = self._run_named_case(_good_full_adapter(), "full.search.deterministic_ids")
        assert outcome.passed


# ---------------------------------------------------------------------------
# Report rendering.
# ---------------------------------------------------------------------------

class TestReport:
    def test_to_markdown_includes_verdict_and_tables(self):
        report = run_conformance(_good_full_adapter())
        md = report.to_markdown()
        assert "jMRI Conformance Report" in md
        assert report.verdict in md
        assert "Core (MUST)" in md
        assert "Full (SHOULD)" in md

    def test_to_json_payload_is_complete(self):
        report = run_conformance(_good_full_adapter())
        payload = json.loads(report.to_json())
        assert payload["spec_version"] == "1.0.0"
        assert payload["core"]["compliant"] is True
        assert payload["full"]["compliant"] is True
        assert isinstance(payload["results"], list)
        assert all("case_name" in r for r in payload["results"])

    def test_full_compliant_requires_core_compliant(self):
        # Adapter that satisfies all FULL but breaks one CORE.
        adapter = _good_full_adapter()
        original = adapter.search
        def _max_violator(q, **opts):
            # Always returns 99 results regardless of max_results — breaks
            # core.search.respects_max_results.
            return [{"id": f"sym{i}"} for i in range(99)]
        adapter.search = _max_violator
        report = run_conformance(adapter)
        assert not report.core_compliant
        assert not report.full_compliant
        assert "NOT compliant" in report.verdict
