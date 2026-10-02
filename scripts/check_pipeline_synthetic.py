"""Integration fixture only: synthetic values must never be manuscript evidence."""
from pathlib import Path
import datetime as dt
import json
import subprocess
import sys
import numpy as np
import pandas as pd

root=Path(__file__).resolve().parents[1]
folder=root/'temp'/('SYNTHETIC_SOFTWARE_TEST_'+dt.datetime.now().strftime('%Y%m%d_%H%M%S'))
folder.mkdir(parents=True)
rng=np.random.default_rng(20260929)
rows=[]
terms=['thermal cooling battery module heat exchanger','electronic circuit cooling substrate heat sink',
       'liquid flow temperature control heat transfer','battery cell thermal coolant vehicle assembly']
for year in range(2008,2018):
    for j in range(120):
        org=j%6
        topic=j%4
        owners=f'ORG{org}' if j%13 else f'ORG{org}|ORG{(org+1)%6}'
        rows.append(dict(patent_id=f'TESTONLY_{year}_{j:04d}',patent_date=f'{year}-06-01',
            patent_title=terms[topic]+f' apparatus {j}',patent_abstract=terms[topic]*3,
            assignee_id=owners,cpc_codes=['H01M10/60','H05K7/20','F28F1/00','H01M10/60'][topic],
            is_core=topic in [0,3],num_claims=10,early_external_attention=int(rng.poisson(1)),
            future_external_attention=int(rng.poisson(2+topic))))
data=folder/'SYNTHETIC_NOT_EMPIRICAL.parquet'
pd.DataFrame(rows).to_parquet(data,index=False)
out=folder/'run'
command=[sys.executable,str(root/'scripts'/'run_search_study.py'),'--input',str(data),
         '--output',str(out),'--years','2013','2014','2017','--development-end','2014',
         '--capacities','5','--min-history','6','--min-core-history','2',
         '--max-organizations','2','--random-repeats','1','--max-features','500']
subprocess.run(command,check=True)
audit=json.loads((out/'context_rule_audit.json').read_text())
assert audit['test_years']==[2017]
assert audit['test_start_after_label_maturity']==2017
for path in out.glob('vocabulary_audit_*.json'):
    row=json.loads(path.read_text());assert row['latest_training_label_year']<=row['year']
result=pd.read_parquet(out/'heldout_policy_results.parquet')
keys=['organization_id','year','k','model']
expected=set(map(tuple,result.loc[result.policy=='topk',keys].to_numpy()))
for policy in ['context_rule_retention_0.9','context_rule_retention_1.0']:
    actual=set(map(tuple,result.loc[result.policy==policy,keys].to_numpy()))
    assert actual==expected
print('PASS: synthetic end-to-end integration, matured model and policy labels, common holdout decision sets. No empirical evidence generated.')
print(folder)
