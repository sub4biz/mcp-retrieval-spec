# Changelog

## [1.1.1] — 2026-05-09 — Zenodo deposit trigger (no spec changes)

Re-release with no spec or SDK changes. Sole purpose: trigger
Zenodo's GitHub-release webhook now that the per-repo toggle is
enabled at https://zenodo.org/account/settings/github/. The DOI
minted by this release becomes the canonical citation for the
spec at jMRI v1.1.

Spec text remains at v1.0.0; the SDK surface is unchanged from
v1.1.0. CITATION.cff version bumped only for cff/release parity.

## [1.1.0] — 2026-05-09 — Conformance suite + CITATION.cff (Zenodo deposit)

Spec text unchanged at v1.0.0; the bump reflects the new SDK surface
(`jmri.conformance` subpackage + `jmri-conformance` console script).

### Added
- **`jmri.conformance` subpackage** — a portable test fixture any MCP
  retrieval server can run against itself to validate jMRI v1.0
  compliance. Two tiers (Core MUST / Full SHOULD), 14 named cases
  pinned to specific spec invariants. Pure Python; an Adapter
  protocol decouples the suite from any specific transport so
  non-MCP servers can run it too.
- **`python -m jmri.conformance`** CLI / **`jmri-conformance`** console
  script — wraps an `MRIClient` against a target server and prints a
  markdown or JSON report. Exit code 0 on Core-compliant runs (with
  or without Full gaps); 1 otherwise.
- **`CITATION.cff`** — Citation File Format metadata for Zenodo
  deposit. Once deposited, the DOI gets cross-linked from this
  repo's README + each reference-implementation's README so future
  citations target the *spec*, not vendor methodology papers.

### Self-reporting policy
The conformance suite is for self-assessment, not adversarial
benchmarking. Maintainers run it against their own servers and
publish the resulting report. We don't run conformance against
competitors and publish — that's the wrong shape for a
standards-bearer position. Third parties claiming jMRI compliance
should run the suite, save the report, and link it from their own
README.

## [1.0.1] — 2026-04-13

### Documentation
- Updated README reference implementations table: jCodeMunch 70+ languages / 1,500+ stars, jDocMunch 135+ stars
- Added jDataMunch as third reference implementation (tabular data: CSV, Excel, Parquet, JSONL)
- Removed stale token counter snapshot (was pinned to March 3 figure)

## [1.0.0] — 2026-03-09

Initial publication.

- Defined four core jMRI methods: `discover`, `search`, `retrieve`, `metadata`
- Defined `_meta` response envelope with required and optional fields
- Defined stable identifier formats for code symbols and doc sections
- Defined jMRI-Core and jMRI-Full compliance levels
- Published reference implementations: jCodeMunch (code) and jDocMunch (docs)
- Apache 2.0 license
