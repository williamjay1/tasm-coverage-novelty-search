"""Locked new-task policy transport: electronics thermal conditioning.

No v1/v2 artifact is changed. Protocol and label-free lists are saved before
electronics task outcome evaluation. Frozen predictors know broad thermal data.
"""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
import argparse, datetime as dt, hashlib, itertools, json, re
from pathlib import Path
import duckdb
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from policy_core import quota_select, stable_order

ROOT=Path(__file__).resolve().parents[1]
DS=ROOT/'datasets/revision_v3'; RS=ROOT/'results/revision_v3'
ELEC=re.compile(r'^H05K7/20'); BAT=re.compile(r'^H01M10/(6[0-9]|50)')
PROTO={
 'task':'H05K7/20 electronics thermal conditioning, CPC or IPC and descendants',
 'official_definition':'https://www.uspto.gov/web/patents/classification/cpc/html/defH05K.html',
 'interpretation':'Cooling, ventilating or heating arrangements for electric apparatus; coded association, not applicability',
 'origins':[2018,2019,2020,2021], 'history_years':5,
 'identity':'As-published upper-alphanumeric owner names; full owner sets',
 'eligibility':{'total_grants_min':15,'pure_electronics_core_grants_min':3,'classified_fraction_min':.8},
 'candidate_source':'Frozen current-grant v1 broad thermal candidate universe; remove any battery coded candidate and union of previously evaluated battery shortlist grant IDs',
 'prior_list_exclusion':'All selected_primary_*.parquet in primary_v1 and text_distance_v1; decision_selected*.parquet, taskpool_raw_selected*.parquet, taskpool_disambig_selected*.parquet and fine_core_slot_selected.parquet in revision_v2. Union across years, policies, boundaries and models before outcomes',
 'core_definition':'CPC/IPC H05K7/20-prefix and no CPC/IPC battery H01M10/(6[0-9]|50)-prefix',
 'task_profile':'Focal prior-five-year pure electronics core title centroid',
 'vocabulary':'Original mature-origin TFIDF title fit, 2010 to t-3; max20000 min_df2 max_df.98 unigram/bigram English-stopwords sublinear float32',
 'admission':{'title_cosine_min':.03,'external_owner':True,'classified':True,'pool_min':50},
 'models':['boosting','ridge'], 'K':30, 'core_C':9,
 'policies':['forecast_top30','fixed_core9','fixed_core9_pair3'],
 'novelty':'At least one unordered four-character CPC/IPC subclass pair absent from focal pure-core five-year history',
 'pair_quota':{'core_share':.3,'minimum_newpair_core':3},
 'feasibility':'Require >=9 core and >=21 noncore pool patents; pair policy also >=3 newpair core. Report failures, do not change capacity/definition',
 'selection':'Original score descending and stable patent-ID ties; pair3 reserves 3 novel core then fills remaining6 core by score; same21 noncore across fixed policies',
 'primary_outcome':'At least one external pure-electronics-core citing grant, t+1 through t+3',
 'secondary_outcomes':['General external >=2 raw organizations','Applicant-category external >=2 raw organizations'],
 'filters':'Known citing owner, full citing/cited owner-set nonoverlap, different known application; utility nonwithdrawn grant; no battery-coded electronics citing core',
 'inference':'Paired organization bootstrap2000, seed20261001, retain all sampled organization origins, denominator sampled situation count',
 'planned_contrasts':['fixed_core9 minus forecast_top30','fixed_core9_pair3 minus fixed_core9','fixed_core9_pair3 minus forecast_top30'],
 'transport_boundary':'Task not used for original policy design; shared 2018-21 period and broad thermal corpus, predictors may train on electronics. Not prospective or unseen prediction domain',
 'no_outcome_driven_changes':True,
}
def q(p): return "'"+str(p).replace('\\','/').replace("'","''")+"'"
def codes(v): return {x for x in str(v).split('|') if x and x not in {'nan','None'}}
def pairs(v): return set(itertools.combinations(sorted(v),2))
def now():return dt.datetime.now(dt.timezone.utc).isoformat()
def log(event,**kw):print(json.dumps({'utc':now(),'event':event,**kw},default=str),flush=True)
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def connect():
 DS.mkdir(parents=True,exist_ok=True);RS.mkdir(parents=True,exist_ok=True)
 c=duckdb.connect(str(DS/'validation.duckdb'))
 c.execute("SET threads=2; SET memory_limit='3GB'; SET preserve_insertion_order=false")
 temp=DS/'validation_temp';temp.mkdir(exist_ok=True)
 c.execute('SET temp_directory='+q(temp))
 c.execute('ATTACH '+q(ROOT/'datasets/patent_work/patents.duckdb')+' AS source (READ_ONLY)')
 return c
