"""Render the four unchanged v8 main tables at 183 mm with open rules.

No results are recomputed. Cell/caption/note strings come verbatim from v8 MD.
"""
from __future__ import annotations
import os
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
os.environ['MPLCONFIGDIR']=str(ROOT/'temp/nature_mpl')
import argparse,hashlib,json,re
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.font_manager import FontProperties
from nature_visual_common import apply_style,save_figure

OUT=ROOT/'figures/nature_v1'
SOURCE=ROOT/'data/main_table_content.json'
MM_TO_PT=72/25.4
WIDTH_MM=183.0
DESIGNS={
 1:dict(stem='table1_concepts',widths_mm=[45,76,62],align=['left']*3),
 2:dict(stem='table2_allocation',widths_mm=[21,26,34,35,34,33],align=['left','right','right','right','right','right']),
 3:dict(stem='table3_exchanges',widths_mm=[45,25,28,43,42],align=['left','center','right','right','right']),
 4:dict(stem='table4_handoff',widths_mm=[28,54,47,54],align=['left']*4),
}

def extract_tables(path=SOURCE):
    payload=json.loads(path.read_text(encoding='utf-8'))
    tables=payload['tables']
    if [t['number'] for t in tables]!=[1,2,3,4]:raise ValueError('Four main tables required')
    return tables

def text_width(renderer,text,prop):return renderer.get_text_width_height_descent(text,prop,ismath=False)[0]

def wrap_text(text,max_width,renderer,prop):
    """Greedy natural word wrapping, preserving each token and all cell content."""
    words=text.split();lines=[];current=''
    for word in words:
        if text_width(renderer,word,prop)>max_width:
            raise ValueError(f'Unbreakable token {word!r} ({text_width(renderer,word,prop):.2f} pt) exceeds {max_width:.2f} pt; increase column width')
        trial=(current+' '+word).strip()
        if current and text_width(renderer,trial,prop)>max_width:lines.append(current);current=word
        else:current=trial
    if current:lines.append(current)
    if ' '.join(lines)!=' '.join(text.split()):raise AssertionError('Wrapping changed content')
    return lines

