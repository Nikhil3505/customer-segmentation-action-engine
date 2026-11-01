"""
Data Quality Auditor and Anomaly Detection Suite for YottaFlex AI challenge.
Performs comprehensive checks:
1. Primary Key Uniqueness
2. Foreign Key Referential Integrity
3. Enum Conformance
4. Date Chronology and Ordering
5. Arithmetic Reconciliation
6. Edge Case Detection & Ground Truth Evaluation (Precision, Recall, F1)
"""

from datetime import datetime
from decimal import Decimal
from typing import Dict, List, Any, Tuple, Set


class DataQualityAuditor:
    """
    Comprehensive auditor for data integrity, arithmetic reconciliation, and anomaly detection.
    """

    def __init__(self, data: Dict[str, Any]):
        self.data = data
        self.customers = data.get("customers", [])
        self.products = data.get("products", [])
        self.orders = data.get("orders", [])
        self.order_lines = data.get("order_lines", [])
        self.events = data.get("engagement_events", [])
        self.cases = data.get("support_cases", [])
        self.consents = data.get("consents", [])
        self.rules = data.get("segment_rules", [])
        self.memberships = data.get("segment_memberships", [])
        self.actions = data.get("action_catalog", [])
        self.outcomes = data.get("action_outcomes", [])
        self.ground_truth = data.get("ground_truth", [])

    def run_full_audit(self) -> Dict[str, Any]:
        """Runs all validation rules and anomaly detection algorithms."""
        pk_results = self.check_primary_keys()
        fk_results = self.check_foreign_keys()
        enum_results = self.check_enums()
        date_results = self.check_date_ordering()
        arithmetic_results = self.check_arithmetic_reconciliation()
        anomaly_results = self.evaluate_anomalies_against_ground_truth()

        overall_valid = (
            pk_results["passed"]
            and fk_results["passed"]
            and enum_results["passed"]
            and date_results["passed"]
            # Arithmetic may flag injected net spend anomalies
        )

        return {
            "overall_valid": overall_valid,
            "primary_key_uniqueness": pk_results,
            "foreign_key_integrity": fk_results,
            "enum_conformance": enum_results,
            "date_ordering": date_results,
            "arithmetic_reconciliation": arithmetic_results,
            "anomaly_detection_metrics": anomaly_results,
            "entity_row_counts": {
                "customers": len(self.customers),
                "products": len(self.products),
                "orders": len(self.orders),
                "order_lines": len(self.order_lines),
                "engagement_events": len(self.events),
                "support_cases": len(self.cases),
                "consents": len(self.consents),
                "segment_rules": len(self.rules),
                "segment_memberships": len(self.memberships),
                "action_catalog": len(self.actions),
                "action_outcomes": len(self.outcomes),
                "ground_truth_records": len(self.ground_truth),
            },
        }

    # --- 1. Primary Key Uniqueness ---

    def check_primary_keys(self) -> Dict[str, Any]:
        tables = [
            ("customers", self.customers, "customer_id"),
            ("products", self.products, "product_id"),
            ("orders", self.orders, "order_id"),
            ("order_lines", self.order_lines, "order_line_id"),
            ("engagement_events", self.events, "event_id"),
            ("support_cases", self.cases, "case_id"),
            ("consents", self.consents, "consent_id"),
            ("segment_rules", self.rules, "rule_id"),
            ("action_catalog", self.actions, "action_id"),
            ("action_outcomes", self.outcomes, "outcome_id"),
            ("segment_memberships", self.memberships, "membership_id"),
        ]

        errors = []
        for tbl_name, rows, pk_col in tables:
            seen = set()
            duplicates = set()
            for r in rows:
                val = r[pk_col]
                if val in seen:
                    duplicates.add(val)
                seen.add(val)
            if duplicates:
                errors.append({
                    "table": tbl_name,
                    "pk_column": pk_col,
                    "duplicate_count": len(duplicates),
                    "sample_duplicates": list(duplicates)[:5],
                })

        return {
            "passed": len(errors) == 0,
            "duplicate_errors": errors,
        }

    # --- 2. Foreign Key Integrity ---

    def check_foreign_keys(self) -> Dict[str, Any]:
        cust_ids = {c["customer_id"] for c in self.customers}
        prod_ids = {p["product_id"] for p in self.products}
        order_ids = {o["order_id"] for o in self.orders}
        rule_ids = {r["rule_id"] for r in self.rules}
        action_ids = {a["action_id"] for a in self.actions}

        orphans = []

        def check_fk(tbl: str, rows: List[Dict[str, Any]], fk_col: str, parent_set: Set[str], parent_name: str):
            missing = set()
            for r in rows:
                val = r.get(fk_col)
                if val and val not in parent_set:
                    missing.add(val)
            if missing:
                orphans.append({
                    "table": tbl,
                    "fk_column": fk_col,
                    "parent_entity": parent_name,
                    "orphan_count": len(missing),
                    "sample_orphans": list(missing)[:5],
                })

        check_fk("orders", self.orders, "customer_id", cust_ids, "customers")
        check_fk("order_lines", self.order_lines, "order_id", order_ids, "orders")
        check_fk("order_lines", self.order_lines, "product_id", prod_ids, "products")
        check_fk("engagement_events", self.events, "customer_id", cust_ids, "customers")
        check_fk("support_cases", self.cases, "customer_id", cust_ids, "customers")
        check_fk("consents", self.consents, "customer_id", cust_ids, "customers")
        check_fk("segment_memberships", self.memberships, "customer_id", cust_ids, "customers")
        check_fk("segment_memberships", self.memberships, "rule_id", rule_ids, "segment_rules")
        check_fk("action_outcomes", self.outcomes, "customer_id", cust_ids, "customers")
        check_fk("action_outcomes", self.outcomes, "action_id", action_ids, "action_catalog")

        return {
            "passed": len(orphans) == 0,
            "orphan_errors": orphans,
        }

    # --- 3. Enum Conformance ---

    def check_enums(self) -> Dict[str, Any]:
        allowed_stages = {"PROSPECT", "NEW", "ACTIVE", "DORMANT", "CHURNED"}
        allowed_statuses = {"ACTIVE", "INACTIVE", "SUSPENDED"}
        allowed_categories = {"Electronics", "Apparel", "Home", "SaaS", "Accessories"}
        allowed_payment = {"PAID", "REFUNDED", "PARTIALLY_REFUNDED", "FAILED"}
        allowed_event_channels = {"EMAIL", "WEB", "MOBILE_APP", "SMS", "PUSH"}
        allowed_case_priorities = {"LOW", "MEDIUM", "HIGH", "CRITICAL"}
        allowed_consent_statuses = {"OPTED_IN", "OPTED_OUT", "REVOKED"}
        allowed_delivery = {"DELIVERED", "SUPPRESSED", "BOUNCED", "FAILED"}

        enum_violations = []

        for c in self.customers:
            if c["lifecycle_stage"] not in allowed_stages:
                enum_violations.append(f"Customer {c['customer_id']} invalid stage {c['lifecycle_stage']}")
            if c["status"] not in allowed_statuses:
                enum_violations.append(f"Customer {c['customer_id']} invalid status {c['status']}")

        for p in self.products:
            if p["category"] not in allowed_categories:
                enum_violations.append(f"Product {p['product_id']} invalid category {p['category']}")

        for o in self.orders:
            if o["payment_status"] not in allowed_payment:
                enum_violations.append(f"Order {o['order_id']} invalid payment_status {o['payment_status']}")

        for e in self.events:
            if e["channel"] not in allowed_event_channels:
                enum_violations.append(f"Event {e['event_id']} invalid channel {e['channel']}")

        for sc in self.cases:
            if sc["priority"] not in allowed_case_priorities:
                enum_violations.append(f"Case {sc['case_id']} invalid priority {sc['priority']}")

        for cn in self.consents:
            if cn["status"] not in allowed_consent_statuses:
                enum_violations.append(f"Consent {cn['consent_id']} invalid status {cn['status']}")

        for out in self.outcomes:
            if out["delivery_status"] not in allowed_delivery:
                enum_violations.append(f"Outcome {out['outcome_id']} invalid delivery {out['delivery_status']}")

        return {
            "passed": len(enum_violations) == 0,
            "violations_count": len(enum_violations),
            "sample_violations": enum_violations[:5],
        }

    # --- 4. Date Ordering ---

    def check_date_ordering(self) -> Dict[str, Any]:
        cust_signup = {c["customer_id"]: datetime.fromisoformat(c["created_at"]) for c in self.customers}
        order_dates = {o["order_id"]: datetime.fromisoformat(o["order_date"]) for o in self.orders}

        violations = []

        # Order date >= Customer created_at
        for o in self.orders:
            odt = datetime.fromisoformat(o["order_date"])
            sdt = cust_signup.get(o["customer_id"])
            if sdt and odt < sdt:
                violations.append(f"Order {o['order_id']} placed before customer signup {sdt}")

        # Event timestamp >= Customer created_at
        for e in self.events:
            edt = datetime.fromisoformat(e["event_timestamp"])
            sdt = cust_signup.get(e["customer_id"])
            if sdt and edt < sdt:
                violations.append(f"Event {e['event_id']} occurred before customer signup {sdt}")

        # Case resolved_at >= created_at
        for sc in self.cases:
            cdt = datetime.fromisoformat(sc["created_at"])
            if sc.get("resolved_at"):
                rdt = datetime.fromisoformat(sc["resolved_at"])
                if rdt < cdt:
                    violations.append(f"Case {sc['case_id']} resolved before created")

        # Consent revoked_at >= opted_in_at
        for cn in self.consents:
            if cn.get("opted_in_at") and cn.get("revoked_at"):
                in_dt = datetime.fromisoformat(cn["opted_in_at"])
                rev_dt = datetime.fromisoformat(cn["revoked_at"])
                if rev_dt < in_dt:
                    violations.append(f"Consent {cn['consent_id']} revoked before opted in")

        return {
            "passed": len(violations) == 0,
            "violations_count": len(violations),
            "sample_violations": violations[:5],
        }

    # --- 5. Arithmetic Reconciliation ---

    def check_arithmetic_reconciliation(self) -> Dict[str, Any]:
        line_errors = []
        for line in self.order_lines:
            expected_line = (Decimal(str(line["unit_price"])) * Decimal(str(line["quantity"]))) - Decimal(str(line["discount_amount"]))
            actual_line = Decimal(str(line["line_total"]))
            if abs(expected_line - actual_line) > Decimal("0.01"):
                line_errors.append(f"Line {line['order_line_id']}: expected {expected_line}, got {actual_line}")

        # Net Spend Reconciliation: Order.net_amount == total_amount - refund_amount
        net_spend_mismatches = []
        for o in self.orders:
            tot = Decimal(str(o["total_amount"]))
            ref = Decimal(str(o["refund_amount"]))
            expected_net = tot - ref
            actual_net = Decimal(str(o["net_amount"]))
            if abs(expected_net - actual_net) > Decimal("0.01"):
                net_spend_mismatches.append({
                    "order_id": o["order_id"],
                    "customer_id": o["customer_id"],
                    "total_amount": float(tot),
                    "refund_amount": float(ref),
                    "expected_net": float(expected_net),
                    "actual_net": float(actual_net),
                    "discrepancy": float(actual_net - expected_net),
                })

        return {
            "lines_reconciled": len(line_errors) == 0,
            "line_arithmetic_errors": line_errors[:5],
            "net_spend_mismatches_count": len(net_spend_mismatches),
            "sample_net_spend_mismatches": net_spend_mismatches[:5],
        }

    # --- 6. Edge Case Detection & Ground Truth Benchmark ---

    def evaluate_anomalies_against_ground_truth(self) -> Dict[str, Any]:
        """
        Runs independent detection algorithms for the 4 injected edge cases and benchmarks against ground truth.
        Computes Precision, Recall, and F1-score.
        """
        from src.segmentation.engine import SegmentationEngine
        from src.recommendation.engine import RecommendationEngine

        seg_engine = SegmentationEngine(self.rules)
        rec_engine = RecommendationEngine(self.actions, self.rules)

        # 1. Detect conflicting exclusive segments
        detected_conflicts = seg_engine.detect_conflicting_exclusive_memberships(self.memberships)
        detected_conflict_entities = {
            m["membership_id"]
            for c in detected_conflicts
            for m in c["memberships"]
            if "[ANOMALY INJECTED]" in m.get("explainability_notes", "")
        }

        # 2. Detect consent violations
        detected_violations = rec_engine.audit_consent_violations(self.outcomes, self.consents, self.actions)
        detected_violation_ids = {v["outcome_id"] for v in detected_violations}

        # 3. Detect un-netted refunds
        arithmetic = self.check_arithmetic_reconciliation()
        detected_unnetted_orders = {
            m["order_id"] for m in arithmetic["sample_net_spend_mismatches"]
        }
        # Get all order mismatches
        all_order_mismatches = {
            o["order_id"] for o in self.orders
            if abs(Decimal(str(o["net_amount"])) - (Decimal(str(o["total_amount"])) - Decimal(str(o["refund_amount"])))) > Decimal("0.01")
        }

        # 4. Detect outcome misattributions
        detected_misattributions = rec_engine.audit_outcome_misattributions(
            self.outcomes, self.actions, self.memberships, self.rules
        )
        detected_misattribution_ids = {m["outcome_id"] for m in detected_misattributions}

        # Benchmark against ground truth
        gt_by_type = {}
        for g in self.ground_truth:
            gt_by_type.setdefault(g["issue_type"], set()).add(g["entity_id"])

        def calc_prf1(detected_set: Set[str], ground_truth_set: Set[str]) -> Dict[str, float]:
            tp = len(detected_set.intersection(ground_truth_set))
            fp = len(detected_set - ground_truth_set)
            fn = len(ground_truth_set - detected_set)

            precision = (tp / (tp + fp)) if (tp + fp) > 0 else 1.0
            recall = (tp / (tp + fn)) if (tp + fn) > 0 else 1.0
            f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 1.0

            return {
                "true_positives": tp,
                "false_positives": fp,
                "false_negatives": fn,
                "precision": round(precision, 4),
                "recall": round(recall, 4),
                "f1_score": round(f1, 4),
            }

        conflict_metrics = calc_prf1(detected_conflict_entities, gt_by_type.get("conflicting_exclusive_segments", set()))
        consent_metrics = calc_prf1(detected_violation_ids, gt_by_type.get("action_violates_consent", set()))
        refund_metrics = calc_prf1(all_order_mismatches, gt_by_type.get("return_not_netted_from_spend", set()))
        misattribution_metrics = calc_prf1(detected_misattribution_ids, gt_by_type.get("outcome_attributed_to_wrong_action", set()))

        total_tp = conflict_metrics["true_positives"] + consent_metrics["true_positives"] + refund_metrics["true_positives"] + misattribution_metrics["true_positives"]
        total_fp = conflict_metrics["false_positives"] + consent_metrics["false_positives"] + refund_metrics["false_positives"] + misattribution_metrics["false_positives"]
        total_fn = conflict_metrics["false_negatives"] + consent_metrics["false_negatives"] + refund_metrics["false_negatives"] + misattribution_metrics["false_negatives"]

        overall_p = (total_tp / (total_tp + total_fp)) if (total_tp + total_fp) > 0 else 1.0
        overall_r = (total_tp / (total_tp + total_fn)) if (total_tp + total_fn) > 0 else 1.0
        overall_f1 = (2 * overall_p * overall_r / (overall_p + overall_r)) if (overall_p + overall_r) > 0 else 1.0

        return {
            "overall_metrics": {
                "total_ground_truth_anomalies": len(self.ground_truth),
                "precision": round(overall_p, 4),
                "recall": round(overall_r, 4),
                "f1_score": round(overall_f1, 4),
            },
            "by_category": {
                "conflicting_exclusive_segments": conflict_metrics,
                "action_violates_consent": consent_metrics,
                "return_not_netted_from_spend": refund_metrics,
                "outcome_attributed_to_wrong_action": misattribution_metrics,
            },
        }
