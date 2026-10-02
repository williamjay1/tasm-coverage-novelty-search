"""Re-render verified v8 process and allocation evidence as editable artwork."""
from pathlib import Path
import hashlib
import json
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, Patch
from nature_visual_common import apply_style, save_figure, COLORS, MM

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'figures/nature_v1'
apply_style()

def workflow():
    height = 151
    fig = plt.figure(figsize=(183*MM, height*MM))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, 183); ax.set_ylim(height, 0); ax.axis('off')
    def text(x,y,s,**kwargs):
        return ax.text(x,y,s, color=COLORS['ink'], va='center', **kwargs)
    def box(x,y,w,h,title,body,title_y=6,body_y=20,body_size=8.6):
        ax.add_patch(Rectangle((x,y),w,h,facecolor='white',edgecolor=COLORS['line'],lw=.65))
        text(x+w/2,y+title_y,title,ha='center',fontsize=9.2,fontweight='bold')
        text(x+w/2,y+body_y,body,ha='center',fontsize=body_size,linespacing=1.48)
    def arrow(start,end,dashed=False):
        ax.add_patch(FancyArrowPatch(start,end,arrowstyle='-|>',mutation_scale=8,
                                    color=COLORS['muted'],lw=.75,
                                    linestyle=(0,(3,2)) if dashed else '-'))
    text(5,8,'Selection at the search origin',fontsize=10,fontweight='bold',ha='left')
    boxes=[(5,'Search objective','Task and outcome\nspecified by sponsor'),
           (50,'Starting shortlist','Frozen ranking $U$\nBaseline coverage $C_0$\nCandidate supply'),
           (95,'Task allocation','Task positions $C$\nUnfamiliar minimum $m$\nRecord infeasibility'),
           (140,'Unfamiliar shortfall','Count $n_{B(C)}$ in $B(C)$\n$d = \\max\\{0,\\, m - n_{B(C)}\\}$')]
    for x,title,body in boxes:
        box(x,20,38,33,title,body,body_y=21,body_size=8.3 if x==140 else 8.6)
    for end,start in [(43,50),(88,95),(133,140)]:
        arrow((end+.7,36.5),(start-.7,36.5))
    arrow((159,53.8),(159,66.2))
    ax.add_patch(Rectangle((5,67),173,23,facecolor='white',edgecolor=COLORS['line'],lw=.65))
    text(91.5,73,'Actual action in a feasible list',ha='center',fontsize=9.2,fontweight='bold')
    text(48,83,'$d = 0$: identical to $B(C)$',ha='center',fontsize=9)
    text(134,83,'$d > 0$: $d$ core exchanges',ha='center',fontsize=9)
    # Both assessments depart from the complete action node, not from its
    # two individual d=0/d>0 labels. The shared junction avoids implying that
    # either action state exclusively determines one evidence assessment.
    ax.plot([91.5,91.5],[90.8,97],color=COLORS['muted'],lw=.75)
    ax.plot([57,91.5],[97,97],color=COLORS['muted'],lw=.75)
    ax.plot([91.5,149.5],[97,97],color=COLORS['muted'],lw=.75,linestyle=(0,(3,2)))
    arrow((57,97),(57,109.2))
    arrow((149.5,97),(149.5,109.2),dashed=True)
    text(5,101,'Evidence assessments',ha='left',fontsize=9.5,fontweight='bold')
    ax.add_patch(Rectangle((5,110),104,35,facecolor='white',edgecolor=COLORS['line'],lw=.65))
    text(57,117,'Proposed source-based handoff',ha='center',fontsize=9.2,fontweight='bold')
    text(57,126,'Direct function  ·  Mechanism analogy',ha='center',fontsize=8.7)
    text(57,133,'Unsupported match  ·  Unresolved evidence',ha='center',fontsize=8.7)
    text(57,140,'Original text, constraints and precise locators',ha='center',fontsize=8.5)
    ax.add_patch(Rectangle((121,110),57,35,facecolor='white',edgecolor=COLORS['line'],lw=.65))
    text(149.5,119,'Later archival evaluation',ha='center',fontsize=9.2,fontweight='bold')
    text(149.5,133,'Task links\nUnfamiliar exposure\nGeneral reach',ha='center',fontsize=8.7,linespacing=1.48)
    return save_figure(fig,OUT/'figure1_screening',extra_metadata={
        'source':'data/workflow_specification.json',
        'source_sha256':hashlib.sha256((ROOT/'data/workflow_specification.json').read_bytes()).hexdigest(),
        'semantic_checks':['Current source handoff does not wait for future citations',
                           'Dashed branch is retrospective outcome evaluation',
                           'd=0 identical selection, d>0 core exchanges in feasible lists'],
        'line_semantics':'Solid: selection and current handoff; dashed: later archival assessment'})

