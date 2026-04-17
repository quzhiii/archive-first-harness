"""
Exp3 方案B：信息密度量化分析

对每个 scenario 的 raw_logs 和 archive_compare 材料计算：
1. 总字符数
2. 关键诊断字符数（能直接回答"失败在哪步+根因"的最小片段）
3. 信息密度 = 关键字符数 / 总字符数
4. 推断路径长度（需跨越几个独立信息块）

输出：Markdown 表格 + JSON 原始数据
"""

from __future__ import annotations

import json
import re
from pathlib import Path

MATERIALS_DIR = Path(__file__).parent / "materials"

# ---------------------------------------------------------------------------
# 关键诊断片段定义
# 每个条目：(描述, 正则或字面量, 是否正则)
# 原则：能让开发者直接得出"失败阶段 + 根因"结论的最小文本单元
# ---------------------------------------------------------------------------

DIAGNOSTIC_SPANS = {
    "scenario1_raw_logs": [
        ("检索策略退化信号", r"retrieval_strategy.*broad_noisy", True),
        ("grounding失败码", r"grounding_failed", True),
        ("策略退化reason code", r"retrieval_strategy_regressed", True),
        ("verification失败", r'"passed":\s*false', True),
    ],
    "scenario1_archive_compare": [
        ("策略退化transition", r"retrieval_strategy_regressed", True),
        ("grounding失败码", r"grounding_failed", True),
        ("verification退化标记", r"verification:.*passed.*failed", True),
        ("幻觉输出标注", r"SaaS dashboard", True),
    ],
    "scenario2_raw_logs": [
        (
            "step2启动无响应（时间戳推断）",
            r"step_started.*step=2[\s\S]{0,200}runtime_completed",
            True,
        ),
        ("tool_unavailable warning", r"tool_unavailable", True),
        ("partial_output warning", r"partial_output", True),
        ("execution_failed reason", r"execution_failed", True),
    ],
    "scenario2_archive_compare": [
        ("failure transition", r"failure:.*none.*restaurant_api_timeout", True),
        ("step2_timeout码", r"step2_timeout", True),
        ("artifacts全部丢失", r"artifacts:.*compatible.*none", True),
        ("verification退化标记", r"verification:.*passed.*failed", True),
    ],
}

# 推断路径：需要跨越几个独立信息块才能得出结论
# 定义每个材料里的"信息块"（section headers）
INFERENCE_PATH = {
    "scenario1_raw_logs": {
        "blocks_needed": ["Agent Output", "Verification Report", "Reassessment"],
        "path_length": 3,
        "note": "需从 metadata.retrieval_strategy → verification warnings → reassessment reason_codes 综合推断",
    },
    "scenario1_archive_compare": {
        "blocks_needed": ["Key Transitions", "Reason Codes Changed"],
        "path_length": 2,
        "note": "Key Transitions 直接标注 verification regressed，Reason Codes 给出 retrieval_strategy_regressed",
    },
    "scenario2_raw_logs": {
        "blocks_needed": [
            "Execution Trace",
            "Verification Report",
            "Reassessment",
            "Failure Signature",
        ],
        "path_length": 4,
        "note": "需从时间戳推断 step2 卡住，failure_signature 不暴露具体步骤，需综合4个块",
    },
    "scenario2_archive_compare": {
        "blocks_needed": ["Key Transitions", "Reason Codes Changed"],
        "path_length": 2,
        "note": "Key Transitions 直接给出 restaurant_api_timeout，Root Cause in One Line 直接说明",
    },
}


def load_material(name: str) -> str:
    path = MATERIALS_DIR / f"{name}.md"
    return path.read_text(encoding="utf-8")


def expand_to_line(text: str, match: re.Match) -> tuple[int, int]:
    """把匹配位置扩展到整行（含换行符）"""
    start = text.rfind("\n", 0, match.start())
    start = 0 if start == -1 else start + 1
    end = text.find("\n", match.end())
    end = len(text) if end == -1 else end + 1
    return start, end


