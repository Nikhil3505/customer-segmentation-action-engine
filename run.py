"""
Unified CLI Entrypoint for Customer Segmentation & Action Intelligence Platform.
Provides commands for:
  - generate: Generate 11 relational tables + separate ground truth (starter or full scale)
  - audit: Run comprehensive Data Quality and Anomaly Benchmark Audit
  - reproduce: Execute Step 10 two-run hash comparison
  - serve: Launch FastAPI backend + Interactive Analyst Web UI
"""

import os
import sys
import argparse
from tabulate import tabulate

from src.generator.synthetic_engine import SyntheticDataGenerator
from src.validation.auditor import DataQualityAuditor
from verify_reproducibility import verify_reproducibility


def cmd_generate(args):
    scale = args.scale
    seed = args.seed
    out_dir = args.out_dir or os.path.join("data", scale)
    inject_anomalies = not args.no_anomalies

    print(f"\n=======================================================")
    print(f"  Generating Synthetic Data (Scale: {scale}, Seed: {seed})")
    print(f"  Destination: {out_dir}")
    print(f"=======================================================\n")

    gen = SyntheticDataGenerator(seed=seed, scale=scale, inject_anomalies=inject_anomalies)
    data = gen.generate_all()

    # Export CSV, JSON, SQLite
    csv_dir = os.path.join(out_dir, "csv")
    json_dir = os.path.join(out_dir, "json")
    sqlite_path = os.path.join(out_dir, "seed_data.sqlite")

    print("-> Exporting CSV files...")
    gen.export_csv(csv_dir)
    print("-> Exporting JSON files...")
    gen.export_json(json_dir)
    print("-> Exporting SQLite database...")
    gen.export_sqlite(sqlite_path)

    # Summary table
    table = [
        ("Customers", len(data["customers"])),
        ("Products", len(data["products"])),
        ("Orders", len(data["orders"])),
        ("Order Lines", len(data["order_lines"])),
        ("Engagement Events", len(data["engagement_events"])),
        ("Support Cases", len(data["support_cases"])),
        ("Consents", len(data["consents"])),
        ("Segment Rules", len(data["segment_rules"])),
        ("Segment Memberships", len(data["segment_memberships"])),
        ("Action Catalog", len(data["action_catalog"])),
        ("Action Outcomes", len(data["action_outcomes"])),
        ("Ground Truth Anomalies", len(data["ground_truth"])),
    ]
    print(tabulate(table, headers=["Entity Table", "Record Count"], tablefmt="github"))
    print(f"\n[DONE] Generation complete. Files saved to {out_dir}")


def cmd_audit(args):
    scale = args.scale
    data_dir = args.data_dir or os.path.join("data", scale, "csv")
    seed = args.seed

    print(f"\n=======================================================")
    print(f"  Running Data Quality Audit & Benchmark Evaluation")
    print(f"=======================================================\n")

    # Generate in-memory or load
    gen = SyntheticDataGenerator(seed=seed, scale=scale, inject_anomalies=True)
    data = gen.generate_all()

    auditor = DataQualityAuditor(data)
    results = auditor.run_full_audit()

    print("--- 1. Relational Integrity Checks ---")
    print(f"  Primary Key Uniqueness:  {'PASSED' if results['primary_key_uniqueness']['passed'] else 'FAILED'}")
    print(f"  Foreign Key Integrity:   {'PASSED' if results['foreign_key_integrity']['passed'] else 'FAILED'}")
    print(f"  Enum Conformance:        {'PASSED' if results['enum_conformance']['passed'] else 'FAILED'}")
    print(f"  Date Ordering Logic:     {'PASSED' if results['date_ordering']['passed'] else 'FAILED'}")
    print(f"  Line Math Reconciled:    {'PASSED' if results['arithmetic_reconciliation']['lines_reconciled'] else 'FAILED'}")

    print("\n--- 2. Anomaly Detection vs. Ground Truth Benchmark ---")
    overall = results["anomaly_detection_metrics"]["overall_metrics"]
    print(f"  Ground Truth Anomalies:  {overall['total_ground_truth_anomalies']}")
    print(f"  Overall Precision:       {overall['precision'] * 100:.2f}%")
    print(f"  Overall Recall:          {overall['recall'] * 100:.2f}%")
    print(f"  Overall F1-Score:        {overall['f1_score'] * 100:.2f}%\n")

    cat_table = []
    for cat_name, m in results["anomaly_detection_metrics"]["by_category"].items():
        cat_table.append([
            cat_name,
            m["true_positives"],
            m["false_positives"],
            m["false_negatives"],
            f"{m['precision'] * 100:.1f}%",
            f"{m['recall'] * 100:.1f}%",
            f"{m['f1_score'] * 100:.1f}%",
        ])

    headers = ["Anomaly Category", "TP", "FP", "FN", "Precision", "Recall", "F1 Score"]
    print(tabulate(cat_table, headers=headers, tablefmt="github"))
    print("\n[DONE] Audit complete.")


def cmd_reproduce(args):
    scale = args.scale
    seed = args.seed
    success = verify_reproducibility(seed=seed, scale=scale)
    if not success:
        sys.exit(1)


def cmd_serve(args):
    import uvicorn
    host = args.host
    port = args.port
    print(f"\n=======================================================")
    print(f"  Starting YottaFlex AI Analyst Web Dashboard")
    print(f"  URL: http://{host}:{port}")
    print(f"=======================================================\n")
    uvicorn.run("src.web.app:app", host=host, port=port, reload=False)


def main():
    parser = argparse.ArgumentParser(description="YottaFlex AI Forward Deployed Engineer Platform")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # generate
    p_gen = subparsers.add_parser("generate", help="Generate synthetic datasets (CSV, JSON, SQLite)")
    p_gen.add_argument("--scale", choices=["starter", "full"], default="starter", help="Dataset volume scale")
    p_gen.add_argument("--seed", type=int, default=20261022, help="Deterministic random seed")
    p_gen.add_argument("--out-dir", type=str, default=None, help="Output directory path")
    p_gen.add_argument("--no-anomalies", action="store_true", help="Disable injection of edge cases")
    p_gen.set_defaults(func=cmd_generate)

    # audit
    p_audit = subparsers.add_parser("audit", help="Run comprehensive data quality and anomaly detection audit")
    p_audit.add_argument("--scale", choices=["starter", "full"], default="starter", help="Scale to audit")
    p_audit.add_argument("--seed", type=int, default=20261022, help="Random seed")
    p_audit.add_argument("--data-dir", type=str, default=None, help="Directory containing data files")
    p_audit.set_defaults(func=cmd_audit)

    # reproduce
    p_rep = subparsers.add_parser("reproduce", help="Verify Step 10 reproducibility across two identical runs")
    p_rep.add_argument("--scale", choices=["starter", "full"], default="starter", help="Dataset scale")
    p_rep.add_argument("--seed", type=int, default=20261022, help="Random seed")
    p_rep.set_defaults(func=cmd_reproduce)

    # serve
    p_serve = subparsers.add_parser("serve", help="Launch interactive web UI dashboard and REST API")
    p_serve.add_argument("--host", type=str, default="127.0.0.1", help="Server host")
    p_serve.add_argument("--port", type=int, default=8000, help="Server port")
    p_serve.set_defaults(func=cmd_serve)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
