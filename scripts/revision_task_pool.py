"""Post-critique task-specific pools, recorded core novelty and identity audit.

Forecast scores are the frozen v1 scores; no future label enters selection.
All mutable outputs stay on D. Raw and v1 artifacts are read only.
"""
from __future__ import annotations
import os
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
os.environ.setdefault('MKL_NUM_THREADS','2')
import argparse, json, re, itertools
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from policy_core import quota_select, stable_order

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/revision_v2'
CORE=re.compile(r'^H01M10/(6[0-9]|50)')
def codes(v): return {x for x in str(v).split('|') if x and x!='nan'}
def pairs(v): return set(itertools.combinations(sorted(v),2))
def emit(**v): print(json.dumps(v,ensure_ascii=False),flush=True)

def run(identity):
    OUT.mkdir(parents=True,exist_ok=True)
    patents=pd.read_parquet(ROOT/'datasets/canonical_v1/study_patents.parquet')
    patents['patent_id']=patents.patent_id.astype(str)
    patents['year']=pd.to_datetime(patents.patent_date).dt.year
    if identity=='raw':
        hist=pd.read_parquet(ROOT/'datasets/canonical_v1/study_portfolios.parquet')
    else:
        hist=pd.read_parquet(ROOT/'datasets/revision_v2/task_disambig_portfolios.parquet')
        patents['assignee_id']=patents['disambig_assignee_id'].fillna('')
    hist['patent_id']=hist.patent_id.astype(str)
    if 'patent_date' not in hist:hist=hist.rename(columns={'date':'patent_date','title':'patent_title'})
    if identity=='disambig' and 'disambig_assignee_id' in hist:
        hist['assignee_id']=hist['disambig_assignee_id'].fillna('')
    hist['year']=pd.to_datetime(hist.patent_date).dt.year
    hist['owners']=hist.assignee_id.map(codes)
    hist['subclasses']=hist.cpc_codes.map(codes)
    # CPC exact groups are used only for recorded core novelty, never relevance.
    rawhist=pd.read_parquet(ROOT/'datasets/patent_portfolios.parquet',columns=['patent_id','cpc_at_issue']).drop_duplicates('patent_id')
    rawhist['patent_id']=rawhist.patent_id.astype(str)
    hist=hist.merge(rawhist,on='patent_id',how='left',validate='one_to_one') if 'cpc_at_issue' not in hist else hist
    hist['core_groups']=hist.cpc_at_issue.fillna('').map(lambda v:{x for x in codes(v) if CORE.match(x)})
    hist['core_pairs']=hist['subclasses'].map(pairs)
    allrows=[]; selected=[]; poolrows=[]; samples=[]
    for year in [2013,2014,2015,2018,2019,2020,2021]:
        train=patents.loc[(patents.year>=2010)&(patents.year<=year-3)]
        tv=TfidfVectorizer(max_features=20000,min_df=2,max_df=.98,ngram_range=(1,2),stop_words='english',dtype=np.float32,sublinear_tf=True)
        tv.fit(train.patent_title.fillna(''))
        cur=pd.read_parquet(ROOT/f'results/primary_v1/scores_{year}.parquet')
        cur['patent_id']=cur.patent_id.astype(str)
        if identity=='disambig':cur['assignee_id']=cur.disambig_assignee_id.fillna('')
        cur['owners']=cur.assignee_id.map(codes)
        cur['subclasses']=cur.cpc_codes.map(codes)
        cur['core_groups']=cur.cpc_at_issue.fillna('').map(lambda v:{x for x in codes(v) if CORE.match(x)})
        cur['core_pairs']=cur['subclasses'].map(pairs)
        current_core_groups=cur.core_groups.tolist(); current_core_pairs=cur.core_pairs.tolist()
        h=hist.loc[(hist.year>=year-5)&(hist.year<year)].reset_index(drop=True)
        xh=tv.transform(h.patent_title.fillna('')); xc=tv.transform(cur.patent_title.fillna(''))
        memberships=h[['patent_id','owners','is_core']].explode('owners').dropna(subset=['owners'])
        n=memberships.groupby('owners').patent_id.nunique()
        nc=memberships.loc[memberships.is_core].groupby('owners').patent_id.nunique()
        elig=n.loc[(n>=15)&(nc.reindex(n.index,fill_value=0)>=3)].sort_index()
        memberindex=memberships.groupby('owners').groups
        ids=cur.patent_id.to_numpy(); owners=cur.owners.tolist(); sub=cur.subclasses.tolist()
        core=cur.is_core.to_numpy(bool)
        general=(cur[('future_disambig_attention' if identity=='disambig' else 'future_external_attention')].to_numpy()>=2)
        applicant=(cur.future_applicant_attention.to_numpy()>=2)
        for org in elig.index:
            ii=np.asarray(memberindex[org],dtype=int)
            coverage=h.iloc[ii].subclasses.map(bool).mean()
            if coverage<.8:continue
            ci=ii[h.iloc[ii].is_core.to_numpy(bool)]
            hc=set().union(*h.iloc[ii].subclasses)
            hg=set().union(*h.iloc[ii].core_groups)
            hp=set().union(*h.iloc[ci].core_pairs)
            ext=np.asarray([bool(x) and org not in x for x in owners])
            classified=np.asarray([bool(x) for x in sub])
            far=np.asarray([bool(x) and not bool(x&hc) for x in sub])
            core_newgroup=np.asarray([core[j] and bool(current_core_groups[j]-hg) for j in range(len(cur))])
            core_newpair=np.asarray([core[j] and bool(current_core_pairs[j]-hp) for j in range(len(cur))])
            for relevance,hi in [('whole_organization',ii),('core_task',ci)]:
                centroid=normalize(sparse.csr_matrix(np.asarray(xh[hi].mean(axis=0))))
                sim=(xc@centroid.T).toarray().ravel()
                pi=np.flatnonzero(ext&classified&(sim>=.03))
                if len(pi)<50:continue
                common={'identity':identity,'organization_id':str(org),'year':year,'relevance':relevance,'history_n':len(ii),'core_history_n':len(ci),'core_history_fraction':len(ci)/len(ii),'pool_n':len(pi),'core_pool_n':int(core[pi].sum()),'classification_coverage':float(coverage)}
                samples.append(common)
                boundaries={'subclass_external':far[pi],'text_quartile':sim[pi]<=np.quantile(sim[pi],.25),'core_newgroup':core_newgroup[pi],'core_newpair':core_newpair[pi]}
                if year>=2018:
                    poolrows.extend([{'identity':identity,'organization_id':str(org),'year':year,'relevance':relevance,'patent_id':str(ids[j]),'is_core':bool(core[j]),'task_similarity':float(sim[j]),'general_signal':bool(general[j]),'applicant_signal':bool(applicant[j]),**{b:bool(v[z]) for b,v in boundaries.items()}} for z,j in enumerate(pi)])
                for boundary,bfar in boundaries.items():
                    # Identity audit uses every boundary in the same reconstructed pool.
                    for model in ['boosting','ridge','popularity']:
                        score=cur.iloc[pi]['score_'+model].to_numpy()
                        base=quota_select(score,ids[pi],bfar,30,0); bset=set(base.tolist())
                        for q in [0.,.1,.2,.3,.4]:
                            sel=quota_select(score,ids[pi],bfar,30,q); sset=set(sel.tolist())
                            add=np.asarray(sorted(sset-bset),int); rem=np.asarray(sorted(bset-sset),int)
                            row={**common,'boundary':boundary,'model':model,'q':q,'changed_n':len(add),'unfamiliar_pool_n':int(bfar.sum()),'unfamiliar_selected':int(bfar[sel].sum())}
                            for lname,lab in [('general',general),('applicant',applicant)]:
                                lp=lab[pi]; bt=int(lp[base].sum());rt=int(lp[rem].sum());at=int(lp[add].sum())
                                row.update({lname+'_T':int(lp[sel].sum()),lname+'_U':int((lp[sel]&bfar[sel]).sum()),lname+'_base_T':bt,lname+'_removed':rt,lname+'_added':at,lname+'_original_survival':(bt-rt)/bt if bt else np.nan})
                            allrows.append(row)
                            if year>=2018:
                                selected.extend([{'identity':identity,'organization_id':str(org),'year':year,'relevance':relevance,'boundary':boundary,'model':model,'q':q,'patent_id':str(ids[pi[j]]),'unfamiliar':bool(bfar[j]),'is_core':bool(core[pi[j]]),'added':j not in bset} for j in sel])
                emit(identity=identity,year=year,organization=str(org),relevance=relevance,pool=len(pi)) if len(samples)%80==0 else None
        emit(event='year_done',identity=identity,year=year,situations=len([s for s in samples if s['year']==year]))
        if year>=2018:
            pd.DataFrame(selected).to_parquet(OUT/f'taskpool_{identity}_selected_{year}.parquet',index=False)
            pd.DataFrame(poolrows).to_parquet(OUT/f'taskpool_{identity}_pools_{year}.parquet',index=False)
            selected=[];poolrows=[]
    details=pd.DataFrame(allrows); details.to_parquet(OUT/f'taskpool_{identity}_detail.parquet',index=False)
    pd.DataFrame(samples).to_parquet(OUT/f'taskpool_{identity}_situations.parquet',index=False)
    test=details.loc[details.year>=2018]
    summary=test.groupby(['identity','relevance','boundary','model','q']).agg(n=('organization_id','size'),organizations=('organization_id','nunique'),general_T=('general_T','mean'),general_U=('general_U','mean'),applicant_T=('applicant_T','mean'),applicant_U=('applicant_U','mean'),general_added=('general_added','mean'),general_removed=('general_removed','mean'),changed_n=('changed_n','mean')).reset_index()
    summary.to_csv(OUT/f'taskpool_{identity}_summary.csv',index=False)
    emit(event='done',identity=identity,rows=len(details),selected=len(selected),poolrows=len(poolrows))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--identity',choices=['raw','disambig'],default='raw');a=p.parse_args();run(a.identity)
