"""Post-critique archival task linkage, citation source and co-ownership audit.

This exploratory extension leaves v1 data and manuscript untouched. It does not
infer adoption, commercial value, independent validation or an algorithm effect.
"""
from __future__ import annotations

import os
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import duckdb

ROOT = Path(__file__).resolve().parents[1]
DS = ROOT / "datasets" / "revision_v2"
RS = ROOT / "results" / "revision_v2"
CORE = r"^H01M10/(6[0-9]|50)"

def q(path):
    return "'" + str(path).replace("\\", "/").replace("'", "''") + "'"

def log(event, **kwargs):
    print(json.dumps({"utc": dt.datetime.now(dt.timezone.utc).isoformat(), "event": event, **kwargs}, default=str), flush=True)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raw-audit", action="store_true")
    ap.add_argument("--audit-only", action="store_true")
    args = ap.parse_args()
    DS.mkdir(parents=True, exist_ok=True)
    RS.mkdir(parents=True, exist_ok=True)
    tmp = ROOT / "temp" / "task_evidence_v2"
    tmp.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect(str(DS / "task_evidence.duckdb"))
    con.execute("SET threads=2; SET memory_limit='3GB'; SET preserve_insertion_order=false")
    con.execute("SET temp_directory=" + q(tmp))
    con.execute("ATTACH " + q(ROOT / "datasets/patent_work/patents.duckdb") + " AS source (READ_ONLY)")
    con.execute("ATTACH " + q(ROOT / "datasets/canonical_v1/labels.duckdb") + " AS canonical (READ_ONLY)")
    scalar = lambda s: con.execute(s).fetchone()[0]
    def export(sql, target):
        con.execute("COPY (" + sql + ") TO " + q(target) + " (FORMAT PARQUET, COMPRESSION ZSTD)")
        log("export", file=str(target), rows=scalar("SELECT count(*) FROM read_parquet(" + q(target) + ")"), bytes=target.stat().st_size)
    # Only fully matured three-year cohorts; extension is not used to reselect
    # v1 predictive models, policies or thresholds after held-out inspection.
    con.execute("CREATE OR REPLACE TEMP VIEW study AS SELECT * FROM read_parquet(" + q(ROOT / "datasets/canonical_v1/study_patents.parquet") + ") WHERE year(patent_date)<=2021")
    if args.audit_only:
        con.execute("CREATE OR REPLACE TEMP VIEW labels AS SELECT * FROM read_parquet(" + q(DS / "task_patent_labels.parquet") + ")")
        raw = raw_audit(con, DS, RS)
        apath = RS / "task_label_audit.json"
        audit = json.loads(apath.read_text(encoding="utf-8")) if apath.exists() else {}
        audit["raw_audit"] = raw
        apath.write_text(json.dumps(audit, indent=2), encoding="utf-8")
        log("raw_audit_complete", **raw)
        con.close()
        return
    con.execute("""CREATE OR REPLACE TABLE task_citing_class AS
      SELECT DISTINCT p.patent_id AS citing_id,
        coalesce(c.cpc_core,false) AS citing_cpc_core,
        coalesce(i.ipc_core,false) AS citing_ipc_core,
        coalesce(c.cpc_core,false) OR coalesce(i.ipc_core,false) AS citing_is_core,
        cp.cpc_at_issue AS citing_cpc_at_issue,ip.ipc_at_issue AS citing_ipc_at_issue
      FROM source.patents p JOIN (SELECT DISTINCT citing_id FROM canonical.edges) z ON p.patent_id=z.citing_id
      LEFT JOIN source.cpc_domain_flags c ON c.patent_id=p.patent_id
      LEFT JOIN source.ipc_domain_flags i ON i.patent_id=p.patent_id
      LEFT JOIN source.classification cp ON cp.patent_id=p.patent_id
      LEFT JOIN source.ipc_classification ip ON ip.patent_id=p.patent_id""")
    # Use the exact full-set owner overlap/same-application filters of v1.
    con.execute("""CREATE OR REPLACE TABLE task_edges AS
      SELECT e.cited_id AS patent_id,e.year,e.citing_id,e.citing_date,
        e.citation_category,e.citing_assignee_id,e.cited_assignee_id,
        cc.citing_is_core,cc.citing_cpc_core,cc.citing_ipc_core,
        cc.citing_cpc_at_issue,cc.citing_ipc_at_issue,
        nullif(a.filing_date,'') AS citing_filing_date,
        try_cast(a.filing_date AS DATE)>make_date(e.year,12,31) AS citing_filed_after_origin,
        lower(e.citation_category) LIKE '%applicant%' AS is_applicant,
        lower(e.citation_category) LIKE '%examiner%' AS is_examiner,
        e.citing_date<=make_date(e.year+3,12,31) AS in_three_year_window,
        e.citing_date<=make_date(e.year+5,12,31) AS in_five_year_window
      FROM canonical.edges e JOIN study d ON e.cited_id=d.patent_id
      LEFT JOIN task_citing_class cc USING(citing_id)
      LEFT JOIN source.applications a ON a.patent_id=e.citing_id
      WHERE e.known_citing_owner AND NOT e.overlapping_raw_owners
        AND NOT coalesce(e.same_application,false)
        AND e.citing_date>=make_date(e.year+1,1,1)
        AND e.citing_date<=make_date(e.year+5,12,31)
        AND e.citing_date>=e.cited_date""")
    export("SELECT * FROM task_edges WHERE in_three_year_window", DS / "task_future_edges.parquet")
    export("SELECT * FROM task_edges WHERE year<=2019 AND in_five_year_window", DS / "task_five_year_edges.parquet")
    # Distinct category rows are retained. Count distinct grant and organization
    # IDs so multi-category records cannot multiply an indicator.
    agg_parts=[]
    for prefix, condition in [
        ("future_external", "in_three_year_window"),
        ("future_applicant", "in_three_year_window AND is_applicant"),
        ("future_examiner", "in_three_year_window AND is_examiner"),
        ("future_core", "in_three_year_window AND citing_is_core"),
        ("future_core_applicant", "in_three_year_window AND citing_is_core AND is_applicant"),
        ("future_core_examiner", "in_three_year_window AND citing_is_core AND is_examiner"),
        ("five_year_external", "year<=2019 AND in_five_year_window"),
        ("five_year_applicant", "year<=2019 AND in_five_year_window AND is_applicant"),
        ("five_year_core", "year<=2019 AND in_five_year_window AND citing_is_core"),
    ]:
        for what, expr in [("orgs", "owner"),("patents", "citing_id")]:
            agg_parts.append(f"count(DISTINCT {expr}) FILTER(WHERE {condition}) AS {prefix}_{what}")
    con.execute("CREATE OR REPLACE TABLE task_attention AS SELECT patent_id," + ",".join(agg_parts) + " FROM task_edges, unnest(string_split(citing_assignee_id,'|')) AS u(owner) WHERE nullif(owner,'') IS NOT NULL GROUP BY patent_id")
    prefixes=["future_external","future_applicant","future_examiner","future_core","future_core_applicant","future_core_examiner","five_year_external","five_year_applicant","five_year_core"]
    cols=[]
    for p in prefixes:
        for suffix in ["orgs","patents"]:
            cols.append(f"CASE WHEN {('d.year<=2019' if p.startswith('five_') else 'true')} THEN coalesce(a.{p}_{suffix},0) END AS {p}_{suffix}")
        cols.extend([
            f"CASE WHEN {('d.year<=2019' if p.startswith('five_') else 'true')} THEN coalesce(a.{p}_orgs,0)>=2 END AS {p}_signal_2org",
            f"CASE WHEN {('d.year<=2019' if p.startswith('five_') else 'true')} THEN coalesce(a.{p}_patents,0)>=1 END AS {p}_signal_1patent",
            f"CASE WHEN {('d.year<=2019' if p.startswith('five_') else 'true')} THEN coalesce(a.{p}_orgs,0)>=2 AND coalesce(a.{p}_patents,0)>=2 END AS {p}_signal_2org2patent",
        ])
    export("SELECT d.patent_id,year(d.patent_date) AS year,d.is_core," + ",".join(cols).replace("d.year", "year(d.patent_date)") + " FROM study d LEFT JOIN task_attention a USING(patent_id)", DS / "task_patent_labels.parquet")
    con.execute("CREATE OR REPLACE TEMP VIEW labels AS SELECT * FROM read_parquet(" + q(DS / "task_patent_labels.parquet") + ")")
    n_bad=scalar("SELECT count(*) FROM labels l JOIN study d USING(patent_id) WHERE l.future_external_orgs<>d.future_external_attention OR l.future_applicant_orgs<>d.future_applicant_attention OR l.future_external_patents<>d.future_external_citing_patents")
    if n_bad:
        raise AssertionError(f"v1 exact count reconciliation failed: {n_bad}")
    # Org-specific subsequent grant citations to focal candidates. These are
    # sparse archival links, not tool usage or commercial adoption. Included
    # filings predating origin are flagged to avoid a temporal innovation claim.
    con.execute("""CREATE OR REPLACE TABLE task_focal_links AS
      SELECT owner AS organization_id,year,patent_id,
        count(DISTINCT citing_id) AS focal_core_citing_patents,
        count(DISTINCT citing_id) FILTER(WHERE is_applicant) AS focal_core_applicant_citing_patents,
        count(DISTINCT citing_id) FILTER(WHERE citing_filed_after_origin) AS focal_core_postorigin_filing_citing_patents,
        count(DISTINCT citing_id) FILTER(WHERE is_applicant AND citing_filed_after_origin) AS focal_core_applicant_postorigin_filing_citing_patents,
        string_agg(DISTINCT citing_id,'|' ORDER BY citing_id) AS focal_core_citing_ids
      FROM task_edges, unnest(string_split(citing_assignee_id,'|')) AS u(owner)
      WHERE in_three_year_window AND citing_is_core AND nullif(owner,'') IS NOT NULL
      GROUP BY organization_id,year,patent_id""")
    export("SELECT *,focal_core_citing_patents>=1 AS focal_core_signal_1patent,focal_core_applicant_citing_patents>=1 AS focal_core_applicant_signal_1patent FROM task_focal_links", DS / "task_focal_core_links.parquet")
    export("SELECT DISTINCT organization_id,year,patent_id,e.citing_id,e.citing_date,e.citation_category,e.citing_filing_date,e.citing_filed_after_origin,e.citing_cpc_at_issue,e.citing_ipc_at_issue FROM task_focal_links f JOIN task_edges e USING(patent_id,year) WHERE e.in_three_year_window AND e.citing_is_core AND list_contains(string_split(e.citing_assignee_id,'|'),f.organization_id)", DS / "task_focal_core_edges.parquet")
    # Native at-issue finer codes are already in source portfolios. No invented
    # mapping of old 10/50 finer groups onto modern 10/6x finer groups is applied.
    export("SELECT DISTINCT * FROM read_parquet(" + q(ROOT / "datasets/patent_portfolios.parquet") + ") WHERE is_core", DS / "task_core_history.parquet")
    # Expand to all grants of all retrospectively disambiguated core owners,
    # rather than merely relabeling owners inside the raw-name portfolio. This
    # permits a full-pipeline identity sensitivity, including recovered aliases.
    con.execute("""CREATE OR REPLACE TEMP TABLE task_disambig_core_orgs AS
      SELECT DISTINCT owner AS organization_id FROM source.disambiguated_orgs o
      JOIN source.patents p USING(patent_id)
      LEFT JOIN source.cpc_domain_flags c USING(patent_id)
      LEFT JOIN source.ipc_domain_flags i USING(patent_id),
      unnest(o.disambig_assignee_ids) AS u(owner)
      WHERE p.patent_type='utility' AND coalesce(p.withdrawn,0)=0
        AND p.patent_date BETWEEN DATE '2005-01-01' AND DATE '2024-12-31'
        AND (coalesce(c.cpc_core,false) OR coalesce(i.ipc_core,false))
        AND nullif(owner,'') IS NOT NULL""")
    con.execute("""CREATE OR REPLACE TEMP TABLE task_disambig_history_ids AS
      SELECT DISTINCT o.patent_id FROM source.disambiguated_orgs o,
      unnest(o.disambig_assignee_ids) AS u(owner)
      JOIN task_disambig_core_orgs c ON c.organization_id=owner""")
    export("""SELECT p.patent_id,p.patent_date,p.patent_title,
        d.disambig_assignee_id AS assignee_id,d.disambig_assignee_ids,
        d.disambig_assignee_names,o.assignee_id AS raw_assignee_id,
        coalesce(c.cpc_core,false) OR coalesce(i.ipc_core,false) AS is_core,
        cp.cpc_at_issue,ip.ipc_at_issue,
        array_to_string(list_sort(list_distinct(list_concat(
          string_split(coalesce(cp.cpc_class_codes,''),'|'),
          string_split(coalesce(ip.ipc_class_codes,''),'|')))),'|') AS cpc_codes
      FROM source.patents p JOIN task_disambig_history_ids h USING(patent_id)
      JOIN source.disambiguated_orgs d USING(patent_id)
      LEFT JOIN source.orgs o USING(patent_id)
      LEFT JOIN source.cpc_domain_flags c USING(patent_id)
      LEFT JOIN source.ipc_domain_flags i USING(patent_id)
      LEFT JOIN source.classification cp USING(patent_id)
      LEFT JOIN source.ipc_classification ip USING(patent_id)
      WHERE p.patent_type='utility' AND coalesce(p.withdrawn,0)=0
        AND p.patent_date BETWEEN DATE '2005-01-01' AND DATE '2024-12-31'""", DS / "task_disambig_portfolios.parquet")
    export("SELECT year,count(*) AS candidates,sum(future_external_signal_2org::INT) AS all_2org,sum((future_external_signal_2org AND future_external_patents=1)::INT) AS all_2org_single_patent,sum(future_external_signal_2org2patent::INT) AS all_2org2patent,sum(future_applicant_signal_2org::INT) AS applicant_2org,sum((future_applicant_signal_2org AND future_applicant_patents=1)::INT) AS applicant_2org_single_patent,sum(future_core_signal_1patent::INT) AS core_1patent,sum(future_core_signal_2org::INT) AS core_2org,sum(future_core_signal_2org2patent::INT) AS core_2org2patent,sum(future_core_applicant_signal_1patent::INT) AS core_applicant_1patent FROM labels GROUP BY year ORDER BY year", RS / "task_cohort_summary.parquet")
    # Select v1 K30 lists solely to summarize measurement consequences.
    con.execute("CREATE OR REPLACE TEMP VIEW selected AS SELECT * FROM read_parquet(" + q(ROOT / "results/primary_v1/selected_primary_*.parquet") + ") WHERE year>=2018 AND k=30")
    export("SELECT s.year,s.policy,count(*) AS selection_events,count(DISTINCT s.patent_id) AS unique_patents,sum(l.future_external_signal_2org::INT) AS all_2org,sum((l.future_external_signal_2org AND l.future_external_patents=1)::INT) AS all_2org_single_patent,sum(l.future_external_signal_2org2patent::INT) AS all_2org2patent,sum(l.future_core_signal_1patent::INT) AS core_1patent,sum(l.future_core_signal_2org::INT) AS core_2org,sum(l.future_core_signal_2org2patent::INT) AS core_2org2patent,sum(l.future_core_applicant_signal_1patent::INT) AS core_applicant_1patent,sum((s.distant AND l.future_core_signal_1patent)::INT) AS distant_core_1patent,sum((s.distant AND l.future_core_signal_2org)::INT) AS distant_core_2org,sum((s.distant AND l.future_core_applicant_signal_1patent)::INT) AS distant_core_applicant_1patent,sum(coalesce(f.focal_core_citing_patents,0)>=1)::BIGINT AS focal_core_1patent,sum(coalesce(f.focal_core_applicant_citing_patents,0)>=1)::BIGINT AS focal_core_applicant_1patent FROM selected s JOIN labels l ON l.patent_id=s.patent_id LEFT JOIN task_focal_links f ON f.organization_id=s.organization_id AND f.year=s.year AND f.patent_id=s.patent_id GROUP BY s.year,s.policy ORDER BY s.year,s.policy", RS / "task_v1_selected_summary.parquet")
    audit={
        "created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),
        "status":"Exploratory post-critique extension; no v1 model/rule reclassification",
        "release_end":"2024-12-31", "core_regex":CORE,
        "core_definition":"Any CPC or IPC at-issue code matching battery thermal H01M10/6x or H01M10/50, not title keywords or any thermal-field citation",
        "externality":"Full known citing owner set must not overlap full candidate owner set; no same application, exact v1 logic",
        "n_candidates":scalar("SELECT count(*) FROM labels"),
        "n_future_edges":scalar("SELECT count(*) FROM task_edges WHERE in_three_year_window"),
        "n_future_core_edges":scalar("SELECT count(*) FROM task_edges WHERE in_three_year_window AND citing_is_core"),
        "n_v1_count_mismatches":n_bad,
        "n_focal_core_org_candidate_rows":scalar("SELECT count(*) FROM task_focal_links"),
        "n_single_citing_patent_2org_cases":scalar("SELECT count(*) FROM labels WHERE future_external_signal_2org AND future_external_patents=1"),
        "n_2org_cases":scalar("SELECT count(*) FROM labels WHERE future_external_signal_2org"),
        "limits":["Core classification is task-associated citation evidence, not technical transfer or use", "One grant may have multiple owners; two owners and two grants still do not demonstrate independent projects or families", "International and continuation-family independence unavailable", "Later grant citation can come from an application filed before the screening origin", "Organization-specific links do not establish actual recommendation receipt or an algorithm effect", "Fine code novelty can reflect schema evolution; preserve native codes and report this boundary"],
    }
    prior_audit = RS / "task_label_audit.json"
    if prior_audit.exists():
        prior = json.loads(prior_audit.read_text(encoding="utf-8"))
        if "raw_audit" in prior:
            audit["raw_audit"] = prior["raw_audit"]
    (RS / "task_label_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    if args.raw_audit:
        audit["raw_audit"]=raw_audit(con, DS, RS)
    (RS / "task_label_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    con.close()
    log("complete", **audit)

def raw_audit(con,ds,rs):
    """Independently reconstruct 12 complete labels from retained raw source TSVs."""
    # deterministic strata; categories and outcomes used to audit measurement,
    # not to select policy or manufacture a validation sample.
    ids=con.execute("""SELECT patent_id FROM (
      SELECT patent_id,year,'ordinary' AS stratum FROM labels
      WHERE year BETWEEN 2018 AND 2021 AND NOT future_core_signal_1patent
        AND NOT(future_external_signal_2org AND future_external_patents=1)
      QUALIFY row_number() OVER(PARTITION BY year ORDER BY patent_id)=1
      UNION ALL
      SELECT patent_id,year,'coownership' FROM labels
      WHERE year BETWEEN 2018 AND 2021 AND future_external_signal_2org AND future_external_patents=1
      QUALIFY row_number() OVER(PARTITION BY year ORDER BY patent_id)=1
      UNION ALL
      SELECT patent_id,year,'core_applicant' FROM labels
      WHERE year BETWEEN 2018 AND 2021 AND future_core_applicant_signal_1patent
      QUALIFY row_number() OVER(PARTITION BY year ORDER BY patent_id)=1
      ) ORDER BY year,stratum""").fetchall()
    ids=[r[0] for r in ids]
    idsql="("+",".join(q(i) for i in ids)+")"
    # Read raw stream, not the canonical edges or derived citations.
    con.execute("CREATE OR REPLACE TEMP TABLE audit_raw_cites AS SELECT * FROM read_csv("+q(ROOT/"datasets/patent_work/g_us_patent_citation.tsv")+", delim='\t', header=true, all_varchar=true, quote='\"', escape='\"', strict_mode=true, nullstr='') WHERE citation_patent_id IN "+idsql)
    rawcols={r[0] for r in con.execute("DESCRIBE audit_raw_cites").fetchall()}
    log("raw_columns",columns=sorted(rawcols),rows=con.execute("SELECT count(*) FROM audit_raw_cites").fetchone()[0])
    # Independently rebuild full-set owner normalization from individual original
    # organization names and core association from individual retained code rows.
    # These deliberately do not reuse source org aggregates or core flag tables.
    con.execute("""CREATE OR REPLACE TEMP TABLE audit_orgs AS
      SELECT patent_id,string_agg(DISTINCT orgkey,'|' ORDER BY orgkey) AS assignee_id
      FROM (SELECT patent_id,regexp_replace(upper(trim(raw_assignee_name)),
        '[^A-Z0-9]','','g') AS orgkey FROM source.assignee_raw
        WHERE patent_id IN (SELECT DISTINCT patent_id FROM audit_raw_cites)
        OR patent_id IN (SELECT DISTINCT citation_patent_id FROM audit_raw_cites))
      WHERE nullif(orgkey,'') IS NOT NULL GROUP BY patent_id""")
    con.execute("""CREATE OR REPLACE TEMP TABLE audit_core AS
      SELECT patent_id,bool_or(regexp_matches(code,'^H01M10/(6[0-9]|50)')) AS is_core
      FROM (SELECT patent_id,code FROM source.cpc WHERE patent_id IN
        (SELECT DISTINCT patent_id FROM audit_raw_cites)
        UNION ALL SELECT patent_id,code FROM source.ipc WHERE patent_id IN
        (SELECT DISTINCT patent_id FROM audit_raw_cites)) GROUP BY patent_id""")
    # Raw titles/classes/owners are independently joined from their original
    # tables. Source normalization must exactly match the v1 documented key.
    rows=con.execute("""SELECT r.patent_id AS citing_id,r.citation_patent_id AS cited_id,
      r.citation_category,p.patent_date,oa.assignee_id AS citing_owners,
      da.assignee_id AS candidate_owners,coalesce(cf.is_core,false) AS is_core,
      a.application_id AS citing_application_id,d.application_id AS cited_application_id
      FROM audit_raw_cites r JOIN source.patents p ON p.patent_id=r.patent_id
      JOIN audit_orgs oa ON oa.patent_id=r.patent_id
      JOIN audit_orgs da ON da.patent_id=r.citation_patent_id
      JOIN study d ON d.patent_id=r.citation_patent_id
      LEFT JOIN audit_core cf ON cf.patent_id=r.patent_id
      LEFT JOIN source.applications a ON a.patent_id=r.patent_id
      WHERE p.patent_type='utility' AND coalesce(p.withdrawn,0)=0""").fetchdf()
    observed={}
    expected=con.execute("SELECT * FROM labels WHERE patent_id IN "+idsql).fetchdf().set_index("patent_id")
    mismatch=[]
    for pid in ids:
        year=int(expected.loc[pid,"year"])
        s=rows[rows.cited_id==pid]
        s=s[(s.patent_date.dt.year>year)&(s.patent_date.dt.year<=year+3)]
        kept=[]
        for r in s.itertuples():
            a=set(str(r.citing_owners).split("|"));b=set(str(r.candidate_owners).split("|"))
            if a&b:continue
            if r.citing_application_id and r.citing_application_id==r.cited_application_id:continue
            kept.append(r)
        obs={}
        for prefix,fn in [("future_external",lambda r:True),("future_applicant",lambda r:"applicant" in str(r.citation_category).lower()),("future_core",lambda r:r.is_core),("future_core_applicant",lambda r:r.is_core and "applicant" in str(r.citation_category).lower())]:
            keep=[r for r in kept if fn(r)]
            obs[prefix+"_orgs"]=len(set(o for r in keep for o in str(r.citing_owners).split("|") if o))
            obs[prefix+"_patents"]=len(set(r.citing_id for r in keep))
        observed[pid]=obs
        for col,v in obs.items():
            if int(expected.loc[pid,col])!=v:mismatch.append({"patent_id":pid,"field":col,"expected":int(expected.loc[pid,col]),"raw_rebuild":v})
    (rs/"task_raw_label_checks.json").write_text(json.dumps({"selected_ids":ids,"observed":observed,"mismatches":mismatch},indent=2),encoding="utf-8")
    if mismatch:raise AssertionError(f"raw source audit failed: {mismatch}")
    return {"n_sample_patents":len(ids),"n_count_fields":8*len(ids),"mismatches":0,"raw_citation_rows_scanned":"All source TSV rows; exact eligible citation subset independently rebuilt", "sampling":"Each held-out year: lowest ID ordinary, single-grant coownership, and positive core applicant strata", "independence_scope":"Citation raw TSV read separately; owner keys independently rebuilt from retained original organization-name rows and core flags from individual CPC/IPC code rows; patent dates and applications from retained source database, not canonical labels"}

if __name__=="__main__":
    main()
