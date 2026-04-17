# Exp3 信息密度分析结果

## 汇总表

| 材料 | 总字符数 | 关键诊断字符数 | 信息密度 | 推断路径长度 |
|------|----------|----------------|----------|--------------|
| scenario1\_raw\_logs | 1219 | 221 | 18.1% | 3 步 |
| scenario1\_archive\_compare | 1376 | 540 | 39.2% | 2 步 |
| scenario2\_raw\_logs | 1365 | 485 | 35.5% | 4 步 |
| scenario2\_archive\_compare | 1147 | 534 | 46.6% | 2 步 |

## 对比摘要（按 Scenario）

### RAG Agent

- 信息密度：Raw 18.1% → Archive 39.2% （+116%）
- 推断路径：Raw 3 步 → Archive 2 步 （减少 1 步）
- Raw 路径说明：需从 metadata.retrieval_strategy → verification warnings → reassessment reason_codes 综合推断
- Archive 路径说明：Key Transitions 直接标注 verification regressed，Reason Codes 给出 retrieval_strategy_regressed

### Multi-Step Agent

- 信息密度：Raw 35.5% → Archive 46.6% （+31%）
- 推断路径：Raw 4 步 → Archive 2 步 （减少 2 步）
- Raw 路径说明：需从时间戳推断 step2 卡住，failure_signature 不暴露具体步骤，需综合4个块
- Archive 路径说明：Key Transitions 直接给出 restaurant_api_timeout，Root Cause in One Line 直接说明

## 方法说明

**信息密度** = 关键诊断字符数 / 总字符数

关键诊断字符定义为：能直接回答「失败发生在哪一步」和「根本原因是什么」
的最小文本片段，通过正则匹配提取。

**推断路径长度** = 开发者需要跨越的独立信息块数量，
才能从材料中综合得出完整诊断结论。

> 注：信息密度高不等于材料更短，而是意味着有效信息占比更高、噪声更少。
> 推断路径短意味着开发者需要在更少的位置之间跳转才能得出结论。