# v8 组织样本描述与披露/复现核验

执行日期：2026-10-02。范围：只读既有资料，补充样本描述与准确披露；未修改主稿、旧数据或旧复现包，未下载数据或进行外部存档。

## 1 路线与执行

Route：SSCI 技术管理实证，历史筛选回放。核心标准是组织样本与搜索任务的关系、比较的可核性、主张与档案证据的匹配；不要求默认因果识别或把预测精度当主要贡献。本任务只做描述统计与材料核验，不新增假设检验或结局筛选。

运行 [revision_v8_org_profile.py](../scripts/revision_v8_org_profile.py) 后，逐情景重建所有搜索起点前五个完整授予年份的组合。运行约 5 秒；运行前 D 盘约 133 GB 可用，输出均为 D 盘小规模派生结果。没有新模型拟合、原始下载或引用结局导入。

实际核验通过：

- battery：356 个组织—年、114 个 normalized owner keys；electronics：1,077 个组织—年、371 个 keys。组织—年集合、候选池数与核心候选数和 v7 `U` 样本逐行一致，不重复计算模型/政策行。
- 两任务的历史总授予数、任务授予数与 classification coverage 全部逐情景恢复；battery 的分类广度与 v4 既有特征逐行相等。
- electronics 历史合格 1,082 个情景中，5 个因候选池不足 50 被排除，保留实际 1,077 个可行情景。

来源与校验：[profile_audit.json](../results/revision_v8_profiles/profile_audit.json)、[source manifest](../results/revision_v8_profiles/profile_source_manifest.json)、[protocol](../results/revision_v8_profiles/profile_protocol.json)。这不是新增独立样本。

## 2 主描述：组织—年作为观察单位

每个情景使用 t−5 至 t−1 的完整授予年份、所有技术领域的组合。分类广度是四字符 CPC/IPC subclass 的去重并集，不能称为工程师认知距离、吸收能力或 Katila and Ahuja 的 search scope。组合大小指观察到的授予专利数，不能替代员工数、企业规模或研发投入。

| 既有历史指标 | Battery，356 情景 | Electronics，1,077 情景 |
|---|---|---|
| 前五年总授予数：中位数（IQR）；范围 | 478.5（142–2,958.5）；15–44,285 | 481（123–1,684）；15–44,285 |
| 前五年任务授予数：中位数（IQR）；范围 | 6.5（4–14）；3–210 | 6（4–12）；3–407 |
| 任务授予数/总授予数：中位数（IQR）；范围 | 1.760%（0.474–6.558%）；0.009–46.667% | 1.566%（0.553–4.865%）；0.044–100% |
| 历史分类广度：中位数（IQR）；范围 | 121.5（60–220.25）；6–421 | 93（44–164）；6–421 |
| 准入候选文档数：中位数（IQR）；范围 | 1,554.5（1,110.25–2,072）；318–4,061 | 787（536–1,135）；51–2,748 |
| 核心候选文档数：中位数（IQR）；范围 | 346（268.25–383.25）；63–462 | 204（136–277）；10–570 |

IQR 采用 linear 25th/75th quantiles。历史记录的 classification coverage 在两个入样集合均为 100%；这描述已有分类可用性，并不验证分类的工程功能准确性。历史多 owner grants 比例中位数分别为 0.572%（IQR 0–5.530%）和 0.926%（0–5.926%）；共有人专利可分别计入各 owner 的组合，同一 owner—年内只计一次。

完整未舍入结果：[profile_summary_orgyear.csv](../results/revision_v8_profiles/profile_summary_orgyear.csv)。逐情景记录：[organization_year_profiles.csv](../results/revision_v8_profiles/organization_year_profiles.csv)。源文件为已有 `study_portfolios.parquet`、`validation_portfolios.parquet` 与原准入情景；本报告没有引入行业或企业规模标签。

建议主文以这个组织—年描述为主，避免把它写成 114 或 371 个独立组织的分布。

### 可直接加入 §3.1/§3.3 的英文

