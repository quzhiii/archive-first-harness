# 招募文案模板集

## 文案 1：技术社区/Reddit（强调定位差异）

---

**标题**：我开源了一个 AI Agent 的「Evidence Layer」——不是 Observability，而是专门解决"昨天还能跑，今天怎么了"

**正文**：

做 AI Agent 的朋友应该都遇到过：Agent 昨天运行正常，今天突然失败，只能翻日志、猜原因、碰运气调参数。

现有工具的问题是：
- **Framework**（LangGraph/CrewAI）：只负责编排，不管诊断
- **Observability**（LangSmith/Braintrust）：云端 Trace，对比的是分数，不是执行阶段
- **Harness**（OpenHands）：运行时环境，不帮你定位失败根因

**Agent 生态缺了第四层：Evidence Layer（运行证据层）。**

于是我做了 archive-first-harness：
✅ **本地零依赖** — 纯 Python 标准库，数据存在本地文件
✅ **四层失败定位** — routing / execution / verification / governance
✅ **30+ 维度对比** — 两次运行的结构化差异，不是日志 grep
✅ **Governance 追踪** — 验证后风险再评估，override 记录

**一个命令看到问题**：
```bash
python -m entrypoints.cli archive --compare-run-id <昨天> --compare-run-id <今天>
```

输出直接告诉你：失败阶段、输入是否相同、执行时间差异、transition 类型。

🔗 GitHub: https://github.com/quzhiii/archive-first-harness

**现在招募测试者**：如果你也在为 Agent 调试头疼，试试这个 30 秒上手的任务 👇

---

## 文案 2：开发者社群/Discord（强调实用价值）

---

**标题**：Agent 调试神器 —— 用证据定位问题，不靠猜

**正文**：

 archive-first-harness：让你的 Agent 每次运行都有据可查

**痛点场景**：
- Agent 昨天能跑，今天挂了 → 不知道哪里变了
- 日志说"成功"，但产物没生成 → 成功了个寂寞
- 调参数靠碰运气 → 改了 A，B 又坏了

**解决方案**：
每次 `run` 自动归档结构化证据（manifest/verification/failure/trace），然后：
- `archive --latest` —— 查看最新运行摘要
- `archive --compare` —— 对比两次运行，精确定位差异
- `archive --summary` —— 统计趋势，发现规律

**代码示例**：
```python
# 运行任务
python -m entrypoints.cli run --task "研究 X" --task-type retrieval

# 昨天 vs 今天，看到底哪里变了
python -m entrypoints.cli archive \
  --compare-run-id 20260411_success \
  --compare-run-id 20260412_failed
```

输出示例：
```
状态: success → failed
失败阶段: execution
执行时间: 2s → 30s (超时)
输入: 相同
结论: 外部 API 变慢，需增加重试
```

**现在测试招募中**：10 分钟体验任务，完成送 Star ⭐
https://github.com/quzhiii/archive-first-harness/blob/main/docs/tester-mission.md

---

## 文案 3：Twitter/X（短平快）

---

Agent 昨天能跑，今天挂了，只能翻日志猜原因？

我做了个「Evidence Layer」：每次运行自动归档，一键对比两次运行，精确看到哪里变了。

✅ 本地零依赖
✅ 四层失败定位
✅ 30+ 维度对比

30 秒上手：
```bash
git clone https://github.com/quzhiii/archive-first-harness.git
python quickstart.py
```

招募测试者，10 分钟任务 👇
https://github.com/quzhiii/archive-first-harness

#AIAgent #LLM #OpenSource

---

## 文案 4：技术博客/Hacker News（深度长文预告）

---

**标题**：为什么 Agent Observability 不够？我们需要 Evidence Layer

**大纲**：
1. 当前 Agent 生态的三层格局（Framework/Harness/Observability）
2. "昨天还能跑" 问题的本质：缺了第四层（Evidence Layer）
3. Observability vs Evidence Layer 的根本区别
   - Observability：看 trace，比分数
   - Evidence Layer：看阶段，比差异
4. 我开源的 archive-first-harness 实践
5. 真实案例：如何用 3 分钟定位超时问题
6. 招募测试者

**CTA**：
如果你也遇到 Agent 调试难题，欢迎试用并反馈：
https://github.com/quzhiii/archive-first-harness

---

## 使用建议

| 平台 | 推荐文案 | 调整建议 |
|------|---------|----------|
| Reddit r/LocalLLaMA | 文案 1 | 强调与 Observability 的差异 |
| Discord/微信群 | 文案 2 | 贴代码示例，降低门槛 |
| Twitter/X | 文案 3 | 加标签，配截图 |
| Hacker News | 文案 4 | 写成长文，技术深度 |

---

## 关键信息核对清单

发布前确认包含：

- [ ] Evidence Layer 定位（第四层）
- [ ] 核心差异化（本地零依赖、四层定位、30+ 维度对比）
- [ ] 30 秒上手命令
- [ ] 对比输出示例（显示价值）
- [ ] 测试者招募链接
- [ ] GitHub 仓库链接
