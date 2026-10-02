"""Development-only reconstruction from existing D caches; no predictor fitting."""
from __future__ import annotations
import os
for k in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ[k]='2'
from pathlib import Path
import argparse,itertools,json,time,shutil
import datetime
import hashlib
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from policy_core import stable_order,mmr_select,quota_select

ROOT=Path(__file__).resolve().parents[1]
os.environ['TEMP']=str(ROOT/'temp');os.environ['TMP']=str(ROOT/'temp')
OUT=ROOT/'results/revision_v6'
REPORT=ROOT/'research/revision_v6_development.md'
YEARS=(2013,2014,2015)
MODELS=('boosting','ridge')
CAPACITIES=(0,3,6,9,12,15,30)
FLOORS=(0,3,9)
CONTEXTS=('low_lt20pct','middle_20_to40pct_inclusive','high_gt40pct')
METRICS=('task_linked','novel_document_exposure','unique_unseen_core_pairs','general_reach')
SEED=20261002

def emit(event,**kw):print(json.dumps(dict(event=event,**kw),ensure_ascii=False),flush=True)
def codes(v):return {x for x in str(v).split('|') if x and x not in ('nan','None','<NA>')}
def pairs(v):return set(itertools.combinations(sorted(v),2))
def context(c):return CONTEXTS[0] if c<6 else (CONTEXTS[1] if c<=12 else CONTEXTS[2])
def dump(path,obj):path.write_text(json.dumps(obj,indent=2,ensure_ascii=False),encoding='utf-8')
def pname(c,m):return f'C{c:02d}_m{m:02d}'

def protocol():
    OUT.mkdir(parents=True,exist_ok=True)
    p=dict(status='development_exploratory_locked_before_new_point_summaries',years=list(YEARS),
      source='Existing D canonical caches and frozen primary_v1 scores; no new predictor',
      retrospective_status='Original development outcomes were previously accessible; not preregistered or independent confirmation',
      baseline='Top30 under each frozen ranker in the reconstructed core-task admission pool',
      thresholds={'low':'core positions/30 < .20 (0..5)','middle':'.20 <= core positions/30 <= .40 (6..12)','high':'> .40 (13..30)'},
      capacities=list(CAPACITIES),absolute_novel_document_floors=list(FLOORS),
      infeasibility='C<m, core supply<C, noncore supply<30-C, or novel-core supply<m; never shrink exact grid targets',
      axes='Hold C fixed and vary absolute m; hold absolute m fixed and vary C. Constant fractional r would vary the absolute floor.',
      objectives=list(METRICS),weights='None; no weighted utility or optimized deployment policy',
      comparators=['top30','task_title_cosine','core_priority_score','original_pair_q9','original_pair_q9_matched','mmr_0.5','mmr_0.7','mmr_0.9'],
      core_priority='Highest frozen-score core candidates up to min(30,core supply), then score-ranked noncore backfill; not semantic relevance',
      task_title_cosine='Rank the admitted candidates by preceding-core title-centroid cosine; lexical task score, not validated engineering relevance',
      mmr='Existing policy_core.mmr_select, weights .5/.7/.9, same reconstructed pool and mature title TF-IDF vectors',
      ratio_guard={'minimum_mean_positive_combined_gain':.1,'strictly_greater':True,'minimum_situations':10,'minimum_organizations':5},
      uncertainty='Overall primary task/general contrasts only: paired organization percentile and crossed org x patent Exp(1) sensitivity; fixed lists/years; sparse contexts descriptive',
      bootstrap_seed=SEED,bootstrap_draws=2000,temporary_directory=str(ROOT/'temp'),numeric_threads=2,
      new_2022_external_validation='Not performed by this script')
    path=OUT/'development_protocol.json'
    if path.exists():
        old=json.loads(path.read_text(encoding='utf-8'))
        if old!=p:raise RuntimeError('Existing v6 protocol differs; do not overwrite its lock')
    else:dump(path,p)
    dump(OUT/'development_protocol_semantic_amendment.json',dict(reason='Verification of existing quota_select: legacy q=.30 is supply-capped, unlike the exact C,m grid. Add the authentic legacy policy and its matched control; retain all originally locked strict-target comparisons.',
      change='Companion legacy_pair_q30 and legacy_pair_q30_matched for all admitted situations; no changes to years, baseline contexts, thresholds, objectives, predictors, exact-grid floors, or original strict q9 results',
      disclosure='Amendment after first point run; deterministic reconstruction correction, not outcome-based selection',
      legacy_requested_target=9,legacy_effective_target='min(9, novel-core supply)',strict_q9_policy_identifier='original_pair_q9'))
    return p

def hist_read(columns,core_only=False):
    p=ROOT/'datasets/canonical_v1/study_portfolios.parquet'
    typ=pq.ParquetFile(p).schema_arrow.field('patent_date').type
    lower=pd.Timestamp('2008-01-01') if pa.types.is_timestamp(typ) else (datetime.date(2008,1,1) if pa.types.is_date(typ) else '2008-01-01')
    upper=pd.Timestamp('2015-01-01') if pa.types.is_timestamp(typ) else (datetime.date(2015,1,1) if pa.types.is_date(typ) else '2015-01-01')
    filters=[('patent_date','>=',lower),('patent_date','<',upper)]
    if core_only:filters.append(('is_core','==',True))
    h=pd.read_parquet(p,columns=columns,filters=filters)
    h['year']=pd.to_datetime(h.patent_date).dt.year
    h['patent_id']=h.patent_id.astype(str)
    h['owners']=h.assignee_id.map(codes)
    return h

