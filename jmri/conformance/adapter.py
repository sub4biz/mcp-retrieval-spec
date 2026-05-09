"""Adapter abstraction for the conformance runner.

The runner doesn't talk MCP directly — it talks to an Adapter, which
is a thin protocol covering the four jMRI operations. That keeps the
suite testable (mock adapters in unit tests) and decouples conformance
from any specific transport.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Optional


class AdapterError(Exception):
    """Raised when the adapter can't reach the underlying server.

    Distinct from a structured jMRI error returned by the server itself.
    Adapter errors usually mean transport / config trouble — wrong server
    command, broken stdio, missing repo, etc.
    """


@dataclass
class Adapter:
    """Thin protocol the runner calls into.

    Each field is a callable matching the jMRI operation shape. Build one
    via :meth:`from_mri_client` for the standard MCP-stdio path, or
    construct directly with arbitrary callables for testing.
    """

    discover: Callable[[], list[dict]]
    search:   Callable[..., list[dict]]
    retrieve: Callable[..., dict]
    metadata: Callable[[Optional[str]], dict]
    repo: str
    """Repository the suite should target. Must already be indexed by
    the server under test."""

    known_symbol_id: Optional[str] = None
    """If set, used directly for retrieve() tests. If omitted, the runner
    derives a candidate from the first search() result."""

    server_label: str = ""
    """Human label for the report (e.g. ``jcodemunch-mcp 1.90.0``)."""

    @classmethod
    def from_mri_client(
        cls,
        client: Any,
        *,
        repo: str,
        domain: str = "code",
        known_symbol_id: Optional[str] = None,
        server_label: str = "",
    ) -> "Adapter":
        """Wrap an :class:`jmri.client.MRIClient` as an :class:`Adapter`.

        The client's optional kwargs (``domain``, ``max_results``, etc.) are
        injected as defaults; the runner passes only the args its cases
        require.
        """
        def _discover() -> list[dict]:
            try:
                return client.discover(domain=domain)
            except Exception as e:
                raise AdapterError(f"discover failed: {e}") from e

        def _search(query: str, **opts: Any) -> list[dict]:
            try:
                return client.search(query, repo=repo, domain=domain, **opts)
            except Exception as e:
                raise AdapterError(f"search failed: {e}") from e

        def _retrieve(id: str, **opts: Any) -> dict:
            try:
                return client.retrieve(id, repo=repo, domain=domain, **opts)
            except Exception as e:
                raise AdapterError(f"retrieve failed: {e}") from e

        def _metadata(id: Optional[str] = None) -> dict:
            try:
                return client.metadata(id=id, repo=repo, domain=domain)
            except AttributeError:
                # Older clients may not implement metadata; surface so
                # the case can register a structured failure rather than
                # crashing the run.
                raise AdapterError("client has no metadata() method")
            except Exception as e:
                raise AdapterError(f"metadata failed: {e}") from e

        return cls(
            discover=_discover,
            search=_search,
            retrieve=_retrieve,
            metadata=_metadata,
            repo=repo,
            known_symbol_id=known_symbol_id,
            server_label=server_label,
        )
