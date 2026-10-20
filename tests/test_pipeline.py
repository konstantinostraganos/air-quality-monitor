import os

from dotenv import load_dotenv

from pipeline import OpenAQClient

load_dotenv()


def test_client_initialization():
    """Test that the API client initializes correctly."""
    api_key = os.getenv("OPENAQ_API_KEY", "test_key")
    client = OpenAQClient(api_key)
    assert client.session is not None
    assert "X-API-Key" in client.session.headers
