"""``python -m jmri.conformance`` — CLI for the conformance suite.

Wraps an :class:`jmri.client.MRIClient` as an :class:`Adapter` and runs
the suite. Output is markdown to stdout by default; ``--json``
writes a machine-readable payload for CI / dashboards.
"""

from __future__ import annotations

import argparse
import shlex
import sys
from pathlib import Path
from typing import Optional


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m jmri.conformance",
        description="Run the jMRI conformance suite against a jMRI-compliant MCP server.",
    )
    parser.add_argument(
        "--repo", required=True,
        help="Repo identifier the suite should target (must already be indexed).",
    )
    parser.add_argument(
        "--server-cmd",
        default="jcodemunch-mcp",
        help="Command to launch the MCP server (default: jcodemunch-mcp). "
        "Quote multi-arg invocations: --server-cmd 'uvx jcodemunch-mcp'.",
    )
    parser.add_argument(
        "--domain",
        choices=["code", "docs"],
        default="code",
        help="Which client domain to use (default: code).",
    )
    parser.add_argument(
        "--known-symbol-id",
        default=None,
        help="Optional symbol id to use for retrieve() tests; if omitted, "
        "the runner derives one from a generic search query.",
    )
    parser.add_argument(
        "--server-label",
        default="",
        help="Human label for the report (e.g. 'jcodemunch-mcp 1.90.0').",
    )
    parser.add_argument(
        "--core-only",
        action="store_true",
        help="Skip jMRI-Full SHOULD cases.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON instead of markdown.",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Write report to this path instead of stdout.",
    )
    args = parser.parse_args(argv)

    from ..client import MRIClient
    from .adapter import Adapter
    from .runner import run_conformance

    server_cmd = shlex.split(args.server_cmd)
    if args.domain == "code":
        client = MRIClient(code_server_cmd=server_cmd)
    else:
        client = MRIClient(doc_server_cmd=server_cmd)

    adapter = Adapter.from_mri_client(
        client,
        repo=args.repo,
        domain=args.domain,
        known_symbol_id=args.known_symbol_id,
        server_label=args.server_label or " ".join(server_cmd),
    )

    report = run_conformance(adapter, include_full=not args.core_only)

    payload = report.to_json() if args.json else report.to_markdown()
    if args.out:
        args.out.write_text(payload, encoding="utf-8")
        print(f"wrote report -> {args.out}", file=sys.stderr)
    else:
        sys.stdout.write(payload)
        sys.stdout.write("\n" if not payload.endswith("\n") else "")

    return 0 if report.core_compliant else 1


if __name__ == "__main__":
    raise SystemExit(main())
