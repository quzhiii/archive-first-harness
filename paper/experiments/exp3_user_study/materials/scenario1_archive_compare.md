# Scenario 1: Archive Compare — RAG Agent

> **背景**：一个 RAG agent 被要求回答"What is archive-first-harness?"。同一个任务跑过两次：一次成功，一次失败。以下是两次运行的结构化对比。

---

## Run Overview

```
成功 run:  status=success | verification=passed  | risk=low  | followup=no
失败 run:  status=failed  | verification=failed  | risk=high | followup=yes
```

## Key Transitions (成功 → 失败)

```
failure:       none → verification_failed      ⚠️ REGRESSED
verification:  passed → failed                  ⚠️ REGRESSED
risk:          low → high                       ⚠️ REGRESSED
artifacts:     compatible:2 → breaking:1,warning:1  ⚠️ REGRESSED
```

## Artifact Diff

```
成功 run:  期望=[answer, retrieval_report]  实际产出了 answer + retrieval_report ✅
失败 run:  期望=[answer, retrieval_report]  实际只产出了 answer               ❌ 缺少 retrieval_report
```

## Reason Codes Changed

```
+ grounding_failed              (新增：回答未基于检索到的证据)
+ retrieval_strategy_regressed  (新增：检索策略退化)
- grounding_confirmed           (消失：之前确认过有根据)
```

## Agent Output (失败 run)

```
"This tool is mainly an observability dashboard SaaS."
→ 这个回答是错误的（幻觉），实际不是 SaaS dashboard
→ retrieval_strategy 从精确搜索退化为 broad_noisy (top_k=12)
→ 导致检索了大量无关信息，回答基于噪声而非真实内容
```

## Highlights

> failure regressed; verification regressed; artifacts regressed  
> 评估原因: +artifact_missing, +ungrounded_answer, -grounded_answer, -sufficient_retrieval  
> 产出物: 缺少 retrieval_report

---

### 请回答：

1. **失败发生在哪一步？**
2. **你认为根本原因是什么？**
