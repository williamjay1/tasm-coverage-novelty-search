"""SYNTHETIC SOFTWARE TEST ONLY. The fixture is not research evidence."""
import datetime as dt
import json
from pathlib import Path
import subprocess
import sys
import pandas as pd

ROOT=Path(__file__).resolve().parents[1]
work=ROOT/"temp"/("SYNTHETIC_LABEL_TEST_"+dt.datetime.now().strftime("%Y%m%d_%H%M%S"))
work.mkdir(parents=True)
def candidate(pid,date,app,owners="A|B",disambig="DA|DB"):
    return dict(patent_id=pid,patent_date=pd.Timestamp(date),application_id=app,assignee_id=owners,
        disambig_assignee_id=disambig,patent_title="Synthetic battery thermal title",
        abstract="Synthetic software testing material only",cpc_codes="H01M|F28F",is_core=True)
pd.DataFrame([candidate("P1","2013-06-01","APP1"),candidate("P2","2014-01-01","APP1"),
    candidate("P3","2022-01-01","APP3"),candidate("P4","2013-01-01","APP4","","")]).to_parquet(work/"patent_domain.parquet",index=False)
def edge(cid,date,owners,app="OTHER",category="cited by examiner"):
    return dict(citing_id=cid,cited_id="P1",citing_date=pd.Timestamp(date),citing_assignee_id=owners,
        citing_disambig_assignee_id="|".join("D"+x for x in owners.split("|")) if owners else "",
        citing_application_id=app,citation_category=category)
pd.DataFrame([edge("C1","2013-10-01","C"),edge("C2","2014-01-01","D"),edge("C3","2014-01-02","B|J"),
    edge("C4","2014-06-01","E","APP1"),edge("C5","2015-01-01",""),edge("C6","2013-03-01","F"),
    edge("C7","2017-01-01","G"),edge("C8","2016-12-31","D"),
    edge("C9","2015-02-01","H",category="cited by applicant"),
    edge("C9","2015-02-01","H",category="cited by applicant")]).to_parquet(work/"patent_citations.parquet",index=False)
pd.DataFrame([dict(patent_id="P1",date="2013-06-01",title="Synthetic title",assignee_id=owner,
    cpc_codes="H01M|F28F",is_core=True) for owner in ["A","B"]]).to_parquet(work/"patent_portfolios.parquet",index=False)
subprocess.run([sys.executable,str(ROOT/"scripts"/"prepare_study_data.py"),"--source",str(work),"--output",str(work/"canonical")],check=True)
p=pd.read_parquet(work/"canonical"/"study_patents.parquet").set_index("patent_id")
assert set(p.index)=={"P1","P3"}
assert p.loc["P1","early_external_attention"]==1
assert p.loc["P1","future_external_attention"]==2
assert p.loc["P1","future_applicant_attention"]==1
assert p.loc["P1","future_external_citing_patents"]==3
assert p.loc["P1","future_disambig_attention"]==2
assert pd.isna(p.loc["P3","future_external_attention"])
h=pd.read_parquet(work/"canonical"/"study_portfolios.parquet")
assert len(h)==1 and set(h.iloc[0].assignee_id.split("|"))=={"A","B"}
audit=json.loads((work/"canonical"/"label_audit.json").read_text())
assert audit["n_same_application_duplicates_removed"]==1
print("PASS: SYNTHETIC label adapter tests: temporal windows, co-ownership, unknown owners, duplicate edges, same application, censoring, owner aggregation. No empirical result generated.")
