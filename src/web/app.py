"""
FastAPI Backend Application for YottaFlex AI Explainable Customer Segmentation & Action Recommendation.
Serves analytical APIs and the interactive Analyst Web Dashboard.
"""

import os
import json
from decimal import Decimal
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any

from fastapi import FastAPI, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from src.generator.synthetic_engine import SyntheticDataGenerator
from src.segmentation.engine import SegmentationEngine
from src.recommendation.engine import RecommendationEngine
from src.recommendation.guardrails import GuardrailPolicyEngine
from src.validation.auditor import DataQualityAuditor

app = FastAPI(
    title="YottaFlex AI - Explainable Customer Segmentation & Action Platform",
    description="End-to-end Forward Deployed AI system for explainable segmentation, consent guardrails, and anomaly auditing.",
    version="1.0.0",
)

# Global dataset cache
CURRENT_DATA: Dict[str, Any] = {}
DATA_SCALE = "starter"


def load_or_generate_dataset(scale: str = "starter", seed: int = 20261022) -> Dict[str, Any]:
    global CURRENT_DATA, DATA_SCALE
    DATA_SCALE = scale
    gen = SyntheticDataGenerator(seed=seed, scale=scale, inject_anomalies=True)
    CURRENT_DATA = gen.generate_all()
    return CURRENT_DATA


# Initialize dataset on startup
@app.on_event("startup")
def startup_event():
    load_or_generate_dataset("starter")


# Helper JSON serializer for Decimals
def clean_json(obj: Any) -> Any:
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, (datetime, )):
        return obj.isoformat()
    if isinstance(obj, list):
        return [clean_json(x) for x in obj]
    if isinstance(obj, dict):
        return {k: clean_json(v) for k, v in obj.items()}
    return obj


# --- API Routes ---

@app.get("/api/overview")
def get_overview():
    """Returns high-level executive KPIs, segment distribution, and quality score."""
    if not CURRENT_DATA:
        load_or_generate_dataset("starter")

    customers = CURRENT_DATA["customers"]
    orders = CURRENT_DATA["orders"]
    memberships = CURRENT_DATA["segment_memberships"]
    outcomes = CURRENT_DATA["action_outcomes"]
    rules = CURRENT_DATA["segment_rules"]

    total_net_revenue = sum((Decimal(str(o["net_amount"])) for o in orders), Decimal("0.00"))
    total_refunds = sum((Decimal(str(o["refund_amount"])) for o in orders), Decimal("0.00"))

    # Segment counts
    rule_map = {r["rule_id"]: r["segment_name"] for r in rules}
    segment_counts = {}
    for m in memberships:
        name = rule_map.get(m["rule_id"], "Unknown")
        segment_counts[name] = segment_counts.get(name, 0) + 1

    # Dispatches & Guardrail suppression
    total_outcomes = len(outcomes)
    delivered = sum(1 for o in outcomes if o.get("delivery_status") == "DELIVERED")
    suppressed = sum(1 for o in outcomes if o.get("delivery_status") == "SUPPRESSED")
    conversions = sum(1 for o in outcomes if o.get("engagement_response") == "CONVERTED")
    conversion_rev = sum((Decimal(str(o["conversion_revenue"])) for o in outcomes if o.get("conversion_revenue")), Decimal("0.00"))

    return clean_json({
        "scale": DATA_SCALE,
        "kpis": {
            "total_customers": len(customers),
            "total_orders": len(orders),
            "total_net_revenue": total_net_revenue,
            "total_refunds": total_refunds,
            "total_events": len(CURRENT_DATA["engagement_events"]),
            "total_support_cases": len(CURRENT_DATA["support_cases"]),
            "total_recommendations": total_outcomes,
            "actions_delivered": delivered,
            "actions_suppressed_by_guardrails": suppressed,
            "suppression_rate_pct": round((suppressed / total_outcomes * 100), 2) if total_outcomes else 0,
            "total_conversions": conversions,
            "conversion_revenue": conversion_rev,
        },
        "segment_distribution": segment_counts,
    })