def data():
    start=time.perf_counter()
    corpus=pd.read_parquet(ROOT/'datasets/canonical_v1/study_patents.parquet',columns=['patent_id','patent_date','patent_title'])
    corpus['year']=pd.to_datetime(corpus.patent_date).dt.year
    thin=hist_read(['patent_id','patent_date','assignee_id','cpc_codes','is_core'])
    thin['classified']=thin.cpc_codes.map(lambda x:bool(codes(x)))
    ch=hist_read(['patent_id','patent_date','patent_title','assignee_id','cpc_codes','is_core'],True)
    ch['pairs']=ch.cpc_codes.map(lambda x:pairs(codes(x)))
    labs=pd.read_parquet(ROOT/'datasets/revision_v2/task_patent_labels.parquet',columns=['patent_id','year','future_core_signal_1patent','future_external_signal_2org'])
    labs['patent_id']=labs.patent_id.astype(str)
    if labs.patent_id.duplicated().any():raise AssertionError('Duplicate cached label IDs')
    old=pd.read_parquet(ROOT/'results/revision_v2/taskpool_raw_situations.parquet')
    old=old[(old.relevance=='core_task')&old.year.isin(YEARS)].copy()
    audit={'years':list(YEARS),'old_core_task_situations':len(old),'old_unique_organization_keys':int(old.organization_id.nunique()),
      'source_bytes':{str(p.relative_to(ROOT)):p.stat().st_size for p in [ROOT/'datasets/canonical_v1/study_patents.parquet',ROOT/'datasets/canonical_v1/study_portfolios.parquet',ROOT/'datasets/revision_v2/task_patent_labels.parquet']},
      'slim_history_rows_2008_2014':len(thin),'core_title_history_rows_2008_2014':len(ch),
      'corpus_title_rows':len(corpus),'scores':{},'load_seconds':time.perf_counter()-start,'D_free_bytes':shutil.disk_usage(ROOT).free}
    for y in YEARS:
        p=ROOT/f'results/primary_v1/scores_{y}.parquet'
        f=pq.ParquetFile(p); ids=f.read(columns=['patent_id']).to_pandas().patent_id.astype(str)
        audit['scores'][str(y)]={'rows':len(ids),'bytes':p.stat().st_size,'missing_task_labels':int((~ids.isin(labs.patent_id)).sum())}
    dump(OUT/'development_data_audit.json',audit)
    emit('DATA_READY',**audit)
    return corpus,thin,ch,labs,old,audit

def exact(scores,ids,core,novel,c,m):
    reasons=[]
    if m>c:reasons.append('novel_floor_exceeds_capacity')
    if int(core.sum())<c:reasons.append('insufficient_core_supply')
    if int((~core).sum())<30-c:reasons.append('insufficient_noncore_supply')
    if int(novel.sum())<m:reasons.append('insufficient_novel_core_supply')
    if reasons:return None,reasons
    order=stable_order(scores,ids);cr=order[core[order]];nr=order[~core[order]]
    blind=cr[:c]
    if int(novel[blind].sum())>=m:sel=blind
    else:
        mandatory=list(cr[novel[cr]][:m]);used=set(mandatory)
        for j in cr:
            if len(mandatory)>=c:break
            if int(j) not in used:mandatory.append(int(j));used.add(int(j))
        sel=np.asarray(mandatory,dtype=int)
    return np.r_[sel,nr[:30-c]],[]

