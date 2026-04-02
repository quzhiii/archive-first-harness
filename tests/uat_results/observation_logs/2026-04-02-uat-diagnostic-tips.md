# UAT 诊断建议与极简任务说明 - 2026-04-02

针对第二阶段 UAT 出现的超时与语法错误，工部提供以下诊断建议与修复指令。

## 1. 超时 (>120s) 原因分析与对策
**现象**: `run` 命令长时间无返回。
**诊断**:
-   **I/O 挂死**: 核心逻辑在内存中运行时间 < 0.3s。超时极大概率发生在文件写入阶段。
-   **风险点**: 若项目位于 **百度网盘同步空间、OneDrive、iCloud** 等同步盘目录下，Windows 的文件锁定机制可能导致 10+ 个 JSON 文件的并发写入操作出现阻塞。
-   **建议**: 确保项目位于本地非同步目录（如 `C:\temp\my-agent`）。
-   **诊断脚本**: 请测试者运行 `python tests/uat_results/observation_logs/uat_diagnostic.py` 查看环境 I/O 速度。

## 2. 语法错误 ("命令语法不正确") 修复
**现象**: CMD 下报错 `命令语法不正确`。
**原因**:
-   `PYTHONPATH` 设置语法不规范（如 `set PYTHONPATH=. & python ...` 缺少空格）。
-   PowerShell 对 `"` 和模块路径的处理与 CMD 冲突。
-   **推荐指令**:
    -   **CMD**: `set PYTHONPATH=. && python -m entrypoints.cli run --task "ping"`
    -   **PowerShell**: `$env:PYTHONPATH="."; python -m entrypoints.cli run --task "ping"`
    -   **Bash/Git Bash**: `PYTHONPATH=. python3 -m entrypoints.cli run --task "ping"`

## 3. 极简验证任务 (Minimal Task)
为了快速跑通链路，建议先执行以下 10 秒内必返回的任务：

### 第 1 步：环境自检
```bash
python tests/uat_results/observation_logs/uat_diagnostic.py
```

### 第 2 步：极简 Run (Ping 模式)
```bash
# PowerShell
$env:PYTHONPATH="."; python -m entrypoints.cli run --task "ping"
```

### 第 3 步：快速查看状态 (无需 Orchestrator)
```bash
python -m entrypoints.cli inspect-state
```

## 4. 后续方案
-   **工部**：已完成 `uat_diagnostic.py` 诊断工具。
-   **兵部**：请参考上述指令集更新 `Quickstart` 文档。
-   **吏部**：建议指导测试者优先进行 `inspect-state` 验证，确认安装成功后再跑 `run`。

---
**工部**
2026-04-02