> The samples vary substantially in their preceding five-year patent portfolios. Across the 356 battery organization-year situations, the median portfolio contains 478.5 grants (interquartile range 142–2,958.5), with a median task share of 1.76% (0.47–6.56%) and 121.5 distinct recorded CPC/IPC subclasses (60–220.25). The corresponding values across 1,077 electronics situations are 481 grants (123–1,684), 1.57% task share (0.55–4.86%) and 93 subclasses (44–164). These are historical patent-portfolio measures, rather than observations of organizational size, engineers' expertise or enacted search. The samples share 53 owner keys and 156 organization-year situations. They represent two task comparisons within a common historical setting.

如果篇幅紧，只保留组合中位数和 IQR，将 task share、breadth 和范围移到补充表；不要删除两任务组织重叠的解释。

## 3 唯一组织的辅助描述与重复年份

如果需要一行对应一个 unique owner，而非较频繁合格者拥有较大权重，使用其在该任务中**最后一个合格历史 origin**。这不是所有组织共同的 2021 横截面：battery 中 102 个 owner 最后在 2021、8 个在 2020、3 个在 2019、1 个在 2018；electronics 中相应为 312、25、21、13。

| 每 unique owner 最后合格 origin 的指标 | Battery，114 keys | Electronics，371 keys |
|---|---|---|
| 总授予数：中位数（IQR）；范围 | 427.5（133.5–2,312.5）；15–44,285 | 388（89–1,429）；15–44,285 |
| 任务占比：中位数（IQR）；范围 | 1.756%（0.471–7.362%）；0.009–36.842% | 1.751%（0.598–6.158%）；0.045–100% |
| 历史分类广度：中位数（IQR）；范围 | 120（53.5–219.25）；6–420 | 86（37.5–150.5）；6–420 |

来源：[unique-owner summary](../results/revision_v8_profiles/profile_summary_unique_owner.csv)、[one-row-per-owner records](../results/revision_v8_profiles/organization_last_origin_profiles.csv)、[last-origin year composition](../results/revision_v8_profiles/profile_last_origin_years.csv)。本辅助描述保留全样本 owner 集合，不以单一年份删去较早退出的 owner。

重复入样构成：

| 可行情景数量/owner | Battery keys | Electronics keys |
|---|---:|---:|
| 1 个 origin | 15 | 75 |
| 2 个 origins | 19 | 62 |
| 3 个 origins | 17 | 58 |
| 全部 4 个 origins | 63 | 176 |

Battery 2018–2021 情景数分别为 72、86、96、102；electronics 分别为 225、254、286、312。来源：[participation counts](../results/revision_v8_profiles/profile_participation_counts.csv)、[annual counts](../results/revision_v8_profiles/profile_annual_counts.csv)。这些数量说明组织与年份重复结构，不将它们解释为真实监测行为或组织规模增长。

## 4 组织身份、类型与跨任务重叠

主身份仍为源记录 as-published organization name 经 uppercase ASCII alphanumeric 规范化后的 key。完整 co-owner 集合进入外部所有权判断；机械规范化合并大小写、空格与标点差异，但不可靠合并公司别名、子公司、更名或并购集团，去除 non-ASCII 也可能造成键碰撞。回溯消歧是已有敏感性，不能据此声称已识别真实 corporate groups。

原源完整 schemas 确实包含 `assignee_type`，并在 retrospective `patent_assignee_disambig.parquet` 留存该字段。但当前分析表没有经过验证的 firm/university/research-institute 类型或产业行业映射，`assignee_type` 不能在本任务中无核验转成这三个标签。因此本报告**没有**按“University”“Institute”等名称片段编造经过验证的样本分类或比例，也没有声称原源完全不含任何类型字段。

以只读源 DuckDB `assignee_raw` 核实，可提供实际 literal name 清单：[owner_literal_name_map.csv](../results/revision_v8_profiles/owner_literal_name_map.csv)。两样本去重并集为 432 keys，其中 420 keys 在完整 release 记录中对应多种 literal spelling；共 4,204 literal names，单 key 最多 133 种。这个审计反映规范化与字面变体，并不自动证明误合并或变更了历史身份。它使用全 release 的名称审计，不能倒称这些所有名称在每个历史 origin 已知。

