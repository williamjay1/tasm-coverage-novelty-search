"""Post-evaluation fixed-list sensitivity excluding focal-organization citing edges."""
from pathlib import Path
from collections import defaultdict
import json
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
RUN=ROOT/'results'/'primary_v1'
def owners(x):
    return set(str(x).split('|')) if pd.notna(x) and str(x) else set()

def main():
    p=pd.read_parquet(ROOT/'datasets/canonical_v1/study_patents.parquet')
    meta=p.set_index('patent_id').to_dict('index')
    s=pd.concat([pd.read_parquet(RUN/f'selected_primary_{y}.parquet') for y in range(2018,2022)])
    s=s.loc[s.k.eq(30)].copy()
    context=pd.read_parquet(RUN/'heldout_policy_results.parquet')
    context=context.loc[context.model.eq('boosting')&context.k.eq(30)&context.policy.eq('topk'),['organization_id','year','context']]
    s=s.merge(context,on=['organization_id','year'],validate='many_to_one')
    rules=pd.read_csv(RUN/'development_allocation_rules.csv')
    extra=[]
    for threshold in [.9,1.]:
        r=rules.loc[rules.model.eq('boosting')&rules.k.eq(30)&rules.minimum_retention.eq(threshold),['context','share']]
        x=s.merge(r,on='context',validate='many_to_one')
        chosen=x.share.map(lambda v:'topk' if v==0 else f'quota_{v:.1f}')
        x=x.loc[x.policy.eq(chosen)].copy()
        x['policy']=f'context_rule_retention_{threshold:.1f}'
        extra.append(x[s.columns])
    s=pd.concat([s,*extra],ignore_index=True)
    assert s.groupby(['organization_id','year','policy']).size().eq(30).all()
    chosen_ids=set(s.patent_id)
    edges=pd.read_parquet(ROOT/'datasets/patent_citations.parquet')
    edges=edges.loc[edges.cited_id.isin(chosen_ids)].drop_duplicates(['cited_id','citing_id'])
    valid=defaultdict(list)
    for e in edges.itertuples(index=False):
        m=meta[e.cited_id]
        y=pd.Timestamp(m['patent_date']).year
        d=pd.Timestamp(e.citing_date)
        if not (pd.Timestamp(y+1,1,1)<=d<=pd.Timestamp(y+3,12,31)):continue
        own=owners(m['assignee_id']); citing=owners(e.citing_assignee_id)
        if not citing or own.intersection(citing):continue
        if pd.notna(e.citing_application_id) and pd.notna(e.cited_application_id) and e.citing_application_id==e.cited_application_id:continue
        valid[e.cited_id].append(citing)
    for pid in chosen_ids:
        seen=set().union(*valid[pid]) if valid[pid] else set()
        assert len(seen)==int(meta[pid]['future_external_attention']),(pid,len(seen),meta[pid]['future_external_attention'])
    pairs=s[['organization_id','patent_id']].drop_duplicates()
    changed=0; high=[]
    for r in pairs.itertuples(index=False):
        kept=[o for o in valid[r.patent_id] if r.organization_id not in o]
        seen=set().union(*kept) if kept else set()
        high.append(int(len(seen)>=2))
        changed+=len(seen)!=int(meta[r.patent_id]['future_external_attention'])
    pairs['high']=high
    s=s.merge(pairs,on=['organization_id','patent_id'],validate='many_to_one')
    s['distant_high']=s.high*s.distant
    a=s.groupby(['organization_id','year','policy'],as_index=False).agg(hits=('high','sum'),distant_hits=('distant_high','sum'))
    b=a.loc[a.policy.eq('topk'),['organization_id','year','hits','distant_hits']]
    a=a.merge(b,on=['organization_id','year'],suffixes=('','_topk'),validate='many_to_one')
    rows=[]
    for policy,g in a.groupby('policy'):
        assert len(g)==356
        rows.append(dict(policy=policy,n_decisions=len(g),mean_total_hits=g.hits.mean(),mean_distant_hits=g.distant_hits.mean(),mean_total_gain=(g.hits-g.hits_topk).mean(),mean_distant_gain=(g.distant_hits-g.distant_hits_topk).mean(),pooled_total_retention=g.hits.sum()/g.hits_topk.sum()))
    pd.DataFrame(rows).to_csv(RUN/'focal_excluded_sensitivity.csv',index=False)
    notes=dict(status='PASS',analysis_timing='Post-evaluation measurement sensitivity; no model or policy reselection',unique_selected_patents=len(chosen_ids),organization_patent_pairs=len(pairs),pairs_with_changed_counts=changed,primary_label_reconstruction='All selected patent counts match canonical counts exactly',exclusion='Discard entire citing edge if any citing owner is the focal searching organization; then recount distinct citing organizations and apply >=2',fixed_sample=356)
    (RUN/'focal_excluded_sensitivity_notes.json').write_text(json.dumps(notes,indent=2),encoding='utf-8')
    print(json.dumps(notes))
    print(pd.DataFrame(rows).round(5).to_string(index=False))

if __name__=='__main__':main()
