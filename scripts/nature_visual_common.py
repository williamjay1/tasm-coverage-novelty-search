"""Shared scientific artwork style and deterministic final-size layout checks.

Uses the installed MIT-licensed SciencePlots science/nature/no-latex styles;
explicit overrides retain Arial, editable vectors and readable TASM artwork.
No manuscript evidence or outcome calculations are changed here.
"""
from pathlib import Path
import json
import itertools
import hashlib
import importlib.metadata
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.text import Text
from matplotlib.transforms import Bbox
from PIL import Image
import scienceplots  # registers the actual GitHub SciencePlots styles

MM = 1 / 25.4
WIDTH_MM = 183
COLORS = {'battery': '#0072B2', 'electronics': '#D55E00',
          'ink': '#202124', 'muted': '#5D646B', 'line': '#8F969D',
          'teal': '#009E73', 'pale': '#F5F7F8'}

def apply_style():
    plt.style.use(['science', 'nature', 'no-latex'])
    plt.rcParams.update({
        'font.family': 'sans-serif', 'font.sans-serif': ['Arial'],
        'font.size': 9, 'axes.labelsize': 9, 'axes.titlesize': 9.5,
        'xtick.labelsize': 8.5, 'ytick.labelsize': 8.5,
        'legend.fontsize': 8.5, 'text.color': COLORS['ink'],
        'axes.labelcolor': COLORS['ink'], 'xtick.color': COLORS['ink'],
        'ytick.color': COLORS['ink'], 'axes.edgecolor': COLORS['ink'],
        'axes.linewidth': .6, 'lines.linewidth': 1.0,
        'lines.markersize': 4, 'axes.grid': False,
        'xtick.direction': 'out', 'ytick.direction': 'out',
        'xtick.major.size': 3, 'ytick.major.size': 3,
        'xtick.major.width': .65, 'ytick.major.width': .65,
        'xtick.minor.visible': False, 'ytick.minor.visible': False,
        'xtick.top': False, 'ytick.right': False,
        'axes.spines.top': False, 'axes.spines.right': False,
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'savefig.facecolor': 'white', 'savefig.bbox': None,
        'svg.fonttype': 'none', 'pdf.fonttype': 42, 'ps.fonttype': 42,
        'text.usetex': False, 'mathtext.fontset': 'custom',
        'mathtext.rm': 'Arial', 'mathtext.it': 'Arial:italic', 'mathtext.bf': 'Arial:bold',
        'axes.formatter.use_mathtext': False, 'figure.dpi': 150,
    })

def _path_intersects(path, box):
    # Compound arrow paths contain CLOSEPOLY placeholders at (0,0). Do not
    # treat those placeholders as real lines; inspect the rendered segments.
    def segment_hit(a, b):
        if max(a[0], b[0]) < box.x0 or min(a[0], b[0]) > box.x1 or max(a[1], b[1]) < box.y0 or min(a[1], b[1]) > box.y1:
            return False
        delta = b-a; low=0.; high=1.
        for p,q in [(-delta[0],a[0]-box.x0),(delta[0],box.x1-a[0]),
                    (-delta[1],a[1]-box.y0),(delta[1],box.y1-a[1])]:
            if abs(p) < 1e-12:
                if q < 0:return False
            elif p < 0:
                low=max(low,q/p)
            else:
                high=min(high,q/p)
            if low > high:return False
        return True
    try:
        previous = start = None
        for vertices, code in path.iter_segments(curves=False, simplify=False):
            if code == path.MOVETO:
                previous = start = np.asarray(vertices[-2:])
            elif code == path.CLOSEPOLY:
                if previous is not None and start is not None and segment_hit(previous,start):return True
                previous = start
            elif code == path.LINETO:
                current = np.asarray(vertices[-2:])
                if previous is not None and segment_hit(previous,current):return True
                previous=current
        return False
    except (ValueError, TypeError):
        return False