跨任务：[profile_overlap.json](../results/revision_v8_profiles/profile_overlap.json) 给出共有 53 keys、156 owner—years；battery-only 61、electronics-only 318，owner 并集 432，owner—year 并集 1,277。已有两个任务的核心候选和选中 ID 排除关系仍是另一项准入设计，不能用组织重叠掩盖或取代它。

两任务入样历史组合去重授予集合分别含 388,887 和 835,327 grants，共享 347,879 grants。这是**所有入样历史窗口的组合并集**，包含相同 owner、共同所有权与重叠年份；不是当年候选池或最终选中 ID 的 overlap，也不是独立发明或家庭数。正文无需新增这些历史集合数，只保留真实组织重叠和共同档案限制即可。

### 身份及选择边界的英文补充句

> Organizational identity follows normalized as-published owner names, with complete co-owner sets retained. The keys do not consolidate subsidiaries or changes of corporate ownership. We report patent-portfolio characteristics because the analysis files do not provide a verified firm, university or research-institute typology or industry classification. Eligibility selects patent-active owners with at least three task grants in their preceding five-year portfolios; the sample does not represent all organizations seeking technology intelligence.

来源：[owner identity audit](../results/revision_v8_profiles/profile_owner_identity_audit.json)、既有 [patent README](../datasets/patent_README.md)、`scripts/build_patent_subset.py` 的 actual raw owner normalization。不要称该样本“所有美国企业”或将一般 owner 一律写为 firms。

## 5 AI 披露：评审建议与实际记录

新评审要求更具体的工具、方法、验证和独立专家证据。可落实的改进是说明实际 AI 工作与当前验证范围，不是删去实际用途。

当前 v7 主文真实披露：OpenAI Codex 参与 literature discovery、research design development、programming、computational analysis、historical patent desk assessment 和 manuscript drafting；同时已说明功能证据未获 independent expert validation。补充材料的披露更加具体：现有执行记录识别 Codex interface 和 GPT-6 model family，但未为每次历史交互保存 exact build 或完整 prompt archive。因此不得新造模型版本、历史 prompt 或人类专家审批。

技术材料包含可复核的 sample membership、固定选择规则、逐案例功能/机制/介质/几何/约束、来源定位及下一步问题。新增 16 occurrences 是确定性、未使用后来引用结局抽样；旧 16 result-stratified cases 与 2 purposeful cases 仍单独保留。共 34 occurrences/30 patents，不是随机代表性样本。标题/摘要为主要阅读层次，两案例补读 claims/description。由此可增强 Methods 的 audit trail，但不能把 4 routes 当准确率、模型一致性效度或已验证的工程转移分类。

来源：v7 主稿 `AI assistance`；[v7 supplement](TASM_supplementary_evidence_v7.md) 的 AI record 与功能证据部分；[technical audit](revision_v3_technical_audit.md)；`results/revision_v3/technical_case_matrix.csv` 和相应 sample/protocol records。完整历史提示词缺失仍是事实，不将本轮写的新模板说成当时提示。

### 准确的 Methods 增强说明

> The desk assessment was assisted by OpenAI Codex. It records the disclosed object, mechanism, medium, geometry, constraints and unresolved conditions alongside source locators and the proposed next assessment. Existing outcome-stratified cases, purposeful diagnostic cases and the additional outcome-independent deterministic sample remain separately identified. Titles and abstracts provide the principal reading level, with claims and descriptions examined for two cases. The available records identify the Codex interface and GPT-6 model family but do not retain the exact model build and complete prompt archive for every historical interaction. These case interpretations illustrate a proposed information handoff; they have no independent expert validation and supply no classification accuracy estimate.

### 准确的全稿披露增强说明

> OpenAI Codex assisted literature discovery, research design development, programming, computational analysis, historical patent desk assessment and manuscript drafting and revision. The execution record identifies the Codex interface and GPT-6 model family; exact model-build identifiers and a complete historical prompt archive are not retained. Reported computations were executed on the identified public patent records and checked against recorded outputs; literature and technical statements were checked at the reading levels specified in the supplement. Functional interpretations remain AI-assisted desk assessments without independent expert or organizational validation.

