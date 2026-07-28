---
name: yys-decision-tree
description: 从阴阳师斗技数据库(MySQL)生成阵容四五手决策树静态HTML可视化。当用户要求查看阵容决策树、四五手推荐、对局胜率统计、阵容克制分析时使用。适用于以下场景：(1) 分析某套前三手(如神龙平)面对不同对方前三手的应对策略 (2) 统计每手选择的次数和胜率 (3) 生成可点击展开的HTML决策树文件。需要读取MySQL yys库。
---

# 斗技阵容决策树 HTML 生成

## 前置条件

- MySQL路径: `C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`
- 临时文件目录: `D:\GitStore\yys\.tmp\`
- D:\GitStore\yys\session-context.md 阅读获取当前规则（ban位、简称等）、数据库信息等

## 输出规范

生成**单文件自包含HTML**，存放到 `.tmp\` 目录，双击即可浏览器打开。

### HTML结构

- 卡片式布局，按**对方前三手组合**分组（顺序无关，式神ID排序后拼接作为分组key）
- 每张卡片标题=对方前三手简称 + 对局总数
- 内层嵌套4层：对方前三手 → 我方第四手 → 对方第四手 → 我方第五手
- 每行显示：简称、胜率、次数，胜率最高行黄色高亮
- 点击展开/收起（CSS `display:block/none` + JS `classList.toggle`）
- 最内层（我方第五手）加横向条形图
- 式神名称统一使用 `shi_shen_lu.aliases` 的第一个简称

### 文件名

`{对战双方简称}_决策树.html`，如 `神龙平vs阎面花_决策树.html`

## 数据查询流程

### Step 1: 确定查询条件

- 我方前三手固定阵容（式神ID列表）
- 对方前三手条件（若不指定，按对方前三手所有组合分组统计）
- win rate统计：默认按胜局/总局，可指定仅胜局
- ban位排除：若有，需排除对方含该式神的对局
- dt范围：默认 `dt >= '2026-07-06'`

### Step 2: SQL聚合查询

核心思路：分别统计【我方第四手】→【对方第四手】→【我方第五手】三层数据。

查询模式：

```sql
-- 1. 先找出符合条件的所有对局（CTE）
WITH base AS (
    SELECT DISTINCT rbd.id, rbd.battle_time, rbd.battle_result,
           rbd.battle_shi_shen_id1~5, rbd.d_battle_shi_shen_id1~5
    FROM ranking_battle_detail rbd
    JOIN ranking r ON rbd.id = r.id
    WHERE r.dt >= '{dt}'
      AND {我方前三手条件}
      AND {对方前三手条件}
      AND {ban位排除}
)

-- 2. 统计我方第四手（对方前三手分组下）
-- 对每个对方前三手组合（ID排序后拼接），统计我方第四手各选项的次数和胜率

-- 3. 对于每个我方第四手选项，统计对方第四手各选项

