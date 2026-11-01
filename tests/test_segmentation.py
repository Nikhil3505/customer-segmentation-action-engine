"""
Unit tests for RFM calculations, explainable segmentation rules, and conflict detection.
"""

from decimal import Decimal
from datetime import datetime, timezone
import pytest

from src.segmentation.rfm import MetricCalculator
from src.segmentation.engine import SegmentationEngine


@pytest.fixture
def sample_rules():
    return [
        {
            "rule_id": "SEG-2026-000001",
            "segment_code": "VIP_LOYALIST",
            "segment_name": "VIP Loyalists",
            "criteria_description": "High spenders",
            "criteria_json": "{}",
            "is_exclusive": True,
            "priority_rank": 1,
            "is_active": True,
        },
        {
            "rule_id": "SEG-2026-000002",
            "segment_code": "SERVICE_HEAVY_DISSATISFIED",
            "segment_name": "Service-Heavy",
            "criteria_description": "Support friction",
            "criteria_json": "{}",
            "is_exclusive": True,
            "priority_rank": 2,
            "is_active": True,
        },
        {
            "rule_id": "SEG-2026-000003",
            "segment_code": "AT_RISK_DORMANT",
            "segment_name": "At-Risk Dormant",
            "criteria_description": "Inactivity",
            "criteria_json": "{}",
            "is_exclusive": True,
            "priority_rank": 3,
            "is_active": True,
        },
        {
            "rule_id": "SEG-2026-000004",
            "segment_code": "HIGH_POTENTIAL",
            "segment_name": "High Potential",
            "criteria_description": "Growth pool",
            "criteria_json": "{}",
            "is_exclusive": False,
            "priority_rank": 4,
            "is_active": True,
        },
        {
            "rule_id": "SEG-2026-000005",
            "segment_code": "NEW_ONBOARDING",
            "segment_name": "New Onboarding",
            "criteria_description": "Recent signups",
            "criteria_json": "{}",
            "is_exclusive": True,
            "priority_rank": 5,
            "is_active": True,
        },
    ]


def test_rfm_calculation_nets_refunds():
    calc = MetricCalculator(datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc))
    customer = {
        "customer_id": "CUS-000001",
        "created_at": "2025-01-01T00:00:00+00:00",
    }
    orders = [
        {
            "order_id": "ORD-2026-000001",
            "customer_id": "CUS-000001",
            "order_date": "2026-10-01T12:00:00+00:00",
            "total_amount": Decimal("500.00"),
            "refund_amount": Decimal("100.00"),
            "net_amount": Decimal("400.00"),
            "payment_status": "PARTIALLY_REFUNDED",
            "fulfillment_status": "DELIVERED",
        },
        {
            "order_id": "ORD-2026-000002",
            "customer_id": "CUS-000001",
            "order_date": "2026-10-15T12:00:00+00:00",
            "total_amount": Decimal("250.00"),
            "refund_amount": Decimal("0.00"),
            "net_amount": Decimal("250.00"),
            "payment_status": "PAID",
            "fulfillment_status": "DELIVERED",
        },
    ]

    res = calc.calculate_rfm(customer, orders)
    assert res["frequency_count"] == 2
    assert res["monetary_net_spend"] == Decimal("650.00")
    assert res["recency_days"] == 16  # from Oct 15 to Oct 31


def test_vip_segment_qualifies(sample_rules):
    engine = SegmentationEngine(sample_rules, datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc))
    customer = {"customer_id": "CUS-000100", "created_at": "2024-01-01T00:00:00+00:00"}
    orders = [
        {
            "order_id": f"ORD-2026-{i:06d}",
            "order_date": "2026-10-20T00:00:00+00:00",
            "total_amount": Decimal("300.00"),
            "refund_amount": Decimal("0.00"),
            "net_amount": Decimal("300.00"),
            "payment_status": "PAID",
            "fulfillment_status": "DELIVERED",
        }
        for i in range(1, 5)
    ]
    events = [{"event_type": "PAGE_VIEW", "channel": "WEB"} for _ in range(10)]
    cases = [{"service_cost": Decimal("20.00"), "priority": "LOW", "status": "CLOSED", "csat_score": 5}]

    res = engine.evaluate_customer(customer, orders, events, cases)
    assert res["primary_segment_code"] == "VIP_LOYALIST"
    assert "Qualified VIP" in res["explainability_notes"]


def test_conflict_detection(sample_rules):
    engine = SegmentationEngine(sample_rules)
    memberships = [
        {
            "membership_id": "MEM-SEG-2026-000001-CUS-000001",
            "rule_id": "SEG-2026-000001",
            "customer_id": "CUS-000001",
            "is_active": True,
        },
        {
            "membership_id": "MEM-SEG-2026-000003-CUS-000001",
            "rule_id": "SEG-2026-000003",
            "customer_id": "CUS-000001",
            "is_active": True,
        },
    ]
    conflicts = engine.detect_conflicting_exclusive_memberships(memberships)
    assert len(conflicts) == 1
    assert conflicts[0]["customer_id"] == "CUS-000001"
    assert "VIP_LOYALIST" in conflicts[0]["exclusive_segment_codes"]
    assert "AT_RISK_DORMANT" in conflicts[0]["exclusive_segment_codes"]
