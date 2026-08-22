from trashport.chatbot.services.llm_client import LLMClient


def test_llm_client_fallback():
    client = LLMClient()
    resp = client.generate_response("System prompt", "User query")
    assert resp is None or isinstance(resp, str)
