"""
Step 10: Reproducibility Verification Script for YottaFlex AI challenge.
Generates data twice using the exact same fixed seed (20261022) into two separate directories,
computes SHA256 hashes and row counts across all tables, and proves 100% deterministic reproducibility.
"""

import os
import hashlib
import shutil
from tabulate import tabulate
from src.generator.synthetic_engine import SyntheticDataGenerator


def calculate_file_sha256(filepath: str) -> str:
    """Computes SHA-256 hexadecimal digest of a file."""
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def count_file_lines(filepath: str) -> int:
    """Counts non-empty lines in a file (header + data rows)."""
    with open(filepath, "r", encoding="utf-8") as f:
        return sum(1 for line in f if line.strip())


def verify_reproducibility(seed: int = 20261022, scale: str = "starter") -> bool:
    print(f"\n=======================================================")
    print(f"  Step 10: Verifying Reproducibility (Seed: {seed}, Scale: {scale})")
    print(f"=======================================================\n")

    dir_run1 = os.path.join("data", "reproducibility_run1")
    dir_run2 = os.path.join("data", "reproducibility_run2")

    # Clean prior run directories if present
    for d in (dir_run1, dir_run2):
        if os.path.exists(d):
            shutil.rmtree(d)
        os.makedirs(d, exist_ok=True)

    print("-> Executing Run 1...")
    gen1 = SyntheticDataGenerator(seed=seed, scale=scale, inject_anomalies=True)
    gen1.generate_all()
    gen1.export_csv(dir_run1)

    print("-> Executing Run 2...")
    gen2 = SyntheticDataGenerator(seed=seed, scale=scale, inject_anomalies=True)
    gen2.generate_all()
    gen2.export_csv(dir_run2)

    # Compare files
    files = sorted([f for f in os.listdir(dir_run1) if f.endswith(".csv")])
    table_data = []
    all_matched = True

    for filename in files:
        path1 = os.path.join(dir_run1, filename)
        path2 = os.path.join(dir_run2, filename)

        sha1 = calculate_file_sha256(path1)
        sha2 = calculate_file_sha256(path2)

        lines1 = count_file_lines(path1)
        lines2 = count_file_lines(path2)

        is_match = (sha1 == sha2) and (lines1 == lines2)
        if not is_match:
            all_matched = False

        status_str = "MATCH (100% IDENTICAL)" if is_match else "MISMATCH"
        table_data.append([
            filename,
            lines1 - 1,  # exclude header row for data count
            lines2 - 1,
            f"{sha1[:12]}...",
            f"{sha2[:12]}...",
            status_str,
        ])

    headers = ["Table CSV", "Run 1 Rows", "Run 2 Rows", "Run 1 SHA256", "Run 2 SHA256", "Status"]
    print(tabulate(table_data, headers=headers, tablefmt="github"))

    print("\n-------------------------------------------------------")
    if all_matched:
        print("[SUCCESS] ALL 11 TABLES + GROUND TRUTH ARE 100% IDENTICAL AND REPRODUCIBLE!")
    else:
        print("[FAILURE] DISCREPANCIES DETECTED BETWEEN RUNS.")
    print("-------------------------------------------------------\n")

    return all_matched


if __name__ == "__main__":
    import sys
    scale_arg = sys.argv[1] if len(sys.argv) > 1 else "starter"
    success = verify_reproducibility(seed=20261022, scale=scale_arg)
    sys.exit(0 if success else 1)
