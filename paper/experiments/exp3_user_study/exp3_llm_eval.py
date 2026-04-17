"""
Exp3 方案C：LLM-as-Evaluator

用多个 LLM 模型模拟"有 3 年经验的 Python 开发者"，
对 raw_logs 和 archive_compare 材料进行盲评诊断。

设计原则：
- 盲评：每次只给一种材料，不告诉模型这是哪种格式
- 多模型：OpenAI GPT-4o + Anthropic Claude-3.5-Sonnet（可扩展）
- 重复采样：每个条件跑 3 次，取多数答案
- 评分维度：stage 正确性 + cause 正确性 + 置信度 + 关键字段

用法：
    # 需要设置环境变量（至少一个）：
    # OPENAI_API_KEY=sk-...
    # ANTHROPIC_API_KEY=sk-ant-...
    # DEEPSEEK_API_KEY=sk-...

    python exp3_llm_eval.py                    # 跑全部
    python exp3_llm_eval.py --dry-run          # 只打印 prompt，不调用 API
    python exp3_llm_eval.py --model gpt-4o     # 只跑指定模型
    python exp3_llm_eval.py --runs 1           # 每个条件只跑 1 次（省钱调试）
"""

from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path
from typing import Any, cast

MATERIALS_DIR = Path(__file__).parent / "materials"
RESULTS_DIR = Path(__file__).parent
RESULTS_FILE = RESULTS_DIR / "results_llm_eval.json"
SUMMARY_FILE = RESULTS_DIR / "results_llm_eval_summary.md"

# ---------------------------------------------------------------------------
# 正确答案（供评分用）
# ---------------------------------------------------------------------------

GROUND_TRUTH = {
    "scenario1": {
        "stage": "verification",
        "cause_keywords": [
            "retrieval",
            "strategy",
            "broad_noisy",
            "hallucin",
            "grounding",
            "检索",
            "退化",
            "幻觉",
        ],
    },
    "scenario2": {
        "stage": "execution",
        "cause_keywords": [
            "step2",
            "restaurant",
            "api",
            "timeout",
            "tool",
            "unavailable",
            "超时",
            "餐厅",
            "第2步",
            "第二步",
        ],
    },
}

# ---------------------------------------------------------------------------
# Prompt 模板
# ---------------------------------------------------------------------------

SYSTEM_PROMPT = """You are a Python developer with 3 years of experience debugging AI agent failures.
You will be shown failure information from an AI agent run.
Your job is to diagnose the failure as quickly and accurately as possible.
Respond ONLY with a JSON object, no explanation outside the JSON."""

USER_PROMPT_TEMPLATE = """Here is the failure information:

---
{material}
---

Answer these questions:
1. At which stage did the failure occur? Choose ONE from: routing, execution, verification, governance
2. What is the root cause in one sentence?
3. How confident are you? (1=pure guess, 5=very certain)
4. Which field or section was most helpful for your diagnosis?

Respond with ONLY this JSON (no markdown, no explanation):
{{"stage": "...", "cause": "...", "confidence": 1-5, "key_field": "..."}}"""

# ---------------------------------------------------------------------------
# 材料加载
# ---------------------------------------------------------------------------


def load_material(name: str) -> str:
    path = MATERIALS_DIR / f"{name}.md"
    text = path.read_text(encoding="utf-8")
    # 去掉"请回答"部分，避免泄露任务提示
    if "### 请回答" in text:
        text = text[: text.index("### 请回答")]
    # 去掉背景说明里的中文提示（保留英文内容）
    return text.strip()


# ---------------------------------------------------------------------------
# 模型调用
# ---------------------------------------------------------------------------


def call_openai(model: str, material: str, dry_run: bool = False) -> dict:
    prompt = USER_PROMPT_TEMPLATE.format(material=material)
    if dry_run:
        print(f"\n[DRY RUN] OpenAI {model}\n{prompt[:300]}...\n")
        return {
            "stage": "DRY_RUN",
            "cause": "DRY_RUN",
            "confidence": 0,
            "key_field": "DRY_RUN",
        }

    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        raise ImportError("pip install openai")

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=256,
    )
    raw = _extract_json(_extract_text(response.choices[0].message.content))
    return json.loads(raw)


