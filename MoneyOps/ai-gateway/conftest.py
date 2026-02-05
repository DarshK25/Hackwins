"""
Pytest configuration for AI Gateway tests
"""
import os
import pytest


@pytest.fixture(scope="session", autouse=True)
def setup_test_environment():
    """
    Set up test environment variables before any tests run.
    This ensures Settings can be instantiated even without a .env file.
    """
    # Set default test environment variables if not already set
    test_env_vars = {
        "GROQ_API_KEY": "test-groq-api-key",
        "ANTHROPIC_API_KEY": "test-anthropic-api-key",
        "BACKEND_BASE_URL": "http://localhost:8000",
        "REDIS_HOST": "localhost",
        "REDIS_PORT": "6379",
        "JWT_SECRET_KEY": "test-secret-key",
        "ENVIRONMENT": "test",
    }
    
    for key, value in test_env_vars.items():
        if key not in os.environ:
            os.environ[key] = value
    
    yield
    
    # Cleanup is optional since these are just test values
    # but you can uncomment if needed:
    # for key in test_env_vars:
    #     os.environ.pop(key, None)


@pytest.fixture
def mock_settings():
    """
    Fixture to provide a mock settings object for tests.
    Use this when you need to override specific settings in a test.
    """
    from app.config import Settings
    return Settings()
