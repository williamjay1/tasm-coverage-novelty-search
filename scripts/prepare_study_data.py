"""Build fixed, grant-visible citation labels from the real acquired source tables.

Unknown owners never become invented external organizations. Derived outputs are
versioned on D; no original file is changed. Run after acquisition is complete.
"""
from __future__ import annotations
import os
os.environ.setdefault("OMP_NUM_THREADS","1")
import argparse
import datetime as dt
import hashlib
import json
from pathlib import Path
import duckdb

ROOT=Path(__file__).resolve().parents[1]

def q(value):
    return "'"+str(value).replace("\\","/").replace("'","''")+"'"

def log(event,**fields):
    print(json.dumps(dict(time=dt.datetime.now(dt.timezone.utc).isoformat(),event=event,**fields),default=str),flush=True)

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--source",type=Path,default=ROOT/"datasets")
    parser.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists() and any(args.output.iterdir()):
        raise FileExistsError("Use a new versioned canonical output directory")
    args.output.mkdir(parents=True,exist_ok=True)
    con=duckdb.connect(str(args.output/"labels.duckdb"))
    con.execute("SET threads=1; SET memory_limit='3GB'; SET preserve_insertion_order=false")
    con.execute("SET temp_directory="+q(ROOT/"temp"/"duckdb_labels"))
    sources={name:args.source/f"patent_{name}.parquet" for name in ["domain","citations","portfolios"]}
    for name,path in sources.items():
        if not path.exists():raise FileNotFoundError(path)
        con.execute(f"CREATE VIEW raw_{name} AS SELECT * FROM read_parquet({q(path)})")
    def scalar(sql):return con.execute(sql).fetchone()[0]
    def export(sql,name):
        path=args.output/name
        con.execute(f"COPY ({sql}) TO {q(path)} (FORMAT PARQUET,COMPRESSION ZSTD)")
        log("exported",file=str(path),bytes=path.stat().st_size)
    if scalar("SELECT count(*)-count(DISTINCT patent_id) FROM raw_domain"):
        raise ValueError("Domain has duplicate grant IDs: resolve joins before labeling")
    # A grant without an organizational owner is outside this organization-search
    # study; retain its source record but do not manufacture an externality label.
    con.execute("""CREATE TABLE candidates AS
      SELECT *,year(patent_date) AS year,
        CASE WHEN nullif(trim(application_id),'') IS NULL THEN 'GRANT:'||patent_id
             ELSE 'APPLICATION:'||application_id END AS application_key
      FROM raw_domain WHERE nullif(trim(assignee_id),'') IS NOT NULL
      QUALIFY row_number() OVER (PARTITION BY application_key ORDER BY patent_date,patent_id)=1""")
    log("candidate_table",n=scalar("SELECT count(*) FROM candidates"))
    # One row per citing-cited-category preserves category sensitivity without
    # multiplying observed relationships due to repeated source records.
    con.execute("""CREATE TABLE edges AS SELECT DISTINCT
      c.citing_id,c.cited_id,CAST(c.citing_date AS DATE) AS citing_date,c.citation_category,
      c.citing_assignee_id,c.citing_disambig_assignee_id,
      d.patent_date AS cited_date,d.year,
      d.assignee_id AS cited_assignee_id,d.disambig_assignee_id AS cited_disambig_assignee_id,
      nullif(trim(c.citing_assignee_id),'') IS NOT NULL AS known_citing_owner,
      coalesce(list_has_any(string_split(c.citing_assignee_id,'|'),string_split(d.assignee_id,'|')),false) AS overlapping_raw_owners,
      coalesce(list_has_any(string_split(c.citing_disambig_assignee_id,'|'),string_split(d.disambig_assignee_id,'|')),false) AS overlapping_disambig_owners,
      (nullif(c.citing_application_id,'') IS NOT NULL AND nullif(d.application_id,'') IS NOT NULL
        AND c.citing_application_id=d.application_id) AS same_application
      FROM raw_citations c JOIN candidates d ON c.cited_id=d.patent_id
      WHERE CAST(c.citing_date AS DATE)<=DATE '2024-12-31'""")
    log("edge_table",n=scalar("SELECT count(*) FROM edges"))
    export("""SELECT year,count(*) AS edges,count(*) FILTER (WHERE known_citing_owner) AS known_owner_edges,
      count(*) FILTER (WHERE overlapping_raw_owners) AS overlapping_owner_edges,
      count(*) FILTER (WHERE same_application) AS same_application_edges,
      count(*) FILTER (WHERE citing_date<cited_date) AS before_cited_grant_edges,
      count(*) FILTER (WHERE lower(citation_category) LIKE '%applicant%') AS applicant_edges
      FROM edges GROUP BY year ORDER BY year""","citation_coverage.parquet")
    # Grant-only visibility excludes earlier citing grants; their links can
    # reflect pre-grant publication, which this conservative design does not use.
    early="citing_date>=cited_date AND citing_date<=make_date(year,12,31)"
    future="citing_date>=make_date(year+1,1,1) AND citing_date<=make_date(year+3,12,31)"
    con.execute(f"""CREATE TABLE attention AS
      SELECT cited_id,
        count(DISTINCT owner) FILTER (WHERE {early}) AS early_external_attention,
        count(DISTINCT owner) FILTER (WHERE {future}) AS future_external_attention,
        count(DISTINCT owner) FILTER (WHERE {early} AND lower(citation_category) LIKE '%applicant%') AS early_applicant_attention,
        count(DISTINCT owner) FILTER (WHERE {future} AND lower(citation_category) LIKE '%applicant%') AS future_applicant_attention,
        count(DISTINCT citing_id) FILTER (WHERE {future}) AS future_external_citing_patents
      FROM edges,unnest(string_split(citing_assignee_id,'|')) AS u(owner)
      WHERE known_citing_owner AND NOT overlapping_raw_owners AND NOT coalesce(same_application,false)
        AND nullif(owner,'') IS NOT NULL AND citing_date>=cited_date
      GROUP BY cited_id""")
    con.execute(f"""CREATE TABLE disambiguated_attention AS
      SELECT cited_id,
        count(DISTINCT owner) FILTER (WHERE {early}) AS early_disambig_attention,
        count(DISTINCT owner) FILTER (WHERE {future}) AS future_disambig_attention
      FROM edges,unnest(string_split(citing_disambig_assignee_id,'|')) AS u(owner)
      WHERE nullif(cited_disambig_assignee_id,'') IS NOT NULL AND nullif(owner,'') IS NOT NULL
        AND NOT overlapping_disambig_owners AND NOT coalesce(same_application,false) AND citing_date>=cited_date
      GROUP BY cited_id""")
    # Only outcomes whose entire three-year window ends in the release are coded
    # zero. Later cohorts remain censored, never zero-filled for training.
    export("""SELECT d.* EXCLUDE(abstract,year),abstract AS patent_abstract,
      coalesce(a.early_external_attention,0)::DOUBLE AS early_external_attention,
      CASE WHEN d.year<=2021 THEN coalesce(a.future_external_attention,0)::DOUBLE END AS future_external_attention,
      coalesce(a.early_applicant_attention,0)::DOUBLE AS early_applicant_attention,
      CASE WHEN d.year<=2021 THEN coalesce(a.future_applicant_attention,0)::DOUBLE END AS future_applicant_attention,
      CASE WHEN d.year<=2021 THEN coalesce(a.future_external_citing_patents,0)::DOUBLE END AS future_external_citing_patents,
      CASE WHEN nullif(d.disambig_assignee_id,'') IS NOT NULL THEN coalesce(b.early_disambig_attention,0)::DOUBLE END AS early_disambig_attention,
      CASE WHEN d.year<=2021 AND nullif(d.disambig_assignee_id,'') IS NOT NULL THEN coalesce(b.future_disambig_attention,0)::DOUBLE END AS future_disambig_attention
      FROM candidates d LEFT JOIN attention a ON d.patent_id=a.cited_id
      LEFT JOIN disambiguated_attention b ON d.patent_id=b.cited_id""","study_patents.parquet")
    export("""SELECT patent_id,min(CAST(date AS DATE)) AS patent_date,first(title) AS patent_title,
      string_agg(DISTINCT assignee_id,'|' ORDER BY assignee_id) AS assignee_id,
      first(cpc_codes) AS cpc_codes,bool_or(is_core) AS is_core
      FROM raw_portfolios GROUP BY patent_id""","study_portfolios.parquet")
    export("""SELECT year(patent_date) AS year,count(*) AS n_patents,sum(is_core::INTEGER) AS n_core,
      count(*) FILTER (WHERE nullif(patent_abstract,'') IS NOT NULL) AS with_abstract,
      count(*) FILTER (WHERE nullif(cpc_codes,'') IS NOT NULL) AS with_classification,
      avg(future_external_attention) AS mean_external_attention,
      count(*) FILTER (WHERE future_external_attention>0) AS positive_attention,
      count(*) FILTER (WHERE future_applicant_attention>0) AS positive_applicant_attention
      FROM read_parquet("""+q(args.output/"study_patents.parquet")+") GROUP BY 1 ORDER BY 1","cohort_description.parquet")
    audit={"created_utc":dt.datetime.now(dt.timezone.utc).isoformat(),"release_end":"2024-12-31",
      "n_raw_domain":scalar("SELECT count(*) FROM raw_domain"),
      "n_no_organizational_owner":scalar("SELECT count(*) FROM raw_domain WHERE nullif(trim(assignee_id),'') IS NULL"),
      "n_canonical_candidates":scalar("SELECT count(*) FROM candidates"),
      "n_same_application_duplicates_removed":scalar("SELECT count(*) FROM raw_domain WHERE nullif(trim(assignee_id),'') IS NOT NULL")-scalar("SELECT count(*) FROM candidates"),
      "label_window":"Jan 1 of grant year+1 through Dec 31 of grant year+3",
      "early_window":"Cited grant date through Dec 31 of its grant year",
      "external":"Known, nonoverlapping full owner sets; no same application; distinct documented organization names",
      "unknown_owners":"Excluded from documented external-organization counts, coverage reported",
      "family_limit":"Application-level de-duplication only; complete international and continuation family links unavailable",
      "disambiguation":"Raw names for primary label, retrospective disambiguated IDs for outcome sensitivity only",
      "source_files":{name:{"path":str(path),"size_bytes":path.stat().st_size} for name,path in sources.items()}}
    (args.output/"label_audit.json").write_text(json.dumps(audit,indent=2),encoding="utf-8")
    con.close()
    log("canonical_data_complete",**audit)

if __name__=="__main__":main()