def export(c,sql,p):
 c.execute('COPY ('+sql+') TO '+q(p)+' (FORMAT PARQUET, COMPRESSION ZSTD)')
 log('export',file=p.name,rows=c.execute('SELECT count(*) FROM read_parquet('+q(p)+')').fetchone()[0],bytes=p.stat().st_size)
def freeze():
 RS.mkdir(parents=True,exist_ok=True)
 p=RS/'validation_protocol.json'
 if p.exists():
  old=json.loads(p.read_text(encoding='utf-8'))
  if old['protocol']!=PROTO:raise AssertionError('Protocol already locked; no silent amendments allowed')
 else:p.write_text(json.dumps({'locked_utc':now(),'stage':'before electronics outcome evaluation','protocol':PROTO},indent=2),encoding='utf-8')
 log('locked_protocol',sha256=sha(p))
def prepare():
 freeze();c=connect()
 prior=[]
 for folder in ['primary_v1','text_distance_v1']:
  prior.extend(sorted((ROOT/'results'/folder).glob('selected_primary_*.parquet')))
 for pattern in ['decision_selected*.parquet','taskpool_raw_selected*.parquet','taskpool_disambig_selected*.parquet','fine_core_slot_selected.parquet']:
  prior.extend(sorted((ROOT/'results/revision_v2').glob(pattern)))
 old_ids=set();source_manifest=[]
 for p in prior:
  old_ids.update(pd.read_parquet(p,columns=['patent_id']).patent_id.astype(str))
  source_manifest.append({'path':str(p.relative_to(ROOT)),'sha256':sha(p)})
 pd.DataFrame({'patent_id':sorted(old_ids)}).to_parquet(DS/'validation_prior_selected_ids.parquet',index=False)
 (RS/'validation_prior_list_manifest.json').write_text(json.dumps({'files':source_manifest,'unique_prior_selected_ids':len(old_ids),'union_sha256':sha(DS/'validation_prior_selected_ids.parquet')},indent=2),encoding='utf-8')
 cp="regexp_matches(coalesce(c.cpc_at_issue,''),'(^|\\|)H05K7/20') OR regexp_matches(coalesce(i.ipc_at_issue,''),'(^|\\|)H05K7/20')"
 bp="regexp_matches(coalesce(c.cpc_at_issue,''),'(^|\\|)H01M10/(6[0-9]|50)') OR regexp_matches(coalesce(i.ipc_at_issue,''),'(^|\\|)H01M10/(6[0-9]|50)')"
 c.execute(f"""CREATE OR REPLACE TABLE validation_electronics_grants AS
 SELECT p.*,o.assignee_id,o.assignee_ids,c.cpc_at_issue,i.ipc_at_issue,
 concat_ws('|',c.cpc_class_codes,i.ipc_class_codes) AS cpc_codes,
 ({cp}) AS electronics_core,({bp}) AS battery_core
 FROM source.patents p LEFT JOIN source.orgs o USING(patent_id)
 LEFT JOIN source.classification c USING(patent_id) LEFT JOIN source.ipc_classification i USING(patent_id)
 WHERE p.patent_type='utility' AND p.withdrawn=0
 AND p.patent_date BETWEEN DATE '2013-01-01' AND DATE '2024-12-31' AND ({cp})""")
 c.execute("CREATE OR REPLACE TABLE validation_orgs AS SELECT DISTINCT owner AS organization_id FROM validation_electronics_grants,unnest(assignee_ids)u(owner) WHERE NOT battery_core AND patent_date<=DATE '2020-12-31' AND nullif(owner,'') IS NOT NULL")
 c.execute(f"""CREATE OR REPLACE TABLE validation_portfolios AS
 SELECT p.patent_id,p.patent_date,p.patent_title,o.assignee_id,c.cpc_at_issue,i.ipc_at_issue,
 concat_ws('|',c.cpc_class_codes,i.ipc_class_codes) AS cpc_codes,
 ({cp}) AND NOT ({bp}) AS electronics_core,({bp}) AS battery_core
 FROM source.patents p JOIN source.orgs o USING(patent_id)
 LEFT JOIN source.classification c USING(patent_id) LEFT JOIN source.ipc_classification i USING(patent_id)
 WHERE p.patent_type='utility' AND p.withdrawn=0
 AND p.patent_date BETWEEN DATE '2013-01-01' AND DATE '2020-12-31'
 AND EXISTS(SELECT 1 FROM source.assignee_raw r JOIN validation_orgs v ON r.raw_org_key=v.organization_id WHERE r.patent_id=p.patent_id)""")
 export(c,'SELECT * FROM validation_portfolios',DS/'validation_portfolios.parquet')
 export(c,'SELECT * FROM validation_electronics_grants',DS/'validation_electronics_grants.parquet')
 report={'prepared_utc':now(),'complete_history_source':'All utility nonwithdrawn source grants and all original as-published owners, not old battery portfolio subset',
 'electronics_grants':c.execute('SELECT count(*),sum(battery_core::INT),sum((NOT battery_core)::INT) FROM validation_electronics_grants').fetchone(),
 'eligible_owner_universe':c.execute('SELECT count(*) FROM validation_orgs').fetchone()[0],
 'portfolio_grants':c.execute('SELECT count(*),count(DISTINCT patent_id) FROM validation_portfolios').fetchone(),
 'no_new_download':True,'protocol_sha256':sha(RS/'validation_protocol.json')}
 (RS/'validation_feasibility.json').write_text(json.dumps(report,indent=2),encoding='utf-8');c.close();log('prepared',**report)