def call_deepseek(model: str, material: str, dry_run: bool = False) -> dict:
    prompt = USER_PROMPT_TEMPLATE.format(material=material)
    if dry_run:
        print(f"\n[DRY RUN] DeepSeek {model}\n{prompt[:300]}...\n")
        return {
            "stage": "DRY_RUN",
            "cause": "DRY_RUN",
            "confidence": 0,
            "key_field": "DRY_RUN",
        }

    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        raise ImportError("pip install openai")

    client = OpenAI(
        api_key=os.environ["DEEPSEEK_API_KEY"],
        base_url="https://api.deepseek.com",
    )
    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        temperature=0.2,
        max_tokens=256,
    )
    raw = _extract_json(_extract_text(response.choices[0].message.content))
    return json.loads(raw)


def call_anthropic(model: str, material: str, dry_run: bool = False) -> dict:
    prompt = USER_PROMPT_TEMPLATE.format(material=material)
    if dry_run:
        print(f"\n[DRY RUN] Anthropic {model}\n{prompt[:300]}...\n")
        return {
            "stage": "DRY_RUN",
            "cause": "DRY_RUN",
            "confidence": 0,
            "key_field": "DRY_RUN",
        }

    try:
        import anthropic  # type: ignore
    except ImportError:
        raise ImportError("pip install anthropic")

    client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])
    response = client.messages.create(
        model=model,
        max_tokens=256,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = _extract_anthropic_text(response.content)
    return json.loads(raw)


def _extract_text(content: object) -> str:
    if content is None:
        return ""
    return str(content).strip()


def _extract_json(raw: str) -> str:
    """从模型输出中提取 JSON，兼容 markdown 代码块和多余文字。"""
    raw = raw.strip()
    # 去掉 ```json ... ``` 或 ``` ... ```
    for fence in ("```json", "```"):
        if raw.startswith(fence):
            raw = raw[len(fence) :]
            if "```" in raw:
                raw = raw[: raw.index("```")]
            return raw.strip()
    # 尝试找第一个 { ... } 块
    start = raw.find("{")
    end = raw.rfind("}")
    if start != -1 and end != -1 and end > start:
        return raw[start : end + 1]
    return raw


def _extract_anthropic_text(blocks: object) -> str:
    if not isinstance(blocks, list):
        return ""
    for block in blocks:
        text = cast(Any, block).text
        if isinstance(text, str) and text.strip():
            return text.strip()
    return ""


MODELS = {
    "gpt-4o": ("openai", "gpt-4o"),
    "gpt-4o-mini": ("openai", "gpt-4o-mini"),
    "claude-3-5-sonnet-20241022": ("anthropic", "claude-3-5-sonnet-20241022"),
    "claude-3-haiku-20240307": ("anthropic", "claude-3-haiku-20240307"),
    "deepseek-chat": ("deepseek", "deepseek-chat"),
    "deepseek-reasoner": ("deepseek", "deepseek-reasoner"),
    "glm-4-flash": ("zhipu", "glm-4-flash"),
    "glm-4": ("zhipu", "glm-4"),
    "glm-4-plus": ("zhipu", "glm-4-plus"),
    "glm-5.1": ("zhipu", "glm-5.1"),
}


def call_zhipu(model: str, material: str, dry_run: bool = False) -> dict:
    prompt = USER_PROMPT_TEMPLATE.format(material=material)
    if dry_run:
        print(f"\n[DRY RUN] Zhipu {model}\n{prompt[:300]}...\n")
        return {
            "stage": "DRY_RUN",
            "cause": "DRY_RUN",
            "confidence": 0,
            "key_field": "DRY_RUN",
        }

    try:
        from openai import OpenAI  # type: ignore
    except ImportError:
        raise ImportError("pip install openai")

    client = OpenAI(
        api_key=os.environ["ZHIPU_API_KEY"],
        base_url="https://open.bigmodel.cn/api/paas/v4/",
    )
    # GLM-5.1 开启 thinking 模式，需要更大的 max_tokens
    is_51 = model == "glm-5.1"
    kwargs: dict = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2
        if not is_51
        else 1.0,  # 5.1 thinking 模式要求 temperature=1.0
        "max_tokens": 2048 if is_51 else 512,
    }
    response = client.chat.completions.create(**kwargs)
    msg = response.choices[0].message
    # GLM-5.1 thinking 模式：最终答案在 content，思考过程在 reasoning_content
    content = getattr(msg, "content", None) or ""
    raw = _extract_json(_extract_text(content))
    return json.loads(raw)


