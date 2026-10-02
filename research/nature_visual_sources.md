# Nature 风格图表来源与本文执行建议

核验日期：2026-10-02。目标期刊仍是 *Technology Analysis & Strategic Management*；以下 Nature 信息是视觉设计参照，不是本文投稿规范或质量认证。本文属 SSCI 技术与创新管理的档案实证研究，图表应呈现名额配置、搜索目标与证据边界，不把算法精度包装成主贡献。

## 调研结论

1. Nature 官方强调最终尺寸可读、无衬线字体、可编辑的矢量文字和线条、RGB 以及可访问配色。其终版字号 5–7 pt、面板字母 8 pt 和 89/183 mm 栏宽是明确的 Nature 家规；TASM 的实际 Word 插图不必机械缩至相同字号。本文应按插入后的尺寸选字号，保持全套一致。 [Nature figure specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)；[Nature final submission](https://www.nature.com/nature/for-authors/final-submission)
2. 公开 GitHub 的 SciencePlots `nature` 样式提供轴线 0.5 pt、数据线 1 pt、标记 3 pt 和无衬线 7 pt 的清晰起点，但没有解决本文的多面板布局、标签避让或统计编码。必须根据本稿重新设计布局。该仓库为 MIT 许可，可以选择性借鉴；不能据此宣称图已符合出版社全部规定。 [SciencePlots nature 源码](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/src/scienceplots/styles/journals/nature.mplstyle)；[MIT 许可](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/LICENSE)
3. K-Dense 的公开科学绘图技能强调原始意义、真实不确定性、颜色的冗余编码、精确物理尺寸和最终文件检查，适用于本次升级；其中软件版本、CLI 和环境安装指令没有执行，也无需为了绘图引入新依赖。 [scientific-visualization 全文](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-visualization/SKILL.md)

## 实际读取范围

| 来源 | 实际读取程度 | 核验结果与用途 |
|---|---|---|
| Nature, Preparing figures—our specifications | 官方 HTML 全文，154 行 | 核字体、字号、图形轴线与单位、配色、RGB、嵌入字体、矢量输出及不重叠原则。 |
| Nature, Building and exporting figure panels | 官方 HTML 全文，127 行 | 核 89/183 mm、170 mm 图高、面板排列、配色十六进制值、黑字、可编辑 PDF/EPS/SVG；主图与 Extended Data 格式分开。 |
| Nature, Final submission | 官网的完整正文经 Jina Reader 读取；直接 web open 被站点身份重定向阻止，未登录 | 核终版适用阶段、0.25–1 pt 线宽、同套字体、RGB、矢量与最小 300 dpi 照片。Jina 返回的是指定官方 URL 正文，不是第三方博客。 |
| Nature, Extended data formatting guidelines | 官方 HTML 全文，79 行 | 核 0.25–1 pt、三条主要水平线及用留白分组的表格规则；此页的在线 raster 限制不是本文 900 dpi 导出的限制。 |
| SciencePlots README、science/nature/no-latex 样式与 LICENSE | 通过 `gh api` 实际读取全部四个文本资源及完整许可；master 固定到上述 commit | 核样式组合顺序、LaTeX 依赖、字体重置风险和 MIT 条件，未安装或执行远程代码。 |
| K-Dense scientific-visualization SKILL.md 与 LICENSE.md | 通过 `gh api` 读取完整技能与许可；main 固定到上述 commit | 原 `K-Dense-AI/claude-scientific-skills` 地址已重定向到 `K-Dense-AI/scientific-agent-skills`。MIT 许可；未执行其中代码、联网命令或工具安装。 |
| Nature Communications How to submit | 官方检索正文读取相关 line-art 段落，未做全文逐段审阅 | 仅作为其他 Nature 期刊采用 1,200 dpi 非矢量线稿的补充例证，不将其规则移植成 TASM 规则。 |

## 官方规则与本文选择必须分开

| 项目 | 官方或源码实际内容 | 本文可执行选择 |
|---|---|---|
| 字号 | Nature 通常文字 5–7 pt，面板字母 8 pt 加粗、小写；Arial/Helvetica。 | TASM 中保持 Arial；按真实插图尺寸选择正文标签约 8–9 pt、面板字母约 9–10 pt。若采用 Nature 的 7 pt，须在最终 Word 尺寸确实可读。不要仅靠提高 dpi 补救小字。 |
| 物理尺寸 | Nature 终版 89/183 mm；图稿指南图高通常 ≤170 mm。不同页面的 90/180 mm 是近似尺寸或不同阶段说明。 | 复杂双面板优先在约 170–183 mm 宽画布设计；插入 Word 前计算缩放比例，必要时直接按 Word 宽度出图。尺寸只作设计参照。 |
| 线条 | Nature 终版建议 0.25–1 pt；SciencePlots nature 轴 0.5 pt、数据线 1 pt。 | 轴线约 0.5–0.6 pt；置信区间与数据线约 0.8–1 pt；示意箭头约 0.7–0.9 pt。缩放后的线宽应仍清楚，避免全部加粗。 |
| 配色 | Nature 官方给出 Wong 色盲友好色板，并要求高对比文字和区分线索。 | 数据类别使用固定色义；建议黑 #000000、蓝 #0072B2、朱红 #D55E00、蓝绿 #009E73。用标记/线型/面板分离冗余区分；不要靠红绿或彩虹传递全部信息。 |
| 布局 | 官方反对重叠文字、装饰、阴影、繁忙背景、无必要网格线及彩色正文。 | 白底、黑字；移除默认网格、阴影和装饰图标。区间图将长说明放在留白/图注；流程箭头沿固定留白走线，不穿越盒内文字。 |
| 文件 | 官方主图偏好可编辑矢量；禁止将线稿文字全部栅格化或转轮廓。 | 每图提供 PDF 和 SVG，另从原生绘图直接导出 ≥900 dpi PNG/TIFF。本次可统一 1,200 dpi raster；它是用户要求的交付选择，不是声称 Nature 所有图都强制 900 dpi。 |
| 表格 | 官方 Extended Data 建议表头上下和表底水平线，用留白分块，避免非必要颜色。 | 保留可编辑 Word 表格；统一表头与数字对齐、少量水平线，避免彩色大单元格、竖线网格、数字断行与靠截图压成位图。独立表图若另导出，仍应保留源数据和矢量版。 |

上表综合下列实际来源，明确区分官方要求与本项目的尺寸/字号选择： [Nature final submission](https://www.nature.com/nature/for-authors/final-submission)、[panel building guide](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)、[Extended Data guide](https://research-figure-guide.nature.com/figures/extended-data-formatting-guidelines/)、[SciencePlots nature style](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/src/scienceplots/styles/journals/nature.mplstyle)。

## 对本稿最有用的操作技巧

- **精确画布与字体。** 优先使用 Matplotlib 面向对象接口、GridSpec 或 constrained layout；布局完成后不要再调用 `tight_layout()`。要保持指定物理尺寸时，避免 `bbox_inches='tight'` 改变纸面大小，留足预定边距，并核实际 PDF MediaBox 和 raster 像素。PDF 使用 `pdf.fonttype=42`；SVG 使用 `svg.fonttype='none'` 保留文字，但它不嵌入字体，跨机仍需核字体。 [K-Dense 绘图技能](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-visualization/SKILL.md)
- **不要直接照搬样式组合。** SciencePlots `science` 开启 `text.usetex=True` 且使用 serif；`nature` 将字体改为 sans-serif；`no-latex` 又设为 serif/STIX。如组合，应最终明确 `text.usetex=False`、Arial sans-serif 和匹配的 mathtext 字体。本文只需手工写入经过审阅的少数 rcParams，无需安装 SciencePlots 或 LaTeX。 [science](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/src/scienceplots/styles/science.mplstyle)、[no-latex](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/src/scienceplots/styles/misc/no-latex.mplstyle)
- **效应图用位置和区间。** 本稿适合共轴的点—区间图，清楚分开 coverage contribution、within-coverage novelty contribution 和 total contrast；保留零参考线、真实区间、组织/组织年单位以及联合区间定义。不同目标放在独立面板并说明单位，不按任意权重合成“技术价值”。图中的负值、跨零宽区间和支持不足不可为美观而隐藏。 [K-Dense honest encoding](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-visualization/SKILL.md)
- **规则图重视可追踪路径。** 四路交接图只表达提出的路由：直接功能、机理类比、无支持、未知；不画成已验证采纳或组织绩效的因果链。箭头的锚点置于盒边，水平/竖直预留通道；要缩短标签时同步检查正文含义。用文字识别任务、选择规则和证据层次，比“脑/机器/灯泡”等装饰图标更明确。 [Nature panel guide](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)
- **提高 dpi 不能解决排版碰撞。** 高分辨率版必须从可编辑绘图直接输出，不能把原低分辨率图插值放大。交付前检查各独立图原图、完整 Word 页面和最终插入尺寸；自动 bbox/metadata 检查只能筛错，实际视觉检查仍需逐图逐表完成。 [Nature specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)

## 风险与验收边界

1. Nature 官方 Extended Data 的最大 300 dpi/10 MB 与 main vector 规则分别适用不同输出。本项目以 TASM 为目标，并额外交付用户要求的 ≥900 dpi 源生 raster，不能把两种规则混成一个所谓“Nature 认证”。 [Nature panel guide](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)
2. MIT 开源许可不等于官方 endorsed Nature 模板。若复制样式源码或工具的实质部分，保留相应版权和许可；只采用通用设计参数也不应声称运行了该软件。SciencePlots README 说正式文献引用并非必需。本次仅做源码与原则调研，不改变环境。 [SciencePlots README](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/README.md)、[K-Dense LICENSE](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/LICENSE.md)
3. “最高水平”通过清晰、准确、可读、可编辑和审查充分来实现，不能以配色或 dpi 单独证明。具体检验：字线不交叉、标签不裁切、符号和单位完整、相同量使用相同视觉尺度、图注与数字一致、真实科学区间没有省略。 [K-Dense review checklist](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-visualization/SKILL.md)

## 来源列表

- [Nature — Preparing figures: specifications](https://research-figure-guide.nature.com/figures/preparing-figures-our-specifications/)
- [Nature — Building and exporting figure panels](https://research-figure-guide.nature.com/figures/building-and-exporting-figure-panels/)
- [Nature — Final submission](https://www.nature.com/nature/for-authors/final-submission)
- [Nature — Extended Data formatting](https://research-figure-guide.nature.com/figures/extended-data-formatting-guidelines/)
- [Nature Communications — How to submit](https://www.nature.com/ncomms/submit/how-to-submit)
- [SciencePlots repo](https://github.com/garrettj403/SciencePlots)
- [SciencePlots nature style](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/src/scienceplots/styles/journals/nature.mplstyle)
- [SciencePlots MIT license](https://github.com/garrettj403/SciencePlots/blob/b9b16959570bd2fbc9ff5118bacc423c3bddd592/LICENSE)
- [K-Dense scientific-visualization skill](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/skills/scientific-visualization/SKILL.md)
- [K-Dense MIT license](https://github.com/K-Dense-AI/scientific-agent-skills/blob/154988403bb5a18e9d3c0ce4e6d5e2e4b184a298/LICENSE.md)

未安装插件、软件包或运行远程脚本；没有登录、创建账户、下载新数据或写入原始数据。只新增此 D 盘研究说明。

## 后续绘图实际执行记录

上文记录的是来源研究阶段。后续绘图阶段实际导入本机已经安装的 SciencePlots 2.2.2，组合 `science`、`nature`、`no-latex` 后明确设为 Arial 与可编辑矢量文字，并应用本稿需要的字号与留白；没有新增安装或执行远程代码。三图四表均原生导出 PDF/SVG 和 1200 dpi PNG/TIFF，真实几何检查与最终 Word 逐页复核见 `nature_artwork_check.json`、`nature_evidence_fidelity_check.json` 及 `nature_delivery_check.json`。原研究结果与非图注正文保留。
