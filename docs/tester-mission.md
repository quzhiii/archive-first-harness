# 测试任务：Agent 诊断实战

## 任务目标

体验 **Evidence Layer** 的核心价值：当 Agent 运行异常时，不靠猜，用证据定位问题。

---

## 背景故事

你是一个 AI Agent 开发者。昨天你写了一个能正常运行的 "研究摘要" Agent，今天它突然超时失败了。你需要找出原因。

---

## 任务步骤（预计 10 分钟）

### Step 1: 环境准备（2 分钟）

```bash
git clone https://github.com/quzhiii/archive-first-harness.git
cd archive-first-harness
python quickstart.py
```

确认看到 ✅ 首次运行完成。

### Step 2: 创建"昨天"的成功运行（2 分钟）

```bash
python -m entrypoints.cli run \
  --task "研究 Rust 编程语言的内存安全机制" \
  --task-type retrieval
```

记录输出的 `run_id`（格式如：`20260412_143022_abc123`），这是你的"昨天成功运行"。

### Step 3: 创建"今天"的失败运行（1 分钟）

```bash
python -m entrypoints.cli run \
  --task "研究 Rust 编程语言的内存安全机制" \
  --task-type retrieval \
  --workflow-profile-id slow_api_simulation
```

> 注：`slow_api_simulation` 会模拟外部 API 响应变慢，导致超时失败。

### Step 4: 对比两次运行，诊断问题（3 分钟）

```bash
# 先查看 summary，确认有两次运行
python -m entrypoints.cli archive --summary

# 用 compare 对比（替换为实际的 run_id）
python -m entrypoints.cli archive \
  --compare-run-id <昨天的成功id> \
  --compare-run-id <今天的失败id>
```

### Step 5: 回答问题（2 分钟）

基于对比输出，回答：

1. **失败发生在哪个阶段？**（routing / execution / verification / governance）
2. **两次运行的输入是否相同？**
3. **执行时间差异是多少？**
4. **你的诊断结论是什么？**（如："外部 API 变慢导致超时"）

---

## 预期对比输出示例

```
Compare: run_20260411_120000_success vs run_20260412_143022_failed
================================================================
状态:         success        →   failed
失败阶段:     -              →   execution
失败类型:     -              →   timeout
验证:         passed         →   failed
任务输入:     相同
执行时间:     2.5s           →   30.2s (超时)
产物:         1 file         →   0 files

transitions:
  failure:      none → execution_failed
  verification: passed → failed
```

---

## 成功标准

✅ 能在 5 分钟内完成两次运行并对比  
✅ 能准确指出失败阶段（execution）和原因（timeout）  
✅ 能得出"外部 API 变慢"的诊断结论

---

## 进阶挑战（可选）

如果你完成了基础任务，试试：

1. **用 `--summary` 查看趋势**：
   ```bash
   python -m entrypoints.cli archive --summary --status failed
   ```

2. **手动修复并验证**：
   - 查看失败运行的 `failure_signature.json`
   - 思考如果是真实场景，你会怎么修复（如增加重试、调大超时）
   - 在反馈中告诉我们你的修复思路

---

## 提交反馈

完成后，请填写 [反馈表单](docs/2026-04-12-external-feedback-checklist.md) 或提交 GitHub Issue，告诉我们：

- 你在哪里卡住了？
- 对比输出是否清晰？
- 这个诊断流程比翻日志快多少？
- 你会在实际项目中使用吗？
