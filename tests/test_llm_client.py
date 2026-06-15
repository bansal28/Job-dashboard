from server import llm_client


def test_auto_provider_prefers_openai_when_both_keys_exist(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "auto")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GROQ_API_KEY", "gsk-test")

    assert llm_client.get_llm_provider() == "openai"


def test_explicit_provider_requires_matching_key(monkeypatch):
    monkeypatch.setenv("LLM_PROVIDER", "groq")
    monkeypatch.setenv("OPENAI_API_KEY", "sk-test")
    monkeypatch.setenv("GROQ_API_KEY", "")

    assert llm_client.get_llm_provider() == ""


def test_extract_openai_text_from_responses_api_payload():
    payload = {
        "output": [
            {
                "content": [
                    {"type": "output_text", "text": "Generated text"},
                ]
            }
        ]
    }

    assert llm_client._extract_openai_text(payload) == "Generated text"
