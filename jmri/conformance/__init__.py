"""jMRI conformance suite.

A portable test fixture any MCP retrieval server can run against itself
to validate jMRI v1.0 compliance.

Public API:
    Adapter           — protocol the runner calls into (any jMRI client works)
    ConformanceCase   — a single named assertion against a server
    ConformanceResult — a case's outcome (pass/fail/skip + evidence)
    ConformanceReport — aggregated outcome of a full run
    run_conformance() — execute the suite against an adapter, return a report
    CORE_CASES        — built-in jMRI-Core MUSTs
    FULL_CASES        — built-in jMRI-Full SHOULDs

Usage::

    from jmri.client import MRIClient
    from jmri.conformance import Adapter, run_conformance

    client = MRIClient()  # or your own jMRI server adapter
    adapter = Adapter.from_mri_client(client, repo="owner/repo")
    report = run_conformance(adapter)
    print(report.to_markdown())
"""

from .adapter import Adapter, AdapterError
from .cases import CORE_CASES, FULL_CASES, ConformanceCase
from .report import ConformanceReport, ConformanceResult
from .runner import run_conformance

__all__ = [
    "Adapter",
    "AdapterError",
    "CORE_CASES",
    "FULL_CASES",
    "ConformanceCase",
    "ConformanceReport",
    "ConformanceResult",
    "run_conformance",
]
