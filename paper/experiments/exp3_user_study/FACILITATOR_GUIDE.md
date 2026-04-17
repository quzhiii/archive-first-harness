# 用户测试：主持人手册

## 概述

- **目的**：验证 archive compare 是否比原始日志更快帮助用户定位 agent failure
- **时长**：每位参与者约 15-20 分钟
- **人数**：2-3 人即可
- **方式**：远程/当面均可，可以屏幕共享也可以直接发文件

## 参与者条件

最低要求：
- 会用命令行
- 写过 Python 代码
- 知道什么是 LLM / AI agent（用过 ChatGPT 即可）

不需要：
- NLP 研究经验
- 读过论文
- 安装任何软件

## 测试流程

### Step 1：开场（1 分钟）

念这段话：

> "今天我会给你两个 agent 失败案例。你的目标是：尽可能快地判断'这次失败的主要原因是什么'。我会用两种不同的方式展示失败信息，每次看完后请你回答两个问题并告诉我你看花了多长时间。"

### Step 2：Scenario 1 — RAG Agent（约 5 分钟）

**先给 Condition A（原始日志）**：

把 `materials/scenario1_raw_logs.md` 发给参与者。

> "这是一个 RAG（检索增强生成）agent 的失败日志。请阅读后回答：
> 1. 失败发生在哪一步？
> 2. 你认为根本原因是什么？
> 请记录你开始阅读到给出答案的时间。"

**再给 Condition B（archive compare）**：

把 `materials/scenario1_archive_compare.md` 发给参与者。

> "这是同一次失败的另一种呈现方式（成功 run vs 失败 run 的结构化对比）。请再次回答同样的问题，看看你能否更快或更准确地定位问题。"

记录两个时间差。

### Step 3：Scenario 2 — Multi-Step Agent（约 5 分钟）

流程同上，材料换成：
- `materials/scenario2_raw_logs.md`
- `materials/scenario2_archive_compare.md`

**注意**：对第二个参与者，先给 Condition B 再给 Condition A（抵消顺序效应）。

### Step 4：反馈问卷（3 分钟）

把 `materials/feedback_form.md` 发给参与者填写。

### Step 5：感谢

> "测试到此结束，非常感谢你的时间！你的反馈会帮助我改进这个工具。"

## 记录

把每位参与者的结果填入 `score_sheet.csv`。

## 反抵消顺序

| 参与者 | Scenario 1 | Scenario 2 |
|--------|------------|------------|
| P1 | A → B | A → B |
| P2 | B → A | B → A |
| P3 | A → B | B → A |
