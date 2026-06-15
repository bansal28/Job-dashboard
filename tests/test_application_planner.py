import sys
from pathlib import Path

SERVER_DIR = Path(__file__).resolve().parent.parent / "server"
sys.path.insert(0, str(SERVER_DIR))

from application_planner import _flatten_greenhouse_questions, _greenhouse_parts  # noqa: E402


def test_greenhouse_parts_parse_internal_job_id():
    token, post_id = _greenhouse_parts({"id": "gh_acme_12345", "url": ""})

    assert token == "acme"
    assert post_id == "12345"


def test_flatten_greenhouse_questions_includes_required_fields():
    questions = _flatten_greenhouse_questions({
        "questions": [
            {
                "label": "First Name",
                "required": True,
                "fields": [{"name": "first_name", "type": "input_text"}],
            }
        ],
        "location_questions": [
            {
                "label": "Location",
                "required": False,
                "fields": [{"name": "location", "type": "input_text"}],
            }
        ],
    })

    assert questions[0]["label"] == "First Name"
    assert questions[0]["required"] is True
    assert questions[0]["fields"][0]["type"] == "input_text"
    assert questions[1]["source"] == "location_questions"
