# Paper: archive-first-harness @ EMNLP 2026 Demo Track

**目标会议**: EMNLP 2026 System Demonstrations Track  
**预计 Deadline**: ~2026年7月4日  
**论文类型**: Demo/Tool Paper（6+1 页）

---

## 目录结构

```
paper/
├── README.md                        # 本文件：整体计划和进度
├── data/
│   ├── agentrx_raw/                 # AgentRx 下载的原始数据（gitignore 大文件）
│   └── case_study_archives/         # Case Study 产生的 archive 数据
├── experiments/
│   ├── exp1_agentrx/                # 实验1：AgentRx 覆盖率映射
│   ├── exp2_case_studies/           # 实验2：真实场景 Case Study
│   │   ├── case_a_coding/           # Case A: Coding agent (Aider)
│   │   ├── case_b_rag/              # Case B: RAG agent (自建)
│   │   └── case_c_multistep/        # Case C: Multi-step tool agent (自建)
│   └── exp3_user_study/             # 实验3：用户测试
└── writing/                         # 论文草稿（LaTeX / Markdown）
```

---

## 实验进度追踪

| 实验 | 状态 | 产出 |
|------|------|------|
| Exp1: AgentRx 数据下载 | ✅ 已完成 | `data/agentrx_raw/` |
| Exp1: Adapter 脚本 | ✅ 已完成 | `experiments/exp1_agentrx/adapter.py` |
| Exp1: 覆盖率映射跑通 | ✅ 已完成（73条轨迹，0 unmapped；tau_retail=29, magentic_one=44） | `experiments/exp1_agentrx/results_real/` |
| Exp2 Case A: Coding agent | ✅ 已完成（真实 Aider 运行 + reduced-scope failure） | `experiments/exp2_case_studies/case_a_coding/` |
| Exp2 Case B: RAG agent | ✅ 已完成 | `experiments/exp2_case_studies/case_b_rag/` |
| Exp2 Case C: Multi-step agent | ✅ 已完成 | `experiments/exp2_case_studies/case_c_multistep/` |
| Exp3: 用户测试材料准备 | ✅ 已完成 | `experiments/exp3_user_study/` |
| Exp3: 用户测试执行 | ⬜ 待开始 | - |
| 论文初稿 | ✅ 已完成（持续迭代中） | `writing/draft.md` |

---

## 关键时间线

| 时间 | 里程碑 |
|------|--------|
| W1-2 (4/14-4/27) | Exp1 完成：AgentRx 73条轨迹映射（tau_retail=29, magentic_one=44）+ 覆盖率表格 |
| W3-5 (4/28-5/18) | Exp2 完成：3个 Case Study 数据收集完毕 |
| W7-8 (5/26-6/8) | Exp3 完成：用户测试数据 |
| W9-10 (6/9-6/22) | 论文初稿完成 |
| W11-12 (6/23-7/4) | 打磨 + 演示视频 + 投稿 |

---

## 论文 Contribution Statement（草稿）

1. **概念贡献**：提出 Agent Evidence Layer 作为 agent 生态第四层
2. **设计贡献**：archive schema（11文件/run，30+维度，6类transition）
3. **工程贡献**：零依赖 CLI 工具，可接入任意 agent runtime
4. **实证贡献**：AgentRx 73条失败覆盖率（tau_retail=29, magentic_one=44）+ 3场景 Case Study + 用户测试

---

## 快速运行实验

```bash
# 安装依赖（实验只需要标准库 + datasets + openai可选）
pip install datasets

# Exp1: 下载 AgentRx 数据并运行覆盖率映射
cd experiments/exp1_agentrx
python download_agentrx.py          # Step1: 下载数据
python adapter.py                   # Step2: 转换格式
python run_mapping.py               # Step3: 跑映射，生成结果表

# Exp2 Case B: RAG agent
cd experiments/exp2_case_studies/case_b_rag
python run_rag_agent.py             # 跑 success + failure 两次
python show_compare.py              # 展示 archive --compare 结果

# Exp2 Case C: Multi-step tool agent
cd experiments/exp2_case_studies/case_c_multistep
python run_multistep_agent.py       # 跑 success + failure 两次
python show_compare.py              # 展示 archive --compare 结果

# Exp2 Case A: Real coding-agent capture pipeline
cd experiments/exp2_case_studies/case_a_coding
python capture_aider_run.py --emit-template success
python capture_aider_run.py --emit-template failure
# 真实跑完 Aider 后，填写 template_success.json / template_failure.json
# 再执行：
python capture_aider_run.py --input template_success.json
python capture_aider_run.py --input template_failure.json
python show_compare.py
```