def reconstruct(pilot=False):
    run_start=time.perf_counter();year_seconds={}
    protocol();corpus,thin,ch,labs,old,audit=data()
    rows=[];selections=[];pools=[];situations=[];failures=[];feasibility=[];recovery=[];invariant=[]
    label_index=labs.set_index('patent_id')
    for y in YEARS:
        ys=time.perf_counter()
        train=corpus[(corpus.year>=2010)&(corpus.year<=y-3)]
        tv=TfidfVectorizer(max_features=20000,min_df=2,max_df=.98,ngram_range=(1,2),stop_words='english',dtype=np.float32,sublinear_tf=True)
        tv.fit(train.patent_title.fillna(''))
        cur=pd.read_parquet(ROOT/f'results/primary_v1/scores_{y}.parquet')
        cur['patent_id']=cur.patent_id.astype(str)
        if cur.patent_id.duplicated().any():raise AssertionError('Duplicate score IDs')
        if cur.year.ne(y).any():raise AssertionError('Unexpected score year')
        cur=cur.sort_values('patent_id').reset_index(drop=True)
        ids=cur.patent_id.to_numpy();xc=tv.transform(cur.patent_title.fillna(''))
        owner=cur.assignee_id.map(codes).tolist();sub=cur.cpc_codes.map(codes).tolist();cp=[pairs(s) for s in sub]
        core=cur.is_core.to_numpy(bool)
        lab=label_index.loc[ids]
        task=lab.future_core_signal_1patent.to_numpy(bool);general=lab.future_external_signal_2org.to_numpy(bool)
        if not np.array_equal(general,cur.future_external_attention.to_numpy()>=2):raise AssertionError('Cached general labels differ from frozen score labels')
        h=thin[(thin.year>=y-5)&(thin.year<y)]
        mem=h[['patent_id','is_core','classified','owners']].explode('owners').dropna(subset=['owners'])
        stats=mem.groupby('owners').agg(history_n=('patent_id','nunique'),core_history_n=('is_core','sum'),classification_coverage=('classified','mean'))
        eligible=stats[(stats.history_n>=15)&(stats.core_history_n>=3)&(stats.classification_coverage>=.8)].sort_index()
        hc=ch[(ch.year>=y-5)&(ch.year<y)].reset_index(drop=True)
        hmem=hc[['owners']].explode('owners').dropna(subset=['owners']);hgroups=hmem.groupby('owners').groups
        xh=tv.transform(hc.patent_title.fillna(''))
        accepted=0
        for org,st in eligible.iterrows():
            ps=time.perf_counter();ci=np.asarray(hgroups[org],int)
            if len(ci)!=int(st.core_history_n):raise AssertionError('Core history membership differs')
            hp=set().union(*hc.iloc[ci].pairs)
            centroid=normalize(sparse.csr_matrix(np.asarray(xh[ci].mean(axis=0))))
            sim=(xc@centroid.T).toarray().ravel()
            ext=np.asarray([bool(s) and org not in s for s in owner])
            classified=np.asarray([bool(s) for s in sub])
            pi=np.flatnonzero(ext&classified&(sim>=.03))
            base=dict(organization_id=str(org),year=y,history_n=int(st.history_n),core_history_n=int(st.core_history_n),
              classification_coverage=float(st.classification_coverage),pool_n=len(pi),core_pool_n=int(core[pi].sum()))
            if len(pi)<50:failures.append(dict(**base,status='admission_pool_below_50'));continue
            accepted+=1
            known=old[(old.year==y)&(old.organization_id==org)]
            if len(known)!=1:raise AssertionError(f'Reconstructed accepted situation not in old core-task record: {org} {y}')
            k=known.iloc[0]
            checks={z:(float(base[z])==float(k[z])) for z in ('history_n','core_history_n','pool_n','core_pool_n','classification_coverage')}
            recovery.append(dict(organization_id=str(org),year=y,**checks))
            if not all(checks.values()):raise AssertionError(f'Core-task reconstruction mismatch {org} {y}: {checks}')
            pids=ids[pi];pc=core[pi];unseen=[cp[j]-hp if core[j] else set() for j in pi];nov=np.asarray([bool(s) for s in unseen])
            t=task[pi];g=general[pi]
            for j in range(len(pi)):
                pools.append(dict(organization_id=str(org),year=y,patent_id=str(pids[j]),is_core=bool(pc[j]),
                  novel_document=bool(nov[j]),unseen_pairs_json=json.dumps(sorted(unseen[j])),task_similarity=float(sim[pi[j]]),
                  score_boosting=float(cur.iloc[pi[j]].score_boosting),score_ridge=float(cur.iloc[pi[j]].score_ridge),
                  task_linked=int(t[j]),general_reach=int(g[j]),pool_exposure=1/len(pi)))
            for model in MODELS:
                score=cur.iloc[pi]['score_'+model].to_numpy();order=stable_order(score,pids);top=order[:30]
                c0=int(pc[top].sum());cat=context(c0)
                sb=dict(**base,model=model,baseline_core_positions=c0,baseline_core_share=c0/30,
                  baseline_novel_documents=int(nov[top].sum()),novel_core_supply=int(nov.sum()),core_context=cat)
                situations.append(sb)
                policies={'top30':top,'task_title_cosine':stable_order(sim[pi],pids)[:30]}
                cc=min(30,int(pc.sum()));policies['core_priority_score']=exact(score,pids,pc,nov,cc,0)[0]
                for w in (.5,.7,.9):policies[f'mmr_{w:.1f}']=mmr_select(score,pids,xc[pi],30,w)
                legacy=quota_select(score,pids,nov,30,.30)
                lc=int(pc[legacy].sum());legacy_matched=np.r_[order[pc[order]][:lc],legacy[~pc[legacy]]]
                policies['legacy_pair_q30']=legacy;policies['legacy_pair_q30_matched']=legacy_matched
                if int(nov.sum())>=9:
                    mandatory=list(order[nov[order]][:9]);used=set(mandatory)
                    for j in order:
                        if len(mandatory)>=30:break
                        if int(j) not in used:mandatory.append(int(j));used.add(int(j))
                    q=np.asarray(mandatory,int);cq=int(pc[q].sum())
                    matched=np.r_[order[pc[order]][:cq],q[~pc[q]]]
                    policies['original_pair_q9']=q;policies['original_pair_q9_matched']=matched
                    if set(q)!=set(legacy):raise AssertionError('Strict/legacy mismatch when supply adequate')
                    if set(q[~pc[q]])!=set(matched[~pc[matched]]):raise AssertionError('Matched noncore IDs differ')
                else:feasibility.append(dict(organization_id=str(org),year=y,model=model,policy='original_pair_q9',feasible=False,reason='insufficient_novel_core_supply',C=None,m=9))
                for c in CAPACITIES:
                    for m in FLOORS:
                        name=pname(c,m);sel,why=exact(score,pids,pc,nov,c,m)
                        feasibility.append(dict(organization_id=str(org),year=y,model=model,policy=name,feasible=sel is not None,reason=';'.join(why),C=c,m=m))
                        if sel is not None:policies[name]=sel
                for name,sel in policies.items():
                    if len(sel)!=30 or len(set(sel))!=30:raise AssertionError('Wrong selection length/duplicates')
                    up=set().union(*(unseen[j] for j in sel))
                    rows.append(dict(**sb,policy=name,core_positions=int(pc[sel].sum()),novel_document_exposure=int(nov[sel].sum()),
                      unique_unseen_core_pairs=len(up),task_linked=int(t[sel].sum()),novel_task_linked=int((t[sel]&nov[sel]).sum()),
                      general_reach=int(g[sel].sum()),changed_from_top=len(set(sel)-set(top)),
                      quota_binding=(int(nov[top].sum())<min(9,int(nov.sum()))) if name=='legacy_pair_q30' else ((int(nov[top].sum())<9) if name=='original_pair_q9' else None),
                      quota_requested_target=9 if name in ('legacy_pair_q30','original_pair_q9') else None,
                      quota_effective_target=min(9,int(nov.sum())) if name=='legacy_pair_q30' else (9 if name=='original_pair_q9' else None),
                      quota_supply_capped=int(nov.sum())<9 if name=='legacy_pair_q30' else None))
                    selections.extend(dict(organization_id=str(org),year=y,model=model,policy=name,patent_id=str(pids[j])) for j in sel)
                for c in CAPACITIES:
                    b=policies.get(pname(c,0))
                    if b is None:continue
                    for m in (3,9):
                        q=policies.get(pname(c,m))
                        if q is None:continue
                        bind=int(nov[b].sum())<m;added=set(q)-set(b);removed=set(b)-set(q)
                        ok=(set(q)==set(b)) if not bind else (all(nov[j] for j in added) and all(not nov[j] for j in removed))
                        if not ok:raise AssertionError('Binding/nonbinding identity failed')
                        if set(q[~pc[q]])!=set(b[~pc[b]]):raise AssertionError('Within-capacity noncore mismatch')
                        invariant.append(dict(organization_id=str(org),year=y,model=model,C=c,m=m,binding=bind,
                          changed_n=len(added),nonbinding_exact_invariant=not bind and set(q)==set(b),novel_additions_only=all(nov[j] for j in added),non_novel_removals_only=all(not nov[j] for j in removed)))
            if pilot:
                a=dict(**base,pilot_seconds=time.perf_counter()-ps,total_seconds=time.perf_counter()-ys,
                  baseline_core_positions={s['model']:s['baseline_core_positions'] for s in situations},recovery_checks=checks,
                  novel_core_supply=int(nov.sum()),policy_rows=len(rows),selection_events=len(selections),status='PASS')
                dump(OUT/'development_pilot.json',a);emit('PILOT_PASS',**a);return
        year_seconds[str(y)]=time.perf_counter()-ys
        emit('YEAR_REBUILT',year=y,eligible_history_situations=len(eligible),accepted=accepted,seconds=year_seconds[str(y)])
    detail=pd.DataFrame(rows);selected=pd.DataFrame(selections);pool=pd.DataFrame(pools);sit=pd.DataFrame(situations)
    if set(zip(sit.organization_id,sit.year))!=set(zip(old.organization_id,old.year)):raise AssertionError('Old/new accepted situation set differs')
    detail.to_parquet(OUT/'development_policy_detail.parquet',index=False)
    selected.to_parquet(OUT/'development_selected.parquet',index=False)
    pool.to_parquet(OUT/'development_pools.parquet',index=False)
    sit.to_csv(OUT/'development_situations.csv',index=False)
    pd.DataFrame(failures,columns=['organization_id','year','history_n','core_history_n','classification_coverage','pool_n','core_pool_n','status']).to_csv(OUT/'development_admission_failures.csv',index=False)
    pd.DataFrame(feasibility).to_csv(OUT/'development_feasibility.csv',index=False)
    pd.DataFrame(recovery).to_csv(OUT/'development_reconstruction_checks.csv',index=False)
    pd.DataFrame(invariant).to_csv(OUT/'development_binding_checks.csv',index=False)
    audit.update(status='PASS',accepted_situations=len(sit)//2,unique_organizations=int(sit.organization_id.nunique()),
      policy_rows=len(detail),selected_events=len(selected),pool_exposures=len(pool),accepted_years=sit.drop_duplicates(['organization_id','year']).groupby('year').size().to_dict(),
      recovery='Exact prior core-task history counts, classification coverage and candidate/core pool counts; original v1 pool not substituted',
      nonbinding='All feasible same-C nonbinding floors preserve exact identifiers; additions novel and removals nonnovel',
      predictor_fits=0,heldout_years_used=0,new_2022_external_validation=False,
      output_bytes=sum(p.stat().st_size for p in OUT.iterdir() if p.is_file()))
    dump(OUT/'development_data_audit.json',audit)
    summarize(detail,sit)
    verify_legacy(detail)
    audit['year_reconstruction_seconds']=year_seconds
    audit['complete_point_run_seconds']=time.perf_counter()-run_start
    source_paths=[ROOT/'datasets/canonical_v1/study_patents.parquet',ROOT/'datasets/canonical_v1/study_portfolios.parquet',ROOT/'datasets/revision_v2/task_patent_labels.parquet',ROOT/'results/revision_v2/taskpool_raw_situations.parquet',ROOT/'results/revision_v2/taskpool_raw_detail.parquet',*[ROOT/f'results/primary_v1/scores_{y}.parquet' for y in YEARS],ROOT/'scripts/policy_core.py']
    manifest=[]
    for p in source_paths:
        hsh=hashlib.sha256()
        with p.open('rb') as f:
            for chunk in iter(lambda:f.read(1048576),b''):hsh.update(chunk)
        manifest.append(dict(path=str(p.relative_to(ROOT)),bytes=p.stat().st_size,sha256=hsh.hexdigest()))
    dump(OUT/'development_source_manifest.json',manifest)
    audit['complete_readonly_source_bytes']=sum(x['bytes'] for x in manifest)
    audit['source_manifest']='development_source_manifest.json'
    dump(OUT/'development_data_audit.json',audit)
    emit('POINTS_READY',**audit)

