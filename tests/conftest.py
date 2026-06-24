"""
conftest.py — Pytest fixtures for Gen-Health Analytics Playwright tests.

Assumes the Streamlit app is already running on localhost:8501.
Start it with:  pipenv run streamlit run app.py
Then run tests: pipenv run pytest tests/ -v
"""

import pytest
from playwright.sync_api import Page, expect

BASE_URL = "http://localhost:8501"


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args):
    """Shared browser context — widen viewport for the wide Streamlit layout."""
    return {**browser_context_args, "viewport": {"width": 1400, "height": 900}}


@pytest.fixture
def app(page: Page):
    """
    Navigate to the app and wait until the main title is visible.
    Returns the Page object ready for interaction.
    """
    page.goto(BASE_URL)
    expect(page.get_by_role("heading", name="Gen-Health Analytics")).to_be_visible(
        timeout=15000
    )
    return page