def count_diagnostic_chars(text: str, spans: list[tuple]) -> tuple[int, list[dict]]:
    """返回 (关键字符总数, 匹配详情列表)

    计算方式：找到关键词所在的完整行，合并去重后统计字符数。
    这样能反映"有效信息行"的占比，而不只是关键词本身的长度。
    """
    covered: set[int] = set()
    details = []
    for desc, pattern, is_regex in spans:
        if is_regex:
            matches = list(re.finditer(pattern, text, re.IGNORECASE | re.DOTALL))
        else:
            matches = [
                m for m in [re.search(re.escape(pattern), text, re.IGNORECASE)] if m
            ]
        line_chars = 0
        for m in matches:
            s, e = expand_to_line(text, m)
            new = set(range(s, e)) - covered
            covered |= new
            line_chars += len(new)
        details.append(
            {
                "description": desc,
                "pattern": pattern,
                "match_count": len(matches),
                "chars": line_chars,
            }
        )
    total = sum(d["chars"] for d in details)
    return total, details


def analyze_material(name: str) -> dict:
    text = load_material(name)
    # 去掉问题部分（### 请回答 之后）不计入材料长度
    if "### 请回答" in text:
        text = text[: text.index("### 请回答")]
    total_chars = len(text)
    spans = DIAGNOSTIC_SPANS.get(name, [])
    key_chars, details = count_diagnostic_chars(text, spans)
    density = key_chars / total_chars if total_chars > 0 else 0
    path_info = INFERENCE_PATH.get(name, {})
    return {
        "name": name,
        "total_chars": total_chars,
        "key_chars": key_chars,
        "density": round(density, 4),
        "density_pct": f"{density * 100:.1f}%",
        "path_length": path_info.get("path_length", "?"),
        "blocks_needed": path_info.get("blocks_needed", []),
        "path_note": path_info.get("note", ""),
        "span_details": details,
    }


def format_markdown_table(results: list[dict]) -> str:
    lines = [
        "# Exp3 信息密度分析结果",
        "",
        "## 汇总表",
        "",
        "| 材料 | 总字符数 | 关键诊断字符数 | 信息密度 | 推断路径长度 |",
        "|------|----------|----------------|----------|--------------|",
    ]
    for r in results:
        name = r["name"].replace("_", "\\_")
        lines.append(
            f"| {name} | {r['total_chars']} | {r['key_chars']} "
            f"| {r['density_pct']} | {r['path_length']} 步 |"
        )

    lines += ["", "## 对比摘要（按 Scenario）", ""]

    for scenario in ["scenario1", "scenario2"]:
        raw = next(r for r in results if r["name"] == f"{scenario}_raw_logs")
        arc = next(r for r in results if r["name"] == f"{scenario}_archive_compare")
        label = "RAG Agent" if scenario == "scenario1" else "Multi-Step Agent"
        density_lift = (
            (float(arc["density"]) - float(raw["density"]))
            / float(raw["density"])
            * 100
            if raw["density"] > 0
            else 0
        )
        path_reduction = raw["path_length"] - arc["path_length"]
        lines += [
            f"### {label}",
            "",
            f"- 信息密度：Raw {raw['density_pct']} → Archive {arc['density_pct']} "
            f"（+{density_lift:.0f}%）",
            f"- 推断路径：Raw {raw['path_length']} 步 → Archive {arc['path_length']} 步 "
            f"（减少 {path_reduction} 步）",
            f"- Raw 路径说明：{raw['path_note']}",
            f"- Archive 路径说明：{arc['path_note']}",
            "",
        ]

    lines += [
        "## 方法说明",
        "",
        "**信息密度** = 关键诊断字符数 / 总字符数",
        "",
        "关键诊断字符定义为：能直接回答「失败发生在哪一步」和「根本原因是什么」",
        "的最小文本片段，通过正则匹配提取。",
        "",
        "**推断路径长度** = 开发者需要跨越的独立信息块数量，",
        "才能从材料中综合得出完整诊断结论。",
        "",
        "> 注：信息密度高不等于材料更短，而是意味着有效信息占比更高、噪声更少。",
        "> 推断路径短意味着开发者需要在更少的位置之间跳转才能得出结论。",
    ]

    return "\n".join(lines)


def main() -> None:
    names = [
        "scenario1_raw_logs",
        "scenario1_archive_compare",
        "scenario2_raw_logs",
        "scenario2_archive_compare",
    ]

    results = [analyze_material(n) for n in names]

    # 输出 Markdown 表格
    md = format_markdown_table(results)
    out_md = Path(__file__).parent / "results_info_density.md"
    out_md.write_text(md, encoding="utf-8")
    print(md)

    # 输出 JSON 原始数据
    out_json = Path(__file__).parent / "results_info_density.json"
    out_json.write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print(f"\n→ Markdown: {out_md}")
    print(f"→ JSON:     {out_json}")


if __name__ == "__main__":
    main()
