# Case A: Aider Coding Agent Integration Plan

## 目标

使用真实 coding agent（优先 Aider）生成一对 success/failure archives，作为论文里的“真实框架”案例。

## 为什么选 Aider

- 环境比 OpenHands 更轻
- CLI 驱动，容易手工复现实验
- 更贴近“开发者实际使用 agent 修 bug”的场景

## 最小实验设计

### Success run
- 任务：修一个很小的、确定能通过的 bug
- 预期：Aider 成功修改 1-2 个文件，并给出可验证输出
- archive 期待：
  - `status=success`
  - `verification=passed`
  - `produced_artifacts=file_change`

### Failure run
- 任务：给一个更含糊或依赖外部上下文的修改请求
- 可能失败方式：
  - 修改错误文件
  - 未生成预期改动
  - 测试/验证失败
- archive 期待：
  - `failure_transition=regressed` 或 `changed`
  - `verification_transition=regressed`

## 接入方式

1. 运行 Aider 完成任务
2. 手工整理一份最小 `run_result`：
   - `execution_result.status`
   - `execution_result.artifacts`（至少记录 file_change）
   - `verification_report`
   - `realm_evaluation`
   - `residual_followup`
3. 调用项目现有 `write_run_archive()` 写入 paper 专用 archive 目录

## 待补脚本

- `capture_aider_run.py`: 把手工记录/JSON 输入转成 archive
- `show_compare.py`: 调用 `compare_run_archives()` 生成论文截图文本

## 现在先不自动化的原因

- 当前重点是先把论文实验框架搭起来
- Aider 接入涉及真实交互流程，后续单独做更稳
