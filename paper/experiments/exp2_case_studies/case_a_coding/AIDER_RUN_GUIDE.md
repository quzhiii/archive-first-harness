# Aider 安装与实验执行指南

## 一、安装 Aider（PowerShell）

### 方法 1：直接安装到当前 Python 环境
```powershell
python -m pip install -U aider-chat
```

### 方法 2：创建独立虚拟环境（推荐，避免污染）
```powershell
# 1. 创建虚拟环境
python -m venv .venv-aider

# 2. 激活虚拟环境
.\.venv-aider\Scripts\Activate.ps1

# 3. 升级 pip 并安装 aider
python -m pip install -U pip
python -m pip install -U aider-chat

# 4. 验证安装
aider --version
```

### 如果 aider 命令找不到，用完整路径
```powershell
python -m aider --version
```

---

## 二、配置模型 API

### 如果你用 OpenAI
```powershell
$env:OPENAI_API_KEY="你的API Key"
```

### 如果你用 OpenAI 兼容服务
```powershell
$env:OPENAI_API_KEY="你的API Key"
$env:OPENAI_API_BASE="你的Base URL"
```

### 常用模型设置
```powershell
# GPT-4
$env:OPENAI_MODEL="gpt-4"

# 或 GPT-4 Turbo
$env:OPENAI_MODEL="gpt-4-turbo-preview"
```

---

## 三、实验 1：Success Run（高概率成功）

### 1. 准备工作
```powershell
# 切换到仓库根目录
cd "E:\BaiduSyncdisk\koni电脑\创业\科研小工具\my-agent"

# 创建并切换到 success 分支
git checkout -b paper-case-a-success

# 确认当前分支
git branch
```

### 2. 启动 Aider
```powershell
# 激活虚拟环境（如果你用了虚拟环境）
.\.venv-aider\Scripts\Activate.ps1

# 启动 Aider，只打开目标文件
aider paper/experiments/exp2_case_studies/case_a_coding/README.md
```

### 3. 在 Aider 交互界面粘贴以下 Prompt

```text
请更新 paper/experiments/exp2_case_studies/case_a_coding/README.md。

目标：
在 README 中添加一个具体的 JSON 示例，展示真实 Aider 运行后如何填写 template_success.json。

要求：
1. 只编辑这一个 README 文件
2. 在"第三步：写入 archive"之后添加一个小节，标题为"真实实验记录示例"
3. 提供一个简短的、填写完整的 JSON 示例（2-3 个字段即可）
4. 示例内容要真实可信，格式与现有模板一致
5. 不要改动文档的其他部分
6. 不要编辑任何 Python 文件

示例应该包含以下字段的填写示例：
- task（具体的任务描述）
- changed_files（实际改动的文件路径）
- verification_passed（验证是否通过）
```

### 4. Aider 修改后验证
```powershell
# 查看改动
git diff -- paper/experiments/exp2_case_studies/case_a_coding/README.md

# 查看状态
git status
```

### 5. 记录结果（填 template_success.json）
运行完成后，编辑 `paper/experiments/exp2_case_studies/case_a_coding/template_success.json`，填入真实值：

```json
{
  "run_kind": "success",
  "run_id": "case_a_coding_success",
  "created_at": "2026-04-13T14:00:00+00:00",
  "task": "用 Aider 更新 Case A README，添加真实实验记录示例 JSON",
  "execution_status": "success",
  "output_summary": "Aider 成功在 README 中添加了 JSON 示例小节",
  "changed_files": [
    "paper/experiments/exp2_case_studies/case_a_coding/README.md"
  ],
  "verification_passed": true,
  "verification_command": "git diff --stat paper/experiments/exp2_case_studies/case_a_coding/README.md"
}
```

---

## 四、实验 2：Failure-prone Run（容易跑偏）

### 1. 准备工作
```powershell
# 回到 main 分支
git checkout main

# 创建并切换到 failure 分支
git checkout -b paper-case-a-failure

# 确认当前分支
git branch
```

### 2. 启动 Aider
```powershell
# 激活虚拟环境（如果需要）
.\.venv-aider\Scripts\Activate.ps1

# 启动 Aider，打开论文相关文件
aider paper/writing/paper.tex paper/writing/draft.md
```

### 3. 在 Aider 交互界面粘贴以下 Prompt

```text
请更新论文文件以反映 Case A 的最新进展。

目标：
加强 Case A 部分的描述，使其更符合学术发表标准。

文件：
- paper/writing/paper.tex
- paper/writing/draft.md

要求：
1. 改进 Case A 部分的表述
2. 使其更加具体、可验证
3. 参考 Case B 和 Case C 的写作风格
4. 确保 Case A 的描述与当前仓库状态一致

注意：
- Case A 的代码位于 paper/experiments/exp2_case_studies/case_a_coding/
- 已经实现了采集脚本 capture_aider_run.py
- 请根据实际情况完善描述
```

