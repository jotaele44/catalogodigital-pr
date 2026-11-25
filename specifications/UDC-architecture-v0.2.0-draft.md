# Universal Data Catalog Initiative — architecture reconciliation v0.2.0-draft

Status: PROPOSED / NOT FROZEN. Operation UDC-APF-0002. Baseline: main 92778b85504627273f1f47a64bf1eca83b98ead0; recovered candidate APF retained at specifications/baselines/APF-v1.0.md.

## Scope and invariants
Geographically neutral UDU (resource universe), UDT (taxonomy), AUCD (architecture); Puerto Rico is the initial geographic profile. Independent operation, Spanish-primary/English-secondary public interface, data-first/source-second. One modular application and canonical registry; subject catalogs are projections/configurable profiles, not new repositories by default. Metadata-first List–Link–Verify–Preserve; selective bytes, no bulk replication by default. No mandatory external catalog runtime dependency. Do not imply official endorsement.
Existing 120 subject seeds/12 families, 78 municipal seeds, 40 municipal categories, 3,120 cells, 15 discovery passes and 1,170 assignments are historical design counts, not actual holdings. Recover their machine-readable definitions before renumbering or migrating. The former 33 proposed universal domains and 74 profile candidates are not normative denominators.

## UDU: independent resource dimensions
Subject/concept; observed entity and variable; resource kind; representation and format; geographic and temporal applicability; producer/publisher/custodian/distributor; publication mechanism; processing and methodology; resolution/units; access/rights; quality/uncertainty; lifecycle; relations.
Resource kinds include datasets, series, data services, documents, imagery, multimedia, software, models, streams and composite/opaque digital resources. Formats and protocols are open registries, not fixed enumerations. A non-parseable resource may retain metadata and a format-unknown state. Restricted records only expose lawfully public metadata; no bypass, secret-bearing URLs or sensitive personal record publication. Unknown is not absent or zero.

## UDT: reference standards and provisional coverage crosswalk
Mappings are candidates, not formal equivalences. Preserve external scheme, release, native concept ID, labels, mapping predicate (exact/close/broad/narrow/related/unmapped), evidence and reviewer status. Use SKOS mapping predicates; do not infer exact equivalence from text similarity.
| External scheme | Intended role | Reference |
|---|---|---|
| OECD FORD 2015 | Research field crosswalk | https://unstats.un.org/unsd/classifications/Family/Detail/1039 |
| NASA GCMD | Earth science concepts/variables/platforms | https://www.earthdata.nasa.gov/ |
| Library of Congress Classification | Bibliographic and humanities subjects | https://www.loc.gov/catdir/cpso/lcco/ |
| UN ISIC | Economic activity, not financial transaction types | https://unstats.un.org/unsd/classifications/ |
| UN COFOG | Government function, not agency identity | https://unstats.un.org/unsd/classifications/ |
| UNESCO ISCED | Education fields and levels, not research equivalence | https://uis.unesco.org/ |
| IANA / PRONOM | Media type and format identity | https://www.iana.org/assignments/media-types/ ; https://www.nationalarchives.gov.uk/PRONOM/ |
| DataCite | Citation, resource types and identifiers | https://schema.datacite.org/ |
| W3C DCAT 3 | Catalog interoperability, dated 2024-08-22 | https://www.w3.org/TR/2024/REC-vocab-dcat-3-20240822/ |
| W3C SKOS / PROV-O | Concepts and provenance | https://www.w3.org/TR/skos-reference/ ; https://www.w3.org/TR/prov-o/ |
| OGC STAC | Spatiotemporal collection/item/asset interoperability | https://docs.ogc.org/cs/25-004/25-004.html |

Coarse FORD mapping plan: Natural sciences -> mathematical, computing, physics, chemistry, earth/atmospheric/water/ocean, space, biology/environment concepts; Engineering and technology -> engineering, infrastructure, transportation, energy; Medical and health -> medicine/health/nutrition; Agricultural and veterinary -> agriculture/forestry/fisheries and veterinary; Social sciences -> economics, population, governance, behavior, education, law; Humanities and arts -> history, language, philosophy, religion, culture. These are broad candidate correspondences, not exhaustive or one-to-one. Monetary/fiscal records and administrative/legal material need independent non-R&D classification. Exact external releases/bytes and concept crosswalks remain open.
Unknown concepts remain registered; retain source terms and flag provisional/unclassified/conflicting; change vocabulary via versioned additions/deprecations and stable identifiers.

