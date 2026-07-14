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

### 阈值过滤

数据量大时，低频选项会干扰分析，建议按层级设置最低场次阈值：

| 层级 | 建议阈值 | 说明 |
|---|---|---|
| 我方第4手 | ≥20局 (M4_MIN) | 筛选主流选择，去除试验性上卡 |
| 对方第4手 | ≥10局 (E4_MIN) | 对方常见应对 |
| 我方第5手 | ≥5局 (M5_MIN) | 我方具体克制方案 |

低于阈值的项**不单独列出**，而是汇总为一行 其他N种，这样既能保留信息又保持界面干净。

### "其他N种"聚合逻辑

统计所有低于阈值的项，合计总局数和胜率，渲染为灰色一行：

`
其他11种  ██████  54.5%  22局  ← 灰色文字+灰色进度条
`

示例：对方·阎的第五手中，有11种式神每种都只出现了1-4局，合计22局，胜率54.5%。这样用户知道"这里还有11种冷门选择，合计22局"但不干扰主要数据的阅读。

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
- 对方前三手只有1种组合（如固定面花阎）：M4_MIN=20即可
- 对方前三手有几十种组合：M4_MIN可能需要50-100才能控制卡片数量