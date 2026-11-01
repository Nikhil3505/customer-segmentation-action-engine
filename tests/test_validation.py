"""
Unit and integration tests for Data Quality Auditor and Ground Truth Benchmarking.
"""

import pytest
from src.generator.synthetic_engine import SyntheticDataGenerator
from src.validation.auditor import DataQualityAuditor


@pytest.fixture(scope="module")
def audited_data():
    gen = SyntheticDataGenerator(seed=20261022, scale="starter", inject_anomalies=True)
    return gen.generate_all()


def test_validation_integrity_checks(audited_data):
    auditor = DataQualityAuditor(audited_data)
    results = auditor.run_full_audit()

    assert results["primary_key_uniqueness"]["passed"] is True
    assert results["foreign_key_integrity"]["passed"] is True
    assert results["enum_conformance"]["passed"] is True
    assert results["date_ordering"]["passed"] is True
    assert results["arithmetic_reconciliation"]["lines_reconciled"] is True


def test_ground_truth_anomaly_detection_benchmark(audited_data):
    auditor = DataQualityAuditor(audited_data)
    results = auditor.run_full_audit()

    metrics = results["anomaly_detection_metrics"]["overall_metrics"]
    assert metrics["total_ground_truth_anomalies"] == 20
    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1_score"] == 1.0

    by_cat = results["anomaly_detection_metrics"]["by_category"]
    assert by_cat["conflicting_exclusive_segments"]["true_positives"] == 5
    assert by_cat["action_violates_consent"]["true_positives"] == 5
    assert by_cat["return_not_netted_from_spend"]["true_positives"] == 5
    assert by_cat["outcome_attributed_to_wrong_action"]["true_positives"] == 5
