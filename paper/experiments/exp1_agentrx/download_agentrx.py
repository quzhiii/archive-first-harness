#!/usr/bin/env python3
"""
Step 1: Download AgentRx dataset from HuggingFace.

AgentRx dataset: https://huggingface.co/datasets/microsoft/AgentRx
Paper: https://arxiv.org/abs/2602.02475

Usage:
    python download_agentrx.py
    python download_agentrx.py --output ../../data/agentrx_raw
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def download_with_huggingface(output_dir: Path) -> None:
    """Download via HuggingFace datasets library."""
    try:
        from datasets import load_dataset  # type: ignore
    except ImportError:
        print("ERROR: 'datasets' package not installed.")
        print("Run: pip install datasets")
        raise

    print("Downloading microsoft/AgentRx from HuggingFace...")
    ds = load_dataset("microsoft/AgentRx")
    if not hasattr(ds, "keys") or not hasattr(ds, "items"):
        raise TypeError("Expected a DatasetDict-like object from load_dataset")

    split_names = list(ds.keys())
    print(f"Dataset splits: {split_names}")
    for split_name, split_data in ds.items():
        print(f"  {split_name}: {len(split_data)} rows")

    # Save raw data
    output_dir.mkdir(parents=True, exist_ok=True)
    for split_name, split_data in ds.items():
        out_path = output_dir / f"{split_name}.jsonl"
        with out_path.open("w", encoding="utf-8") as f:
            for row in split_data:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        print(f"Saved {len(split_data)} rows → {out_path}")

    # Print sample to understand schema
    print("\n--- Sample row keys ---")
    first_split = ds[split_names[0]]
    sample = next(iter(first_split))
    if isinstance(sample, dict):
        for key, val in sample.items():
            val_preview = str(val)[:120] + "..." if len(str(val)) > 120 else str(val)
            print(f"  {key}: {val_preview}")

    print(f"\nDone. Raw data saved to: {output_dir}")


def inspect_schema(output_dir: Path) -> None:
    """Print schema of downloaded data to understand fields."""
    jsonl_files = list(output_dir.glob("*.jsonl"))
    if not jsonl_files:
        print("No .jsonl files found. Run download first.")
        return

    for path in jsonl_files:
        print(f"\n=== {path.name} ===")
        with path.open(encoding="utf-8") as f:
            for i, line in enumerate(f):
                if i >= 3:
                    break
                row = json.loads(line)
                print(f"\n-- Row {i} --")
                for key, val in row.items():
                    val_str = str(val)
                    preview = val_str[:200] + "..." if len(val_str) > 200 else val_str
                    print(f"  [{key}] ({type(val).__name__}): {preview}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Download AgentRx dataset")
    parser.add_argument(
        "--output",
        default="../../data/agentrx_raw",
        help="Output directory for raw data",
    )
    parser.add_argument(
        "--inspect-only",
        action="store_true",
        help="Only inspect existing downloaded data (no download)",
    )
    args = parser.parse_args()

    output_dir = Path(args.output)

    if args.inspect_only:
        inspect_schema(output_dir)
    else:
        download_with_huggingface(output_dir)
        print("\n--- Inspecting schema ---")
        inspect_schema(output_dir)


if __name__ == "__main__":
    main()
