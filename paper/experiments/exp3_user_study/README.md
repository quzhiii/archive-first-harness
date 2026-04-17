# User Study (Exp3)

## 目标

验证 archive compare 是否比原始日志更快帮助用户定位 agent failure。

## 最小样本

- 2-3 位参与者
- 条件：会用命令行、写过 Python、知道什么是 LLM

## 测试流程（每位参与者约 15 分钟）

1. **开场**（1 min）— 见 `FACILITATOR_GUIDE.md`
2. **Scenario 1**（5 min）— RAG agent，分别用 raw logs 和 archive compare
3. **Scenario 2**（5 min）— Multi-step agent，同上
4. **反馈问卷**（3 min）

## LLM 评测脚本

`exp3_llm_eval.py` 支持以下环境变量：

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `DEEPSEEK_API_KEY`

示例：

```powershell
$env:DEEPSEEK_API_KEY="your-key"
python exp3_llm_eval.py --model deepseek-chat
```

如果只想先检查 prompt / 流程：

```powershell
python exp3_llm_eval.py --model deepseek-chat --dry-run
```

## 文件说明

```
exp3_user_study/
├── FACILITATOR_GUIDE.md        ← 主持人手册（完整流程 + 开场白）
├── score_sheet.csv              ← 记录表（时间 + 正确性 + 评分）
├── participant_script.md        ← 旧版主持词（可忽略）
├── post_study_form.md           ← 旧版问卷（可忽略）
├── materials/                   ← 参与者阅读材料
│   ├── scenario1_raw_logs.md         ← S1: RAG 原始日志
│   ├── scenario1_archive_compare.md  ← S1: RAG archive 对比
│   ├── scenario2_raw_logs.md         ← S2: Multi-step 原始日志
│   ├── scenario2_archive_compare.md  ← S2: Multi-step archive 对比
│   └── feedback_form.md              ← 反馈问卷
```

## 主持要点

- **反抵消顺序**：P1 先看 A→B，P2 先看 B→A，P3 混合
- **每次记录**：开始时间、结束时间、参与者回答
- **不要提示**：让参与者自己读材料，不解释字段含义

## 正确答案（供主持人参考，不要给参与者看）

### Scenario 1 (RAG Agent)
- 失败阶段：**verification**（验证阶段）
- 根本原因：**检索策略退化**（retrieval_strategy 从精确退化为 broad_noisy），导致检索了过多无关内容，回答产生幻觉（称工具是 "SaaS dashboard"，实际不是），且缺少 retrieval_report

### Scenario 2 (Multi-Step Agent)
- 失败阶段：**execution**（执行阶段）
- 根本原因：**第 2 步餐厅 API 调用失败**（tool_unavailable，实为超时），导致 3 步 workflow 中断，plan_note 未生成
- 推断路径：failure_signature 不直接暴露根因（stage=unknown, type=tool_call_error），需综合 execution trace（step=2 启动后 28 秒无响应）+ verification warnings（tool_unavailable + partial_output）+ reassessment（execution_failed）才能定位
