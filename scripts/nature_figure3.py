"""Redraw frozen Figure 3 policy means without changing research outputs.

The two objectives remain separate. A grey path joins the seven computed
score-only coverage configurations in increasing C; it is not a frontier.
All ten policy symbols are keyed outside the data panels, without leaders.
"""
from pathlib import Path
import os
import json
import hashlib
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
os.environ['TEMP'] = os.environ['TMP'] = str(ROOT / 'temp')
os.environ['MPLCONFIGDIR'] = str(ROOT / 'temp/mpl_nature_figure3')

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.colors import Normalize
from matplotlib.ticker import FixedLocator
from matplotlib.font_manager import findfont, FontProperties
import pymupdf
from PIL import Image
from nature_visual_common import apply_style, save_figure, MM


POLICIES = [
    ('C00_r00', 'C = 0', 'o'),
    ('C03_r00', 'C = 3', 'v'),
    ('C06_r00', 'C = 6', 'D'),
    ('C09_r00', 'C = 9', 'p'),
    ('C12_r00', 'C = 12', 'h'),
    ('C15_r00', 'C = 15', 'P'),
    ('C30_r00', 'C = 30', '*'),
    ('unconstrained_top30', 'Baseline', 'X'),
    ('original_q30_matched', 'Coverage match', 's'),
    ('original_q30', 'Novelty reservation', '^'),
]


