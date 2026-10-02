"""Data-quality audit; no model fit or outcome-based sample tuning."""
import os
os.environ.update(OMP_NUM_THREADS='1',OPENBLAS_NUM_THREADS='1',MKL_NUM_THREADS='1')
import argparse,datetime,hashlib,json,pathlib,stat,sys
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=pathlib.Path(os.environ.get('TASM_RAW_ROOT', str(ROOT/'source_raw')))
import duckdb
con=duckdb.connect()
con.execute("SET threads=1; SET memory_limit='2GB'")
con.execute("SET temp_directory='"+str(ROOT/'temp/duckdb_patent_audit').replace('\\','/')+"'")
def q(p):return "'"+str(p).replace('\\','/').replace("'","''")+"'"
def query(sql):
    cur=con.execute(sql)
    return [dict(zip([c[0] for c in cur.description],r)) for r in cur.fetchall()]
def digest(path,algo):
    h=hashlib.new(algo)
    with path.open('rb') as f:
        for b in iter(lambda:f.read(4*1024*1024),b''):h.update(b)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--applications-only',action='store_true');ap.add_argument('--classifications-only',action='store_true');ap.add_argument('--organizations-only',action='store_true');args=ap.parse_args()
    if args.organizations_only:
        path=ROOT/'datasets'/'patent_work'/'g_assignee_not_disambiguated.tsv'
        meta=ROOT/'datasets'/'patent_all_grants_meta.parquet'
        con.execute(f"CREATE TABLE named AS SELECT a.patent_id,a.raw_assignee_organization AS raw_name,regexp_replace(upper(trim(a.raw_assignee_organization)),'[^A-Z0-9]','','g') AS raw_key FROM read_csv({q(path)},header=true,delim='\t',all_varchar=true,nullstr='') a JOIN read_parquet({q(meta)}) p USING(patent_id) WHERE a.raw_assignee_organization IS NOT NULL")
        result={'rows':query("SELECT count(*) n_rows,count(DISTINCT raw_key) normalized_keys,count(DISTINCT raw_name) raw_names,count(*) FILTER(WHERE raw_key='') empty_normalized_rows,count(*) FILTER(WHERE regexp_matches(raw_name,'[^\\x00-\\x7F]')) non_ascii_name_rows FROM named"),'multiple_names':query("SELECT count(*) normalized_keys_with_multiple_literal_names,sum(n) literal_names_in_these_keys FROM (SELECT raw_key,count(DISTINCT raw_name) n FROM named WHERE raw_key<>'' GROUP BY raw_key HAVING n>1)"),'empty_examples':query("SELECT patent_id,raw_name FROM named WHERE raw_key='' LIMIT 10")}
        (ROOT/'datasets'/'patent_organization_name_audit.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8');print(json.dumps(result,default=str));return
    if args.classifications_only:
        con.execute(f"CREATE VIEW grants AS SELECT patent_id,patent_date FROM read_parquet({q(ROOT/'datasets'/'patent_all_grants_meta.parquet')})")
        result={}
        for table,field in [('g_cpc_at_issue','cpc_action_date'),('g_ipc_at_issue','action_date')]:
            path=ROOT/'datasets'/'patent_work'/(table+'.tsv')
            source=f"read_csv({q(path)},header=true,delim='\t',all_varchar=true,nullstr='')"
            result[table]=query(f"SELECT count(*) n_rows,count(*) FILTER(WHERE TRY_CAST(c.{field} AS DATE) IS NULL) unknown_action_date,count(*) FILTER(WHERE TRY_CAST(c.{field} AS DATE)>p.patent_date) after_grant,count(*) FILTER(WHERE TRY_CAST(c.{field} AS DATE)=p.patent_date) at_grant,count(*) FILTER(WHERE TRY_CAST(c.{field} AS DATE)<p.patent_date) before_grant FROM {source} c JOIN grants p USING(patent_id)")
            result[table+'_later_examples']=query(f"SELECT c.patent_id,c.{field} AS action_date,p.patent_date FROM {source} c JOIN grants p USING(patent_id) WHERE TRY_CAST(c.{field} AS DATE)>p.patent_date LIMIT 10")
        (ROOT/'datasets'/'patent_classification_date_audit.json').write_text(json.dumps(result,indent=2,default=str),encoding='utf-8')
        print(json.dumps(result,default=str));return
    app=ROOT/'datasets'/'patent_work'/'g_application.tsv'
    con.execute(f"CREATE VIEW app AS SELECT * FROM read_csv({q(app)},header=true,delim='\t',all_varchar=true,nullstr='')")
    report={'audited_utc':datetime.datetime.now(datetime.timezone.utc).isoformat()}
    prior_path=ROOT/'datasets'/'patent_application_audit.json'
    prior=json.loads(prior_path.read_text(encoding='utf-8')) if prior_path.exists() and not args.applications_only else {}
    def app_query(key,sql):return prior[key] if key in prior else query(sql)
    if prior:report['application_audit_reused_utc']=prior['audited_utc']
    report['applications']=app_query('applications',"SELECT count(*) AS n_rows,count(DISTINCT patent_id) patents,count(DISTINCT application_id) applications,count(*) FILTER(WHERE application_id IS NULL) missing_application,count(*) FILTER(WHERE substr(application_id,1,2)<>series_code) prefix_series_mismatch,count(*) FILTER(WHERE NOT regexp_full_match(application_id,'[0-9]{8}')) non_eight_digit FROM app")
    report['application_shapes']=app_query('application_shapes',"SELECT length(application_id) length,substr(application_id,1,2) prefix,series_code,count(*) n FROM app GROUP BY ALL ORDER BY n DESC LIMIT 20")
    report['duplicate_applications']=app_query('duplicate_applications',"SELECT count(*) repeated_ids,sum(n) grants_in_repeated_ids FROM (SELECT application_id,count(DISTINCT patent_id) n FROM app WHERE application_id IS NOT NULL GROUP BY 1 HAVING n>1)")
    metadata=ROOT/'datasets'/'patent_all_grants_meta.parquet'
    con.execute(f"CREATE VIEW study_app AS SELECT a.*,p.patent_date FROM app a JOIN read_parquet({q(metadata)}) p USING(patent_id)")
    report['study_applications']=app_query('study_applications',"SELECT count(*) n_rows,count(DISTINCT application_id) applications,count(*) FILTER(WHERE NOT regexp_full_match(application_id,'[0-9]{8}')) non_eight_digit,count(*) FILTER(WHERE substr(application_id,1,2)<>series_code) prefix_series_mismatch FROM study_app")
    report['study_app_cross_series']=app_query('study_app_cross_series',"SELECT application_id,string_agg(DISTINCT series_code,'|') series_codes,count(*) n FROM study_app GROUP BY 1 HAVING count(DISTINCT series_code)>1 ORDER BY n DESC LIMIT 20")
    report['study_app_nonstandard_examples']=app_query('study_app_nonstandard_examples',"SELECT application_id,patent_id,series_code,patent_date FROM study_app WHERE NOT regexp_full_match(application_id,'[0-9]{8}') OR substr(application_id,1,2)<>series_code LIMIT 20")
    if args.applications_only:
        target=ROOT/'datasets'/'patent_application_audit.json'
        target.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8');print(json.dumps(report,default=str));return
    for name,short in [('patent_domain','d'),('patent_portfolios','p'),('patent_citations','c'),('patent_all_grants_meta','m')]:
        path=ROOT/'datasets'/(name+'.parquet');assert path.exists(),path
        con.execute(f'CREATE VIEW {short} AS SELECT * FROM read_parquet({q(path)})')
    report['domain']=query("SELECT count(*) AS n_rows,count(DISTINCT patent_id) distinct_patents,min(date) first_date,max(date) last_date,sum(is_core::INTEGER) core_rows,sum(is_core_broad::INTEGER) broad_core_rows,count(*) FILTER(WHERE assignee_id IS NULL OR assignee_id='') unknown_org_rows,count(*) FILTER(WHERE abstract IS NULL OR abstract='') missing_abstract_rows,count(*) FILTER(WHERE title IS NULL OR title='') missing_title_rows,count(*) FILTER(WHERE application_id IS NULL) missing_application FROM d")
    report['domain_years']=query("SELECT year(date) AS grant_year,count(*) n,sum(is_core::INTEGER) core,sum(cpc_core::INTEGER) cpc_core,sum(ipc_core::INTEGER) ipc_core,count(*) FILTER(WHERE cpc_at_issue IS NOT NULL) with_cpc,count(*) FILTER(WHERE ipc_at_issue IS NOT NULL) with_ipc,count(*) FILTER(WHERE assignee_id IS NULL) unknown_org,count(*) FILTER(WHERE abstract IS NULL OR abstract='') missing_abstract FROM d GROUP BY 1 ORDER BY 1")
    report['portfolio']=query("SELECT count(*) AS n_rows,count(DISTINCT patent_id) patents,count(DISTINCT assignee_id) organizations,min(date) first_date,max(date) last_date,count(*) FILTER(WHERE is_core AND date<DATE '2010-01-01') early_core_rows FROM p")
    report['portfolio_duplicate_keys']=query("SELECT count(*) repeated_keys FROM (SELECT patent_id,assignee_id,count(*) n FROM p GROUP BY 1,2 HAVING n>1)")
    report['citation']=query("SELECT count(*) AS n_rows,count(DISTINCT (citing_id,cited_id)) distinct_pairs,count(DISTINCT cited_id) cited_patents,count(DISTINCT citing_id) citing_patents,min(citing_date) first_date,max(citing_date) last_date,count(*) FILTER(WHERE citing_assignee_id IS NULL OR citing_assignee_id='') unknown_citing_org_rows,count(*) FILTER(WHERE citing_application_id IS NULL) missing_citing_application_rows,count(*) FILTER(WHERE citing_application_id=cited_application_id) same_application_rows FROM c")
    report['citation_categories']=query("SELECT citation_category,count(*) AS n_rows,count(DISTINCT (citing_id,cited_id)) pairs,count(*) FILTER(WHERE citing_assignee_id IS NULL) unknown_org_rows FROM c GROUP BY 1 ORDER BY n_rows DESC")
    report['citation_years']=query("SELECT year(citing_date) AS citing_year,count(*) AS n_rows,count(*) FILTER(WHERE citing_assignee_id IS NULL) unknown_org_rows FROM c GROUP BY 1 ORDER BY 1")
    report['citation_order']=query("SELECT count(*) before_cited_grant_rows FROM c JOIN d ON c.cited_id=d.patent_id WHERE c.citing_date<d.date")
    report['grant_coverage']=query("SELECT year(patent_date) AS grant_year,count(*) AS n_rows,max(patent_date) last_grant FROM m GROUP BY 1 ORDER BY 1")
    print('COUNTS',json.dumps({k:report[k] for k in ['domain','portfolio','citation','citation_categories','citation_order']},default=str),flush=True)
    meta=json.loads((RAW/'zenodo_15058362_20260929__record.json').read_text(encoding='utf-8'))
    report['verified_raw']=[]
    for entry in meta['files']:
        path=RAW/('zenodo_15058362_20260929__'+entry['key'])
        if not path.exists():continue
        checksum=digest(path,'md5');expected=entry['checksum'].split(':')[1]
        record={'file':path.name,'bytes':path.stat().st_size,'md5':checksum,'checksum_matches':checksum==expected,'size_matches':path.stat().st_size==entry['size'],'readonly':not bool(path.stat().st_mode & stat.S_IWRITE)}
        report['verified_raw'].append(record)
        assert record['checksum_matches'] and record['size_matches'] and record['readonly'],record
    report['output_manifest']=[]
    for name in ['patent_domain.parquet','patent_portfolios.parquet','patent_citations.parquet','patent_all_grants_meta.parquet','patent_assignee_disambig.parquet']:
        path=ROOT/'datasets'/name
        report['output_manifest'].append({'file':path.name,'bytes':path.stat().st_size,'sha256':digest(path,'sha256')})
    assert report['domain'][0]['n_rows']==report['domain'][0]['distinct_patents'],'Duplicate grant rows in domain'
    assert report['applications'][0]['n_rows']==report['applications'][0]['patents'],'Nonunique application join'
    report['audit_status']='completed_with_reported_coverage_limits'
    target=ROOT/'datasets'/'patent_quality_audit.json';target.write_text(json.dumps(report,indent=2,default=str),encoding='utf-8')
    print(json.dumps(report,default=str))
if __name__=='__main__':main()