def call_model(model_key: str, material: str, dry_run: bool = False) -> dict:
    provider, model_id = MODELS[model_key]
    if provider == "openai":
        return call_openai(model_id, material, dry_run)
    elif provider == "anthropic":
        return call_anthropic(model_id, material, dry_run)
    elif provider == "deepseek":
        return call_deepseek(model_id, material, dry_run)
    elif provider == "zhipu":
        return call_zhipu(model_id, material, dry_run)
    raise ValueError(f"Unknown provider: {provider}")


# ---------------------------------------------------------------------------
# 评分
# ---------------------------------------------------------------------------


def score_response(response: dict, scenario: str) -> dict:
    gt = GROUND_TRUTH[scenario]
    stage_correct = response.get("stage", "").lower() == gt["stage"].lower()
    cause = response.get("cause", "").lower()
    cause_correct = any(kw.lower() in cause for kw in gt["cause_keywords"])
    return {
        "stage_correct": stage_correct,
        "cause_correct": cause_correct,
        "confidence": response.get("confidence", 0),
        "key_field": response.get("key_field", ""),
    }


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

EVAL_CONDITIONS = [
    ("scenario1", "scenario1_raw_logs", "raw_logs"),
    ("scenario1", "scenario1_archive_compare", "archive_compare"),
    ("scenario2", "scenario2_raw_logs", "raw_logs"),
    ("scenario2", "scenario2_archive_compare", "archive_compare"),
]


def run_eval(
    model_keys: list[str],
    n_runs: int = 3,
    dry_run: bool = False,
) -> list[dict]:
    all_results = []

    for model_key in model_keys:
        print(f"\n=== Model: {model_key} ===")
        for scenario, material_name, condition in EVAL_CONDITIONS:
            material = load_material(material_name)
            print(f"  {material_name} (n={n_runs})...", end="", flush=True)
            for run_i in range(n_runs):
                try:
                    response = call_model(model_key, material, dry_run)
                    scores = score_response(response, scenario)
                    result = {
                        "model": model_key,
                        "scenario": scenario,
                        "material": material_name,
                        "condition": condition,
                        "run": run_i + 1,
                        "response": response,
                        "scores": scores,
                        "error": None,
                    }
                except Exception as e:
                    result = {
                        "model": model_key,
                        "scenario": scenario,
                        "material": material_name,
                        "condition": condition,
                        "run": run_i + 1,
                        "response": None,
                        "scores": None,
                        "error": str(e),
                    }
                all_results.append(result)
                print(".", end="", flush=True)
                if not dry_run:
                    time.sleep(0.5)  # 避免 rate limit
            print()

    return all_results


# ---------------------------------------------------------------------------
# 汇总输出
# ---------------------------------------------------------------------------