def verify_legacy(detail):
    old=pd.read_parquet(ROOT/'results/revision_v2/taskpool_raw_detail.parquet')
    old=old[(old.year.isin(YEARS))&(old.relevance=='core_task')&(old.boundary=='core_newpair')&(old.q==.30)]
    new=detail[detail.policy=='legacy_pair_q30']
    z=new.merge(old,on=['organization_id','year','model'],validate='one_to_one',suffixes=('_new','_old'))
    checks=pd.DataFrame({'organization_id':z.organization_id,'year':z.year,'model':z.model,
      'general_reach_exact':z.general_reach==z.general_T,
      'novel_document_exposure_exact':z.novel_document_exposure==z.unfamiliar_selected,
      'novel_supply_exact':z.novel_core_supply==z.unfamiliar_pool_n,
      'changed_identifiers_count_exact':z.changed_from_top==z.changed_n})
    if len(z)!=120 or not checks.iloc[:,3:].all().all():raise AssertionError('Legacy policy recovery differs from original v2 development outputs')
    checks.to_csv(OUT/'development_legacy_recovery_checks.csv',index=False)
    dump(OUT/'development_legacy_recovery_audit.json',dict(status='PASS',situation_ranker_rows=len(z),
      exact_fields=list(checks.columns[3:]),source='Existing raw core_task/core_newpair/q=.30 v2 development details',
      note='Old selected IDs were not saved in development; aggregate selection counts and cached outcomes recovered exactly. New selected IDs are saved for reproducibility.'))