def geometry_audit(fig):
    """Audit visible text at the exact canvas size, including side titles.

    Text bounding boxes are compared pairwise and against drawn axes data
    lines, patch edges and scatter symbols. Automated checks complement,
    rather than replace, final-size visual inspection.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    texts = []
    for artist in fig.findobj(match=Text):
        if not artist.get_visible() or not artist.get_text().strip():
            continue
        if artist.axes is not None and not artist.axes.get_visible():
            continue
        box = artist.get_window_extent(renderer)
        if not np.all(np.isfinite(box.extents)) or box.width <= 0 or box.height <= 0:
            continue
        texts.append((artist, box))
    overlaps = []
    for (one, b1), (two, b2) in itertools.combinations(texts, 2):
        if one is two:
            continue
        overlap = Bbox.intersection(b1, b2)
        if overlap is not None and overlap.width > .25 and overlap.height > .25:
            overlaps.append([one.get_text(), two.get_text()])
    outside = []
    canvas = fig.bbox
    for artist, box in texts:
        if box.x0 < canvas.x0 - .3 or box.y0 < canvas.y0 - .3 or box.x1 > canvas.x1 + .3 or box.y1 > canvas.y1 + .3:
            outside.append(artist.get_text())
    intersections = []
    for ai, ax in enumerate(fig.axes):
        if not ax.get_visible():
            continue
        paths = []
        for li, line in enumerate(ax.lines):
            if line.get_visible() and line.get_linestyle() not in ('None', 'none', ''):
                paths.append((f'axes{ai}:line{li}', line.get_transform().transform_path(line.get_path())))
        for pi, patch in enumerate(ax.patches):
            if patch.get_visible() and patch.get_linewidth() > 0:
                paths.append((f'axes{ai}:patch{pi}', patch.get_transform().transform_path(patch.get_path())))
        for artist, box in texts:
            # Limit checks to real plotted segments; axes spine/tick crossings
            # have separate render inspection and are not simulated as data.
            for label, path in paths:
                if _path_intersects(path, box):
                    intersections.append([artist.get_text(), label])
        for ci, collection in enumerate(ax.collections):
            if not collection.get_visible() or not hasattr(collection, 'get_offsets'):
                continue
            offsets = np.asarray(collection.get_offsets())
            if offsets.ndim != 2 or offsets.shape[1] != 2:
                continue
            positions = collection.get_offset_transform().transform(offsets)
            sizes = collection.get_sizes() if hasattr(collection, 'get_sizes') else np.array([])
            for ni, position in enumerate(positions):
                if not np.all(np.isfinite(position)):
                    continue
                radius = np.sqrt(sizes[min(ni, len(sizes)-1)]) / 2 * fig.dpi / 72 if len(sizes) else 0
                markerbox = Bbox.from_extents(position[0]-radius, position[1]-radius,
                                              position[0]+radius, position[1]+radius)
                for artist, box in texts:
                    if Bbox.intersection(markerbox, box) is not None:
                        intersections.append([artist.get_text(), f'axes{ai}:collection{ci}:marker{ni}'])
    return {'status': 'PASS' if not (overlaps or outside or intersections) else 'FAIL',
            'visible_texts': len(texts), 'text_text_overlaps': overlaps,
            'out_of_canvas_text': outside, 'text_line_or_symbol_intersections': intersections,
            'canvas_mm': (fig.get_size_inches()*25.4).tolist(),
            'minimum_font_pt': min((t.get_fontsize() for t,_ in texts), default=None),
            'check_scope': 'Bounding-box text collisions, plot lines/patch edges and scatter symbols; actual visual inspection also required.'}

def save_figure(fig, stem, audit=True, extra_metadata=None):
    stem = Path(stem)
    stem.parent.mkdir(parents=True, exist_ok=True)
    report = geometry_audit(fig)
    report.update({'style_source': 'garrettj403/SciencePlots: science + nature + no-latex, explicit Arial overrides',
                   'scienceplots_version': importlib.metadata.version('SciencePlots'),
                   'matplotlib_version': matplotlib.__version__,
                   'raster_dpi': 1200, 'vector_formats': ['pdf', 'svg'],
                   'metadata': extra_metadata or {}})
    stem.with_suffix('.layout.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    if audit and report['status'] != 'PASS':
        raise AssertionError(f'{stem.name}: geometry audit failed: {json.dumps(report)}')
    fig.savefig(stem.with_suffix('.pdf'), format='pdf')
    fig.savefig(stem.with_suffix('.svg'), format='svg')
    fig.savefig(stem.with_suffix('.png'), format='png', dpi=1200)
    fig.savefig(stem.with_suffix('.tiff'), format='tiff', dpi=1200,
                pil_kwargs={'compression': 'tiff_lzw'})
    fig.savefig(stem.parent / f'{stem.name}.preview.png', format='png', dpi=300)
    with Image.open(stem.with_suffix('.png')) as im:
        report['png_pixels'] = list(im.size)
        report['png_stored_dpi'] = [float(v) for v in im.info.get('dpi', ())]
    with Image.open(stem.with_suffix('.tiff')) as im:
        report['tiff_pixels'] = list(im.size)
        report['tiff_stored_dpi'] = [float(v) for v in im.info.get('dpi', ())]
    report['files'] = {ext: {'bytes': stem.with_suffix(ext).stat().st_size,
                            'sha256': hashlib.sha256(stem.with_suffix(ext).read_bytes()).hexdigest()}
                       for ext in ['.pdf', '.svg', '.png', '.tiff']}
    stem.with_suffix('.layout.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    plt.close(fig)
    return report