现有出版社政策核验：[revision_v5_literature_policy.md](revision_v5_literature_policy.md)，已读政策页面为 [Author Services AI guidance](https://authorservices.taylorandfrancis.com/editorial-policies/using-ai-in-your-research-and-manuscript-preparations/) 与 [central AI policy](https://taylorandfrancis.com/our-policies/ai-policy/)。该核验记录了 first-draft/argument restrictions 和人类作者责任要求；本次没有重复获取政策或宣称符合投稿政策。真实披露、独立专家效度和政策合规是三个不同问题，增加声明本身不证明后两者。外部提交前由实际署名作者完成真实核验及必要政策处理，不捏造其已经完成的动作；本任务不发送编辑询问或进行投稿。

## 6 本地复现材料：已核与可进一步完成

事实核验：[local_replication_audit.json](../results/revision_v8_profiles/local_replication_audit.json)。

- 本地 `TASM_replication_package_revised_v6.zip` 实存 475,860,521 bytes，含 531 archive entries，530 个 v6 manifest 文件全部在 archive 中；ZIP CRC 检查通过。
- v7 是 v6 包上的本地增量 manifest，34 个列明文件均实际存在且 SHA 匹配。v7 effective analysis 的 16 个 frozen-source dependencies 都在 v6 ZIP 中。没有独立 v7 ZIP。
- 组织画像所需的两份跨领域历史 parquet、原准入情景和 v4 特征已在 v6 ZIP 中。姓名核验另读既有 source DuckDB；它不是 ZIP 的内置依赖。若发布单包，可提供本次派生 literal-name map，明确为已核记录，不把它说成独立机构类型标签。
- 未有本研究公共 repository deposit、repository URL 或 assigned study DOI。原始 PatentsView source DOI **10.5281/zenodo.15058362** 不是本研究复现包 DOI。评审建议“改为 deposited with DOI”仅在真正存档后才可采用。
- 本次只检查本地 inventories、hashes、archive CRC 与依赖覆盖，没有运行一次干净目录下的完整独立 replication；不能把材料齐备或 CRC pass 写成该验证已完成。

可执行的 v8 单包方案：保留 v6 相关核心输入/代码与锁定协议，纳入 v7 增量和当前 v8 画像及后续分析；在包根目录新增一份简洁 replay README，列明源版本/许可、环境、预处理与完整重建依赖、从冻结 scores/pools 进行核心 replay 的命令、目标表/图与检查输出。区分“从 public raw 重建”与“从 retained frozen inputs 重放”：前者需要原始表与大 source DuckDB，后者不要求重新训练或新下载。记录准确依赖和自动数值核验，不把只读姓名映射源数据库作为 replay 所有主结果的必要条件。

不用把 superseded manuscripts、所有旧 ZIP、巨型 DuckDB、包缓存和页面预览都放进单包。所发布文件的许可、源归属和版本须保留，原始文件仅引用原公开源及 acquisition manifests。这是基于实际材料的包整理建议，本子任务未创建或上传 v8 包。

### v8 包完成前可立即使用的数据可用性文本

> The study uses the public PatentsView release through 31 December 2024 (source DOI: 10.5281/zenodo.15058362). Local replication materials retain source inventories and checksums, chronological processing, frozen scores and candidate pools, policy lists, outcome joins, analysis code and technical-evidence records. The supplement specifies the comparisons and their dependencies. The study-specific package has not been deposited in a public repository and has no assigned repository DOI.

若主代理确已完成单包，可把第二句改为 “The accompanying replication package includes …”，列明实际内容，并保留最后一句。不得写 “publicly available”“deposited”“DOI forthcoming” 或 authors-approved，除非相应动作真实完成。本子任务范围不包括外部发布，故不安排上传或发送。

## 7 主代理可采用的最小改动

正文添加组织—年 portfolio 中位数/IQR、两任务 53 keys/156 situations overlap、patent-active selection 与 owner identity 边界；补充放完整分布及 unique-owner last-origin 表。AI 方法增加实际工具/记录/验证层次而不捏造专家。数据可用性区分公开原始源和尚未公共存档的研究包；若整理 v8 单包则仅报告该实际交付。其余篇幅留给贡献、边界与管理决策论证。