def sha256(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    apply_style()
    source = ROOT / 'results/revision_v3/decision_policy_summary.csv'
    old_script = ROOT / 'scripts/revision_v6_objective_evidence.py'
    helper = ROOT / 'scripts/nature_visual_common.py'
    out = ROOT / 'figures/nature_v1'
    out.mkdir(parents=True, exist_ok=True)
    stem = out / 'figure3_objective_tradeoffs'
    keys = [p[0] for p in POLICIES]
    raw = pd.read_csv(source)
    points = raw.loc[(raw.boundary == 'core_newpair') & raw.policy.isin(keys)].copy()
    assert len(points) == 20
    assert points.groupby('model').size().to_dict() == {'boosting': 10, 'ridge': 10}
    assert (points.situations == 356).all()
    assert not points[['model', 'policy']].duplicated().any()
    assert np.isfinite(points[['task_T', 'general_T', 'novel_core_seats']]).all().all()
    assert points.novel_core_seats.between(0, 18).all()
    for model, group in points.groupby('model'):
        rows = group.set_index('policy')
        assert set(rows.index) == set(keys)
        assert np.isclose(rows.loc['original_q30', 'core_seats'],
                          rows.loc['original_q30_matched', 'core_seats'])
        for policy, label, _ in POLICIES[:7]:
            assert np.isclose(rows.loc[policy, 'core_seats'], int(label.split('=')[1]))

    display = pd.DataFrame(POLICIES, columns=['policy', 'display_label', 'marker'])
    display['policy_order'] = np.arange(10)
    points = points.merge(display, on='policy', validate='many_to_one')
    points['panel'] = points.model.map({'boosting': 'a', 'ridge': 'b'})
    points = points.sort_values(['panel', 'policy_order']).reset_index(drop=True)
    points.to_csv(out / 'figure3_plot_data.csv', index=False, float_format='%.17g')
    # CSV includes every original source field alongside explicit display keys.
    provenance = {
        'generated_utc': datetime.now(timezone.utc).isoformat(),
        'source': str(source), 'source_sha256': sha256(source),
        'previous_plot_script': str(old_script), 'previous_plot_script_sha256': sha256(old_script),
        'drawing_script_sha256': sha256(__file__),
        'shared_style_sha256': sha256(helper),
        'font': 'Arial', 'font_file': findfont(FontProperties(family='Arial'), fallback_to_default=False),
        'boundary': 'core_newpair', 'point_rows': 20,
        'screens_per_policy_and_ranking': 356,
        'x': 'general_T', 'y': 'task_T', 'colour': 'novel_core_seats',
        'shared_colour_normalization': [0, 18],
        'policies': [{'key': p, 'label': label, 'marker': m} for p, label, m in POLICIES],
        'point_values': points[['panel', 'model', 'policy', 'task_T', 'general_T',
                                'novel_core_seats', 'core_seats', 'situations']].to_dict('records'),
        'interpretation': 'Descriptive means of separate objectives, not a composite value score. The grey line joins only seven computed score-only coverage allocations in increasing C, not an estimated frontier.',
        'uncertainty': 'No independent error bars are inferred from these repeated screening means; manuscript uncertainty is unchanged.',
        'data_changes': 'None. No refitting, relabelling, jittering, interpolation, or recomputation of study outcomes.',
        'status': 'PASS',
    }
    (out / 'figure3_plot_data.json').write_text(json.dumps(provenance, indent=2), encoding='utf-8')

    fig = plt.figure(figsize=(183 * MM, 109 * MM))
    axes = [fig.add_axes([0.096, 0.375, 0.404, 0.49]),
            fig.add_axes([0.575, 0.375, 0.404, 0.49])]
    cmap = plt.get_cmap('cividis')
    norm = Normalize(0, 18)
    for ax, model, title, panel in zip(axes, ['boosting', 'ridge'],
                                      ['Primary ranking', 'Alternative ranking'], ['a', 'b']):
        group = points.loc[points.model == model].set_index('policy')
        core = group.loc[keys[:7]]
        ax.plot(core.general_T, core.task_T, color='#B0B5B8', linewidth=0.85, zorder=1)
        for policy, _, marker in POLICIES:
            row = group.loc[policy]
            size = 36 if marker != '*' else 58
            ax.scatter([row.general_T], [row.task_T], c=[row.novel_core_seats],
                       cmap=cmap, norm=norm, marker=marker, s=size,
                       edgecolors='#202124', linewidths=0.55, zorder=3)
        ax.set_xlim(5.25, 10.2)
        ax.set_ylim(0.5, 8.5)
        ax.xaxis.set_major_locator(FixedLocator([6, 7, 8, 9, 10]))
        ax.yaxis.set_major_locator(FixedLocator([1, 2, 3, 4, 5, 6, 7, 8]))
        ax.set_xlabel('General linked documents per list', labelpad=6)
        ax.set_title(title, pad=10, fontweight='normal')
        ax.tick_params(axis='both', pad=3)
        # Panel identifiers are external to the axes and any data path.
        fig.text(ax.get_position().x0 - 0.029, 0.928, panel,
                 fontweight='bold', fontsize=11, ha='left', va='center')
    axes[0].set_ylabel('Task-linked documents per list', labelpad=7)
    axes[1].tick_params(labelleft=False)

    # Two rails place policy symbols beside exact keys, outside the plotting area.
    # Neutral legend symbols preserve the exclusive meaning of the colour scale.
    for i, (_, label, marker) in enumerate(POLICIES):
        x = [0.040, 0.230, 0.420, 0.610, 0.790][i % 5]
        y = 0.247 if i < 5 else 0.190
        legend_marker = Line2D([x], [y], transform=fig.transFigure,
                              linestyle='None', marker=marker,
                              markersize=6 if marker != '*' else 7.5,
                              markerfacecolor='#D1D4D6', markeredgecolor='#202124',
                              markeredgewidth=0.55)
        fig.add_artist(legend_marker)
        fig.text(x + 0.019, y, label, fontsize=8.3, va='center', ha='left')

    cax = fig.add_axes([0.307, 0.086, 0.386, 0.022])
    bar = fig.colorbar(matplotlib.cm.ScalarMappable(norm=norm, cmap=cmap),
                       cax=cax, orientation='horizontal', ticks=[0, 6, 12, 18])
    # Matplotlib otherwise rasterizes long colour bars even in SVG/PDF.
    # Keep this strip vector as well as all markers, lines and editable text.
    if bar.solids is not None:
        bar.solids.set_rasterized(False)
        # Some Word/LibreOffice SVG renderers reveal hairline seams between
        # adjacent vector cells. Same-colour edges overlap the seams without
        # changing the scale or substituting a raster image.
        bar.solids.set_edgecolor('face')
        bar.solids.set_linewidth(0.25)
    bar.outline.set_linewidth(0.5)
    bar.ax.tick_params(labelsize=8, width=0.5, length=2.5, pad=2)
    bar.set_label('Documents with unseen core combinations', fontsize=8.5, labelpad=4)
    report = save_figure(fig, stem, audit=True, extra_metadata=provenance)
    ns = '{http://www.w3.org/2000/svg}'
    svg = ET.parse(stem.with_suffix('.svg')).getroot()
    doc = pymupdf.open(stem.with_suffix('.pdf'))
    pdf_fonts = [list(item) for item in doc[0].get_fonts()]
    vector_check = {
        'status': 'PASS',
        'svg_text_nodes': len(svg.findall('.//' + ns + 'text')),
        'svg_image_nodes': len(svg.findall('.//' + ns + 'image')),
        'pdf_image_objects': len(doc[0].get_images()),
        'pdf_fonts': pdf_fonts,
        'pdf_canvas_mm': [doc[0].rect.width * 25.4 / 72,
                          doc[0].rect.height * 25.4 / 72],
        'plot_data_sha256': sha256(out / 'figure3_plot_data.csv'),
        'source_sha256': provenance['source_sha256'],
        'geometry_status': report['status'],
        'geometry_collision_count': len(report['text_text_overlaps']) + len(report['text_line_or_symbol_intersections']),
    }
    assert vector_check['svg_text_nodes'] == report['visible_texts'] == 40
    assert vector_check['svg_image_nodes'] == vector_check['pdf_image_objects'] == 0
    assert all('Arial' in row[3] and row[1] == 'ttf' for row in pdf_fonts)
    assert np.allclose(vector_check['pdf_canvas_mm'], [183, 109], atol=0.002)
    for ext in ['.png', '.tiff']:
        with Image.open(stem.with_suffix(ext)) as im:
            assert np.allclose([float(v) for v in im.info['dpi']], [1200, 1200], atol=.01)
    exported = pd.read_csv(out / 'figure3_plot_data.csv')
    assert np.allclose(exported[['task_T', 'general_T', 'novel_core_seats']],
                       points[['task_T', 'general_T', 'novel_core_seats']], atol=1e-12)
    (out / 'figure3_file_verification.json').write_text(json.dumps(vector_check, indent=2), encoding='utf-8')
    doc.close()
    print(json.dumps({'status': report['status'], 'stem': str(stem),
                      'canvas_mm': report['canvas_mm'], 'png_pixels': report['png_pixels'],
                      'visible_texts': report['visible_texts'],
                      'source_sha256': provenance['source_sha256']}, indent=2))


if __name__ == '__main__':
    main()