def select():
 freeze()
 prior_ids=set(pd.read_parquet(DS/'validation_prior_selected_ids.parquet').patent_id.astype(str))
 hist=pd.read_parquet(DS/'validation_portfolios.parquet');hist['year']=pd.to_datetime(hist.patent_date).dt.year
 hist['owners']=hist.assignee_id.fillna('').map(codes);hist['subclasses']=hist.cpc_codes.fillna('').map(codes)
 patents=pd.read_parquet(ROOT/'datasets/canonical_v1/study_patents.parquet',columns=['patent_id','patent_date','patent_title'])
 patents['year']=pd.to_datetime(patents.patent_date).dt.year
 situations=[];selections=[];poolrows=[];checks=[]
 for year in PROTO['origins']:
  train=patents.loc[(patents.year>=2010)&(patents.year<=year-3)]
  tv=TfidfVectorizer(max_features=20000,min_df=2,max_df=.98,ngram_range=(1,2),stop_words='english',dtype=np.float32,sublinear_tf=True)
  tv.fit(train.patent_title.fillna(''))
  cols=['patent_id','patent_title','assignee_id','cpc_codes','cpc_at_issue','ipc_at_issue','score_boosting','score_ridge']
  cur=pd.read_parquet(ROOT/f'results/primary_v1/scores_{year}.parquet',columns=cols)
  cur['battery_core']=[any(BAT.match(x) for x in codes(c)|codes(i)) for c,i in zip(cur.cpc_at_issue.fillna(''),cur.ipc_at_issue.fillna(''))]
  removed_battery=int(cur.battery_core.sum());original_n=len(cur)
  removed_prior=int((~cur.battery_core & cur.patent_id.astype(str).isin(prior_ids)).sum())
  cur=cur.loc[~cur.battery_core & ~cur.patent_id.astype(str).isin(prior_ids)].reset_index(drop=True)
  cur['owners']=cur.assignee_id.fillna('').map(codes);cur['subclasses']=cur.cpc_codes.fillna('').map(codes)
  cur['electronics_core']=[any(ELEC.match(x) for x in codes(c)|codes(i)) for c,i in zip(cur.cpc_at_issue.fillna(''),cur.ipc_at_issue.fillna(''))]
  cur['pairs']=cur.subclasses.map(pairs)
  h=hist.loc[(hist.year>=year-5)&(hist.year<year)].reset_index(drop=True)
  mem=h[['patent_id','owners','electronics_core']].explode('owners').dropna(subset=['owners'])
  n=mem.groupby('owners').patent_id.nunique();nc=mem.loc[mem.electronics_core].groupby('owners').patent_id.nunique()
  elig=n.loc[(n>=15)&(nc.reindex(n.index,fill_value=0)>=3)].sort_index();groups=mem.groupby('owners').groups
  xh=tv.transform(h.patent_title.fillna(''));xc=tv.transform(cur.patent_title.fillna(''))
  ids=cur.patent_id.astype(str).to_numpy();core=cur.electronics_core.to_numpy(bool);cp=cur.pairs.tolist()
  for org in elig.index:
   ii=np.asarray(groups[org],int);ci=ii[h.iloc[ii].electronics_core.to_numpy(bool)]
   coverage=float(h.iloc[ii].subclasses.map(bool).mean())
   common={'organization_id':str(org),'year':year,'history_n':len(ii),'core_history_n':len(ci),'classification_coverage':coverage}
   if coverage<.8:situations.append({**common,'status':'classification_below_.8'});continue
   hp=set().union(*(pairs(s) for s in h.iloc[ci].subclasses))
   centroid=normalize(sparse.csr_matrix(np.asarray(xh[ci].mean(axis=0))))
   sim=(xc@centroid.T).toarray().ravel()
   ext=np.asarray([bool(o) and org not in o for o in cur.owners]);classified=cur.subclasses.map(bool).to_numpy()
   pi=np.flatnonzero(ext&classified&(sim>=.03));pc=core[pi]
   new=np.asarray([bool(core[j]) and bool(cp[j]-hp) for j in pi])
   status='feasible'
   if len(pi)<50:status='pool_below50'
   elif pc.sum()<9:status='core_supply_below9'
   elif (~pc).sum()<21:status='noncore_supply_below21'
   elif new.sum()<3:status='newpair_core_supply_below3'
   common.update(pool_n=len(pi),core_pool_n=int(pc.sum()),newpair_core_pool_n=int(new.sum()),status=status)
   situations.append(common)
   if status!='feasible':continue
   poolrows.extend([{'organization_id':str(org),'year':year,'patent_id':str(ids[j]),'electronics_core':bool(core[j]),'newpair':bool(new[z]),'task_similarity':float(sim[j])} for z,j in enumerate(pi)])
   for model in PROTO['models']:
    score=cur.iloc[pi]['score_'+model].to_numpy();pids=ids[pi]
    order=stable_order(score,pids);ic=order[pc[order]];inn=order[~pc[order]]
    base=order[:30];blind=np.r_[ic[:9],inn[:21]]
    # Existing nearest-integer quota K9 share.3 reserves3 and score-fills six.
    novcore=quota_select(score[ic],pids[ic],new[ic],9,.3)
    novel=np.r_[ic[novcore],inn[:21]]
    assert len(set(blind))==len(set(novel))==30
    assert int(pc[blind].sum())==int(pc[novel].sum())==9
    assert set(blind[~pc[blind]])==set(novel[~pc[novel]])
    assert new[novel].sum()>=3
    checks.append({'organization_id':str(org),'year':year,'model':model,'core_counts_match':True,'noncore_ids_match':True,'pair3_met':True,'pair_core_changed_n':len(set(novel[pc[novel]])-set(blind[pc[blind]]))})
    for policy,sel in [('forecast_top30',base),('fixed_core9',blind),('fixed_core9_pair3',novel)]:
     selections.extend([{'organization_id':str(org),'year':year,'model':model,'policy':policy,'rank':z+1,'patent_id':str(pids[j]),'electronics_core':bool(pc[j]),'newpair':bool(new[j]),'task_similarity':float(sim[pi[j]])} for z,j in enumerate(sel)])
  log('selection_year_done',year=year,original_candidates=original_n,excluded_battery_candidates=removed_battery,excluded_additional_prior_selected=removed_prior,new_candidates=len(cur),eligible_orgs=len(elig),situations=sum(s['year']==year for s in situations),feasible=sum(s['year']==year and s['status']=='feasible' for s in situations))
 pd.DataFrame(situations).to_parquet(RS/'validation_situations.parquet',index=False)
 pd.DataFrame(selections).to_parquet(RS/'validation_selected.parquet',index=False)
 pd.DataFrame(poolrows).to_parquet(RS/'validation_pools.parquet',index=False)
 pd.DataFrame(checks).to_csv(RS/'validation_capacity_audit.csv',index=False)
 manifest={'selected_without_labels_utc':now(),'protocol_sha256':sha(RS/'validation_protocol.json'),'selections_sha256':sha(RS/'validation_selected.parquet'),'situations':len(situations),'feasible_situations':sum(s['status']=='feasible' for s in situations),'selected_rows':len(selections),'capacity_checks':len(checks),'label_columns_loaded_for_selection':[]}
 (RS/'validation_selection_lock.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8');log('selection_locked',**manifest)
