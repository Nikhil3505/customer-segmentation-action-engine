"""
Unit and integration tests for Synthetic Data Generator.
"""

import re
import pytest
from src.generator.synthetic_engine import SyntheticDataGenerator


@pytest.fixture(scope="module")
def starter_dataset():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter", inject_anomalies=True)
    return gen.generate_all()


def test_generator_counts(starter_dataset):
    assert len(starter_dataset["customers"]) == 1000
    assert len(starter_dataset["products"]) == 20
    assert len(starter_dataset["orders"]) == 4000
    assert len(starter_dataset["order_lines"]) > 4000
    assert len(starter_dataset["engagement_events"]) == 20000
    assert len(starter_dataset["support_cases"]) == 500
    assert len(starter_dataset["consents"]) == 4000
    assert len(starter_dataset["segment_rules"]) == 5
    assert len(starter_dataset["action_catalog"]) == 5
    assert len(starter_dataset["ground_truth"]) == 20


def test_id_nomenclature_conventions(starter_dataset):
    # Customer: CUS-000001
    cus_regex = re.compile(r"^CUS-\d{6}$")
    for c in starter_dataset["customers"][:100]:
        assert cus_regex.match(c["customer_id"])

    # Product: PRD-000001
    prd_regex = re.compile(r"^PRD-\d{6}$")
    for p in starter_dataset["products"]:
        assert prd_regex.match(p["product_id"])

    # Order: ORD-2026-000001
    ord_regex = re.compile(r"^ORD-\d{4}-\d{6}$")
    for o in starter_dataset["orders"][:100]:
        assert ord_regex.match(o["order_id"])

    # OrderLine: LIN-ORD-2026-000001-01
    line_regex = re.compile(r"^LIN-ORD-\d{4}-\d{6}-\d{2}$")
    for l in starter_dataset["order_lines"][:100]:
        assert line_regex.match(l["order_line_id"])

    # Segment: SEG-2026-000001
    seg_regex = re.compile(r"^SEG-\d{4}-\d{6}$")
    for s in starter_dataset["segment_rules"]:
        assert seg_regex.match(s["rule_id"])

    # Membership: MEM-SEG-2026-000001-CUS-000001
    mem_regex = re.compile(r"^MEM-SEG-\d{4}-\d{6}-CUS-\d{6}$")
    for m in starter_dataset["segment_memberships"][:100]:
        assert mem_regex.match(m["membership_id"])

    # Action: ACTN-2026-000001
    act_regex = re.compile(r"^ACTN-\d{4}-\d{6}$")
    for a in starter_dataset["action_catalog"]:
        assert act_regex.match(a["action_id"])


def test_master_data_foreign_key_references(starter_dataset):
    customer_ids = {c["customer_id"] for c in starter_dataset["customers"]}
    product_ids = {p["product_id"] for p in starter_dataset["products"]}
    order_ids = {o["order_id"] for o in starter_dataset["orders"]}

    for o in starter_dataset["orders"]:
        assert o["customer_id"] in customer_ids

    for l in starter_dataset["order_lines"]:
        assert l["order_id"] in order_ids
        assert l["product_id"] in product_ids

    for e in starter_dataset["engagement_events"]:
        assert e["customer_id"] in customer_ids

    for c in starter_dataset["support_cases"]:
        assert c["customer_id"] in customer_ids
