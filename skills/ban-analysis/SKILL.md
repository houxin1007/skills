---
name: ban-analysis
description: 从阴阳师斗技数据库推断某阵容的ban位
---

# Ban位推测

## 前置条件

- MySQL路径: `C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe`
- 临时文件目录: `D:\GitStore\yys\.tmp\`
- 数据库: yys (root/123456)

## 核心逻辑

**两轮验证策略：**
1. **第一轮**: 跌幅 >= 80% 且 全局 >= 3% -> 跑50人验证
2. **第二轮**: 第一轮未确认时, 跌幅 >= 50% 且 全局 >= 5% -> 追加验证

**判定标准：**

| 条件 | 判定 |
|------|:----:|
| 50人中 >= 80% 从未出现 | BAN位确认 |
| 50人中 >= 50% 从未出现 | 高度疑似 |

## 使用方式

```bash
python scripts/ban_analysis.py --our 596,573,592 --dt-start 2026-07-20 --dt-end 2026-07-26 --name 神龙平
```

## 已验证案例

参见 `references/ban_analysis_cases.md`


## 参考文件

| 文件 | 说明 |
|------|------|
| `references/ban_analysis_cases.md` | 已验证的ban位案例（脚本输出） |
| `references/known_ban_picks.md` | 人工维护ban位记录（玩家实战+博主视频观察） |

## 注意事项

- Top20玩家ban倾向比Top50更集中
- 每次执行约20~30秒