@app.get("/api/segments")
def get_segments():
    """Returns detailed segment rules, criteria thresholds, and membership analytics."""
    rules = CURRENT_DATA["segment_rules"]
    memberships = CURRENT_DATA["segment_memberships"]

    mems_by_rule: Dict[str, List[Dict[str, Any]]] = {}
    for m in memberships:
        mems_by_rule.setdefault(m["rule_id"], []).append(m)

    segments_data = []
    for r in rules:
        rid = r["rule_id"]
        mems = mems_by_rule.get(rid, [])
        count = len(mems)
        avg_spend = (
            sum(Decimal(str(m["monetary_net_spend"])) for m in mems) / count
            if count > 0 else Decimal("0.00")
        )
        avg_recency = (
            sum(m["recency_days"] for m in mems) / count
            if count > 0 else 0
        )
        avg_eng = (
            sum(Decimal(str(m["engagement_score"])) for m in mems) / count
            if count > 0 else Decimal("0.00")
        )

        segments_data.append({
            "rule_id": r["rule_id"],
            "segment_code": r["segment_code"],
            "segment_name": r["segment_name"],
            "criteria_description": r["criteria_description"],
            "criteria_json": json.loads(r["criteria_json"]) if isinstance(r["criteria_json"], str) else r["criteria_json"],
            "is_exclusive": r["is_exclusive"],
            "priority_rank": r["priority_rank"],
            "member_count": count,
            "avg_net_spend": round(avg_spend, 2),
            "avg_recency_days": round(avg_recency, 1),
            "avg_engagement_score": round(avg_eng, 1),
        })

    return clean_json(segments_data)


@app.get("/api/customers")
def get_customers(
    page: int = Query(1, ge=1),
    page_size: int = Query(15, ge=1, le=100),
    segment_code: Optional[str] = None,
    search: Optional[str] = None,
):
    """Returns paginated customer list with summary RFM metrics and assigned segments."""
    customers = CURRENT_DATA["customers"]
    memberships = CURRENT_DATA["segment_memberships"]
    rules = CURRENT_DATA["segment_rules"]
    rule_map = {r["rule_id"]: r for r in rules}

    # Index memberships by customer
    cust_mems: Dict[str, List[Dict[str, Any]]] = {}
    for m in memberships:
        cust_mems.setdefault(m["customer_id"], []).append(m)

    filtered = []
    for c in customers:
        cid = c["customer_id"]
        mems = cust_mems.get(cid, [])
        primary_mem = mems[0] if mems else {}
        rule_obj = rule_map.get(primary_mem.get("rule_id", ""), {})
        seg_code = rule_obj.get("segment_code", "UNKNOWN")
        seg_name = rule_obj.get("segment_name", "Unassigned")

        # Filtering
        if segment_code and seg_code != segment_code:
            continue
        if search:
            query = search.lower()
            if query not in cid.lower() and query not in c["email"].lower() and query not in f"{c['first_name']} {c['last_name']}".lower():
                continue

        filtered.append({
            "customer_id": cid,
            "name": f"{c['first_name']} {c['last_name']}",
            "email": c["email"],
            "lifecycle_stage": c["lifecycle_stage"],
            "status": c["status"],
            "signup_date": c["signup_date"],
            "segment_code": seg_code,
            "segment_name": seg_name,
            "recency_days": primary_mem.get("recency_days", 0),
            "frequency_count": primary_mem.get("frequency_count", 0),
            "monetary_net_spend": primary_mem.get("monetary_net_spend", Decimal("0.00")),
            "engagement_score": primary_mem.get("engagement_score", Decimal("0.00")),
            "explainability_notes": primary_mem.get("explainability_notes", ""),
        })

    total_count = len(filtered)
    start_idx = (page - 1) * page_size
    paged_records = filtered[start_idx : start_idx + page_size]

    return clean_json({
        "total": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": (total_count + page_size - 1) // page_size,
        "customers": paged_records,
    })


