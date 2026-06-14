from server.grounding import enforce_grounding


def test_grounding_guard_removes_unsupported_candidate_claims():
    report = enforce_grounding(
        "I trained TensorFlow models. I founded a quantum computing lab at Google.",
        ["Trained TensorFlow models behind an async FastAPI service and React dashboard."],
    )

    assert not report.passed
    assert "I trained TensorFlow models." in report.grounded_letter
    assert "quantum computing" not in report.grounded_letter
    assert report.unsupported_claims == ["I founded a quantum computing lab at Google."]


def test_grounding_guard_allows_generic_application_sentences():
    report = enforce_grounding(
        "I am excited about the role. Thank you for your time and consideration.",
        [],
    )

    assert report.passed
    assert report.unsupported_claims == []