-- 4. 对于每个对方第四手选项，统计我方第五手各选项
```

### Step 3: 生成HTML

从查询结果构建嵌套数据结构，按以下模板渲染HTML：

```
对方前三手组合A(总局数)
├── 我方第四手X(次数,胜率) [点击展开]
│   ├── 对方第四手M(次数,胜率) [点击展开]
│   │   ├── 我方第五手a(次数,胜率,进度条)
│   │   ├── 我方第五手b(次数,胜率,进度条)
│   ├── 对方第四手N(次数,胜率) [点击展开]
│   │   ├── 我方第五手c(次数,胜率,进度条)
├── 我方第四手Y(次数,胜率) [点击展开]
│   ├── ...
对方前三手组合B(总局数)
├── ...
```

### Step 4: 关键SQL技巧

- 前三手顺序无关处理：`LEAST/GREATEST` 或 CTE中手动拼接排序后的ID
- 对方前三手分组key：对3个ID排序后拼接成字符串（如 `"255_372_584"`）
- 使用 `COUNT(DISTINCT rbd.id, rbd.battle_time)` 去重（同一id+battle_time可能多条）
- 计算占比/胜率时，分母用该分组的总对局数
- 性能：1.3M行表，WHERE条件用索引覆盖（dt索引、battle_shi_shen_id1~3有索引）

## 注意事项

- 读取 session-context.md 中`式神简称规范`和`阵容查询要点`获取当前对话规则
- 式神ID到简称的映射：`SELECT id, name, aliases FROM shi_shen_lu`
- 御魂ID到名称的映射：`SELECT id, name FROM yu_hun`


## 数据展示最佳实践（经验总结）

### 智能过滤规则（2026-07-14迭代）

数据量大时若低频选项过多会干扰分析，采用**百分比+豁免+最低保障**三级过滤：

例如：我方A B C前三手，对阵对方a b c前三手，该对局累计出现12000局，假如我方四手出现过H I J K L M N这几个式神，那么这几个式神的出现次数就要大于全局对该组合总场次 × 1%，也就是120局，低于120局的就不展示了。点开我方的第四手，假如点开的是H式神（假如H式神出现过1500局），出现的是对方的四手选择，假如对方出现过h i j k l m n这个几个式神，那么对方式神的出现场次低于我方第4手总场次 × 3%，也就是45局，对方四手低于45局的就不展示了。我方第五手同理。

最低场次为，无论我方四五手还是对方四手，只要出现次数低于20场，都不展示。

豁免条件为，无论我方第四手还是第五手，如果该式神的出现场次超过20场，并且胜率超过67%，则不受公式场次限制，可以展示出来。

剔除条件为，无论我方第四手还是第五手，如果该式神的胜率低于40%，直接不展示，无关场次。

最低保障为，无论我方四五手还是对方四手，经上述条件筛选后，若可选式神不足5种，则采取胜率>=40%场次最多的5种。

#### 核心参数

| 层级 | 公式 | 最低场次 | 豁免条件 | 剔除条件 |
|---|---|---|---|---|
| 我方第4手 | ≥ 全局对该组合总场次 × 1% | 20 | 胜率≥67% | 胜率<40% |
| 对方第4手 | ≥ 我方第4手总场次 × 3% | 20 | 胜率≥67% | 胜率<40% |
| 我方第5手 | ≥ 对方第4手总场次 × 5% | 20 | 胜率≥67% | 胜率<40% |

#### 处理流程（伪代码）

`
function shouldShow(total, baseTotal, thresholdPct, winRate):
    minCount = max(floor(baseTotal × thresholdPct / 100), 20)
    if total < 20: return false              // 最低20场硬门槛
    if winRate >= 67: return true            // 胜率豁免（小样本高胜率也展示）
    if winRate < 40: return false            // 低胜率直接剔除
    return total >= minCount                 // 正常百分比判断
`

#### 最低保障：不足5种补到5种

某层级（四选/四对/五选）经上述过滤后，若可选种类不足5种，**从剩余选项中取次数最多的补至5种**：

`
function minimum5Options(allOptions, filteredOptions):
    if filteredOptions.length >= 5: return filteredOptions
    result = copy(filteredOptions)
    remaining = allOptions sorted by total desc, excluding already in filtered
    for each option in remaining:
        if result.length >= 5: break
        if winRate >= 40%: result.push(option)  // 补入规则：仅需胜率≥40%
    return result
`

补入条件宽松（只需胜率≥40%），不设最低场次，确保每个展开项至少能看到5种对位选择。

### 点击展开/收起 (toggle) 实现要点

`javascript
// ✅ 正确：用 classList.contains 判断，再点击可收起
function tog(el) {
    var d = el.nextElementSibling;
    if (d && d.classList.contains('p5d')) {
        d.classList.toggle('open');
        var a = el.querySelector('.arr');
        if (a) a.textContent = d.classList.contains('open') ? '▼' : '▶';
    }
}

