# APF v1.0 — candidate freeze

## APF01 Charter
Independent Puerto Rico catalog; data-first, source-second presentation. No official endorsement. Spanish primary, English secondary.
## APF02 Architecture
One modular application, one canonical registry; catalog, geography, access and sources are projections, not duplicate stores. `prdc/` code; `registry/` contracts/seeds; `standards/` policy; `specifications/` design; `tests/` qualification; `reports/` evidence. Future discovery, UI and publication packages are deferred until justified.
## APF03 Parameters
See registry/contracts/parameters.json; counts are design targets, not discovered holdings.
## APF04 Taxonomy
120 subject seeds, 12 families. Preserve codes; allow multiple subjects. Bilingual definitions and semantic deduplication remain open.
## APF05 Category hierarchy
Subject > data concept > asset > version > distribution > direct link. Asset kind, geography, time and format are orthogonal facets; category vocabulary below subject remains open.
## APF06 Metadata
See metadata.json. Required unknown values are explicit, never manufactured. Field-level bilingual descriptions and schemas remain open.
## APF07 Relationships
Institution roles share identity. Work and version separate; version has distributions, distributions have assets and endpoints. Geography/subjects many-to-many. Source assertions retain original semantics. Logical registry contracts distinguish roles/views from canonical owners; complete cardinality enforcement remains open.
## APF08 Geography
78 municipal planning seeds, 40 categories, 15 discovery passes. 3120 cells and 1170 pass assignments; not evidence of official identities or actual holdings. Shared files linked once to multiple municipalities. Official geographic identities and boundaries pending.
## APF09 Access
See standards/prvds/access.json. Separate directness, scope, stability, authorization, verification. Specific download page fallback; never advertise partial query as complete. No credentials or access bypass. Legacy numeric labels retired; semantic migration pending.
## APF10 Presentation
Default search and browse by data/subject, geography, time, format; source displayed as provenance and optional facet. Asset card includes title, geographic/temporal coverage, format, direct action, verification, authority, rights. No source-first default.
## APF11 Verification
Discovery candidates not verified records. Link metadata verification separate from file-content and fitness verification. All publication blocked until evidence, rights, identity, applicable quality and version gates pass. No fabricated receipts.
## APF12 Discovery
Bounded scope and independent denominators. Unknown or zero denominator not measurable. Recursive discovery with deduplication, rate limits and recorded exclusions. No bulk acquisition by default.
## APF13 Storage/performance
Git code/specifications/seeds; SQLite metadata, FTS candidate; content-addressed external archive selectively. 1M/10M association benchmarks proposed, not measured. No arbitrary latency claims before benchmarking.
## APF14 Qualification
Single gate inventory in reports/gates.json. Local prototype controls distinct from full product and durability gates. All untested gates OPEN. No persistent execution available in this session.
## APF15 Roadmap
Foundation → specialized contracts → data category/metadata closure → metadata-only discovery/direct link resolution → qualified search and export → durable maintenance → bounded public release. No bulk acquisition needed for metadata catalog.

Candidate freeze only; implementation and scientific qualification remain incomplete.
