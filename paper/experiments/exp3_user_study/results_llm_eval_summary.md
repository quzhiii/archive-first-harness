# Exp3 LLM-as-Evaluator 结果汇总

## 设计说明

- 每个模型对每种材料独立评估（盲评，不知道是 raw_logs 还是 archive_compare）
- 评分维度：stage 正确性（0/1）、cause 正确性（0/1）、置信度（1-5）
- 每个条件重复 3 次，取平均
- 有效模型：deepseek-chat、glm-5.1（共 24 条记录）
- 已排除：glm-4-flash（全部空响应）、glm-4-plus（全部空响应）

## 汇总表（按 scenario × condition × 模型）

| Scenario | Condition | 模型 | Stage 准确率 | Cause 准确率 | 平均置信度 |
|----------|-----------|------|-------------|-------------|-----------|
| scenario1 | raw_logs | deepseek-chat | 100% (3/3) | 100% (3/3) | 5.0 |
| scenario1 | raw_logs | glm-5.1 | 100% (3/3) | 100% (3/3) | 4.0 |
| scenario1 | archive_compare | deepseek-chat | 0% (0/3) | 100% (3/3) | 5.0 |
| scenario1 | archive_compare | glm-5.1 | 0% (0/3) | 100% (3/3) | 4.7 |
| scenario2 | raw_logs | deepseek-chat | 100% (3/3) | 100% (3/3) | 5.0 |
| scenario2 | raw_logs | glm-5.1 | 100% (3/3) | 100% (3/3) | 4.0 |
| scenario2 | archive_compare | deepseek-chat | 100% (3/3) | 100% (3/3) | 5.0 |
| scenario2 | archive_compare | glm-5.1 | 100% (3/3) | 100% (3/3) | 5.0 |

## 跨模型聚合（有效模型合并，每条件 n=6）

| Scenario | Condition | Stage 准确率 | Cause 准确率 | 平均置信度 |
|----------|-----------|-------------|-------------|-----------|
| scenario1 | raw_logs | 100% (6/6) | 100% (6/6) | 4.5 |
| scenario1 | archive_compare | 0% (0/6) | 100% (6/6) | 4.8 |
| scenario2 | raw_logs | 100% (6/6) | 100% (6/6) | 4.5 |
| scenario2 | archive_compare | 100% (6/6) | 100% (6/6) | 5.0 |

## 关键发现

### S1 archive_compare stage 系统性误判

- **现象**：两个模型在 S1 archive_compare 条件下，stage 判断均为 `execution`（正确答案：`verification`），6/6 一致复现
- **原因**：`retrieval_strategy_regressed` 语义上发生在 execution 阶段（检索策略退化是执行行为），但 archive schema 将其归类为 verification 失败（因为验证报告检测到了该退化）
- **论文处理**：作为 schema 语义歧义的 finding 写入 Limitations，不修改材料
- **Cause 不受影响**：所有 6 次均正确识别根本原因（检索策略退化 → 幻觉 + 缺少 retrieval_report）

### S2 全部正确

- 两个模型在 S2 两种条件下 stage + cause 均 100% 准确
- archive_compare 条件置信度（5.0）略高于 raw_logs（4.5），与信息密度结果一致

## 错误记录（已排除模型）

- glm-4-flash：全部 12 次空响应（Expecting value: line 1 column 1 (char 0)）
- glm-4-plus：全部 4 次空响应（同上）

## 论文引用建议

```
To complement the user study materials, we conduct a blind LLM-simulated
evaluation using two frontier models (DeepSeek-Chat and GLM-5.1) as proxy
evaluators. Each model is presented with either the raw log or the archive
compare output for each scenario without being told which condition it is
reading. We measure diagnosis accuracy (stage and root cause) and
self-reported confidence across three independent runs per condition (n=6
per cell after aggregating across models).

Cause attribution accuracy is 100% across all conditions and both models.
Stage accuracy is 100% in three of four conditions. The single exception
is Scenario 1 under the archive_compare condition, where both models
consistently classify the failure stage as execution rather than
verification (0/6). We interpret this as a genuine semantic ambiguity in
the archive schema: retrieval strategy degradation occurs during execution
but is surfaced by the verification report, making the stage boundary
ambiguous for an evaluator reading the archive output. This finding
suggests that stage labels for retrieval-specific failures may benefit
from additional disambiguation in future schema versions.
```
