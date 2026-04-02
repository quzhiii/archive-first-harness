import os
import time
import json
from pathlib import Path

def benchmark_io(target_dir: Path):
    print(f"Benchmarking I/O in {target_dir}...")
    target_dir.mkdir(parents=True, exist_ok=True)
    start = time.perf_counter()
    for i in range(10):
        p = target_dir / f"test_{i}.json"
        p.write_text(json.dumps({"test": i}))
        p.read_text()
        p.unlink()
    end = time.perf_counter()
    print(f"10 Small File I/O ops: {end - start:.4f}s")

def check_env():
    print(f"Python: {os.sys.version}")
    print(f"Platform: {os.sys.platform}")
    print(f"CWD: {os.getcwd()}")
    print(f"PYTHONPATH: {os.environ.get('PYTHONPATH', 'NOT SET')}")

if __name__ == "__main__":
    check_env()
    benchmark_io(Path("artifacts/io_test"))
