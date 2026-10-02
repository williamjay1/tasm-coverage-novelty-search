# Operational portability edits

Only public script copies are edited. The scientific algorithms, scores, labels, target definitions and random seeds retain their original implementation. Original project files remain immutable. Local acquisition roots become repository-relative or TASM_RAW_ROOT. Drive-only assertions become workspace checks. Tables read their unchanged 90-cell JSON, and a workflow JSON replaces article hashing. Drawing output provenance therefore hashes the public representation. Local paths in metadata are redacted; source checksums remain historical provenance. Original code/file checksums and edits:

```json
[
  {
    "path": "datasets/canonical_v1/label_audit.json",
    "change": "operational local-path redaction",
    "original_sha256": "4b10fd0d0173630e1b0771a6358c3c7f3b5fd751c33172cea38232b4c1c366fa"
  },
  {
    "path": "datasets/patent_acquisition_extra_manifest.json",
    "change": "operational local-path redaction",
    "original_sha256": "0f9740d40e7c3956d5909c5401a8271e11082a3c905dcf93bb385e0e7b0d1db2"
  },
  {
    "path": "datasets/patent_acquisition_manifest.json",
    "change": "operational local-path redaction",
    "original_sha256": "e389e27b9d2dc965598c645490f13df8a05d60fd11a5553545bece6ca22db7d6"
  },
  {
    "path": "datasets/patent_build_manifest.json",
    "change": "operational local-path redaction",
    "original_sha256": "74d875a9ad8f92cd7e081d257ec9b42db30e9384a9db470bb8b158296bacd45b"
  },
  {
    "path": "datasets/patent_dictionary_manifest.json",
    "change": "operational local-path redaction",
    "original_sha256": "601516756b404a9dabda3516cd0c98a580356d4c2811e2278a99490747f97f38"
  },
  {
    "path": "results/primary_v1/context_and_uncertainty/context_and_uncertainty_notes.json",
    "change": "operational local-path redaction",
    "original_sha256": "f3f7903774bd28255cb4882fd7a472e499b1afa20af0aba541a2cf83e5ee2794"
  },
  {
    "path": "results/primary_v1/run_config.json",
    "change": "operational local-path redaction",
    "original_sha256": "c9a705c89aceec8facb370888b27fb254bd47ea259a733d34235c7b6a6936015"
  },
  {
    "path": "results/revision_v3/technical_new_sample_protocol.json",
    "change": "operational local-path redaction",
    "original_sha256": "534e952a27879a2b9bd6b4b0b4dae369b60fe884fe6b72b0944782f1de4c3a64"
  },
  {
    "path": "results/revision_v6/development_protocol.json",
    "change": "operational local-path redaction",
    "original_sha256": "0d5d5e9c914e140a398ecb145aae4aa496cb633b7f1596bd245cd291158a2111"
  },
  {
    "path": "results/text_distance_v1/run_config.json",
    "change": "operational local-path redaction",
    "original_sha256": "9714631fe7ad9daf0d58384ba36c800e8855a303e55cefb8afa229d3c706aee8"
  },
  {
    "path": "scripts/acquire_patents.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "0d3438e7afc47e45ef0f7ded098e87475ae25ab7a74303c326ca67207ba410ac"
  },
  {
    "path": "scripts/build_patent_subset.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "3245b0e141c8d0510c16e2d50fbf927c97584a54234c9af3fe32460df858239e"
  },
  {
    "path": "scripts/build_patent_subset_audit.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "147e1d0ce3cd904c5ec9c1d4e256887950f347fd4c05d965cc9ac5c0754eddcb"
  },
  {
    "path": "scripts/audit_real_labels.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "bd4731dd6818700cb8faca6f4665c938e0c48c878252af0d2768ff9bbebe655c"
  },
  {
    "path": "scripts/revision_decision_analysis.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "0081067e6911c328c7da1bc3e4441a6d50c4c879b5b66cb7a35c719247b80baf"
  },
  {
    "path": "scripts/revision_v3_decisions.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "d8a8fbdec1cc7354c8c423bbdd1f3b183cf07b05037171c36cb269ae58c37e73"
  },
  {
    "path": "scripts/revision_v4_heterogeneity.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "947604a6dee86cc313fbe0dd8a3c242aa8f1213c040922b37518587b8b8c0fb4"
  },
  {
    "path": "scripts/nature_figures12.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "8971cbcf678f60e66b7920eeada670935fab960b8c5eaa62392418255fb9fd9f"
  },
  {
    "path": "scripts/nature_tables.py",
    "change": "operational portability; no scientific calculation changed",
    "original_sha256": "f9080468423fa28682fd82a25a4b3c6e0ec450c83f27ce30d4d99827daf90940"
  }
]
```
