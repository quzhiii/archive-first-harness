# Archive 真实 Run 试用清单

日期：2026-04-02

## 这份清单是干什么的

这不是开发清单，而是试用清单。

目标很简单：

用 5 到 10 条真实 run，验证 archive 这条线到底是不是已经能在真实工作里帮上忙。

## 试用目标

这次试用重点验证 4 件事：

1. 能不能快速找到想看的 run
2. 单条 run 的信息够不够看
3. compare 能不能快速指出关键变化
4. artifact 差异是不是有实际帮助

## 试用前提

开始前先确认：

- 已经有一批真实 run archive
- 能正常执行 `python -m entrypoints.cli archive ...`
- 当前代码处于可运行状态

## 建议的样本组成

不要全挑同一种 run。

建议至少覆盖下面这些样本：

- 2 条成功 run
- 2 条失败 run
- 1 条 governance review run
- 1 组“修复前 / 修复后”可对比 run
- 1 组 artifact 明显变化的 run

如果真实 run 足够多，建议做到 8 条左右。

## 推荐试用步骤

### 第一步：先扫最近失败样本

```bash
python -m entrypoints.cli archive --status failed --limit 10
```

要观察：

- 能不能很快找到失败 run
- 输出里 `task_type / formation / failure` 是否足够帮助筛选

### 第二步：点开 2 到 3 条单条 run

```bash
python -m entrypoints.cli archive --run-id <run_id>
```

要观察：

- 单条信息够不够直接
- 有没有还需要再去翻大 JSON 才能知道的关键点

### 第三步：做 2 到 3 组 compare

```bash
python -m entrypoints.cli archive --compare-run-id <left_run_id> --compare-run-id <right_run_id>
```

推荐至少做这三类 compare：

- 成功 vs 失败
- 成功 vs governance review
- 修复前 vs 修复后

要观察：

- `transitions` 是否一眼能看懂
- `highlights` 是否真能帮你省时间
- `reason_code_diff` 是否有解释力
- `artifact_diff` 是否真的补充了判断

### 第四步：按任务类型和 formation 试筛选

```bash
python -m entrypoints.cli archive --task-type review --limit 10
python -m entrypoints.cli archive --formation-id discovery --limit 10
```

要观察：

- 过滤维度够不够用
- 是否还缺一个常用维度

## 每条试用记录怎么记

建议每条 run 或每组 compare，都按下面格式记一行：

- 样本：`<run_id>` 或 `<left_run_id> vs <right_run_id>`
- 场景：成功 / 失败 / governance / 修复前后 / artifact 变化
- 是否容易找到：是 / 否
- 是否容易看懂：是 / 否
- 最有用的一行：`transitions / highlights / reason_code_diff / artifact_diff / 其他`
- 还缺什么：一句话

## 通过标准

如果试用后满足下面 4 条，就可以认为 archive 已经接近 M2：

- 大多数 run 都能在几分钟内找到
- 单条 run 不需要再翻大 JSON 才能看懂基本状态
- compare 基本能直接指出关键变化
- artifact_diff 在至少 1 到 2 个真实场景里确实有帮助

## 不通过的典型信号

如果出现下面这些情况，说明还不能说“稳定可用”：

- 你还是经常要回到 archive 目录看原始文件
- `highlights` 经常说不到重点
- compare 很长，但看完还是不知道差异在哪
- artifact 信息存在，但并没有帮助判断

## 试用结束后要产出什么

这次试用结束后，至少产出这 3 样东西：

1. 一份试用记录表
2. 3 到 5 条最常见诊断模式
3. 2 到 3 条最需要优化的输出问题

## 我建议的执行顺序

最省事的做法是：

1. 先挑 5 条 run
2. 跑 browse / run-id / compare
3. 记问题
4. 再决定下一轮到底修“文案”、还是修“结构”

这样不会一上来把试用做得太重，但足够判断这条线有没有真的进入内部可用阶段。