def labels():
 freeze();lock=json.loads((RS/'validation_selection_lock.json').read_text(encoding='utf-8'))
 assert lock['selections_sha256']==sha(RS/'validation_selected.parquet')
 c=connect();c.execute('ATTACH '+q(ROOT/'datasets/canonical_v1/labels.duckdb')+' AS canonical (READ_ONLY)')
 c.execute('CREATE OR REPLACE TABLE validation_candidates AS SELECT DISTINCT patent_id,year FROM read_parquet('+q(RS/'validation_pools.parquet')+')')
 c.execute("""CREATE OR REPLACE TABLE validation_task_edges AS
 SELECT e.*,g.cpc_at_issue AS citing_cpc_at_issue,g.ipc_at_issue AS citing_ipc_at_issue,
 coalesce(g.electronics_core AND NOT g.battery_core,false) AS pure_electronics_core,
 lower(e.citation_category) LIKE '%applicant%' AS is_applicant,
 try_cast(a.filing_date AS DATE)>make_date(e.year,12,31) AS citing_filed_after_origin
 FROM canonical.edges e JOIN validation_candidates d ON e.cited_id=d.patent_id
 LEFT JOIN validation_electronics_grants g ON g.patent_id=e.citing_id
 LEFT JOIN source.applications a ON a.patent_id=e.citing_id
 WHERE e.known_citing_owner AND NOT e.overlapping_raw_owners
 AND NOT coalesce(e.same_application,false)
 AND e.citing_date>=make_date(e.year+1,1,1) AND e.citing_date<=make_date(e.year+3,12,31)
 AND e.citing_date>=e.cited_date""")
 c.execute("""CREATE OR REPLACE TABLE validation_attention AS
 SELECT cited_id AS patent_id,
 count(DISTINCT owner) AS general_orgs,
 count(DISTINCT owner) FILTER(WHERE is_applicant) AS applicant_orgs,
 count(DISTINCT citing_id) FILTER(WHERE pure_electronics_core) AS electronics_core_patents,
 count(DISTINCT citing_id) FILTER(WHERE pure_electronics_core AND is_applicant) AS electronics_core_applicant_patents
 FROM validation_task_edges,unnest(string_split(citing_assignee_id,'|'))u(owner)
 WHERE nullif(owner,'') IS NOT NULL GROUP BY cited_id""")
 export(c,"SELECT d.*,coalesce(general_orgs,0) AS general_orgs,coalesce(applicant_orgs,0) AS applicant_orgs,coalesce(electronics_core_patents,0) AS electronics_core_patents,coalesce(electronics_core_applicant_patents,0) AS electronics_core_applicant_patents,coalesce(general_orgs,0)>=2 AS general,coalesce(applicant_orgs,0)>=2 AS applicant,coalesce(electronics_core_patents,0)>=1 AS task FROM validation_candidates d LEFT JOIN validation_attention a USING(patent_id)",DS/'validation_labels.parquet')
 export(c,'SELECT * FROM validation_task_edges',DS/'validation_edges.parquet')
 # Raw code rows independently reconstruct all task citing-code membership.
 mismatch=c.execute("""SELECT count(*) FROM (SELECT e.citing_id,bool_or(regexp_matches(code,'^H05K7/20')) AS ec,bool_or(regexp_matches(code,'^H01M10/(6[0-9]|50)')) AS bc FROM (SELECT DISTINCT citing_id FROM validation_task_edges)e JOIN (SELECT patent_id,code FROM source.cpc UNION ALL SELECT patent_id,code FROM source.ipc)r ON e.citing_id=r.patent_id GROUP BY e.citing_id)a JOIN (SELECT DISTINCT citing_id,pure_electronics_core FROM validation_task_edges)b USING(citing_id) WHERE (ec AND NOT bc)<>pure_electronics_core""").fetchone()[0]
 assert mismatch==0
 reconc=c.execute('SELECT count(*) FROM read_parquet('+q(DS/'validation_labels.parquet')+')l JOIN read_parquet('+q(ROOT/'datasets/canonical_v1/study_patents.parquet')+")p USING(patent_id) WHERE l.general_orgs<>p.future_external_attention OR l.applicant_orgs<>p.future_applicant_attention").fetchone()[0]
 assert reconc==0
 audit={'evaluation_started_utc':now(),'protocol_sha256':lock['protocol_sha256'],'fixed_selections_sha256':lock['selections_sha256'],'task_code_raw_row_mismatches':mismatch,'general_applicant_v1_exact_count_mismatches':reconc,'three_year_edges':c.execute('SELECT count(*),sum(pure_electronics_core::INT) FROM validation_task_edges').fetchone(),'no_battery_coded_candidates':c.execute("SELECT count(*) FROM validation_candidates d JOIN source.domain p USING(patent_id) WHERE p.is_core").fetchone()[0]}
 assert audit['no_battery_coded_candidates']==0
 (RS/'validation_label_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8');c.close();log('labels_completed',**audit)