def summarize(detail,sit):
    summary=[]
    policies=sorted(detail.policy.unique())
    for model in MODELS:
        for cat in ('all',*CONTEXTS):
            sx=sit[(sit.model==model)&((sit.core_context==cat) if cat!='all' else True)]
            for pol in policies:
                q=detail[(detail.model==model)&(detail.policy==pol)&((detail.core_context==cat) if cat!='all' else True)]
                r=dict(model=model,core_context=cat,policy=pol,admitted_situations=len(sx),admitted_organizations=int(sx.organization_id.nunique()),
                  feasible_situations=len(q),feasible_organizations=int(q.organization_id.nunique()))
                r.update({z:float(q[z].mean()) if len(q) else None for z in ('baseline_core_positions','core_positions',*METRICS,'novel_task_linked','changed_from_top')})
                summary.append(r)
    pd.DataFrame(summary).to_csv(OUT/'development_policy_summary.csv',index=False)
    comparisons=[('original_pair_q9','top30','combined'),('original_pair_q9_matched','top30','matched_allocation'),
      ('original_pair_q9','original_pair_q9_matched','within_matched_coverage'),('C09_m00','top30','coverage_to9'),
      ('legacy_pair_q30','top30','legacy_combined'),('legacy_pair_q30_matched','top30','legacy_matched_allocation'),
      ('legacy_pair_q30','legacy_pair_q30_matched','legacy_within_matched_coverage'),
      ('C09_m03','C09_m00','within_C9_floor3'),('C09_m09','C09_m00','within_C9_floor9'),
      ('C12_m03','C06_m03','coverage6_to12_fixed_floor3'),('C15_m09','C09_m09','coverage9_to15_fixed_floor9')]
    for p in ('task_title_cosine','core_priority_score','mmr_0.5','mmr_0.7','mmr_0.9'):comparisons.append((p,'top30',p+'_vs_top'))
    for c in CAPACITIES:
        for m in (3,9):comparisons.append((pname(c,m),pname(c,0),f'within_C{c}_floor{m}'))
    details=[]
    for model in MODELS:
        d=detail[detail.model==model];ps={p:q.set_index(['organization_id','year']) for p,q in d.groupby('policy')}
        for a,b,name in comparisons:
            if a not in ps or b not in ps:continue
            ix=ps[a].index.intersection(ps[b].index)
            for key in ix:
                aa=ps[a].loc[key];bb=ps[b].loc[key]
                r=dict(organization_id=key[0],year=key[1],model=model,comparison=name,alternative=a,reference=b,core_context=aa.core_context,
                  delta_core_positions=int(aa.core_positions-bb.core_positions),baseline_core_positions=int(aa.baseline_core_positions))
                r.update({'delta_'+z:int(aa[z]-bb[z]) for z in (*METRICS,'novel_task_linked')});details.append(r)
    cd=pd.DataFrame(details).drop_duplicates(['organization_id','year','model','comparison','alternative','reference'])
    cd.to_parquet(OUT/'development_contrast_detail.parquet',index=False)
    cs=[]
    for model in MODELS:
        for cat in ('all',*CONTEXTS):
            for name in sorted(cd.comparison.unique()):
                q=cd[(cd.model==model)&(cd.comparison==name)&((cd.core_context==cat) if cat!='all' else True)]
                r=dict(model=model,core_context=cat,comparison=name,n_situations=len(q),n_organizations=int(q.organization_id.nunique()))
                for z in (*METRICS,'novel_task_linked','core_positions'):
                    v=q['delta_'+z];r['mean_delta_'+z]=float(v.mean()) if len(q) else None
                    r[z+'_wins']=int((v>0).sum());r[z+'_ties']=int((v==0).sum());r[z+'_losses']=int((v<0).sum())
                cs.append(r)
    pd.DataFrame(cs).to_csv(OUT/'development_contrasts.csv',index=False)
    ratios=[]
    for model in MODELS:
      for prefix,variant in (('','strict_target9_feasible_subset'),('legacy_','legacy_supply_capped_all_admitted')):
        for cat in ('all',*CONTEXTS):
            x=cd[(cd.model==model)&((cd.core_context==cat) if cat!='all' else True)]
            by={n:q.set_index(['organization_id','year']) for n,q in x.groupby('comparison')}
            if not all(prefix+p in by for p in ('combined','matched_allocation','within_matched_coverage')):
                ratios.append(dict(model=model,policy_variant=variant,core_context=cat,n=0,ratio=None,ratio_status='no_common_feasible_situations'));continue
            a=by[prefix+'combined'];b=by[prefix+'matched_allocation'];c=by[prefix+'within_matched_coverage'];ix=a.index.intersection(b.index).intersection(c.index)
            a=a.loc[ix];b=b.loc[ix];c=c.loc[ix]
            if not np.array_equal(a.delta_task_linked.to_numpy(),b.delta_task_linked.to_numpy()+c.delta_task_linked.to_numpy()):raise AssertionError('Decomposition identity failed')
            gain=float(a.delta_task_linked.mean());n=len(ix);norg=len(set(ix.get_level_values(0)))
            allowed=n>=10 and norg>=5 and gain>.1
            ratios.append(dict(model=model,policy_variant=variant,core_context=cat,n=n,n_organizations=norg,combined_delta=gain,
              allocation_delta=float(b.delta_task_linked.mean()),within_delta=float(c.delta_task_linked.mean()),
              ratio=float(b.delta_task_linked.mean()/gain) if allowed else None,
              ratio_status='descriptive_point_only' if allowed else 'suppressed_small_group_or_nonpositive_near_zero_denominator',
              strict_naive_positive_controlled_negative=int(((a.delta_task_linked>0)&(c.delta_task_linked<0)).sum()),
              opposite_strict_reversal=int(((a.delta_task_linked<0)&(c.delta_task_linked>0)).sum())))
    pd.DataFrame(ratios).to_csv(OUT/'development_decomposition.csv',index=False)
    frontier=detail[['organization_id','year','model','core_context','policy','core_positions',*METRICS]].copy()
    flags=[]
    for _,q in frontier.groupby(['organization_id','year','model'],sort=False):
        v=q[['task_linked','novel_document_exposure','general_reach']].to_numpy()
        for j in range(len(q)):
            dominated=bool(np.any(np.all(v>=v[j],axis=1)&np.any(v>v[j],axis=1)))
            flags.append((int(q.index[j]),not dominated))
    frontier['nondominated_observed_three_vector']=pd.Series(dict(flags))
    frontier.to_csv(OUT/'development_three_vector_frontier.csv',index=False)