def render_table(table):
    apply_style();d=DESIGNS[table['number']];wpt=WIDTH_MM*MM_TO_PT
    widths=np.asarray(d['widths_mm'],float)*MM_TO_PT
    assert np.isclose(widths.sum(),wpt)
    measure=plt.figure(figsize=(WIDTH_MM/25.4,1),dpi=72);canvas=FigureCanvasAgg(measure);canvas.draw();renderer=canvas.get_renderer()
    body=FontProperties(family='Arial',size=9.5);header=FontProperties(family='Arial',size=9.5,weight='bold')
    caption=FontProperties(family='Arial',size=10,weight='bold');note=FontProperties(family='Arial',size=9)
    pad=5.0;row_pad=6.0;body_leading=13.1;header_leading=13.1;caption_leading=13.8;note_leading=12.4
    caption_lines=wrap_text(table['caption'],wpt-2*pad,renderer,caption)
    note_lines=wrap_text(table['note'],wpt-2*pad,renderer,note)
    source_rows=[table['headers']]+table['rows'];wrapped=[];heights=[]
    for ri,row in enumerate(source_rows):
        prop=header if ri==0 else body;leading=header_leading if ri==0 else body_leading
        rr=[wrap_text(value,widths[ci]-2*pad,renderer,prop) for ci,value in enumerate(row)]
        wrapped.append(rr);heights.append(max(len(x) for x in rr)*leading+2*row_pad)
    plt.close(measure)
    top_pad=5.;caption_height=len(caption_lines)*caption_leading
    table_top=top_pad+caption_height+9.;table_bottom=table_top+sum(heights)
    note_top=table_bottom+10.;height_pt=note_top+len(note_lines)*note_leading+5.
    fig=plt.figure(figsize=(WIDTH_MM/25.4,height_pt/72),dpi=300);ax=fig.add_axes([0,0,1,1]);ax.set(xlim=(0,wpt),ylim=(height_pt,0));ax.set_axis_off()
    ax.text(pad,top_pad,'\n'.join(caption_lines),fontproperties=caption,linespacing=caption_leading/10,ha='left',va='top',parse_math=False)
    edges=np.r_[0,np.cumsum(widths)];row_tops=np.r_[table_top,table_top+np.cumsum(heights)];artists=[]
    for ri,row in enumerate(wrapped):
        for ci,lines in enumerate(row):
            ha='left' if ri==0 else d['align'][ci]
            x=edges[ci]+pad if ha=='left' else edges[ci+1]-pad if ha=='right' else (edges[ci]+edges[ci+1])/2
            prop=header if ri==0 else body;leading=header_leading if ri==0 else body_leading
            artist=ax.text(x,row_tops[ri]+row_pad,'\n'.join(lines),fontproperties=prop,linespacing=leading/prop.get_size_in_points(),ha=ha,va='top',parse_math=False)
            artists.append((ri,ci,artist))
    # Only top, header and bottom rules. No vertical lines, body rules or fills.
    for y,lw in ((table_top,.8),(table_top+heights[0],.5),(table_bottom,.8)):
        ax.plot([0,wpt],[y,y],color='#222222',lw=lw,solid_capstyle='butt')
    ax.text(pad,note_top,'\n'.join(note_lines),fontproperties=note,linespacing=note_leading/9,ha='left',va='top',parse_math=False)
    fig.canvas.draw();renderer=fig.canvas.get_renderer();inverse=ax.transData.inverted();checks=[]
    for ri,ci,artist in artists:
        b=artist.get_window_extent(renderer);coords=inverse.transform([[b.x0,b.y0],[b.x1,b.y1]])
        left,right=sorted(coords[:,0]);top,bottom=sorted(coords[:,1]);cell=(edges[ci],row_tops[ri],edges[ci+1],row_tops[ri+1])
        passed=left>=cell[0]+1 and right<=cell[2]-1 and top>=cell[1]+1 and bottom<=cell[3]-1
        checks.append({'row':ri,'column':ci,'cell_text':source_rows[ri][ci],'wrapped_lines':wrapped[ri][ci],'font_pt':artist.get_fontsize(),'cell_bounds_pt':[float(v) for v in cell],'text_bounds_pt':[float(left),float(top),float(right),float(bottom)],'inside_cell':bool(passed)})
    assert all(c['inside_cell'] for c in checks),'Text exceeds table cell'
    assert all(c['font_pt']>=9 for c in checks)
    metadata={'kind':'table','table_number':table['number'],'source':'unchanged v8 manuscript Markdown','width_mm':WIDTH_MM,'height_mm':height_pt/MM_TO_PT,'column_widths_mm':d['widths_mm'],'body_font_pt':9.5,'header_font_pt':9.5,'note_font_pt':9.,'caption_font_pt':10.,'rules':3,'vertical_rules':0,'striping':False,'content_cell_count':len(checks),'cell_bounds_checks':checks,'all_cells_fit':True,'wrapping_preserves_all_tokens':True,'data':table}
    return fig,metadata

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--preview-only',action='store_true');args=ap.parse_args();OUT.mkdir(parents=True,exist_ok=True)
    tables=extract_tables();data={'source':str(SOURCE.relative_to(ROOT)),'source_sha256':hashlib.sha256(SOURCE.read_bytes()).hexdigest(),'tables':tables}
    (OUT/'table_data.json').write_text(json.dumps(data,indent=2,ensure_ascii=False),encoding='utf-8')
    manifest=[]
    for table in tables:
        fig,metadata=render_table(table);stem=OUT/DESIGNS[table['number']]['stem']
        if args.preview_only:
            fig.savefig(str(stem)+'.preview.png',dpi=300,facecolor='white');(OUT/(stem.name+'.cell_geometry.json')).write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
        else:
            save_figure(fig,stem,audit=True,extra_metadata=metadata)
            (OUT/(stem.name+'.cell_geometry.json')).write_text(json.dumps(metadata,indent=2,ensure_ascii=False),encoding='utf-8')
        manifest.append({'table':table['number'],'stem':stem.name,'height_mm':metadata['height_mm'],'cell_checks':metadata['content_cell_count'],'all_cells_fit':True});plt.close(fig)
        print(json.dumps(manifest[-1],ensure_ascii=False),flush=True)
    (OUT/'table_geometry_summary.json').write_text(json.dumps(manifest,indent=2,ensure_ascii=False),encoding='utf-8')

if __name__=='__main__':main()
