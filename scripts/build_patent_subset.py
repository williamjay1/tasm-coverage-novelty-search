"""Streaming DuckDB construction of an auditable, grant-visible thermal patent corpus.

Memory is bounded; original ZIPs stay immutable on F:, all working copies stay on D:.
"""
import os
os.environ.update(OMP_NUM_THREADS='1', OPENBLAS_NUM_THREADS='1', MKL_NUM_THREADS='1')
import argparse,csv,datetime,hashlib,json,pathlib,re,shutil,sys,time,zipfile
ROOT=pathlib.Path(__file__).resolve().parents[1]
RAW=pathlib.Path(os.environ.get('TASM_RAW_ROOT', str(ROOT/'source_raw')))
import duckdb
WORK=ROOT/'datasets'/'patent_work';WORK.mkdir(exist_ok=True)
CON=duckdb.connect(str(WORK/'patents.duckdb'))
CON.execute("SET threads=1; SET memory_limit='3GB'; SET preserve_insertion_order=false;")
CON.execute("SET temp_directory='"+str(ROOT/'temp'/'duckdb_patents').replace('\\','/')+"'")
SCHEMAS=json.loads((ROOT/'datasets'/'patent_schemas.json').read_text(encoding='utf-8')) if (ROOT/'datasets'/'patent_schemas.json').exists() else {}

def q(s):return "'"+str(s).replace('\\','/').replace("'","''")+"'"
def log(*x):print(datetime.datetime.now().isoformat(timespec='seconds'),*x,flush=True)
def table_exists(t):return bool(CON.execute('SELECT count(*) FROM information_schema.tables WHERE table_name=?',[t]).fetchone()[0])
def extract(name):
    raw=RAW/f'zenodo_15058362_20260929__{name}.tsv.zip'
    dest=WORK/f'{name}.tsv'
    waited=0
    while not raw.exists():
        if waited%60==0:log('WAIT_RAW',raw.name)
        time.sleep(5);waited+=5
    with zipfile.ZipFile(raw) as z:
        info=z.infolist()[0]
        if not dest.exists() or dest.stat().st_size!=info.file_size:
            assert not dest.exists(),f'Partial extraction exists: {dest}'
            log('EXTRACT',name,info.file_size)
            with z.open(info) as source,dest.open('xb') as target:shutil.copyfileobj(source,target,4*1024*1024)
    with dest.open('r',encoding='utf-8',newline='') as f:SCHEMAS[name]=next(csv.reader(f,delimiter='\t'))
    (ROOT/'datasets'/'patent_schemas.json').write_text(json.dumps(SCHEMAS,indent=2),encoding='utf-8')
    log('SCHEMA',name,SCHEMAS[name])
    return dest
def src(name):return f"read_csv({q(extract(name))},header=true,delim='\t',quote='\"',escape='\"',all_varchar=true,strict_mode=true,nullstr='')"
def create(t,sql):
    if table_exists(t):log('REUSE_TABLE',t);return
    log('CREATE',t);started=time.time();CON.execute('CREATE TABLE '+t+' AS '+sql)
    log('CREATED',t,CON.execute('SELECT count(*) FROM '+t).fetchone()[0],round(time.time()-started,1))
    CON.execute('CHECKPOINT')
def create_partitioned(t,sql):
    # DISTINCT list/string aggregates cannot always spill. Hash partitions keep
    # their live state small; each completed partition is restartable.
    if table_exists(t):log('REUSE_TABLE',t);return
    parts=[]
    for bucket in range(16):
        part=f'{t}_part_{bucket:02d}';parts.append(part)
        create(part,sql.replace('__PARTITION__',f'hash(patent_id)%16={bucket}'))
    create(t,' UNION ALL '.join('SELECT * FROM '+part for part in parts))
def out(name,sql):
    path=ROOT/'datasets'/name
    if path.exists():log('REUSE_OUTPUT',name);return
    log('EXPORT',name);CON.execute(f"COPY ({sql}) TO {q(path)} (FORMAT PARQUET,COMPRESSION ZSTD)")
    log('EXPORTED',name,path.stat().st_size)