def bootstrap(repeats=2000):
    boot_start=time.perf_counter()
    cd=pd.read_parquet(OUT/'development_contrast_detail.parquet')
    selected=pd.read_parquet(OUT/'development_selected.parquet')
    pool=pd.read_parquet(OUT/'development_pools.parquet')
    wanted=['within_matched_coverage','legacy_within_matched_coverage','coverage_to9','within_C9_floor3','coverage6_to12_fixed_floor3']
    orgs=sorted(pool.organization_id.unique());pats=sorted(pool.patent_id.unique());oi={v:i for i,v in enumerate(orgs)};pi={v:i for i,v in enumerate(pats)}
    norg=len(orgs);npat=len(pats);D=[];E=[];N=[];desc=[];contrib=[]
    lab=pool.set_index(['organization_id','year','patent_id'])
    for (model,comp),q in cd[cd.comparison.isin(wanted)].groupby(['model','comparison']):
        keys=q[['organization_id','year']].drop_duplicates();a=q.alternative.iloc[0];b=q.reference.iloc[0]
        sa=selected[(selected.model==model)&(selected.policy==a)].merge(keys,on=['organization_id','year'])
        sb=selected[(selected.model==model)&(selected.policy==b)].merge(keys,on=['organization_id','year'])
        x=pd.concat([sa.assign(sign=1),sb.assign(sign=-1)],ignore_index=True)
        x=x.groupby(['organization_id','year','patent_id'],as_index=False)['sign'].sum()
        x=x[x.sign!=0].join(lab[['task_linked','general_reach']],on=['organization_id','year','patent_id'])
        contribution=x[['organization_id','year','patent_id','sign','task_linked','general_reach']].copy()
        contribution['model']=model;contribution['comparison']=comp
        for z in ('task_linked','general_reach'):contribution['contribution_'+z]=contribution['sign']*contribution[z]
        contrib.append(contribution)
        rr=x.organization_id.map(oi).to_numpy();cc=x.patent_id.map(pi).to_numpy()
        d=[sparse.csr_matrix((x.sign.to_numpy()*x[z].to_numpy(),(rr,cc)),shape=(norg,npat)) for z in ('task_linked','general_reach')]
        px=pool.merge(keys,on=['organization_id','year']);er=px.organization_id.map(oi).to_numpy();ec=px.patent_id.map(pi).to_numpy()
        e=sparse.csr_matrix((px.pool_exposure.to_numpy(),(er,ec)),shape=(norg,npat))
        nu=keys.organization_id.map(oi).value_counts().reindex(range(norg),fill_value=0).to_numpy(float)
        orgd=np.vstack([np.asarray(dm.sum(axis=1)).ravel() for dm in d]);point=orgd.sum(axis=1)/len(keys)
        for j,z in enumerate(('task_linked','general_reach')):
            if not np.isclose(point[j],q['delta_'+z].mean(),atol=1e-12):raise AssertionError('Contribution point mismatch')
        D.append(d);E.append(e);N.append(nu);desc.append((model,comp,len(keys),point,orgd,int(px.patent_id.nunique())))
    pd.concat(contrib,ignore_index=True).to_parquet(OUT/'development_uncertainty_contributions.parquet',index=False)
    rng=np.random.default_rng(SEED);orgout=np.empty((repeats,len(desc),2));crossout=np.empty_like(orgout)
    for k in range(repeats):
        count=np.bincount(rng.integers(0,norg,norg),minlength=norg);wo=rng.exponential(size=norg);wp=rng.exponential(size=npat)
        for j,(_,_,_,_,orgd,_) in enumerate(desc):
            den=float(count@N[j]);orgout[k,j]=(orgd@count)/den if den>0 else np.nan
            denx=float(wo@(E[j]@wp));crossout[k,j]=[float(wo@(dm@wp))/denx for dm in D[j]]
        if (k+1)%500==0:emit('BOOTSTRAP_PROGRESS',draws=k+1,total=repeats)
    out=[]
    for j,(model,comp,n,point,_,npool) in enumerate(desc):
        for z,met in enumerate(('task_linked','general_reach')):
            for method,vals in [('paired_organization_percentile',orgout[:,j,z]),('crossed_org_patent_fixed_list_sensitivity',crossout[:,j,z])]:
                lo,hi=np.nanquantile(vals,[.025,.975]);out.append(dict(model=model,comparison=comp,metric=met,n_situations=n,
                  n_organizations=int((N[j]>0).sum()),n_unique_pool_patents=npool,draws=repeats,seed=SEED,method=method,
                  point=float(point[z]),lower=float(lo),upper=float(hi)))
    pd.DataFrame(out).to_csv(OUT/'development_uncertainty.csv',index=False)
    dump(OUT/'development_uncertainty_notes.json',dict(scope='Development exploratory; all years/lists/rankers fixed; no exact CI coverage or future environmental inference',
      independent_units='Organizations, not lists. Recurrent patent effects examined with independent organization and patent Exp(1) product multipliers',
      denominator='Complete pool candidate exposure1/pool_n within each feasible situation; includes unselected candidates',
      contribution_file='development_uncertainty_contributions.parquet contains changed-ID signed numerator contributions; development_pools.parquet contains all per-situation complete-pool denominator exposures',
      contexts='Sparse boundary groups receive descriptive results only; no between-group hypothesis test',source_contribution_audit='Exact task/general recovery all primary comparisons',rows=len(out)))
    dump(OUT/'development_bootstrap_runtime.json',dict(seconds=time.perf_counter()-boot_start,draws_per_method=repeats,methods=2,comparisons_per_model=5,rankers=2,metrics=2,rows=len(out),seed=SEED,predictor_fits=0))

