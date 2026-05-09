"""Conformance runner — walks the case list, collects results."""

from __future__ import annotations

import time
from typing import Iterable, Optional

from .adapter import Adapter
from .cases import CORE_CASES, FULL_CASES, CaseOutcome, ConformanceCase
from .report import ConformanceReport, ConformanceResult


def run_conformance(
    adapter: Adapter,
    *,
    cases: Optional[Iterable[ConformanceCase]] = None,
    include_full: bool = True,
) -> ConformanceReport:
    """Execute the conformance suite against an adapter.

    Args:
        adapter: Test target. Caller is responsible for ensuring the
            referenced repo is indexed before the run starts.
        cases: Override the built-in case list (e.g. for partial runs).
        include_full: If True (default), run jMRI-Full SHOULD cases too.

    Returns:
        :class:`ConformanceReport` with per-case results, tier summary,
        and overall verdict.
    """
    if cases is None:
        case_list = list(CORE_CASES)
        if include_full:
            case_list.extend(FULL_CASES)
    else:
        case_list = list(cases)

    results: list[ConformanceResult] = []
    started = time.perf_counter()
    for case in case_list:
        t0 = time.perf_counter()
        try:
            outcome = case.apply(adapter)
        except Exception as e:
            outcome = CaseOutcome(
                passed=False,
                evidence={"exception": e.__class__.__name__},
                error=f"case raised unhandled exception: {e}",
            )
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        results.append(ConformanceResult(
            case_name=case.name,
            tier=case.tier,
            severity=case.severity,
            spec_ref=case.spec_ref,
            passed=outcome.passed,
            evidence=outcome.evidence,
            error=outcome.error,
            elapsed_ms=round(elapsed_ms, 1),
        ))
    total_ms = (time.perf_counter() - started) * 1000.0

    return ConformanceReport(
        results=results,
        adapter_repo=adapter.repo,
        server_label=adapter.server_label or "(unspecified)",
        total_ms=round(total_ms, 1),
    )
