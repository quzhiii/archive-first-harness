# Case A: 真实 Coding-Agent 实验（Aider 优先）

这个目录的目标不是伪造一个“真实 case”，而是把**真实 coding-agent 运行结果**采集成 paper 可复用的 archive。

当前提供的是一套**半自动采集工作流**：

1. 你先真实运行一次 coding agent（推荐 Aider）
2. 把关键信息填进 JSON 模板
3. 用 `capture_aider_run.py` 写成 archive
4. 用 `show_compare.py` 生成论文可引用的 compare 输出

---

## Aider 是什么？

**Aider** 是一个基于 LLM 的命令行 coding assistant，主要用来：

- 阅读并修改本地代码仓库
- 根据你的 prompt 改 bug / 写功能 / 重构
- 直接生成 git diff 风格的代码变更

它比 OpenHands 轻很多，更适合这里的论文实验，因为：

- CLI 驱动，实验复现简单
- 更贴近“开发者真实用 agent 修 bug”的情境
- 便于我们只采集关键结果，不依赖复杂平台

### 大概占用

- **Python 包本体**：通常几十 MB 级别
- **不会自带大模型权重**：它通常调用你已有的 API / 模型服务
- **额外空间**：主要是你自己的 repo、日志和 git 历史，不是 Aider 本体

所以它一般**不算特别占空间**，比需要完整沙箱/容器环境的 agent 框架轻得多。

---

## 文件

- `capture_aider_run.py`：把一份真实运行记录 JSON 写成 archive
- `show_compare.py`：对比 success/failure 两次 run
- `template_success.json` / `template_failure.json`：可生成的录入模板
- `AIDER_INTEGRATION_PLAN.md`：原始计划说明

---

## 第一步：生成模板

```bash
cd paper/experiments/exp2_case_studies/case_a_coding

python capture_aider_run.py --emit-template success
python capture_aider_run.py --emit-template failure
```

这会生成：

- `template_success.json`
- `template_failure.json`

---

## 第二步：真实运行后填写模板

你需要把以下信息填进去：

- `task`：你给 coding agent 的真实任务
- `execution_status`：`success` / `error`
- `verification_passed`：真实验证是否通过
- `verification_command`：比如 `pytest tests/test_x.py`
- `changed_files`：实际改了哪些文件
- `produced_artifacts`：通常可记录为 `file_change`
- `warning_codes`：如果失败，可填 `verification_failed`、`wrong_file_changed` 等
- `output_summary` / `error_message`：真实结果摘要

---

## 第三步：写入 archive

```bash
python capture_aider_run.py --input template_success.json
python capture_aider_run.py --input template_failure.json
```

默认会写到：

```text
paper/data/case_study_archives/case_a_coding/
```

## 真实实验记录示例

下面是一个 `template_success.json` 的填写示例：

```json
{
  "task": "Fix the path handling bug in export_summary so Windows-style paths are normalized before comparison.",
  "changed_files": [
    "src/export_summary.py"
  ],
  "verification_passed": true
}
```

---

## 第四步：生成对比结果

```bash
python show_compare.py
```

默认比较：

- `case_a_coding_success`
- `case_a_coding_failure`

也可以自定义：

```bash
python show_compare.py --left my_success_run --right my_failure_run
```

---

## 推荐实验设计

### Success run

- 任务足够小、边界清晰
- 例如：修一个单文件 bug、补一个小测试、修文案/路径错误
- 目标是得到：
  - `status=success`
  - `verification=passed`
  - 至少一个 `file_change` artifact

### Failure run

- 任务略含糊，或依赖更多上下文
- 常见失败方式：
  - 改错文件
  - 没产生有效代码改动
  - 改了但验证没过
- 目标是让 compare 输出里出现：
  - `verification_transition=regressed`
  - `artifact_transition=regressed`
  - 必要时 `evaluation_transition=regressed`

---

## 注意

当前这一步只是把 **Case A 的采集框架补齐**。

只有在你真实跑完两次 coding-agent 任务并导入 archive 之后，Case A 才算真正补完整，届时才能把论文正文从“planned”改成“completed real case study”。