def summarize(results: list[dict]) -> str:
    lines = [
        "# Exp3 LLM-as-Evaluator 结果汇总",
        "",
        "## 设计说明",
        "",
        "- 每个模型对每种材料独立评估（盲评，不知道是 raw_logs 还是 archive_compare）",
        "- 评分维度：stage 正确性（0/1）、cause 正确性（0/1）、置信度（1-5）",
        "- 每个条件重复 N 次，取平均",
        "",
        "## 汇总表（按 scenario × condition）",
        "",
        "| Scenario | Condition | 模型 | Stage 准确率 | Cause 准确率 | 平均置信度 |",
        "|----------|-----------|------|-------------|-------------|-----------|",
    ]

    # 按 scenario + condition + model 分组
    from collections import defaultdict

    groups: dict = defaultdict(list)
    for r in results:
        if r["scores"] is None:
            continue
        key = (r["scenario"], r["condition"], r["model"])
        groups[key].append(r["scores"])

    for (scenario, condition, model), scores_list in sorted(groups.items()):
        n = len(scores_list)
        stage_acc = sum(s["stage_correct"] for s in scores_list) / n
        cause_acc = sum(s["cause_correct"] for s in scores_list) / n
        avg_conf = sum(s["confidence"] for s in scores_list) / n
        lines.append(
            f"| {scenario} | {condition} | {model} "
            f"| {stage_acc:.0%} ({sum(s['stage_correct'] for s in scores_list)}/{n})"
            f"| {cause_acc:.0%} ({sum(s['cause_correct'] for s in scores_list)}/{n})"
            f"| {avg_conf:.1f} |"
        )

    lines += [
        "",
        "## Raw vs Archive Compare 对比（跨模型平均）",
        "",
        "| Scenario | 指标 | Raw Logs | Archive Compare | 提升 |",
        "|----------|------|----------|-----------------|------|",
    ]

    for scenario in ["scenario1", "scenario2"]:
        for metric in ["stage_correct", "cause_correct"]:
            raw_scores = [
                r["scores"][metric]
                for r in results
                if r["scores"]
                and r["scenario"] == scenario
                and r["condition"] == "raw_logs"
            ]
            arc_scores = [
                r["scores"][metric]
                for r in results
                if r["scores"]
                and r["scenario"] == scenario
                and r["condition"] == "archive_compare"
            ]
            if not raw_scores or not arc_scores:
                continue
            raw_avg = sum(raw_scores) / len(raw_scores)
            arc_avg = sum(arc_scores) / len(arc_scores)
            delta = arc_avg - raw_avg
            sign = "+" if delta >= 0 else ""
            lines.append(
                f"| {scenario} | {metric} | {raw_avg:.0%} | {arc_avg:.0%} | {sign}{delta:.0%} |"
            )

    lines += [
        "",
        "## 错误记录",
        "",
    ]
    errors = [r for r in results if r["error"]]
    if errors:
        for e in errors:
            lines.append(
                f"- {e['model']} / {e['material']} run {e['run']}: {e['error']}"
            )
    else:
        lines.append("无错误。")

    lines += [
        "",
        "## 论文引用建议",
        "",
        "```",
        "To complement the user study, we conduct an LLM-simulated evaluation",
        "using multiple models as proxy evaluators. Each model is presented with",
        "either the raw log or the archive compare output for each scenario in a",
        "blind setting. We measure diagnosis accuracy (stage and root cause) and",
        "self-reported confidence across N runs per condition.",
        "```",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(description="Exp3 LLM-as-Evaluator")
    parser.add_argument(
        "--dry-run", action="store_true", help="打印 prompt，不调用 API"
    )
    parser.add_argument("--model", help="只跑指定模型（如 gpt-4o）")
    parser.add_argument(
        "--runs", type=int, default=3, help="每个条件重复次数（默认 3）"
    )
    args = parser.parse_args()

    # 决定跑哪些模型
    if args.model:
        if args.model not in MODELS:
            print(f"未知模型: {args.model}，可选: {list(MODELS.keys())}")
            return
        model_keys = [args.model]
    else:
        # 根据环境变量决定跑哪些
        model_keys = []
        if os.environ.get("OPENAI_API_KEY"):
            model_keys.append("gpt-4o")
        if os.environ.get("ANTHROPIC_API_KEY"):
            model_keys.append("claude-3-5-sonnet-20241022")
        if os.environ.get("DEEPSEEK_API_KEY"):
            model_keys.append("deepseek-chat")
        if os.environ.get("ZHIPU_API_KEY"):
            model_keys.append("glm-4-flash")
        if not model_keys:
            print("未检测到 API key，使用 --dry-run 模式")
            args.dry_run = True
            model_keys = [
                "gpt-4o",
                "claude-3-5-sonnet-20241022",
                "deepseek-chat",
                "glm-4-flash",
            ]

    print(f"模型: {model_keys}")
    print(f"每条件运行次数: {args.runs}")
    print(f"Dry run: {args.dry_run}")

    results = run_eval(model_keys, n_runs=args.runs, dry_run=args.dry_run)

    # 追加到已有结果（不覆盖其他模型的数据）
    existing: list[dict] = []
    if RESULTS_FILE.exists():
        try:
            existing = json.loads(RESULTS_FILE.read_text(encoding="utf-8"))
        except Exception:
            existing = []
    # 去掉本次跑的模型的旧数据，再追加新数据
    ran_models = {r["model"] for r in results}
    existing = [r for r in existing if r["model"] not in ran_models]
    merged = existing + results
    RESULTS_FILE.write_text(
        json.dumps(merged, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n→ 原始结果（已合并）: {RESULTS_FILE}")
    print(
        f"   本次新增: {len(results)} 条，历史保留: {len(existing)} 条，合计: {len(merged)} 条"
    )

    # 生成汇总（基于全量合并数据）
    summary = summarize(merged)
    SUMMARY_FILE.write_text(summary, encoding="utf-8")
    print(f"→ 汇总报告: {SUMMARY_FILE}")
    print("\n" + summary)


if __name__ == "__main__":
    main()
