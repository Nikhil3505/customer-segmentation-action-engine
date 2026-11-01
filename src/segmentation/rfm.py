"""
RFM, Engagement, and Service Burden metrics calculation module.
Derives all scoring metrics from source transactions and behavioral records.
"""

from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Dict, Any, Optional


class MetricCalculator:
    """
    Computes explainable analytical scores for customers:
    - RFM (Recency, Frequency, Monetary Net Spend)
    - Engagement Score (0-100)
    - Service Burden Index ($ and severity)
    """

    def __init__(self, reference_date: Optional[datetime] = None):
        self.reference_date = reference_date or datetime(2026, 10, 31, 23, 59, 59, tzinfo=timezone.utc)

    def calculate_rfm(self, customer: Dict[str, Any], orders: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates Recency, Frequency, and Monetary Net Spend for a single customer.
        Strictly nets refunds and excludes cancelled orders.
        """
        valid_orders = [
            o for o in orders
            if o.get("fulfillment_status") != "CANCELLED" and o.get("payment_status") != "FAILED"
        ]

        # Recency
        if valid_orders:
            order_dates = [datetime.fromisoformat(o["order_date"]) for o in valid_orders]
            latest_dt = max(order_dates)
            recency_days = max(0, (self.reference_date - latest_dt).days)
        else:
            cust_signup = datetime.fromisoformat(customer["created_at"])
            recency_days = max(0, (self.reference_date - cust_signup).days)

        # Frequency
        frequency_count = len(valid_orders)

        # Monetary Net Spend = sum(total_amount) - sum(refund_amount)
        monetary_net_spend = Decimal("0.00")
        gross_spend = Decimal("0.00")
        total_refunds = Decimal("0.00")

        for o in valid_orders:
            tot = Decimal(str(o.get("total_amount", "0.00")))
            ref = Decimal(str(o.get("refund_amount", "0.00")))
            net = Decimal(str(o.get("net_amount", tot - ref)))
            gross_spend += tot
            total_refunds += ref
            monetary_net_spend += net

        return {
            "recency_days": recency_days,
            "frequency_count": frequency_count,
            "monetary_net_spend": monetary_net_spend,
            "gross_spend": gross_spend,
            "total_refunds": total_refunds,
        }

    def calculate_engagement(self, events: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates digital engagement velocity and score (0.00 to 100.00).
        Considers event types (clicks and conversions weighted higher than views).
        """
        if not events:
            return {"engagement_score": Decimal("0.00"), "total_events": 0, "active_channels": []}

        type_weights = {
            "PAGE_VIEW": 1.0,
            "PRODUCT_VIEW": 2.0,
            "CART_ADD": 5.0,
            "EMAIL_OPEN": 2.5,
            "EMAIL_CLICK": 6.0,
            "APP_LOGIN": 3.0,
            "UNSUBSCRIBE": 0.0,
        }

        raw_score = 0.0
        channels = set()
        for e in events:
            etype = e.get("event_type", "PAGE_VIEW")
            w = type_weights.get(etype, 1.0)
            raw_score += w
            if "channel" in e:
                channels.add(e["channel"])

        score = min(Decimal("100.00"), Decimal(f"{raw_score:.2f}"))
        return {
            "engagement_score": score,
            "total_events": len(events),
            "active_channels": list(channels),
        }

    def calculate_service_burden(self, cases: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Calculates service friction, cost burden, CSAT sentiment, and open critical flags.
        """
        total_cost = Decimal("0.00")
        has_open_critical = False
        csat_ratings = []

        for c in cases:
            cost = Decimal(str(c.get("service_cost", "0.00")))
            total_cost += cost
            prio = c.get("priority", "LOW")
            st = c.get("status", "CLOSED")
            if prio == "CRITICAL" and st in ("OPEN", "ESCALATED"):
                has_open_critical = True
            if c.get("csat_score") is not None:
                csat_ratings.append(int(c["csat_score"]))

        avg_csat = (sum(csat_ratings) / len(csat_ratings)) if csat_ratings else 4.5

        return {
            "service_burden_cost": total_cost,
            "has_open_critical": has_open_critical,
            "average_csat": avg_csat,
            "total_cases": len(cases),
        }