// ❌ 错误：用 className === 判断，展开后 className 变成 'p5d open'，无法再收起
`

### 布局变体

根据数据量大小选择布局：

- **条形图布局**（数据多时推荐）：每行用 <div> 包裹，含式神名 + 横向进度条 + 胜率 + 次数。适合数据较多的场景。
- **标签芯片布局**（数据少时推荐）：用 <span class="p5chip"> 包裹，flex-wrap 换行排列。适合每个组只有5-10种选择时，更紧凑。

阈值需随数据总量调整：
- 对方前三手只有1种组合（如固定面花阎）：四选≥20即可
- 对方前三手有几十种组合：四选阈值可能需要50-100才能控制卡片数量

## 踩坑记录（2026-07-15）

### 1. 胜率计算：必须转为百分比
- ❌ 错误：`Math.round(win/total * 10) / 10` → 得到的是小数（如 0.5），不是百分比
- ✅ 正确：`Math.round(win/total * 1000) / 10` → 得到百分比（如 54.5）
- 原因：`win/total` 是 0~1 的小数，要转成 0~100 的百分数必须乘以 100，再加一位小数精度需乘以 1000

### 2. 条形图宽度：应使用胜率值，而非次数占比
- ❌ 错误：条形图宽度 = `Math.round(m5.total / maxTotal * 100)`（次数占比）
- ✅ 正确：条形图宽度 = `Math.round(m5.wr)`（直接取胜率值）
- 预期：高胜率=满条，低胜率=短条，直观反映"这个选项好不好"

### 3. HTML结构：复用已有风格，不要自创
- ❌ 错误：自行设计 CSS 类名和布局（如 `.option-row`, `.bar-wrap`, `.sub-level`），与用户已有文件不一致
- ✅ 正确：参考用户已有 `神龙平_全数据Top24_决策树.html`，复用其 CSS 类名体系：
  - 卡片：`.card` / `.ch` / `.on` / `.ot`
  - 我方4手：`.p4l` / `.p4row` / `.p4n` / `.p4wr` / `.p4ct` / `.arr`
  - 子层：`.p5d` / `.op4h` / `.op4s`
  - 我方5手：`.p5row` / `.p5n` / `.p5bar` / `.p5wr` / `.p5ct`
  - 高亮：`.hl`（黄色背景）
  - 筛选：`.chip` / `.on` / `.ct`
- 展开/收起函数名：`tog(el)`，用 `className.indexOf("p5d")>=0` 判断（注意不是 `classList.contains`）
- 筛选函数名：`tc(el)`（点击芯片），`applyFilter()`（执行筛选）

### 4. 卡片渲染方式
- 预渲染：所有卡片 HTML 在服务端（Node脚本）生成，嵌入到 HTML 文件中，而非页面加载时 JS 动态生成
- 只有筛选逻辑和展开收起的 JS 放在页面末尾的 `<script>` 中

### 5. 式神别名：aliases取最短字符串，而非第一个
- ❌ 错误：`aliases.split(",")[0].strip()` → 取第一个元素，通常是完整名称（如"须佐之男"），不是真别名
- ✅ 正确：`min(aliases.split(","), key=len).strip()` → 取最短的字符串作为展示名
- 原因：`shi_shen_lu.aliases` 字段格式约定为`"全名,简称1,简称2,..."`，首个是正式名，后面的才是别名（如`"须佐之男,须,须佐"`→取`"须"`；`"葛叶,葛"`→取`"葛"`；`"二舅,不相狐"`→取`"二舅"`）
- 例外：若某些式神只填写了全名没有别名，取最短结果仍为全名，可接受

### 6. SP/SSR筛选行：用flex-column + fl-row实现换行
- ❌ 错误：在filter flex容器中用`<br>`分隔SP和SSR → flex布局中`<br>`不产生换行，SSR芯片仍跟在SP后面
- ✅ 正确：filter容器用`flex-direction:column`，SP和SSR各自用`<div class="fl-row">`包裹（`fl-row: display:flex; flex-wrap:wrap`），实现独立行
- 结构示例：
  ```html
  <div class="filter" style="display:flex;flex-direction:column">
    <div class="fl-row"><!-- SP芯片 --></div>
    <div class="fl-row"><!-- SSR芯片 --></div>
  </div>
  ```
  ```css
  .fl-row { display: flex; flex-wrap: wrap; gap: 4px; align-items: center; }
  ```
### 7. 前三手判定：必须限制在位置1~3，而非整个5人阵容
- ❌ 错误：`OUR.issubset(my_set)` → 检查我方5个位置是否包含目标式神，会误把第四、五手的神龙平式神计入
  - 例如：前三手上了神无月+龙珏+须佐，第四手补平将门 → 被错误当作"神龙平"对局
- ✅ 正确：`set(my[:3]) - {0} == OUR` → 只检查前三手是否**恰好等于**目标阵容
- 若我方第四、五手出现前三手阵容的式神（如第四手再上龙珏），虽然极少见但无需理会
- 对方侧同理：对方前三手用 `en[:3]` 排序后作为分组key，与对方四五手无关

## 脚本工具

`scripts/generate_decision_tree.py` 是通用决策树生成脚本，封装了完整流程（SQL查询→数据处理→HTML生成）。

### 使用方式

```bash
python scripts/generate_decision_tree.py \
  --our 596,573,592 \
  --ban 597 \
  --dt-start 2026-07-20 \
  --dt-end 2026-07-26 \
  --min-matches 200 \
  --output "D:\GitStore\yys\.tmp\神龙平_决策树.html" \
  --title "神龙平 决策树"