def evaluate(replay=False):
 # Derived replay needs only released validation lists/labels/pools, not source DB.
 lock=json.loads((RS/'validation_selection_lock.json').read_text(encoding='utf-8'))
 assert lock['selections_sha256']==sha(RS/'validation_selected.parquet')
 sels=pd.read_parquet(RS/'validation_selected.parquet'); labs=pd.read_parquet(DS/'validation_labels.parquet')
 merged=sels.merge(labs,on=['patent_id','year'],validate='many_to_one');assert len(merged)==len(sels)
 rows=[]
 keys=['organization_id','year','model','policy']
 for key,g in merged.groupby(keys,sort=True):
  row=dict(zip(keys,key));row.update(core_selected=int(g.electronics_core.sum()),newpair_selected=int(g.newpair.sum()),documents=len(g))
  for label in ['task','general','applicant']:
   row[label+'_T']=int(g[label].sum());row[label+'_U']=int((g[label]&g.newpair).sum())
  rows.append(row)
 detail=pd.DataFrame(rows);detail.to_parquet(RS/'validation_detail.parquet',index=False)
 detail.groupby(['model','policy']).agg(n=('organization_id','size'),organizations=('organization_id','nunique'),core_selected=('core_selected','mean'),newpair_selected=('newpair_selected','mean'),task_T=('task_T','mean'),task_U=('task_U','mean'),general_T=('general_T','mean'),applicant_T=('applicant_T','mean')).reset_index().to_csv(RS/'validation_summary.csv',index=False)
 contrasts=[]
 for model in PROTO['models']:
  for policy,baseline in [('fixed_core9','forecast_top30'),('fixed_core9_pair3','fixed_core9'),('fixed_core9_pair3','forecast_top30')]:
   a=detail.loc[(detail.model==model)&(detail.policy==policy)];b=detail.loc[(detail.model==model)&(detail.policy==baseline)]
   m=a.merge(b,on=['organization_id','year'],suffixes=('_p','_b'),validate='one_to_one')
   for metric in ['task_T','task_U','general_T','applicant_T']:
    delta=m[metric+'_p']-m[metric+'_b'];z=m[['organization_id']].assign(delta=delta).groupby('organization_id').delta.agg(['sum','count'])
    sums=z['sum'].to_numpy();counts=z['count'].to_numpy();rng=np.random.default_rng(20261001)
    boots=[]
    if len(z)>=5:
     for _ in range(2000):
      ii=rng.integers(0,len(z),size=len(z));boots.append(sums[ii].sum()/counts[ii].sum())
    contrasts.append({'model':model,'policy':policy,'baseline':baseline,'metric':metric,'n':len(m),'organizations':len(z),'difference':float(delta.mean()),'ci_low':float(np.quantile(boots,.025)) if boots else None,'ci_high':float(np.quantile(boots,.975)) if boots else None,'win_fraction':float((delta>0).mean()),'tie_fraction':float((delta==0).mean()),'loss_fraction':float((delta<0).mean())})
 pd.DataFrame(contrasts).to_csv(RS/'validation_contrasts.csv',index=False)
 detail.groupby(['year','model','policy']).agg(n=('organization_id','size'),task_T=('task_T','mean'),task_U=('task_U','mean'),core_selected=('core_selected','mean')).reset_index().to_csv(RS/'validation_annual.csv',index=False)
 if replay:
  audit={'derived_replay_utc':now(),'source_database_access':False,
   'inputs':['results/revision_v3/validation_selected.parquet','results/revision_v3/validation_selection_lock.json','datasets/revision_v3/validation_labels.parquet'],
   'selected_sha256':sha(RS/'validation_selected.parquet'),'labels_sha256':sha(DS/'validation_labels.parquet'),
   'outputs':['validation_detail.parquet','validation_summary.csv','validation_contrasts.csv','validation_annual.csv'],
   'preserved_measurement_evidence':'Prepared histories, outcome edges, protocol, capacity and overlap audits are supplied unchanged; this replay aggregates frozen lists/labels rather than reconstructing raw measurements.'}
  (RS/'validation_replay_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
  log('derived_replay_completed',**audit);return
 # Honest overlap: corpus is shared; report original task list/organization reuse.
 battery=pd.read_parquet(ROOT/'results/revision_v2/taskpool_raw_situations.parquet');battery=battery.loc[(battery.year>=2018)&(battery.relevance=='core_task')]
 v=detail[['organization_id','year']].drop_duplicates();overlap=v.merge(battery[['organization_id','year']],on=['organization_id','year'])
 old_ids=set()
 for y in PROTO['origins']:
  old=pd.read_parquet(ROOT/f'results/revision_v2/taskpool_raw_selected_{y}.parquet',columns=['patent_id','relevance']);old_ids.update(old.loc[old.relevance=='core_task'].patent_id.astype(str))
 selected_ids=set(sels.patent_id.astype(str));pool_ids=set(pd.read_parquet(RS/'validation_pools.parquet',columns=['patent_id']).patent_id.astype(str))
 prior_ids=set(pd.read_parquet(DS/'validation_prior_selected_ids.parquet').patent_id.astype(str))
 assert not selected_ids&prior_ids and not pool_ids&prior_ids
 overlap_report={'evaluation_completed_utc':now(),'task_not_original_policy_design_domain':True,'broad_domain_candidate_universe_shared_fraction':1.0,'unique_validation_pool_candidates':len(pool_ids),'unique_validation_selected_candidates':len(selected_ids),'validation_selected_also_any_battery_task_v2_selected':len(selected_ids&old_ids),'validation_pool_also_any_prior_evaluated_selected':len(pool_ids&prior_ids),'validation_selected_also_any_prior_evaluated_selected':len(selected_ids&prior_ids),'feasible_validation_situations':len(v),'same_orgyear_as_original_battery_sample':len(overlap),'same_orgs_as_original_battery_sample':len(set(v.organization_id)&set(battery.organization_id)),'validation_organizations':v.organization_id.nunique(),'primary_label_counts':labs.groupby('year').agg(n=('patent_id','size'),task=('task','sum'),general=('general','sum'),applicant=('applicant','sum')).reset_index().to_dict('records'),'caveat':'New coded task and complete organization admission; prior shortlist IDs excluded but shared thermal corpus and periods. Bootstrap does not remove shared patent/environment dependence; not corporate benefit or unseen-domain prediction.'}
 (RS/'validation_overlap.json').write_text(json.dumps(overlap_report,indent=2),encoding='utf-8');log('evaluation_complete',**overlap_report)
def main():
 a=argparse.ArgumentParser();a.add_argument('--stage',choices=['prepare','select','labels','evaluate','replay','all'],default='all');stage=a.parse_args().stage
 if stage=='replay':evaluate(replay=True);return
 for name,fn in [('prepare',prepare),('select',select),('labels',labels),('evaluate',evaluate)]:
  if stage in [name,'all']:fn()
if __name__=='__main__':main()