@app.get("/api/customers/{customer_id}")
def get_customer_detail(customer_id: str):
    """Detailed 360-degree customer profile with full explainability trace across all data sources."""
    cust = next((c for c in CURRENT_DATA["customers"] if c["customer_id"] == customer_id), None)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    orders = [o for o in CURRENT_DATA["orders"] if o["customer_id"] == customer_id]
    events = [e for e in CURRENT_DATA["engagement_events"] if e["customer_id"] == customer_id]
    cases = [c for c in CURRENT_DATA["support_cases"] if c["customer_id"] == customer_id]
    consents = [cn for cn in CURRENT_DATA["consents"] if cn["customer_id"] == customer_id]
    memberships = [m for m in CURRENT_DATA["segment_memberships"] if m["customer_id"] == customer_id]
    outcomes = [o for o in CURRENT_DATA["action_outcomes"] if o["customer_id"] == customer_id]

    # Evaluate dynamic explainability trace using SegmentationEngine
    seg_engine = SegmentationEngine(CURRENT_DATA["segment_rules"])
    eval_result = seg_engine.evaluate_customer(cust, orders, events, cases)

    return clean_json({
        "customer": cust,
        "orders": orders,
        "support_cases": cases,
        "consents": consents,
        "memberships": memberships,
        "recent_events": events[:20],
        "action_outcomes": outcomes,
        "segment_evaluation": eval_result,
    })


class RecommendationRequest(BaseModel):
    customer_id: str
    target_action_id: Optional[str] = None


@app.post("/api/recommend")
def test_recommendation(req: RecommendationRequest):
    """
    Live interactive workbench: Evaluates Next Best Action and policy guardrails
    (Consent verification, Support Friction check, Cooldown period) with real-time decision rationale.
    """
    cust_id = req.customer_id
    cust = next((c for c in CURRENT_DATA["customers"] if c["customer_id"] == cust_id), None)
    if not cust:
        raise HTTPException(status_code=404, detail="Customer not found")

    consents = [cn for cn in CURRENT_DATA["consents"] if cn["customer_id"] == cust_id]
    cases = [c for c in CURRENT_DATA["support_cases"] if c["customer_id"] == cust_id]
    prior_outcomes = [o for o in CURRENT_DATA["action_outcomes"] if o["customer_id"] == cust_id]
    memberships = [m for m in CURRENT_DATA["segment_memberships"] if m["customer_id"] == cust_id]
    rule_map = {r["rule_id"]: r["segment_code"] for r in CURRENT_DATA["segment_rules"]}

    current_seg_code = rule_map.get(memberships[0]["rule_id"], "HIGH_POTENTIAL") if memberships else "HIGH_POTENTIAL"

    rec_engine = RecommendationEngine(CURRENT_DATA["action_catalog"], CURRENT_DATA["segment_rules"])
    rec_result = rec_engine.recommend_for_customer(
        customer_id=cust_id,
        segment_code=current_seg_code,
        consents=consents,
        support_cases=cases,
        prior_outcomes=prior_outcomes,
    )

    return clean_json(rec_result)


@app.get("/api/anomalies")
def get_anomalies():
    """Returns anomaly detection benchmark, ground truth records, and detected discrepancies."""
    auditor = DataQualityAuditor(CURRENT_DATA)
    audit_results = auditor.run_full_audit()

    return clean_json({
        "audit_summary": {
            "primary_key_uniqueness": audit_results["primary_key_uniqueness"]["passed"],
            "foreign_key_integrity": audit_results["foreign_key_integrity"]["passed"],
            "enum_conformance": audit_results["enum_conformance"]["passed"],
            "date_ordering": audit_results["date_ordering"]["passed"],
            "arithmetic_reconciliation": audit_results["arithmetic_reconciliation"]["lines_reconciled"],
        },
        "benchmark_metrics": audit_results["anomaly_detection_metrics"],
        "ground_truth_records": CURRENT_DATA.get("ground_truth", []),
    })


@app.post("/api/dataset/reload")
def reload_dataset(scale: str = Query("starter", pattern="^(starter|full)$")):
    """Reloads or generates dataset with the specified scale parameter."""
    load_or_generate_dataset(scale=scale)
    return {"status": "success", "scale": scale, "customer_count": len(CURRENT_DATA["customers"])}


# Mount static assets
static_dir = os.path.join(os.path.dirname(__file__), "static")
os.makedirs(static_dir, exist_ok=True)
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def serve_dashboard():
    """Serves the main single page dashboard."""
    index_path = os.path.join(static_dir, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse({"message": "YottaFlex AI API is running. UI assets loading."})
