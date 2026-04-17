# Scenario 2: Archive Compare — Multi-Step Agent

> **背景**：一个 multi-step agent 被要求执行 3 步任务：调用天气 API → 调用餐厅 API → 生成旅行计划。同一个任务跑过两次：一次成功，一次失败。以下是两次运行的结构化对比。

---

## Run Overview

```
成功 run:  status=success | verification=passed  | risk=low  | followup=no
失败 run:  status=failed  | verification=failed  | risk=high | followup=yes
```

## Key Transitions (成功 → 失败)

```
failure:       none → restaurant_api_timeout   ⚠️ REGRESSED
verification:  passed → failed                  ⚠️ REGRESSED
risk:          low → high                       ⚠️ REGRESSED
artifacts:     compatible:1 → none              ⚠️ REGRESSED
```

## Artifact Diff

```
成功 run:  期望=[plan_note]  实际产出了 plan_note ✅
失败 run:  期望=[plan_note]  实际产出 = 无      ❌ 任务中断，没有输出
```

## Reason Codes Changed

```
+ execution_failed    (新增：执行失败)
+ step2_timeout       (新增：第2步餐厅API超时)
- workflow_complete   (消失：之前工作流正常完成)
```

## Root Cause in One Line

> **Step 2 (餐厅 API 调用) 超时 → 整个 3 步 workflow 中断 → plan_note 未生成**

## Highlights

> failure regressed; verification regressed; artifacts regressed  
> 评估原因: +artifact_missing, +step2_timeout, -all_steps_completed  
> 产出物: plan_note 完全缺失

---

### 请回答：

1. **失败发生在哪一步？**
2. **你认为根本原因是什么？**
