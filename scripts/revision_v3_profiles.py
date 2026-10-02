"""Outcome-free profile admission diagnostic, locked in revision_v3_design.md.

V3 battery results are exploratory. Original artifacts remain read-only.
"""
from __future__ import annotations
import os
for key in ('OMP_NUM_THREADS','OPENBLAS_NUM_THREADS','MKL_NUM_THREADS'):
    os.environ.setdefault(key,'2')
import json, itertools
from pathlib import Path
import numpy as np
import pandas as pd
from scipy import sparse
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.preprocessing import normalize
from policy_core import stable_order, quota_select

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'results/revision_v3'
def codes(x):return {z for z in str(x).split('|') if z and z not in {'nan','None','<NA>'}}
def pairs(x):return set(itertools.combinations(sorted(x),2))

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    patents=pd.read_parquet(ROOT/'datasets/canonical_v1/study_patents.parquet')
    patents['patent_id']=patents.patent_id.astype(str)
    patents['year']=pd.to_datetime(patents.patent_date).dt.year
    hist=pd.read_parquet(ROOT/'datasets/canonical_v1/study_portfolios.parquet')
    hist['patent_id']=hist.patent_id.astype(str)
    hist['year']=pd.to_datetime(hist.patent_date).dt.year
    hist['owners']=hist.assignee_id.map(codes)
    hist['subclasses']=hist.cpc_codes.map(codes)
    hist['pairs']=hist.subclasses.map(pairs)
    sit=pd.read_parquet(ROOT/'results/revision_v2/taskpool_raw_situations.parquet')
    sit=sit[(sit.relevance=='core_task') & (sit.year>=2018)]
    labels=pd.read_parquet(ROOT/'datasets/revision_v2/task_patent_labels.parquet')
    label_cols=['future_core_signal_1patent','future_external_signal_2org','future_applicant_signal_2org']
    profiles=[];details=[];selected=[]
    for year, sy in sit.groupby('year'):
        train=patents[(patents.year>=2010)&(patents.year<=year-3)]
        tv=TfidfVectorizer(max_features=20000,min_df=2,max_df=.98,ngram_range=(1,2),
            stop_words='english',dtype=np.float32,sublinear_tf=True)
        tv.fit(train.patent_title.fillna(''))
        cur=pd.read_parquet(ROOT/f'results/primary_v1/scores_{year}.parquet')
        cur['patent_id']=cur.patent_id.astype(str)
        cur=cur.merge(labels[['patent_id',*label_cols]],on='patent_id',validate='one_to_one',suffixes=('','_v3'))
        ids=cur.patent_id.to_numpy();core=cur.is_core.to_numpy(bool)
        own=cur.assignee_id.map(codes).tolist();sub=cur.cpc_codes.map(codes).tolist()
        cp=[pairs(z) for z in sub]
        xc=tv.transform(cur.patent_title.fillna(''))
        h=hist[(hist.year>=year-5)&(hist.year<year)].reset_index(drop=True)
        xh=tv.transform(h.patent_title.fillna(''))
        mem=h[['patent_id','owners','is_core']].explode('owners')
        groups=mem.groupby('owners').groups
        counts=mem.groupby('owners').patent_id.nunique()
        cn=mem[mem.is_core].groupby('owners').patent_id.nunique().reindex(counts.index,fill_value=0)
        eligible=counts[(counts>=15)&(cn>=3)].sort_index().index.tolist()
        stats={o:(int(counts[o]),int(cn[o])) for o in eligible}
        # Same archived domain, independent of selected organizations.
        generic_h=patents[(patents.year>=year-5)&(patents.year<year)&patents.is_core]
        generic=normalize(sparse.csr_matrix(np.asarray(tv.transform(generic_h.patent_title.fillna('')).mean(axis=0))))
        centroids={}
        for o in eligible:
            ii=np.asarray(groups[o],int);ci=ii[h.iloc[ii].is_core.to_numpy(bool)]
            centroids[o]=normalize(sparse.csr_matrix(np.asarray(xh[ci].mean(axis=0))))
        for s in sy.itertuples():
            org=s.organization_id;ii=np.asarray(groups[org],int)
            ci=ii[h.iloc[ii].is_core.to_numpy(bool)]
            target=np.log1p(stats[org])
            donor=min((o for o in eligible if o!=org),key=lambda o:(float(np.sum((np.log1p(stats[o])-target)**2)),str(o)))
            di=np.asarray(groups[donor],int);dc=di[h.iloc[di].is_core.to_numpy(bool)]
            focal_core=set(h.iloc[ci].patent_id);donor_core=set(h.iloc[dc].patent_id)
            hp=set().union(*h.iloc[ci].pairs)
            novel=np.asarray([core[j] and bool(cp[j]-hp) for j in range(len(cur))])
            external=np.asarray([bool(o) and org not in o for o in own])
            classified=np.asarray([bool(x) for x in sub])
            pools={};lists={}
            for pname,cent in [('actual',centroids[org]),('generic',generic),('matched_donor',centroids[donor])]:
                sim=(xc@cent.T).toarray().ravel()
                pi=np.flatnonzero(external&classified&(sim>=.03));pools[pname]=set(ids[pi])
                ncore=int(core[pi].sum());nn=len(pi)-ncore;nv=int(novel[pi].sum())
                feasible=(ncore>=9 and nn>=21 and nv>=3)
                profiles.append({'organization_id':org,'year':year,'profile':pname,'pool_n':len(pi),
                    'core_pool_n':ncore,'newpair_pool_n':nv,'fixed9_all_policies_feasible':feasible,
                    'donor':donor,'donor_history_n':stats[donor][0],'donor_core_history_n':stats[donor][1],
                    'focal_history_n':len(ii),'focal_core_history_n':len(ci),
                    'donor_log_distance':float(np.linalg.norm(np.log1p(stats[donor])-target)),
                    'donor_core_history_shared_n':len(focal_core&donor_core),
                    'generic_core_history_n':len(generic_h)})
                if not feasible:continue
                for model in ['boosting','ridge']:
                    score=cur['score_'+model].to_numpy()
                    top=pi[stable_order(score[pi],ids[pi])[:30]]
                    cix=pi[core[pi]];nix=pi[~core[pi]]
                    noncore=nix[stable_order(score[nix],ids[nix])[:21]]
                    cbase=cix[stable_order(score[cix],ids[cix])[:9]]
                    cnv=cix[quota_select(score[cix],ids[cix],novel[cix],9,.3)]
                    for policy,sel in [('forecast_top30',top),('fixed9',np.r_[cbase,noncore]),('fixed9_newpair30',np.r_[cnv,noncore])]:
                        assert len(sel)==len(set(sel))==30
                        lists[pname,model,policy]=set(ids[sel])
                        row={'organization_id':org,'year':year,'profile':pname,'model':model,'policy':policy,
                            'core_seats':int(core[sel].sum()),'novel_core_seats':int(novel[sel].sum()),
                            'mean_task_similarity':float(sim[sel].mean())}
                        for lname,col in [('task','future_core_signal_1patent'),('general','future_external_signal_2org'),('applicant','future_applicant_signal_2org')]:
                            vv=cur[col].to_numpy(bool);row[lname+'_T']=int(vv[sel].sum())
                            row[lname+'_novel_T']=int((vv[sel]&novel[sel]).sum())
                        details.append(row)
                        selected.extend({'organization_id':org,'year':year,'profile':pname,'model':model,'policy':policy,
                            'patent_id':str(ids[j]),'is_core':bool(core[j]),'newpair':bool(novel[j])} for j in sel)
            for row in profiles[-3:]:
                pn=row['profile'];aa=pools['actual'];bb=pools[pn]
                row['pool_jaccard_actual']=len(aa&bb)/len(aa|bb) if aa|bb else np.nan
                for model in ['boosting','ridge']:
                    for policy in ['forecast_top30','fixed9','fixed9_newpair30']:
                        if ('actual',model,policy) in lists and (pn,model,policy) in lists:
                            inter=len(lists['actual',model,policy]&lists[pn,model,policy])
                            row[model+'_'+policy+'_changed_from_actual']=30-inter
            if len(profiles)%90==0:print(json.dumps({'year':int(year),'organizations_done':len(profiles)//3}),flush=True)
        pd.DataFrame(selected).to_parquet(OUT/f'profile_selected_{year}.parquet',index=False);selected=[]
        print(json.dumps({'event':'year_done','year':int(year)}),flush=True)
    prof=pd.DataFrame(profiles);detail=pd.DataFrame(details)
    prof.to_parquet(OUT/'profile_admission.parquet',index=False)
    detail.to_parquet(OUT/'profile_policy_detail.parquet',index=False)
    ok=prof.groupby(['organization_id','year']).fixed9_all_policies_feasible.all()
    common=set(ok[ok].index)
    detail['common_support']=[(o,y) in common for o,y in zip(detail.organization_id,detail.year)]
    summary=[]
    for support,df in [('available_by_profile',detail),('all_three_common',detail[detail.common_support])]:
        for (pn,model,policy),g in df.groupby(['profile','model','policy']):
            summary.append({'support':support,'profile':pn,'model':model,'policy':policy,'situations':len(g),
                'organizations':g.organization_id.nunique(),**{c:g[c].mean() for c in ['core_seats','novel_core_seats','task_T','task_novel_T','general_T','applicant_T']}})
    pd.DataFrame(summary).to_csv(OUT/'profile_summary.csv',index=False)
    contrast=[]
    dc=detail[detail.common_support]
    for model in ['boosting','ridge']:
        for policy in ['forecast_top30','fixed9','fixed9_newpair30']:
            g=dc[(dc.model==model)&(dc.policy==policy)]
            for alt in ['generic','matched_donor']:
                a=g[g.profile=='actual'].set_index(['organization_id','year'])
                b=g[g.profile==alt].set_index(['organization_id','year']).reindex(a.index)
                d=a.task_T-b.task_T
                contrast.append({'model':model,'policy':policy,'contrast':'actual_minus_'+alt,'n':len(d),
                    'task_delta':d.mean(),'actual_wins':int((d>0).sum()),'ties':int((d==0).sum()),'actual_losses':int((d<0).sum()),
                    'general_delta':(a.general_T-b.general_T).mean(),'applicant_delta':(a.applicant_T-b.applicant_T).mean()})
    pd.DataFrame(contrast).to_csv(OUT/'profile_contrasts.csv',index=False)
    audit={'original_situations':len(sit),'common_situations':len(common),'profiles':prof.groupby('profile').agg(n=('year','size'),feasible=('fixed9_all_policies_feasible','sum'),median_pool=('pool_n','median'),mean_pool_overlap=('pool_jaccard_actual','mean')).reset_index().to_dict('records'),
        'donor_core_history_overlap_situations':int((prof[prof.profile=='matched_donor'].donor_core_history_shared_n>0).sum()),
        'claim':'Exploratory profile admission diagnostic; no task mandate or adoption validation.'}
    (OUT/'profile_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps(audit),flush=True)

if __name__=='__main__':main()
