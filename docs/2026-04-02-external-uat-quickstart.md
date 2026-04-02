# 非作者快速验收说明 (v1.2)

日期：2026-04-02
版本：v1.2 (纠偏修复版)

这份文档是给第一次接触这个项目的人用的。我们修复了上一轮测试中出现的 Windows 兼容性与超时问题。

目标：确认你能不能在**不依赖作者口头解释**的情况下，独立把最小诊断流程跑通。

---

## ⚠️ 重要：环境预警
如果你的项目文件夹位于 **百度网盘同步空间、OneDrive 或 iCloud** 等同步盘目录下，由于 Windows 的文件锁定机制，可能会导致运行超时（>120s）。请尽量在**非同步盘**的本地目录下进行测试。

---

## 你需要做什么

请按顺序执行下面 6 步。

### 0. 准备环境 (前置步骤)

请确保你已经安装了必要的依赖。

```bash
pip install -r requirements-v0.1.txt
```

### 0.1 路径自检 (必做)

在运行正式任务前，请先确认你的 `PYTHONPATH` 设置正确且模块可识别。

**Windows PowerShell (推荐):**
```powershell
$env:PYTHONPATH="."; python -m entrypoints.cli inspect-state
```

**Windows CMD:**
```cmd
set PYTHONPATH=. & python -m entrypoints.cli inspect-state
```

**Expected Outcome**: 看到打印出项目结构信息且无报错，即说明路径闭环。

---

### 1. 跑一个“极简验证任务” (Ping)

为了排除网络和逻辑干扰，请先跑一个秒级返回的极简任务。

**Windows PowerShell:**
```powershell
$env:PYTHONPATH="."; python -m entrypoints.cli run --task "ping" --task-type retrieval
```

**Expected Outcome**: 在 10 秒内看到 JSON 响应，且包含 `"status": "success"`。如果这一步超时，请检查你的杀毒软件或磁盘 IO。

---

### 2. 看最新归档 (Archive)

确认任务跑完后，查看刚才生成的归档摘要。

```bash
python -m entrypoints.cli archive --latest
```

---

### 3. 查看归档列表与过滤

尝试查看最近的失败任务或特定类型的任务。

```bash
# 查看最近 10 条失败的任务
python -m entrypoints.cli archive --status failed --limit 10

# 查看最近 10 条检索类任务
python -m entrypoints.cli archive --task-type retrieval --limit 10
```

---

### 4. 进行两次运行对比 (Compare)

你可以选取上面跑出来的 run-id，或者使用下面的基准 ID 进行对比。
注意：**`--compare-run-id` 参数必须重复输入两次**。

**基准 ID（兵部提供）：**
- 成功场景: `20260402T083943Z_search_docs_for_runtime_context_90c557`
- 异常场景: `20260402T065322Z_design_a_runtime_harness_plan_e25af2`

```bash
python -m entrypoints.cli archive --compare-run-id <id_1> --compare-run-id <id_2>
```

---

## 你需要回答的问题

完成后，请将反馈填入 `tests/uat_results/feedback/` 目录下你的反馈表中：

1. 哪一步你最容易卡住？（安装、PYTHONPATH、ping 任务、寻找 id？）
2. 哪个输出你完全看不懂？（指出具体字段名）
3. 你能不能快速判断哪条 run 最值得先看？
4. compare 输出有没有真正帮助你理解差异？
5. 如果让你明天再用一次，你还记得怎么用吗？

---

## 验收标准

- **通过**：不用作者解释，能完成上述 5 步（含 ping），能看懂关键字段。
- **未通过**：需要作者解释字段含义，或在执行 ping 任务时依然因环境问题彻底卡死。