def allocation():
    source = ROOT/'results/revision_v7/effective_policy_detail.parquet'
    data = pd.read_parquet(source)
    keys = ['organization_id','year']; Cs=[0,3,6,9,12,15,30]
    policies=[f'B{c:02d}_m00' for c in Cs]
    metadata={'source':source.relative_to(ROOT).as_posix(),
              'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
              'shortfall':[],'allocation_common_support':[]}
    fig = plt.figure(figsize=(183*MM,143*MM))
    axes=np.array([[fig.add_axes([.105,.625,.375,.27]),fig.add_axes([.595,.625,.375,.27])],
                   [fig.add_axes([.105,.105,.375,.315]),fig.add_axes([.595,.105,.375,.315])]])
    fig.legend(handles=[Patch(facecolor=COLORS[t],edgecolor='none',label=t.capitalize())
                        for t in ['battery','electronics']],ncol=2,frameon=False,
               loc='upper center',bbox_to_anchor=(.52,.99),columnspacing=2.5,handlelength=1.2)
    short_rows=[]; allocation_rows=[]
    for col,model in enumerate(['boosting','ridge']):
        name='Primary ranking' if model=='boosting' else 'Alternative ranking'
        ax=axes[0,col]
        for offset,task in zip([-.21,.21],['battery','electronics']):
            rows=data[(data.task==task)&(data.model==model)&(data.policy=='B09_m00')].copy()
            rows['d']=np.maximum(0,3-rows.novel_document_exposure)
            counts=rows.d.value_counts().reindex(range(4),fill_value=0)
            n=len(rows)
            expected={('battery','boosting'):56,('battery','ridge'):36,
                      ('electronics','boosting'):45,('electronics','ridge'):14}[(task,model)]
            assert int(counts.iloc[1:].sum())==expected
            values=counts.to_numpy()/n*100
            bars=ax.bar(np.arange(4)+offset,values,width=.37,color=COLORS[task],linewidth=0)
            for di,(bar,count) in enumerate(zip(bars,counts.to_numpy())):
                ax.annotate(str(int(count)),(bar.get_x()+bar.get_width()/2,bar.get_height()),
                            xytext=(0,4),textcoords='offset points',ha='center',va='bottom',fontsize=8.5)
                short_rows.append(dict(task=task,model=model,n=n,d=di,count=int(count),percent=float(values[di])))
            metadata['shortfall'].append({'task':task,'model':model,'n':n,
                                         'counts_by_d':{str(k):int(v) for k,v in counts.items()}})
        ax.set_xlim(-.65,3.65);ax.set_ylim(0,111);ax.set_yticks([0,25,50,75,100])
        ax.set_xticks(range(4));ax.set_xlabel('Unfamiliar shortfall, d',labelpad=5)
        if col==0:ax.set_ylabel('Screens (%)',labelpad=5)
        ax.set_title(name,loc='left',pad=10,fontweight='normal')
        ax.text(-.19,1.11,'a' if col==0 else 'b',transform=ax.transAxes,
                fontweight='bold',fontsize=11,ha='left',va='center')
        ax=axes[1,col]
        for task in ['battery','electronics']:
            rows=data[(data.task==task)&(data.model==model)&data.policy.isin(policies)].copy()
            complete=rows.groupby(keys).policy.nunique()
            complete=complete[complete==len(policies)].index
            selected=rows.set_index(keys).loc[complete].reset_index()
            assert selected.groupby('policy').size().nunique()==1
            means=selected.groupby('requested_C').task_linked.mean().reindex(Cs)
            n=len(complete)
            ax.plot(Cs,means.to_numpy(),marker='o' if task=='battery' else 's',
                    markersize=4,lw=1,color=COLORS[task],markeredgecolor='white',markeredgewidth=.5)
            allocation_rows.extend(dict(task=task,model=model,n=n,C=c,mean_task_linked=float(v))
                                   for c,v in zip(Cs,means.to_numpy()))
            metadata['allocation_common_support'].append({'task':task,'model':model,'n':n,
                'requested_C':Cs,'mean_task_linked':means.to_list(),
                'distinct_organizations':int(selected.organization_id.nunique())})
        ax.set_xlim(-1,31);ax.set_ylim(0,9)
        ax.set_yticks([0,3,6,9]);ax.set_xticks(Cs)
        ax.set_xlabel('Task positions in a 30-document list, C',labelpad=5)
        if col==0:ax.set_ylabel('Task-linked documents per list',labelpad=5)
        ax.set_title(name,loc='left',pad=10,fontweight='normal')
        ax.text(-.19,1.11,'c' if col==0 else 'd',transform=ax.transAxes,
                fontweight='bold',fontsize=11,ha='left',va='center')
    # Same y limits within each row permit direct comparison of the rankings.
    pd.DataFrame(short_rows).to_csv(OUT/'figure2_shortfall_data.csv',index=False)
    pd.DataFrame(allocation_rows).to_csv(OUT/'figure2_allocation_data.csv',index=False)
    (OUT/'figure2_evidence.json').write_text(json.dumps(metadata,indent=2),encoding='utf-8')
    return save_figure(fig,OUT/'figure2_action_allocation',extra_metadata=metadata)

if __name__=='__main__':
    OUT.mkdir(parents=True,exist_ok=True)
    print(json.dumps({'figure1':workflow()['status'],'figure2':allocation()['status']}))
