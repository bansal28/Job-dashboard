import sys
from pathlib import Path


SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
if str(SERVER_DIR) not in sys.path:
    sys.path.insert(0, str(SERVER_DIR))

from match_engine import _estimate_experience, _role_cap  # noqa: E402


def test_experience_estimator_accepts_years_building_phrase():
    assert _estimate_experience("software engineer with 2+ years building production apps") == 2.0


def test_role_cap_limits_non_technical_business_roles():
    cap = _role_cap(
        {"title": "Global Director of Partnerships"},
        {"years_experience": 2},
    )

    assert cap == 35


def test_role_cap_limits_senior_roles_for_early_career_profile():
    cap = _role_cap(
        {"title": "Senior Machine Learning Engineer"},
        {"years_experience": 2},
    )

    assert cap == 45
