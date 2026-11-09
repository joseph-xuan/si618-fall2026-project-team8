# M2 文件与运行说明

## 主要文件

- `SI618_M2_Team8.py`：英文 marimo 分析 notebook，按老师要求排列章节。
- `SI618_M2_Team8.html`：已执行的 HTML，阅读和提交时使用。
- `docs/research_questions_m2.md`：地区层面的三个修订问题、字段与共同口径。
- `outputs/m2/`：完整模型、地区表、敏感性分析、检查记录和图表。
- `scripts/prepare_m2_spatial.py`：重现坐标到县映射及 CBSA/人口属性的预处理步骤。
- `docs/m2/milestone-2.md`、`decision-log.md`：保存的老师原始要求。
- `docs/m2/data_manifest.json`：输入数据和地理来源的哈希与口径。

## 当前完成范围

完成数据重新加载、M1 清洗、地区聚合、三个问题的分析与回答，以及 county/CBSA、挂牌门槛、相同车源范围、单州区域和聚类标准误检查。正文数值由运行结果生成。保留了 M1 文件与原始数据，没有上传 Canvas。

County 是主分析；第二套划分把 CBSA 内的县合并，CBSA 外的县仍单独保留。CBSA 包含 metropolitan 和 micropolitan，不能全部称为“大城市”。高校密度是符合 M1 筛选条件的高校数除以陆地面积。人口密度、学生规模、州别是本版控制变量；没有声称已经加入 GDP 或收入。

## 仍需真实资料补充

截至 2026-11-09，完整的 Canvas M1 反馈未提供，11 月 11 日 Studio 会议尚未举行。Notebook 已如实标明；会议后需要记录被问到的决策、团队解释及是否改变做法，并逐条补全真实反馈回应。当前分析稿不能替代这部分经历记录。

## 打开与导出

直接打开 HTML 可阅读已计算结果。若编辑 notebook，在项目根目录运行：

```sh
uvx marimo==0.25.1 edit --sandbox SI618_M2_Team8.py
```

按老师要求重新导出：

```sh
uvx marimo export html --sandbox SI618_M2_Team8.py -o SI618_M2_Team8.html
```

M2 的依赖写在 notebook 文件头，独立于 M1 的 `requirements.txt`。Notebook 优先读项目内的相同原始输入，否则从固定 GitHub commit 下载，并核对 SHA256。已用仅含 `.py` 的新目录完成一次独立环境导出，不依赖本机绝对路径。

地理映射是唯一预先计算的查找表，已嵌入 `.py`；统计模型、图和结论均重新计算。因此通常提交老师指定的 `.py` 和 `.html` 即可，运行仍需要网络或相同原始数据。预处理脚本用于核对嵌入的地理映射，不是运行当前 notebook 的前置要求。

## M1 格式对齐

参照用户提供的 M1 HTML：标题与成员信息置前，章节用横线分隔，图表统一字号和尺寸，每张图后有编号说明，decision log 分为独立记录。品牌构成图展示七个主要品牌，车型构成图展示六个主要类别，其余已知类别只在图中合并；完整模型仍保留全部原有检验。主要分析口径、控制变量和结果未改变。
