"""
Integration test verifying Step 10 reproducibility.
"""

from verify_reproducibility import verify_reproducibility


def test_reproducibility_step10():
    success = verify_reproducibility(seed=20261022, scale="starter")
    assert success is True
