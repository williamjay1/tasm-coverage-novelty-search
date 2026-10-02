"""Read frozen historical policy outputs; separate objectives without weights."""
from pathlib import Path
import os
import json
import hashlib
from datetime import datetime, timezone
ROOT = Path(__file__).resolve().parents[1]
os.environ['TEMP'] = os.environ['TMP'] = str(ROOT / 'temp')
os.environ['MPLCONFIGDIR'] = str(ROOT / 'temp/mpl_v6')
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

def main():
    out = ROOT / 'results/revision_v6'
    figures = ROOT / 'figures/revision_v6'
    out.mkdir(parents=True, exist_ok=True)
    figures.mkdir(parents=True, exist_ok=True)
    source = ROOT / 'results/revision_v3/decision_policy_summary.csv'
    data = pd.read_csv(source)
    policies = ['C00_r00','C03_r00','C06_r00','C09_r00','C12_r00','C15_r00','C30_r00',
                'unconstrained_top30','original_q30_matched','original_q30']
    points = data.loc[(data.boundary == 'core_newpair') & data.policy.isin(policies)].copy()
    assert len(points) == 20 and (points.situations == 356).all()
    rows = []
    for model, group in points.groupby('model'):
        lookup = group.set_index('policy')
        base = lookup.loc['unconstrained_top30']
        match = lookup.loc['original_q30_matched']
        novelty = lookup.loc['original_q30']
        assert np.isclose(match.core_seats, novelty.core_seats)
        row = {'model':model, 'situations':356}
        for metric in ['task_T','novel_core_seats','task_U','general_T']:
            row['coverage_' + metric] = float(match[metric] - base[metric])
            row['within_' + metric] = float(novelty[metric] - match[metric])
        row['task_reproduced_percent'] = float(100 * row['coverage_task_T'] /
                                              (novelty.task_T - base.task_T))
        rows.append(row)
    contrasts = pd.DataFrame(rows)
    points.to_csv(out / 'historical_objective_points.csv', index=False)
    contrasts.to_csv(out / 'historical_objective_contrasts.csv', index=False)
    plt.rcParams.update({'font.family':'DejaVu Sans','font.size':10})
    fig, axes = plt.subplots(1, 2, figsize=(10.2, 4.5), sharex=True, sharey=True)
    norm = matplotlib.colors.Normalize(0, 18)
    cmap = plt.get_cmap('viridis')
    for ax, model, title in zip(axes, ['boosting','ridge'], ['Primary ranking','Alternative ranking']):
        group = points.loc[points.model == model].set_index('policy')
        ordinary = group.loc[[p for p in policies if p.startswith('C')]].sort_values('core_seats')
        ax.plot(ordinary.general_T, ordinary.task_T, color='#9b9b9b', lw=1.3, zorder=1)
        ax.scatter(ordinary.general_T, ordinary.task_T, c=ordinary.novel_core_seats,
                   cmap=cmap, norm=norm, s=55, edgecolors='white', linewidths=.6, zorder=2)
        for policy in ['C00_r00','C09_r00','C30_r00']:
            row = group.loc[policy]
            offset = (-40,-13) if policy == 'C09_r00' else (5,6)
            ax.annotate(f'{int(row.core_seats)} core', (row.general_T, row.task_T),
                        xytext=offset, textcoords='offset points', fontsize=9)
        for policy, marker, label in [
            ('unconstrained_top30','X','Forecast baseline'),
            ('original_q30_matched','s','Coverage match'),
            ('original_q30','^','Novelty reservation')
        ]:
            row = group.loc[policy]
            ax.scatter(row.general_T, row.task_T, c=[row.novel_core_seats], cmap=cmap,
                       norm=norm, marker=marker, s=85, edgecolors='black', linewidths=.8,
                       label=label, zorder=3)
        ax.set_title(title)
        ax.set_xlabel('General linked documents per list')
        ax.grid(alpha=.18)
        ax.set_xlim(5.3,10.15)
        ax.set_ylim(.55,8.55)
        ax.spines[['top','right']].set_visible(False)
    axes[0].set_ylabel('Task-linked documents per list')
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', ncol=3, frameon=False,
               bbox_to_anchor=(.48,0), fontsize=9)
    fig.subplots_adjust(left=.085, right=.84, bottom=.20, top=.89, wspace=.14)
    cax = fig.add_axes([.865,.25,.018,.57])
    colorbar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm,cmap=cmap), cax=cax)
    colorbar.set_label('Documents with unseen core combinations')
    for extension in ['svg','pdf','png']:
        fig.savefig(figures / f'objective_tradeoffs.{extension}', dpi=900 if extension=='png' else 150)
    plt.close(fig)
    audit = {
        'checked_utc': datetime.now(timezone.utc).isoformat(),
        'source_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),
        'point_rows':len(points),'all_points_same_356_situations':True,
        'metrics':'Task links, selected documents with an unseen pair, general links; no composite value index.',
        'novelty_contrasts_hold_realized_coverage':True,
        'uncertainty':'The descriptive figure does not turn mean differences into independent uncertainty. Main text retains paired and crossed sensitivity intervals.',
        'status':'PASS'
    }
    (out / 'historical_objective_audit.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(contrasts.to_string(index=False),flush=True)

if __name__ == '__main__':
    main()