def md(df):
    def fmt(v):
        if pd.isna(v):return '—'
        if isinstance(v,(float,np.floating)):return f'{v:.4f}'
        return str(v)
    return '| '+' | '.join(df.columns)+' |\n| '+' | '.join(['---']*len(df.columns))+' |\n'+'\n'.join('| '+' | '.join(fmt(v) for v in row)+' |' for row in df.itertuples(index=False,name=None))

def report():
    a=json.loads((OUT/'development_data_audit.json').read_text(encoding='utf-8'))
    sit=pd.read_csv(OUT/'development_situations.csv');s=pd.read_csv(OUT/'development_policy_summary.csv');c=pd.read_csv(OUT/'development_contrasts.csv');r=pd.read_csv(OUT/'development_decomposition.csv')
    cols=['model','core_context','policy','feasible_situations','feasible_organizations','core_positions',*METRICS]
    main=s[(s.core_context=='all')&s.policy.isin(['top30','task_title_cosine','core_priority_score','original_pair_q9','original_pair_q9_matched','legacy_pair_q30','legacy_pair_q30_matched','C09_m00','C09_m03','mmr_0.5','mmr_0.7','mmr_0.9'])][cols]
    grp=c[c.comparison.isin(['coverage_to9','within_C9_floor3','within_matched_coverage','legacy_within_matched_coverage','coverage6_to12_fixed_floor3'])][['model','core_context','comparison','n_situations','n_organizations','mean_delta_task_linked','mean_delta_novel_document_exposure','mean_delta_unique_unseen_core_pairs','mean_delta_general_reach']]
    text='# v6 开发期边界比较\n\n仅2013–2015，原开发期结果已被读取；本轮为事后开发探索，非预注册或新的独立验证。无新预测模型、下载或2022实验。\n\n'
    text+=f"## 数据及实际恢复\n\n{a['accepted_situations']}情景、{a['unique_organizations']}组织；逐情景恢复原core-task准入的history/core-history/pool/core-pool计数与coverage。不能将原v1 whole-portfolio池直接当作task池。\n\n"
    text+='development_legacy_recovery_checks.csv进一步核对120个情景×排序器行：既有q=.30的general-reach、unfamiliar-selected、novel供给与changed-ID数量全部精确恢复。开发旧文件未保存selected IDs，故不冒称新ID文件与缺失的旧文件逐ID一致。\n\n'
    text+='阈值在新summary前锁定：baseline core positions<6为低，6–12含端点为中，>12为高（即<20%、20–40%、>40%）。空组保留；不以quantile凑组。\n\n'
    text+='语义核查修正记录：既有quota_select对q=.30采用min(9,novel supply)。legacy_pair_q30忠实重建此supply-capped旧规则及matched control，全60情景；original_pair_q9保留最初严格九文档对照，仅供应充分55情景，不能称全体旧规则复现。Exact C,m grid绝不capping。追加比较的时间及原因存development_protocol_semantic_amendment.json。\n\n'
    counts=sit.groupby(['model','core_context']).agg(n_situations=('year','size'),n_organizations=('organization_id','nunique'),mean_baseline_core=('baseline_core_positions','mean')).reset_index()
    text+=md(counts)+'\n\n'
    if 'complete_point_run_seconds' in a:
        text+=f"实际point run {a['complete_point_run_seconds']:.3f}秒；按年重建秒数{a['year_reconstruction_seconds']}；源文件合计{a['complete_readonly_source_bytes']}bytes。只读源bytes及SHA-256见development_source_manifest.json。无额外原始库下载，新增缓存不足5MB。\n\n"
    text+='## 完整主要对照\n\n'+md(main)+'\n\n'
    text+='指标独立：task_linked为后来task-core外部引用的选中文档；novel_document_exposure为含新subclass pair的核心文档数；unique_unseen_core_pairs为列表内去重的新pair联合数，不是独立技术发明；general_reach为达到至少两外部组织引用的文档。禁止任意加权为单一效用。\n\n'
    text+='task_title_cosine是历史core标题词汇cosine排序，不是语义/工程relevance验证。core_priority_score先冻结得分core排序，最多30；不足30时明确noncore backfill。MMR为既有函数及既有三个weight，在同一重建task池重新应用，不能冒充旧whole-portfolio列表完全复现或近期论文复现。\n\n'
    text+='## 边界分组的paired差\n\n'+md(grp)+'\n\n'
    text+='## 原pair政策算术分解\n\n'+md(r)+'\n\n'
    text+='比例仅在共同情景n≥10、组织≥5且combined mean Δtask>0.1时展示；其余缺失不是删组。比例是描述性点值，没有ratio CI。\n\n'
    text+='全60旧规则的task分解：Boost combined +1.200=allocation +0.8667+within +0.3333；Ridge +1.1333=+1.3833−0.2500。该排序器方向分歧及crossed范围跨零，阻止把开发残差称为可稳定迁移的新颖收益。中高组仅4/5与1/3情景，不提供充分高覆盖验证。\n\n'
    text+='固定C9的m3只改变14/60和3/60列表，task各情景Boost全零、Ridge两loss其余tie；floor9则仅55供应充分情景，task均值+0.5091/−0.2182。固定C3的m3 task−0.0667/+0.2000，而C6为+0.2167/−0.1333；因此不能把单个floor或排序器的零/负差推广成novelty无用或有害。完整负向和正向均保留。\n\n'
    b=pd.read_csv(OUT/'development_binding_checks.csv')
    bs=b.groupby(['model','C','m']).agg(n=('binding','size'),binding=('binding','sum'),mean_changed=('changed_n','mean')).reset_index()
    text+='## 机械部分与新增判别信息\n\n'+md(bs)+'\n\n'
    text+='给定C的非bindingfloor保持精确identifier集合；binding时新增novel、移除nonnovel，故novel-document及unique-unseen-pair exposure非下降是结构性。floor要求文档数，不能把m=9写成至少九个不同pair。task-linked与general-reach净差符号不由floor保证，属于经验信息。coverage同C0比较的core席位变动是算术；later-linked变化非必然。固定m时变C仍可能改变实际novel exposure，不能声称实际新颖性不变。\n\n'
    text+='development_three_vector_frontier.csv 保留每个情景所有政策的(task-linked,novel-document-exposure,general-reach)三向量及观察到的非支配标记；非支配不是部署最优，也不用于结果挑政策。\n\n'
    if (OUT/'development_uncertainty.csv').exists():
        u=pd.read_csv(OUT/'development_uncertainty.csv');text+='## 组织及共享专利依赖\n\n'+md(u)+'\n\n'
        br=OUT/'development_bootstrap_runtime.json'
        if br.exists():text+='实际uncertainty运行记录：'+br.read_text(encoding='utf-8')+'\n\n'
    text+='同一组织跨年及共享patent依赖保留。primary uncertainty按组织重抽，crossed org×patent Exp(1)使用complete pool exposure1/pool_n，保持列表与环境固定；后者是敏感性范围，不是已验证coverage的精确CI。Sparse contexts只描述，不做因果moderation、组间显著性或新确认。\n\n全部grid目标及不供给capping由development_feasibility.csv记录；所有组/负向/零差保留。输出仅新v6目录与本报告。\n'
    rv=OUT/'development_readonly_manuscript_review.json'
    if rv.exists():text+='\n## v6 主稿开发结果只读核查\n\n'+rv.read_text(encoding='utf-8')+'\n'
    REPORT.write_text(text,encoding='utf-8');emit('REPORT_READY',path=str(REPORT))

if __name__=='__main__':
    ap=argparse.ArgumentParser();ap.add_argument('--pilot',action='store_true');ap.add_argument('--points',action='store_true');ap.add_argument('--bootstrap',action='store_true');ap.add_argument('--report',action='store_true');args=ap.parse_args()
    if args.pilot:reconstruct(True)
    elif args.points:reconstruct(False);report()
    elif args.bootstrap:bootstrap();report()
    elif args.report:report()
    else:reconstruct(False);bootstrap();report()
