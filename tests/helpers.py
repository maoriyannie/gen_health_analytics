"""Shared helpers for Playwright interactions with the Streamlit app."""

from playwright.sync_api import Page, expect

STREAMLIT_TIMEOUT = 8000  # ms


def add_family_member(page: Page, relationship: str, sex: str, conditions: list[dict]):
    """
    Click '+ Add family member', fill in relationship/sex, then add each condition.

    conditions: list of {"name": str, "onset": int | None}
    """
    page.get_by_role("button", name="+ Add family member").click()
    page.wait_for_timeout(600)

    # Open the last expander (the newly added member)
    expanders = page.locator("[data-testid='stExpander']")
    last = expanders.last
    last.click()
    page.wait_for_timeout(400)

    # Relationship selectbox
    rel_select = last.get_by_label("Relationship")
    rel_select.select_option(relationship)

    # Sex selectbox
    sex_select = last.get_by_label("Sex")
    sex_select.select_option(sex)

    for cond in conditions:
        cond_select = last.get_by_label("Add condition")
        cond_select.select_option(cond["name"])
        if cond.get("onset"):
            onset_input = last.get_by_label("Age onset")
            onset_input.fill(str(cond["onset"]))
        last.get_by_role("button", name="+ Add").click()
        page.wait_for_timeout(400)


def run_analysis(page: Page):
    """Click the primary Analyse button and wait for results to render."""
    page.get_by_role("button", name="Analyse Family History").click()
    # Wait for the Risk Gauges tab to appear — signals analysis is complete
    expect(page.get_by_role("tab", name="Risk Gauges")).to_be_visible(
        timeout=STREAMLIT_TIMEOUT
    )
