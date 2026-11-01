"""
Explainable Segmentation Engine.
Evaluates customer profiles against business segment rules, records full reasoning traces,
and detects exclusive segment conflicts.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional, Tuple

from src.models.entities import SegmentCode
from src.segmentation.rfm import MetricCalculator


class SegmentationEngine:
    """
    Evaluates customer behavior against explicit rules with step-by-step explainability.
    """

    def __init__(self, segment_rules: List[Dict[str, Any]], reference_date: Optional[datetime] = None):
        self.rules = sorted(segment_rules, key=lambda r: r["priority_rank"])
        self.reference_date = reference_date or datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)
        self.calculator = MetricCalculator(self.reference_date)

    def evaluate_customer(
        self,
        customer: Dict[str, Any],
        orders: List[Dict[str, Any]],
        events: List[Dict[str, Any]],
        cases: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """
        Calculates all derived metrics and applies rule-based segmentation with full decision traces.
        """
        rfm = self.calculator.calculate_rfm(customer, orders)
        eng = self.calculator.calculate_engagement(events)
        srv = self.calculator.calculate_service_burden(cases)

        cust_signup = datetime.fromisoformat(customer["created_at"])
        days_since_signup = max(0, (self.reference_date - cust_signup).days)

        recency_days = rfm["recency_days"]
        frequency_count = rfm["frequency_count"]
        monetary_net = rfm["monetary_net_spend"]
        engagement_score = eng["engagement_score"]
        service_cost = srv["service_burden_cost"]
        has_critical = srv["has_open_critical"]
        avg_csat = srv["average_csat"]

        # Rule evaluation pipeline
        matched_rules = []
        decision_trace = []

        # Check VIP Loyalist (Priority 1)
        vip_qualifies = (
            recency_days <= 45
            and frequency_count >= 4
            and monetary_net >= Decimal("1000.00")
            and avg_csat >= 3.5
        )
        if vip_qualifies:
            matched_rules.append(SegmentCode.VIP_LOYALIST.value)
            decision_trace.append(
                f"[PASS VIP_LOYALIST]: Qualified VIP: Recency {recency_days}d <= 45d, Orders {frequency_count} >= 4, "
                f"Net Spend ${monetary_net} >= $1000, CSAT {avg_csat:.1f} >= 3.5."
            )
        else:
            decision_trace.append(
                f"[FAIL VIP_LOYALIST]: Failed threshold criteria (Recency: {recency_days}d/45d, "
                f"Orders: {frequency_count}/4, Net Spend: ${monetary_net}/$1000, CSAT: {avg_csat:.1f}/3.5)."
            )

        # Check Service-Heavy / Dissatisfied (Priority 2)
        service_qualifies = (
            service_cost >= Decimal("150.00")
            or has_critical
            or avg_csat <= 2.0
        )
        if service_qualifies:
            matched_rules.append(SegmentCode.SERVICE_HEAVY_DISSATISFIED.value)
            reasons = []
            if service_cost >= Decimal("150.00"):
                reasons.append(f"High support cost ${service_cost} >= $150")
            if has_critical:
                reasons.append("Active open CRITICAL support ticket")
            if avg_csat <= 2.0:
                reasons.append(f"Low satisfaction rating CSAT {avg_csat:.1f} <= 2.0")
            decision_trace.append(f"[PASS SERVICE_HEAVY_DISSATISFIED]: {'; '.join(reasons)}.")
        else:
            decision_trace.append(
                f"[FAIL SERVICE_HEAVY_DISSATISFIED]: Support burden within normal bounds (Cost: ${service_cost}/$150, "
                f"Critical: {has_critical}, CSAT: {avg_csat:.1f})."
            )

        # Check At-Risk / Dormant (Priority 3)
        dormant_qualifies = (
            recency_days >= 90
            and frequency_count >= 1
            and engagement_score <= Decimal("15.00")
        )
        if dormant_qualifies:
            matched_rules.append(SegmentCode.AT_RISK_DORMANT.value)
            decision_trace.append(
                f"[PASS AT_RISK_DORMANT]: Inactivity alert (Recency {recency_days}d >= 90d, "
                f"Prior Purchases {frequency_count} >= 1, Digital Engagement {engagement_score:.1f} <= 15.0)."
            )
        else:
            decision_trace.append(
                f"[FAIL AT_RISK_DORMANT]: Not dormant (Recency: {recency_days}d/90d, Engagement: {engagement_score:.1f}/15.0)."
            )

        # Check New Onboarding (Priority 5)
        new_qualifies = (days_since_signup <= 30 and frequency_count <= 1)
        if new_qualifies:
            matched_rules.append(SegmentCode.NEW_ONBOARDING.value)
            decision_trace.append(
                f"[PASS NEW_ONBOARDING]: Account created recently ({days_since_signup}d <= 30d, Orders: {frequency_count})."
            )
        else:
            decision_trace.append(
                f"[FAIL NEW_ONBOARDING]: Account age {days_since_signup}d > 30d or repeat purchaser ({frequency_count} orders)."
            )

        # Default / High-Potential Growth (Priority 4)
        if not matched_rules or (
            SegmentCode.VIP_LOYALIST.value not in matched_rules
            and SegmentCode.SERVICE_HEAVY_DISSATISFIED.value not in matched_rules
            and SegmentCode.AT_RISK_DORMANT.value not in matched_rules
            and SegmentCode.NEW_ONBOARDING.value not in matched_rules
        ):
            matched_rules.append(SegmentCode.HIGH_POTENTIAL.value)
            decision_trace.append(
                f"[PASS HIGH_POTENTIAL]: Active customer nurturing pool (Spend: ${monetary_net}, "
                f"Recency: {recency_days}d, Engagement: {engagement_score:.1f})."
            )

        # Primary rule selection by highest priority rank
        rule_map = {r["segment_code"]: r for r in self.rules}
        primary_code = min(matched_rules, key=lambda c: rule_map[c]["priority_rank"])
        primary_rule = rule_map[primary_code]

        primary_explanation = next(
            (t.split(": ", 1)[1] for t in decision_trace if f"[PASS {primary_code}]" in t),
            "Qualified for segment."
        )

        return {
            "customer_id": customer["customer_id"],
            "primary_segment_code": primary_code,
            "primary_rule_id": primary_rule["rule_id"],
            "primary_segment_name": primary_rule["segment_name"],
            "all_matched_segments": matched_rules,
            "metrics": {
                "recency_days": recency_days,
                "frequency_count": frequency_count,
                "monetary_net_spend": monetary_net,
                "gross_spend": rfm["gross_spend"],
                "total_refunds": rfm["total_refunds"],
                "engagement_score": engagement_score,
                "service_burden_cost": service_cost,
                "has_open_critical": has_critical,
                "average_csat": avg_csat,
                "days_since_signup": days_since_signup,
            },
            "explainability_notes": primary_explanation,
            "full_decision_trace": decision_trace,
        }

    def detect_conflicting_exclusive_memberships(
        self,
        memberships: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Audits existing memberships to identify customers assigned to multiple mutually exclusive segments.
        Flags the deliberate anomaly!
        """
        rule_map = {r["rule_id"]: r for r in self.rules}
        memberships_by_cust: Dict[str, List[Dict[str, Any]]] = {}
        for m in memberships:
            if m.get("is_active", True):
                memberships_by_cust.setdefault(m["customer_id"], []).append(m)

        conflicts = []
        for cid, mems in memberships_by_cust.items():
            if len(mems) > 1:
                exclusive_rules = [
                    rule_map[m["rule_id"]]
                    for m in mems
                    if m["rule_id"] in rule_map and rule_map[m["rule_id"]]["is_exclusive"]
                ]
                if len(exclusive_rules) > 1:
                    conflicts.append({
                        "customer_id": cid,
                        "exclusive_segment_codes": [r["segment_code"] for r in exclusive_rules],
                        "rule_ids": [r["rule_id"] for r in exclusive_rules],
                        "memberships": mems,
                        "description": (
                            f"Customer {cid} is concurrently assigned to {len(exclusive_rules)} mutually exclusive "
                            f"segments: {', '.join([r['segment_code'] for r in exclusive_rules])}."
                        ),
                    })

        return conflicts
