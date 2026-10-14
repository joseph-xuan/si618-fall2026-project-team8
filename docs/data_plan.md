# 数据处理准备：美国大学生人口构成与周边二手车市场

截至 2026-10-14：已阅读要求和选题文档；尚无原始数据，尚未执行真实清洗或 JOIN。本文中的阈值和研究问题是候选方案，需用真实数据验证。

## 已读取的要求与选题

- [Milestone 1](https://github.com/cteplovs/si618-fa2026-student/blob/main/project/milestone-1.md)：提交 `SI618_M1_<group name>.py` marimo notebook 与 HTML；按顺序设置 Title and group、Overview、Research questions、Data sources、Data description、Data manipulation、Data visualisation、Decision log。
- [Decision log](https://github.com/cteplovs/si618-fa2026-student/blob/main/project/decision-log.md)：三个真实决策，每个包括 Decision、Alternative、Evidence、Consequence；至少一个应实际运行替代方案。不能把准备阶段的建议写成团队已由数据证实的决定。
- [团队选题文档](https://docs.google.com/document/d/1qrp3vaqyO3xrnp4f61uDZTW6XnVTNttTokOGldnPdqE/edit)：最后选题为大学生人口构成与周边二手车市场，采用 UNITID 合并大学数据，再按距离匹配车辆。
- M1 只做加载、清洗、合并、变形、分组、描述与绘图；暂不进行统计检验。
- 合并前后分别计算行列数、每行含义、研究变量类型/单位/缺失率；每一步记录保留行数，以及合并匹配和未匹配数量；至少三张相关图。

## 数据来源核实与下载清单

| 来源 | 候选文件/作用 | 当前状态 |
|---|---|---|
| NCES / IPEDS [完整数据文件](https://nces.ed.gov/ipeds/datacenter/DataFiles.aspx?year=-1) | `HD2021`：UNITID、学校名称、位置、经纬度、学校层级等 | 官方 ZIP 成功读取并确认文件名；尚未保存到本地 |
| 同上 | `EF2021A`：Fall 2021 按学生层级、性别、种族/族裔统计 | 官方 CSV 与字典成功读取，层级和核心变量已核实；尚未保存到本地 |
| 同上 | 如车辆挂牌主要发生于 2021 春季，可考虑 `HD2020` + `EF2020A` | Fall 2020 先于春季挂牌，更适合时间顺序；先核实挂牌日期再确定 |
| Austin Reese / [Used Cars Dataset](https://www.kaggle.com/datasets/austinreese/craigslist-carstrucks-data) | 候选 `vehicles.csv`：id、price、year、odometer、transmission、manufacturer、paint_color、lat、long、posting_date | 已定位发布页，但当前页面未提供可读文件版本/许可证详情；需下载页核实 |

不要将作者早期 GitHub 项目中的约 70 万行文件，与 Kaggle 的某个后续版本视为同一文件。下载后记录实际行数、列名、日期范围和 SHA256。文档还提到另一份 2019–2020 汽车分类广告数据，它是备选来源，不能默认和 2021 文件混合。

下载步骤：

1. 在 Kaggle 页面确认版本、文件列表、大小及许可证，下载 `vehicles.csv` 放入 `data/raw/`。不要直接提交大文件到 Git。保留原文件。
2. 在 IPEDS 完整数据下载页选择对应年份，下载 HD 与 EF A 的 CSV ZIP **以及两份数据字典**，放入 `data/raw/`。优先下载最终修订版并记录 release。
3. 为每个文件填写 `docs/source_manifest.csv`：发布者、网址、下载日期、许可/使用条款、时间范围、版本。没有确认的项保持空白，不补写猜测。
4. 根据 EF 字典选取“全部学生”“本科生”“研究生”的正确汇总行；不要把总计和细分层级相加。按 UNITID 做一对一合并，并记录仅 HD、仅 EF 的学校数。
5. 如果选择 2021 年文件，运行 `python scripts/prepare_ipeds.py --hd data/raw/HD2021.zip --enrollment data/raw/EF2021A.zip`，生成下述标准表及 `outputs/ipeds_audit.csv`。适配器只支持已核实的 2021 文件，ZIP 中优先选择 `ef2021a_rv.csv`；直接输入 CSV 时需保留官方文件名。2020 年方案须先核对其字典再扩展适配器。

已核实的 [EF2021A 字典 ZIP](https://nces.ed.gov/ipeds/datacenter/data/EF2021A_Dict.zip)：`EFALEVEL=1` 表示 All students total，`EFALEVEL=12` 表示 All students, Graduate；`EFTOTLT`、`EFTOTLW`、`EFNRALT` 分别为总人数、女性人数、nonresident alien 人数。对应 `X...` 列是插补/报告标志，应保留。官方 [HD2021 ZIP](https://nces.ed.gov/ipeds/datacenter/data/HD2021.zip) 和 [EF2021A ZIP](https://nces.ed.gov/ipeds/datacenter/data/EF2021A.zip) 均成功读取。此轮核实在内存中完成，不构成已保存的原始数据下载；manifest 的下载日期保持空白。

适配器先保留 50 州与 DC 的机构，**尚未限制为大学**，会保留 HD 中的学校类型列。学校类型筛选需要核对 HD 字典并由团队确定；否则结果对应美国高等教育机构，而非专指四年制大学。毕业生记录缺失保持空值，不自动解释为零。

## 标准大学输入：`data/raw/colleges.csv`

每行一个 IPEDS UNITID。学校坐标是报告机构位置，不必然覆盖其所有分校；使用主报告位置时要在 notebook 写明限制。

| 列 | 类型/单位 | 规则 |
|---|---|---|
| unitid | 标识符字符串 | 唯一，不允许重复 |
| institution_name | 字符串 | 学校名称 |
| latitude / longitude | 数值，度 | 从 HD 获取，检查有效范围，(0,0) 无效 |
| enrollment_year | 整数年份 | 所有人数来自同一年和同一统计口径 |
| total_students | 非负人数 | 全部学生计数，必须大于零 |
| international_students | 非负人数 | 按字典定义使用 nonresident 类别作代理；不等同于所有外国出生学生 |
| female_students | 非负人数 | 使用 IPEDS 的 women 分类；注明原始统计分类限制 |
| graduate_students | 非负人数 | 不将学校未提供的层级、缺报或特殊代码自动填零 |

缺失计数保留缺失，负数/特殊缺失代码转换为空值，计数大于总人数标记缺失并报告。比例使用对应计数 / total_students，不乘 100（单位是 0–1）。保留原始插补/报告状态列用于后续质量检查。当前标准表只要求核心列，种族多样性可在实际字典核实后扩展。

## 候选三个研究问题

1. 国际学生比例与周边手动挡挂牌比例是否存在稳定关系？使用 `international_student_share`、`manual_share`、`n_known_transmission`。画散点图并显示覆盖情况；没有关系时不出现稳定趋势。
2. 女性学生比例不同的大学，周边车辆颜色构成是否不同？使用 `female_student_share`、`color_share_*`、`n_known_color`。比较分组颜色构成；没有关系时各组相近。学生比例分组边界需真实数据支持。
3. 国际学生比例不同的大学，其周边品牌构成在相似价格区间是否不同？需使用中间匹配表的 `manufacturer`、`price` 与大学比例，分价格区间计算构成；总品牌份额是初步描述，不能代替价格分层分析。

若颜色/手动挡覆盖太差，可从原文候选题中换用研究生比例与车龄/车型。最终三题由样本覆盖与团队决定。

## 清洗、空间匹配与输出

运行：`python scripts/prepare_data.py --colleges data/raw/colleges.csv --vehicles data/raw/vehicles.csv`

- 先统计原始列的缺失率；只读取所需车辆字段，避开很大的 description/image 字段。
- 重复 id：合并前先报告；相同核心记录留一条，若同 id 对应不同核心字段则停止，要求检查冲突，不任意保留。
- 地理匹配只删除无 id 或无有效坐标的记录。**不要求颜色、变速箱、价格等全部完整**。合法范围不等于在美国，首次运行还要检查地理分布；国家/学校筛选在标准学校表构建时明确实施。
- 价格为 0、负数视为不可用价格，但车辆可参与颜色/变速箱分析；不默认删除高价。里程负值和年款晚于挂牌年置空，保留数量报告。挂牌年由当地 posting_date 前四位计算，车龄是挂牌年减年款，绝不使用当前 2026 年。
- 用球面距离匹配 5、10、20 英里。10 英里为候选主分析范围，另外两种提供决策证据。
- 一个挂牌可匹配多个学校；中间表每行是 (UNITID, listing_id)，报告一车多校比例。按大学汇总时允许重叠，跨校样本不独立，不能把挂牌重复计为全国市场独立车辆。
- 主表每行一个大学，包含学生比例与市场指标；学校无车辆时数量为 0，比例/中位数为缺失。手动挡比例分母只用明确 automatic/manual；other 单独保留，不猜测成自动挡。颜色和品牌分母仅用对应已知字段，同时输出字段覆盖率。

输出至 `data/processed/`：`colleges_clean.csv`、`vehicles_clean.csv`、`college_vehicle_links.csv`、`college_market_5mi.csv`、`college_market_10mi.csv`、`college_market_20mi.csv`。

输出至 `outputs/`：逐步行数 `audit.csv`、原始缺失率 `missingness.csv`、匹配/重叠与半径比较 `matching_summary.csv`、实际挂牌日期/异常数量/输入哈希 `run_metadata.json`。该脚本准备数据，不是可直接提交的 M1 notebook。

## 真实数据到位后需要完成

2021 核心字段与适配已准备；仍需核实 HD 学校类型字典、检查学校范围和机构位置、对照官方学校记录抽查人数与比例、审查挂牌极端值/重复 VIN/地理聚集、读取数据实际日期选择 IPEDS 年份、检查各州和大学覆盖、按有效样本量评估三题。最后在 marimo 内执行全过程、计算描述表、制作三张图、填写成员信息和有真实证据的 decision log，并检查 HTML 无错误。

本项目分析的是附近市场**挂牌供给**与学校层面人口构成的关系；不代表成交价格、学生购买行为或某类学生的个人偏好。