### 4. Aider 修改后验证
```powershell
# 查看改动的所有文件
git diff -- paper/writing/paper.tex paper/writing/draft.md

# 查看状态
git status
```

### 5. 人工检查要点
重点检查 Aider 是否：
- 错误声称 Case A 已完成真实实验
- 改动超出预期范围
- 写出与事实不一致的结论

### 6. 记录结果（填 template_failure.json）
假设 Aider 出现了事实偏差，编辑 `template_failure.json`：

```json
{
  "run_kind": "failure",
  "run_id": "case_a_coding_failure",
  "created_at": "2026-04-13T15:00:00+00:00",
  "task": "用 Aider 更新论文中 Case A 的描述",
  "execution_status": "success",
  "output_summary": "Aider 修改了论文，但错误声称 Case A 已完成真实实验",
  "changed_files": [
    "paper/writing/paper.tex",
    "paper/writing/draft.md"
  ],
  "verification_passed": false,
  "warning_codes": [
    "verification_failed",
    "manual_review_needed"
  ],
  "error_message": "The agent updated the paper text in a way that overstated the completion status of Case A."
}
```

---

## 五、导入 Archive

### 1. 回到仓库根目录
```powershell
cd "E:\BaiduSyncdisk\koni电脑\创业\科研小工具\my-agent"
```

### 2. 写入 success archive
```powershell
python paper/experiments/exp2_case_studies/case_a_coding/capture_aider_run.py --input paper/experiments/exp2_case_studies/case_a_coding/template_success.json
```

### 3. 写入 failure archive
```powershell
python paper/experiments/exp2_case_studies/case_a_coding/capture_aider_run.py --input paper/experiments/exp2_case_studies/case_a_coding/template_failure.json
```

### 4. 生成对比结果
```powershell
python paper/experiments/exp2_case_studies/case_a_coding/show_compare.py
```

---

## 六、完整命令速查表

### 一次性执行（如果你准备好了）
```powershell
# === 安装 ===
python -m pip install -U aider-chat

# === 配置 API ===
$env:OPENAI_API_KEY="你的Key"

# === Success 实验 ===
git checkout -b paper-case-a-success
aider paper/experiments/exp2_case_studies/case_a_coding/README.md
# [粘贴 Success Prompt，等待 Aider 完成]
git diff -- paper/experiments/exp2_case_studies/case_a_coding/README.md
# [填写 template_success.json]

# === Failure 实验 ===
git checkout main
git checkout -b paper-case-a-failure
aider paper/writing/paper.tex paper/writing/draft.md
# [粘贴 Failure Prompt，等待 Aider 完成]
git diff -- paper/writing/paper.tex paper/writing/draft.md
# [填写 template_failure.json]

# === 导入 Archive ===
python paper/experiments/exp2_case_studies/case_a_coding/capture_aider_run.py --input paper/experiments/exp2_case_studies/case_a_coding/template_success.json
python paper/experiments/exp2_case_studies/case_a_coding/capture_aider_run.py --input paper/experiments/exp2_case_studies/case_a_coding/template_failure.json

# === 对比 ===
python paper/experiments/exp2_case_studies/case_a_coding/show_compare.py
```

---

## 七、预期结果

如果一切顺利，你会看到：

1. **两个分支**：`paper-case-a-success` 和 `paper-case-a-failure`
2. **干净的 diff**：分别展示 Aider 的改动
3. **Archive 目录**：`paper/data/case_study_archives/case_a_coding/` 下有：
   - `case_a_coding_success/`
   - `case_a_coding_failure/`
4. **Compare 输出**：显示 success vs failure 的对比

---

## 八、如果遇到问题

### Aider 报错找不到模块
```powershell
# 用完整模块路径
python -m aider 文件路径
```

### 分支切换冲突
```powershell
# 先提交或暂存当前改动
git stash
git checkout main
git checkout -b paper-case-a-failure
```

### API Key 无效
检查环境变量是否正确设置：
```powershell
$env:OPENAI_API_KEY
```

---

## 九、下一步

你跑完这两个实验后，把以下任意一种发给我：

1. `git diff` 输出
2. 实际用了什么 prompt
3. 填完的 `template_success.json` / `template_failure.json`

我就能继续帮你：
- 写入真实 archive
- 生成 compare 输出
- 更新论文正文中 Case A 的状态

**准备好了吗？直接复制上面的命令开始即可。**