CORE="regexp_matches(code, '^H01M10/(6[0-9]|50)')"
NEAR="regexp_matches(code, '^(F28|B60H|H05K7/20|H01L23/(34|36|38|40|42|44|46))')"
THERMAL="(?i)(thermal manag|heat exchang|heat transfer|heat sink|heat dissipat|cooling (system|device|apparatus|module)|temperature control)"
BATTERY="(?i)(batter(y|ies)|electrochemical cell|secondary cell|accumulator)"
BTEMP="(?i)(thermal|temperatur|cool|heat)"

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--phase',choices=['metadata','domain','citations','all'],default='all');args=parser.parse_args()
    create('patents',f"SELECT patent_id,patent_type,TRY_CAST(patent_date AS DATE) AS patent_date,patent_title,wipo_kind,TRY_CAST(withdrawn AS INTEGER) AS withdrawn FROM {src('g_patent')}")
    out('patent_all_grants_meta.parquet',"SELECT * FROM patents WHERE patent_type='utility' AND withdrawn=0 AND patent_date BETWEEN DATE '2005-01-01' AND DATE '2024-12-31'")
    create('cpc',f"SELECT patent_id,cpc_sequence,cpc_group AS code,cpc_subclass,TRY_CAST(cpc_action_date AS DATE) AS action_date,cpc_version_indicator,cpc_type FROM {src('g_cpc_at_issue')}")
    create('cpc_domain_flags',f"SELECT patent_id,bool_or({CORE}) AS cpc_core,bool_or({NEAR}) AS cpc_near FROM cpc WHERE {CORE} OR {NEAR} GROUP BY patent_id")
    create('assignee_disambig',f"SELECT patent_id,assignee_sequence,assignee_id,disambig_assignee_organization AS assignee_name,assignee_type FROM {src('g_assignee_disambiguated')} WHERE NULLIF(disambig_assignee_organization,'') IS NOT NULL")
    out('patent_assignee_disambig.parquet','SELECT * FROM assignee_disambig')
    app=src('g_application')
    create('applications',f'SELECT * FROM {app}')
    if args.phase=='metadata':return
    # At-issue IPC and literal as-published organization names preserve pre-CPC coverage.
    ip=src('g_ipc_at_issue'); names=SCHEMAS['g_ipc_at_issue']
    ic=[x for x in ['ipc_section','section','ipc_class','ipc_subclass','class','subclass','main_group','subgroup','ipc_main_group','ipc_subgroup'] if x in names]
    # Inspect real headers before selecting the IPC expression; never guess silent mappings.
    sec='section' if 'section' in names else 'ipc_section';cla='ipc_class' if 'ipc_class' in names else 'class';sub='subclass' if 'subclass' in names else 'ipc_subclass'
    main='main_group' if 'main_group' in names else 'ipc_main_group';sg='subgroup' if 'subgroup' in names else 'ipc_subgroup'
    # The actual release changes zero padding across years; canonicalize without
    # discarding raw fields. A subgroup is a hierarchy string, not a number:
    # only its optional leading slash is removed, and one-digit values padded.
    group=f"regexp_replace(trim({sg}),'^/','')"
    subgroup=f"CASE WHEN length({group})=1 THEN lpad({group},2,'0') ELSE {group} END"
    code=f"upper(concat(trim({sec}),lpad(trim({cla}),2,'0'),trim({sub}),TRY_CAST(TRY_CAST({main} AS INTEGER) AS VARCHAR),'/',{subgroup}))"
    create('ipc',f'SELECT patent_id,{code} AS code,{sec} AS raw_section,{cla} AS raw_class,{sub} AS raw_subclass,{main} AS raw_main_group,{sg} AS raw_subgroup,action_date AS raw_action_date FROM {ip}')
    create('ipc_domain_flags',f"SELECT patent_id,bool_or({CORE}) AS ipc_core,bool_or({NEAR}) AS ipc_near FROM ipc WHERE {CORE} OR {NEAR} GROUP BY patent_id")
    ar=src('g_assignee_not_disambiguated'); an=SCHEMAS['g_assignee_not_disambiguated']
    name='raw_assignee_organization' if 'raw_assignee_organization' in an else 'assignee_organization'
    create('assignee_raw',f"SELECT patent_id,assignee_sequence,{name} AS raw_assignee_name,regexp_replace(upper(trim({name})),'[^A-Z0-9]','','g') AS raw_org_key FROM {ar} WHERE NULLIF({name},'') IS NOT NULL")
    create_partitioned('orgs',"SELECT patent_id,string_agg(DISTINCT raw_org_key,'|' ORDER BY raw_org_key) AS assignee_id,first(raw_org_key ORDER BY TRY_CAST(assignee_sequence AS INTEGER)) AS assignee_id_primary,string_agg(DISTINCT raw_assignee_name,'|' ORDER BY raw_assignee_name) AS assignee_name,list(DISTINCT raw_org_key ORDER BY raw_org_key) AS assignee_ids,list(DISTINCT raw_assignee_name ORDER BY raw_assignee_name) AS assignee_names FROM assignee_raw WHERE raw_org_key<>'' AND __PARTITION__ GROUP BY patent_id")
    create_partitioned('disambiguated_orgs',"SELECT patent_id,string_agg(DISTINCT assignee_id,'|' ORDER BY assignee_id) AS disambig_assignee_id,list(DISTINCT assignee_id ORDER BY assignee_id) AS disambig_assignee_ids,list(DISTINCT assignee_name ORDER BY assignee_name) AS disambig_assignee_names FROM assignee_disambig WHERE __PARTITION__ GROUP BY patent_id")
    create_partitioned('classification',"SELECT patent_id,string_agg(DISTINCT code,'|' ORDER BY code) AS cpc_at_issue,string_agg(DISTINCT cpc_subclass,'|' ORDER BY cpc_subclass) AS cpc_class_codes,list(DISTINCT cpc_subclass ORDER BY cpc_subclass) AS cpc_subclasses FROM cpc WHERE __PARTITION__ GROUP BY patent_id")
    create_partitioned('ipc_classification',"SELECT patent_id,string_agg(DISTINCT code,'|' ORDER BY code) AS ipc_at_issue,string_agg(DISTINCT substr(code,1,4),'|' ORDER BY substr(code,1,4)) AS ipc_class_codes FROM ipc WHERE __PARTITION__ GROUP BY patent_id")
    abstracts=src('g_patent_abstract'); ab='patent_abstract'
    create('domain_text_present',f"SELECT p.patent_id,p.patent_date,p.patent_title,a.{ab} AS abstract,coalesce(c.cpc_core,false) AS cpc_core,coalesce(c.cpc_near,false) AS cpc_near,coalesce(i.ipc_core,false) AS ipc_core,coalesce(i.ipc_near,false) AS ipc_near,(regexp_matches(concat(p.patent_title,' ',a.{ab}),{q(BATTERY)}) AND regexp_matches(concat(p.patent_title,' ',a.{ab}),{q(BTEMP)})) AS text_core FROM {abstracts} a JOIN patents p USING(patent_id) LEFT JOIN cpc_domain_flags c USING(patent_id) LEFT JOIN ipc_domain_flags i USING(patent_id) WHERE p.patent_type='utility' AND p.withdrawn=0 AND p.patent_date BETWEEN DATE '2010-01-01' AND DATE '2024-12-31' AND (coalesce(c.cpc_core,false) OR coalesce(c.cpc_near,false) OR coalesce(i.ipc_core,false) OR coalesce(i.ipc_near,false) OR regexp_matches(concat(p.patent_title,' ',a.{ab}),{q(THERMAL)}) OR (regexp_matches(concat(p.patent_title,' ',a.{ab}),{q(BATTERY)}) AND regexp_matches(concat(p.patent_title,' ',a.{ab}),{q(BTEMP)})))")
    # Keep coded candidates even if the abstract table omits their grant.
    create('domain_text',"SELECT * FROM domain_text_present UNION ALL SELECT p.patent_id,p.patent_date,p.patent_title,NULL AS abstract,coalesce(c.cpc_core,false),coalesce(c.cpc_near,false),coalesce(i.ipc_core,false),coalesce(i.ipc_near,false),false AS text_core FROM patents p LEFT JOIN cpc_domain_flags c USING(patent_id) LEFT JOIN ipc_domain_flags i USING(patent_id) WHERE p.patent_type='utility' AND p.withdrawn=0 AND p.patent_date BETWEEN DATE '2010-01-01' AND DATE '2024-12-31' AND (coalesce(c.cpc_core,false) OR coalesce(c.cpc_near,false) OR coalesce(i.ipc_core,false) OR coalesce(i.ipc_near,false)) AND NOT EXISTS(SELECT 1 FROM domain_text_present x WHERE x.patent_id=p.patent_id)")
    create('domain',"SELECT d.*,d.patent_date AS date,d.patent_title AS title,(cpc_core OR ipc_core) AS is_core,(cpc_core OR ipc_core OR text_core) AS is_core_broad,(cpc_core OR ipc_core) AS is_core_coded,o.assignee_id,o.assignee_id_primary,o.assignee_name,o.assignee_ids,o.assignee_names,dd.disambig_assignee_id,dd.disambig_assignee_ids,dd.disambig_assignee_names,c.cpc_at_issue,c.cpc_subclasses,ic.ipc_at_issue,concat_ws('|',c.cpc_class_codes,ic.ipc_class_codes) AS cpc_codes,a.application_id,a.filing_date AS filing_date_raw FROM domain_text d LEFT JOIN orgs o USING(patent_id) LEFT JOIN disambiguated_orgs dd USING(patent_id) LEFT JOIN classification c USING(patent_id) LEFT JOIN ipc_classification ic USING(patent_id) LEFT JOIN applications a USING(patent_id)")
    out('patent_domain.parquet','SELECT * FROM domain')
    # Export cross-domain title + classifications of every organization observed in core.
    create('core_orgs',"SELECT DISTINCT unnest(assignee_ids) AS assignee_id FROM domain WHERE is_core")
    out('patent_portfolios.parquet',"SELECT DISTINCT p.patent_id,p.patent_date AS date,p.patent_title AS title,r.raw_org_key AS assignee_id,r.raw_assignee_name AS assignee_name,c.cpc_at_issue,c.cpc_subclasses,ic.ipc_at_issue,concat_ws('|',c.cpc_class_codes,ic.ipc_class_codes) AS cpc_codes,(coalesce(cf.cpc_core,false) OR coalesce(ifl.ipc_core,false)) AS is_core FROM patents p JOIN assignee_raw r USING(patent_id) JOIN core_orgs f ON r.raw_org_key=f.assignee_id LEFT JOIN classification c USING(patent_id) LEFT JOIN ipc_classification ic USING(patent_id) LEFT JOIN cpc_domain_flags cf USING(patent_id) LEFT JOIN ipc_domain_flags ifl USING(patent_id) WHERE p.patent_type='utility' AND p.withdrawn=0 AND p.patent_date BETWEEN DATE '2005-01-01' AND DATE '2024-12-31'")
    summary=dict(coverage_end='2024-12-31',visibility='grant_publication',organization='as_published_name_upper_alphanumeric; no parent-group merging',domain_rows=CON.execute('SELECT count(*) FROM domain').fetchone()[0],year_counts=CON.execute('SELECT year(date),count(*),sum(is_core_broad::INTEGER),sum(is_core_coded::INTEGER),count(assignee_id) FROM domain GROUP BY 1 ORDER BY 1').fetchall(),year_count_columns=['year','domain_rows','broad_core_rows','coded_core_rows','with_organization_rows'],raw_tables=SCHEMAS)
    (ROOT/'datasets'/'patent_subset_summary.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8')
    log('DOMAIN_READY',summary['domain_rows'])
    if args.phase=='domain':return
    cites=src('g_us_patent_citation')
    cn=SCHEMAS['g_us_patent_citation'];cited='citation_patent_id' if 'citation_patent_id' in cn else 'citation_id'
    out('patent_citations.parquet',f"SELECT DISTINCT c.patent_id AS citing_id,p.patent_date AS citing_date,o.assignee_id AS citing_assignee_id,o.assignee_name AS citing_assignee_name,o.assignee_ids AS citing_assignee_ids,dd.disambig_assignee_id AS citing_disambig_assignee_id,dd.disambig_assignee_ids AS citing_disambig_assignee_ids,c.{cited} AS cited_id,c.citation_category,ca.application_id AS citing_application_id,d.application_id AS cited_application_id FROM {cites} c JOIN domain d ON c.{cited}=d.patent_id JOIN patents p ON c.patent_id=p.patent_id LEFT JOIN orgs o ON c.patent_id=o.patent_id LEFT JOIN disambiguated_orgs dd ON c.patent_id=dd.patent_id LEFT JOIN applications ca ON c.patent_id=ca.patent_id WHERE p.patent_type='utility' AND p.withdrawn=0 AND p.patent_date<=DATE '2024-12-31'")
    summary['citation_rows']=CON.execute(f"SELECT count(*) FROM read_parquet({q(ROOT/'datasets'/'patent_citations.parquet')})").fetchone()[0]
    (ROOT/'datasets'/'patent_subset_summary.json').write_text(json.dumps(summary,indent=2,default=str),encoding='utf-8')
    log('ALL_DONE',summary)

if __name__=='__main__':main()
