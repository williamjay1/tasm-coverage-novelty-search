# Evaluating coverage and novelty in technology intelligence

Public replication code and derived archival data for the TASM manuscript by
Junjie Zhang. The study evaluates finite shortlists, task allocation, recorded
unfamiliarity and separate archival objectives. This repository does not mirror
the unpublished manuscript or third-party scholarly full texts.

## Data and scientific scope

The acquired source is the USPTO PatentsView release through 31 December 2024,
archived at https://doi.org/10.5281/zenodo.15058362. This is the **source-data DOI**,
not a DOI for this research. Derived records retain CC BY 4.0 attribution;
research software is MIT. See `DATA_LICENSE.md` and `LICENSE`.

The dataset contains public patent and organization records, frozen candidate
pools/rankings, histories, selected lists, citation outcomes and retained results.
Repeated list entries are selection events, not independent inventions or
independent participants. Citation links do not establish adoption. Function
routes are AI-assisted historical desk coding without expert or organizational
validation. Exploratory v6–v8 analyses use previously examined historical data.
The 2022/membrane extension is an unexecuted plan, not public preregistration or
independent confirmation. No human-participant study was conducted.

## Quick verification and safe replay

Use Python 3.12. Install `requirements-replay.txt`; forecasting and drawings use
the separate requirement files. Exact observed originating versions appear in
`environment-lock.json` (an environment record, not a hash-locked package build).

```console
python -B scripts/restore_data_parts.py
python -B scripts/verify_public_release.py
python -B scripts/replay_public.py --layer smoke --work-dir D:/MLWork/TASM_public_smoke
```

`restore_data_parts.py` rejoins four large inputs from checksum-verified pieces,
never overwriting a conflicting file. Every tracked GitHub file is below 50 MB.
Fresh replay directories are required; outputs do not overwrite retained evidence.
On Windows use a computational work disk such as D:, never C:.

## Reproduction layers

1. **Frozen-input statistical replay:** original policy/selection results,
   battery v3 allocation and controls, electronics fixed-list label replay,
   development v6 comparisons, two-task v7 exchange/dependence results and
   v8 budget/joint/random/mature-window sensitivities. No predictor refitting
   or neural-model training is needed. Select `v3`, `v6`, `v7`, or `v8` in
   `replay_public.py`. These preserve original frozen scores and inputs.
2. **Original forecasting reconstruction:** included canonical title/abstract,
   chronology and portfolio files support `--layer primary-refit`. This layer
   refits original Ridge and LightGBM models; it may require more resources and
   is not described as freshly executed by the release smoke test. The temporal
   preprocessing/fitting contract remains in `run_search_study.py`.
The preserved labels.duckdb contains three legacy raw_* views with originating
local-file paths. Safe replay uses its materialized edges/candidates/attention
tables, not those legacy views. Full source reconstruction creates a new database
and must not treat the legacy view definitions as portable inputs.

3. **Cached citation-edge reconstruction:** `--layer v8` includes `--windows`,
   using restored `labels.duckdb`, five-year battery edges and electronics grant
   metadata. This is distinct from scanning the entire public raw archive.
4. **Full source reconstruction:** `acquire_patents.py`, `build_patent_subset.py`,
   `build_patent_subset_audit.py`, `prepare_study_data.py`,
   `revision_task_evidence.py` and `revision_v3_validation.py` preserve the
   extraction/measurement code. Raw multi-GB archives and intermediate source
   database are not mirrored. Inventory files enumerate fixed source tables
   and checksums. Set `TASM_RAW_ROOT` to a separate immutable source location
   (on the originating storage convention, F:/AcademicData/TASM_AlgorithmicSearch/raw).
   Reconstruct in a fresh work copy. No download is performed by safe replay.
   Original filename stamps are part of this source inventory; do not silently
   substitute a current release or treat revised disambiguation as historical.
5. **Drawing replay:** `--layer figures` regenerates three vector figures and
   four editable-text tables from frozen numeric/90-cell inputs, without an
   article copy. Arial must be installed for identical appearance. SVG/PDF are
   vector, PNG/TIFF are native 1200 dpi. SciencePlots 2.2.2 is MIT; Nature-like
   presentation does not imply certification by Nature. Tested computation
   and output records are in `validation/`.

`results/` is the retained historical evidence; safe replay uses an isolated copy.
`data_parts/index.json` describes exact byte reconstruction; `public_manifest.json`
hashes tracked release content. `PORTABILITY.md` lists operational-only source
edits and preserved originating hashes. No conclusions or numerical labels are
changed. `scripts/verify_public_release.py` checks current integrity.

## AI assistance and author responsibility

OpenAI Codex assisted literature discovery, research-design development, programming, computational analysis, historical patent desk assessment and manuscript drafting/revision. Execution records identify the interface and GPT-6 model family, but not exact historical builds or a complete historical prompt archive. Reported numerical computations were executed on the identified archival records and checked against retained outputs. The author remains responsible for source verification, analysis, conclusions and any submission. Function assessments have no independent expert or organizational validity test.

## Attribution and DOI

Author: Junjie Zhang, Shanghai International Studies University.
ORCID: https://orcid.org/0009-0004-8821-4018.
Contact: junjiezhang2024@shisu.edu.cn.
No funding or competing interests are declared. Repository: https://github.com/williamjay1/tasm-coverage-novelty-search.
The source tree and v1.0.0 tag are prepared for GitHub. After the author connects
Zenodo to GitHub and enables this repository, the author can publish a GitHub
Release from that existing tag to trigger Zenodo archiving. The author performs
these steps personally; this preparation neither creates a Zenodo deposit nor
assigns a study DOI. After the DOI exists, update CITATION.cff and the manuscript.
A Git tag alone does not trigger that GitHub-Release archival workflow.
