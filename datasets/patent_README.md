# Patent working data

Source: fixed PatentsView release through 2024-12-31, openly preserved at https://zenodo.org/records/15058362 (DOI 10.5281/zenodo.15058362; repository license CC-BY-4.0). Grant visibility, not filing-date visibility, governs the analysis. All data are real patent records; no simulated data are included in these files.

Construction and detailed limits are in `../research/data_feasibility.md`. Row counts are only final when `patent_subset_summary.json` and `patent_quality_audit.json` exist and report successful construction/audit. Partial or planned outputs are not completed evidence.

Completed and audited 2026-09-29: domain 90,882 unique grants (5,119 coded core); portfolio 1,377,130 grant-by-organization rows, representing 1,353,121 grants and 932 organizations; citations 324,764 distinct pairs. Titles, abstracts and application IDs are complete in the domain. Domain organization missingness is 4,988/90,882 (5.49%); citing-organization missingness is 11,294/324,764 (3.48%). All eight original table checksums, sizes and read-only flags passed the final audit.

| File | Unit and purpose |
|---|---|
| patent_domain.parquet | One granted utility patent, 2010–2024, matching coded thermal core/adjacent classes or the recorded broad text retrieval. |
| patent_portfolios.parquet | One grant × observed core organization, 2005–2024, across all technological domains. A grant may have multiple rows for co-owners. This is a retrieval superset; enforce origin-specific organizational eligibility and history windows. |
| patent_citations.parquet | One observed citing grant × domain cited grant × citation category, with organization sets and application IDs. Different categories can repeat the same citation pair; deduplicate pairs for count outcomes. |
| patent_all_grants_meta.parquet | Metadata for all nonwithdrawn utility grants, 2005–2024; confirms visibility and snapshot coverage. |
| patent_assignee_disambig.parquet | Retrospective disambiguated organization IDs; sensitivity linkage only, not presumed historical corporate groups. |
| patent_schemas.json | Actual headers read from each raw table. |
| patent_acquisition_manifest.json / patent_acquisition_extra_manifest.json | Download source, version, paths, expected/verified checksums and statuses. |
| patent_subset_summary.json | Actual constructed domain and citation counts and yearly coverage. |
| patent_quality_audit.json | Actual duplicate, date, classification, organization, citation-category and checksum checks, generated after completion. |
| patent_build_manifest.json | Consolidated source version/license, verified raw checksums, output/script SHA-256, runtime versions and computational limits. |

## Main fields and decisions

`patent_id` and application IDs are strings. `date` is the public grant issue date; no abstract or assignment metadata is backfilled to a prior filing date. `title` and `abstract` are source text. A coded qualifying patent is retained even if its abstract is missing.

`is_core` equals `cpc_core OR ipc_core`. `is_core_broad` also includes the separate text heuristic. Only coded core is used for primary organizational eligibility. `cpc_codes` combines four-character original CPC/IPC classes for harmonized historical features; deduplicate after splitting by `|`. `cpc_at_issue` and `ipc_at_issue` preserve full canonical classification strings and distinguish source. Historical IPC components are normalized for inconsistent zero padding without substituting current classifications.

Primary `assignee_id` is a pipe-separated set of all as-published organization names normalized to uppercase ASCII letters/numbers. `assignee_ids` and `assignee_names` retain arrays of keys and literal names. This groups punctuation/case variants but does not merge company aliases, subsidiaries, name changes or acquisitions. Non-ASCII characters are removed by this mechanical primary key; literal names remain available for audit. A missing organization is null, never an independent new company. `disambig_assignee_id(s)` are separately retained for sensitivity analysis. Portfolio rows use one observed core organization key each.

`citing_date` is the citing grant issue date. The source citation table's `citation_date` refers to the cited document and is not a citation-event timestamp. `citation_category` distinguishes applicant/examiner and other source values; all-citation outcomes concern recorded technological attention, while applicant-only analysis is a separate sensitivity. Neither proves intentional corporate search, realized use, adoption or business returns.

The citing universe contains US nonwithdrawn utility grants through 2024. Actual categories are `cited by applicant` (232,128), `cited by examiner` (90,617), `cited by other` (1,752), `imported from a related application` (218), `cited by third party` (44), and null (5). Seventeen links have a citing-grant date preceding the cited grant; date-window construction must exclude these chronology anomalies. Unknown citing organizations remain unknown and cannot contribute invented external organizations.

Same-application references can be excluded with `citing_application_id` and `cited_application_id`; complete family/continuation information has not been acquired. Missing citation rows for a mature candidate mean zero observed qualifying citations after verifying coverage, not exclusion from the candidate set. Unknown citing organizations should be counted and reported separately rather than converted to synthetic external organizations.

Downloaded originals are immutable read-only files on F:. Scripts, extracted TSVs, DuckDB, caches, derived data, manifests, logs and audits are on D:. Coverage stops in 2024; there is no claim of 2025 data or of historical real-time database snapshots.
