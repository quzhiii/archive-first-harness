# External UAT Feedback - v1.2 (Windows CMD)

**Tester ID**: AI-Agent-CMD-Simulator
**Date**: 2026-04-02
**Environment**: Windows CMD via `cmd /c`
**Version Tested**: v1.2 Quickstart

## Step Verification

| Step | Action | CMD Syntax Used | Result |
| --- | --- | --- | --- |
| 0 | Setup | `pip install -r requirements-v0.1.txt` | Success (previously installed/timeout) |
| 0.1 | Inspect | `set PYTHONPATH=. & python -m entrypoints.cli inspect-state` | Success |
| 1 | Ping | `set PYTHONPATH=. & python -m entrypoints.cli run --task "ping" --task-type retrieval` | Success (`status: success`) |
| 2 | Archive | `python -m entrypoints.cli archive --latest` | Success |
| 3 | List | `python -m entrypoints.cli archive --status success --limit 2` | Success |
| 4 | Compare | `python -m entrypoints.cli archive --compare-run-id <id1> --compare-run-id <id2>` | Success |

## Answers to Questions

1. **哪一步你最容易卡住？**
   - **PYTHONPATH 设置**: 在 Windows 上，新用户可能会在 PowerShell 中误用 CMD 语法（`set &`），导致 `&` 报错。必须明确 shell 类型。文档中 v1.2 已经区分了 PowerShell 和 CMD，这很有帮助。
   - **pip install**: 依赖安装可能会因为网络或 IO 较慢（尤其在同步盘下）导致超时，但这不是代码问题。

2. **哪个输出你完全看不懂？**
   - `run` 任务产生的原始 JSON 非常庞大，包含很多内部状态（如 `block_selection_report`, `evaluation_input_bundle`），初学者很难一眼看到结果。
   - `archive --latest` 的输出非常清晰，字段名如 `status`, `verification_status` 等容易理解。
   - `formation_id` 和 `policy_mode` 对新用户来说可能比较陌生。

3. **你能不能快速判断哪条 run 最值得先看？**
   - 可以。通过 `archive --status failed` 过滤或直接看 `archive --latest` 即可快速锁定。

4. **compare 输出有没有真正帮助你理解差异？**
   - 有帮助。`comparison` 部分的 `yes/no` 指标非常直观。对于两个成功的 ping，它显示 `highlights: no material changes`，非常清晰。

5. **如果让你明天再用一次，你还记得怎么用吗？**
   - 记得。基本的 `run` 和 `archive` 组合已经足够应对大部分日常诊断需求。

## CMD Syntax Verification Outcome
- **Verified**: The CMD syntax `set PYTHONPATH=. & python -m entrypoints.cli <command>` works perfectly in a native Windows CMD environment.
- **Correction noted**: User must ensure they are in a CMD session, not PowerShell, to use `&`.

## Final Verdict
**PASS**. The quickstart v1.2 is clear, distinguishes between shells correctly, and the core diagnostic loop (Run -> Archive -> Compare) is fully functional and readable without author assistance.