## AUCD: identity and cardinalities
Resource/work -> zero or more versions -> zero or more distributions -> zero or more assets. Data service may serve multiple versions/distributions; endpoint is an access location, not a work identity. Source entities may occupy multiple roles and parent relations; subjects and geography are many-to-many. Source-native assertions retain publisher semantics, acquisition time, evidence and conflict state. Content digest identifies bytes only.
Use a persisted opaque UUID for resolved work identity. Source key is a typed tuple (authority namespace, native object type, native identifier, scope/version if required); enforce uniqueness at binding level. A repeated authoritative key must resolve to the existing record. DOI/CMR/STAC/Socrata/ArcGIS identifiers are scoped and typed, not interchangeable. Missing native IDs get a provisional binding and evidence; never infer equivalence from title, URL, coordinate or bytes alone. Cross-catalog releases carry the original canonical ID and namespace, and import mappings; independent newly discovered resources may remain provisional until reconciled. Merge/split operations retain redirects, history, provenance and aliases; never rewrite evidence. Corrections generate new assertions. No canonical ID derivation from mutable titles or URL.
DCAT mapping candidate: work/version as dcat:Dataset with explicit version relationships; series as dcat:DatasetSeries; distribution as dcat:Distribution; service as dcat:DataService; concepts as SKOS; evidence activities/agents as PROV-O. Assets and endpoint verification are local extensions. STAC collection/item correspondence is source-specific, not a forced global equivalence.

## Direct access
Record independent directness, scope, stability, authorization, verification dimensions. Preference: exact file or persistent file URL, precise export/query/API with reproducible parameters, asset/object access, specific download-page fallback; generic source portal only as provenance/discovery. Record pagination and completeness; never claim a partial query is a full export. Signed URLs and credentials are not persisted publicly. Link metadata verification is distinct from byte integrity, content and scientific fitness.
Source update maintains immutable snapshot and evidence, supersession, explicit temporal semantics and selective invalidation. Use source-native units, CRS and temporal semantics alongside normalized values. Spatial intersection is not proof of municipality-level utility.

## Profile boundaries
Geographic = location/geometry/reference systems; hydrographic = surface-water bodies, drainage networks and watersheds; hydrological observations may cross hydrographic, meteorological and environmental profiles; hydrogeology = subsurface water. Monetary = flow/transfer/payment/award evidence; financial = financial position/reporting; fiscal = public revenues, budgets, fiscal policy; economic = production, prices, employment and trade; contractual = procurement instruments. Environmental = condition/exposure/impact; biological = organisms/occurrences; ecological = habitats/interactions; geological = Earth materials/structure/process; meteorological = atmosphere/weather; climatological = long-term statistics. These are nonexclusive views, with domain-specific metadata extensions. Profiles do not claim ownership of a dataset. The 74 candidate profiles require recovery and semantic disposition before any final count.
## Representative validation
NASA CMR/Terra (collection/granule/version); USGS water (time series); USAspending (award/recipient/performance distinction); SIGE ArcGIS (layer/query); ACAA Socrata 2014 (legacy coordinate uncertainty); biological occurrences; geological maps; historical documents; streams; restricted and opaque fixture; multidomain duplicate identity and cross-deployment imports. Documentation and source discovery alone are not end-to-end validation.
## Qualification and next work
Freeze order: UDU then UDT then AUCD; each requires complete bounded scope, crosswalk disposition, contracts and positive/negative fixtures, no unclassified material architecture gaps. Separate architecture freeze from production readiness/durability and source exhaustion. Production requires all mandatory gates, >=99% measured readiness and 10/10 durability tests. No durable supervisor verified; no claim of autonomous continuation.
Next: recover original prototype archive and all seed/parameter files; exact-source manifests for reference schemes; machine-readable contracts; representative end-to-end tests; resolve residual gaps. No production implementation or release in this branch.