```

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| `--our` | 是 | 我方前三手式神ID，逗号分隔 |
| `--ban` | 否 | 禁用的式神ID，逗号分隔 |
| `--dt-start` | 是 | 起始日期 |
| `--dt-end` | 是 | 截止日期 |
| `--min-matches` | 否 | 最低展示场次 (默认200) |
| `--output` | 否 | 输出HTML路径 (默认 决策树.html) |
| `--title` | 否 | 页面标题 |

### 脚本内置的智能过滤规则

与本文档"数据展示最佳实践"一致：
- 我方第四手 ≥ 全局对该组合总场次 × 1%（最低20场）
- 对方第四手 ≥ 我方第四手总场次 × 3%（最低20场）
- 我方第五手 ≥ 对方第四手总场次 × 5%（最低20场）
- 胜率 ≥ 67% 豁免场次限制（但最低20场硬门槛）
- 胜率 < 40% 直接剔除
- 不足5种补到5种
﻿## Ban位推测功能

通过数据对比和50高频玩家验证，找出某个阵容的ban位。

### 核心逻辑

**两轮验证策略：**
1. **第一轮（自动捕获）**: 查找跌幅 >= 80% 且 全局出现率 >= 3% 的式神 → 跑50人验证
2. **第二轮（查漏补缺）**: 若第一轮未确认，扩展搜索跌幅 >= 50% 且 全局出现率 >= 5% 的式神 → 追加验证

**判定标准：**

| 条件 | 判定 |
|------|:----:|
| 50人中 >= 80% 从未出现 | BAN位确认 ✅ |
| 50人中 >= 50% 从未出现 | 高度疑似 ⚠️ |
| 跌幅 >= 80% 但验证 < 50% | 非ban位（阵容天然克制） |

### 使用方式

`ash
python scripts/ban_analysis.py \
  --our 596,573,592 \
  --dt-start 2026-07-20 \
  --dt-end 2026-07-26 \
  --name "神龙平" \
  --output "D:\GitStore\yys\.tmp\ban_神龙平.txt"
`

### 参数说明

| 参数 | 必填 | 说明 |
|------|------|------|
| --our | 是 | 我方前三手式神ID,逗号分隔 |
| --dt-start | 是 | 起始日期 YYYY-MM-DD |
| --dt-end | 是 | 截止日期 YYYY-MM-DD |
| --name | 否 | 阵容名称 |
| --output | 否 | 输出文件路径 (默认stdout) |

### 参照案例

参见 
eferences/ban_analysis_cases.md，包含3个已验证案例：
- 神龙平 → 葛叶 (BAN位确认)
- 面因龙珏 → 平将门 (BAN位确认)
- 卑因茶 → 葛叶 (高度疑似)

### 注意

- Top20玩家的ban倾向比Top50更集中，高分段ban位更统一
- 非高频玩家可能ban位不固定，导致50人验证稀释结果
- 输出文件用UTF-8编码，若控制台显示乱码请用 --output 保存到文件后查看
