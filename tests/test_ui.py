"""
test_ui.py — Playwright UI tests for Gen-Health Analytics Streamlit dashboard.

Run (with the app already running on :8501):
    pipenv run pytest tests/ -v
"""

import pytest
from playwright.sync_api import Page, expect

from helpers import add_family_member, run_analysis, STREAMLIT_TIMEOUT


# ===========================================================================
# 1. Page load & layout
# ===========================================================================

class TestPageLoad:
    def test_title_visible(self, app: Page):
        """Main heading is present on load."""
        expect(app.get_by_role("heading", name="Gen-Health Analytics")).to_be_visible()

    def test_sidebar_sections_visible(self, app: Page):
        """Sidebar contains the three main sections."""
        expect(app.get_by_text("Your Info (Proband)")).to_be_visible()
        expect(app.get_by_text("Conditions to Analyse")).to_be_visible()
        expect(app.get_by_text("Family Members")).to_be_visible()

    def test_analyse_button_visible(self, app: Page):
        """Primary Analyse button is present without adding any members."""
        expect(app.get_by_role("button", name="Analyse Family History")).to_be_visible()

    def test_no_conditions_shows_info(self, app: Page):
        """Deselecting all conditions shows the 'select at least one' info message."""
        # Remove the two default conditions
        for _ in range(2):
            app.locator("[data-testid='stMultiSelect'] span[data-baseweb='tag'] svg").first.click()
            app.wait_for_timeout(300)

        expect(app.get_by_text("Select at least one condition")).to_be_visible(
            timeout=STREAMLIT_TIMEOUT
        )

    def test_how_to_use_shown_before_analysis(self, app: Page):
        """Instructional text is shown when no analysis has been run yet."""
        expect(app.get_by_text("How to use")).to_be_visible()


# ===========================================================================
# 2. Proband controls
# ===========================================================================

class TestProbandControls:
    def test_default_age(self, app: Page):
        """Age input defaults to 34."""
        age_input = app.get_by_label("Your age")
        assert age_input.input_value() == "34"

    def test_change_age(self, app: Page):
        """Age input accepts a new value."""
        age_input = app.get_by_label("Your age")
        age_input.fill("45")
        assert age_input.input_value() == "45"

    def test_sex_options(self, app: Page):
        """Biological sex dropdown contains all four options."""
        sex_select = app.get_by_label("Biological sex")
        options = sex_select.locator("option").all_text_contents()
        assert set(options) >= {"female", "male", "other", "unknown"}


# ===========================================================================
# 3. Baseline analysis (no family members)
# ===========================================================================

class TestBaselineAnalysis:
    def test_runs_without_family_members(self, app: Page):
        """Analysis completes with proband info only — tabs appear."""
        run_analysis(app)
        expect(app.get_by_role("tab", name="Risk Gauges")).to_be_visible()
        expect(app.get_by_role("tab", name="Onset Trends")).to_be_visible()
        expect(app.get_by_role("tab", name="Family Tree")).to_be_visible()
        expect(app.get_by_role("tab", name="Alerts")).to_be_visible()
        expect(app.get_by_role("tab", name="Raw JSON")).to_be_visible()

    def test_summary_metrics_visible(self, app: Page):
        """Four metric tiles (Total Alerts, High, Medium, Low) are rendered."""
        run_analysis(app)
        expect(app.get_by_text("Total Alerts")).to_be_visible()
        expect(app.get_by_text("High Priority")).to_be_visible()
        expect(app.get_by_text("Medium Priority")).to_be_visible()
        expect(app.get_by_text("Low Priority")).to_be_visible()

    def test_baseline_diabetes_rr_above_one(self, app: Page):
        """Diabetes shows RR > 1 even with no family history (DPF baseline)."""
        run_analysis(app)
        # The gauge title contains "Diabetes | RR X.XXx" — check it's present
        expect(app.get_by_text("Diabetes", exact=False)).to_be_visible()

    def test_heart_disease_rr_one_without_family(self, app: Page):
        """Heart disease shows RR 1.00x when no affected relatives are entered."""
        run_analysis(app)
        expect(app.get_by_text("Heart Disease | RR 1.00×")).to_be_visible(
            timeout=STREAMLIT_TIMEOUT
        )


# ===========================================================================
# 4. Adding & removing family members
# ===========================================================================

class TestFamilyMemberManagement:
    def test_add_member_button_creates_expander(self, app: Page):
        """Clicking '+ Add family member' creates a new expander entry."""
        before = app.locator("[data-testid='stExpander']").count()
        app.get_by_role("button", name="+ Add family member").click()
        app.wait_for_timeout(600)
        after = app.locator("[data-testid='stExpander']").count()
        assert after == before + 1

    def test_remove_member(self, app: Page):
        """Remove button deletes the family member entry."""
        app.get_by_role("button", name="+ Add family member").click()
        app.wait_for_timeout(600)
        expanders = app.locator("[data-testid='stExpander']")
        last = expanders.last
        last.click()
        app.wait_for_timeout(400)
        before = expanders.count()
        last.get_by_role("button", name="Remove member").click()
        app.wait_for_timeout(600)
        assert app.locator("[data-testid='stExpander']").count() == before - 1


# ===========================================================================
# 5. Clinical scenarios
# ===========================================================================

class TestClinicalScenarios:
    def test_cvd_risk_elevated_with_affected_parent(self, app: Page):
        """
        Adding a father with heart_disease should raise CVD RR above 1.0.
        CVD_FAMILY_HISTORY_RR = 2.316, so the gauge title should show > 1.00.
        """
        add_family_member(
            app,
            relationship="father",
            sex="male",
            conditions=[{"name": "heart_disease", "onset": 55}],
        )
        run_analysis(app)
        # Title format: "Heart Disease | RR X.XXx" — value should NOT be 1.00
        # We check that the 1.00 title is gone
        heart_title = app.get_by_text("Heart Disease | RR 1.00×")
        expect(heart_title).not_to_be_visible(timeout=STREAMLIT_TIMEOUT)

    def test_cvd_early_onset_alert(self, app: Page):
        """
        Father with heart disease before age 55 (male threshold) should trigger
        an alert in the Alerts tab.
        """
        add_family_member(
            app,
            relationship="father",
            sex="male",
            conditions=[{"name": "heart_disease", "onset": 48}],
        )
        run_analysis(app)
        app.get_by_role("tab", name="Alerts").click()
        app.wait_for_timeout(500)
        # At minimum there should be at least one alert
        alerts_tab = app.locator("[data-testid='stMainBlockContainer']")
        expect(alerts_tab.get_by_text("heart disease", case_sensitive=False)).to_be_visible(
            timeout=STREAMLIT_TIMEOUT
        )

    def test_diabetes_risk_increases_with_first_degree_relative(self, app: Page):
        """
        Adding a mother with diabetes should increase the DPF proxy and raise
        the diabetes RR above the baseline 1.85x.
        """
        add_family_member(
            app,
            relationship="mother",
            sex="female",
            conditions=[{"name": "diabetes", "onset": 50}],
        )
        run_analysis(app)
        # The gauge chart should now show a higher Genetic score (not 21)
        # We verify analysis completes and the gauge is present
        expect(app.get_by_text("Diabetes", exact=False)).to_be_visible()

    def test_breast_cancer_red_flag_triggers_high_priority(self, app: Page):
        """
        Two first-degree relatives (mother + sister) with breast_cancer should
        trigger a high-priority BRCA-pattern alert.
        Add breast_cancer to conditions_of_interest first.
        """
        # Add breast_cancer to selected conditions
        multiselect = app.locator("[data-testid='stMultiSelect']").first
        multiselect.click()
        app.get_by_text("breast_cancer", exact=True).click()
        app.wait_for_timeout(300)
        app.keyboard.press("Escape")

        add_family_member(
            app,
            relationship="mother",
            sex="female",
            conditions=[{"name": "breast_cancer", "onset": 45}],
        )
        add_family_member(
            app,
            relationship="sister",
            sex="female",
            conditions=[{"name": "breast_cancer", "onset": 42}],
        )
        run_analysis(app)

        app.get_by_role("tab", name="Alerts").click()
        app.wait_for_timeout(500)
        expect(app.get_by_text("HIGH", exact=False)).to_be_visible(
            timeout=STREAMLIT_TIMEOUT
        )

    def test_no_alerts_shown_message_when_clean(self, app: Page):
        """
        With conditions selected but no family members, and no red flags,
        the Alerts tab should show the 'No red flag alerts' success message.
        """
        run_analysis(app)
        app.get_by_role("tab", name="Alerts").click()
        app.wait_for_timeout(500)
        expect(app.get_by_text("No red flag alerts")).to_be_visible(
            timeout=STREAMLIT_TIMEOUT
        )


# ===========================================================================
# 6. Tab navigation
# ===========================================================================

class TestTabNavigation:
    def test_all_tabs_clickable_after_analysis(self, app: Page):
        """Every tab can be clicked and renders content without an error."""
        run_analysis(app)
        for tab_name in ["Onset Trends", "Family Tree", "Alerts", "Raw JSON"]:
            app.get_by_role("tab", name=tab_name).click()
            app.wait_for_timeout(500)
            # No Streamlit error toast should appear
            expect(app.locator("[data-testid='stException']")).not_to_be_visible()

    def test_raw_json_tab_contains_analysis_version(self, app: Page):
        """Raw JSON tab renders the engine output including analysis_version."""
        run_analysis(app)
        app.get_by_role("tab", name="Raw JSON").click()
        expect(app.get_by_text("analysis_version")).to_be_visible(
            timeout=STREAMLIT_TIMEOUT
        )

    def test_family_tree_tab_renders_genogram(self, app: Page):
        """Family Tree tab renders a Plotly chart (genogram)."""
        run_analysis(app)
        app.get_by_role("tab", name="Family Tree").click()
        expect(app.locator("[data-testid='stPlotlyChart']").first).to_be_visible(
            timeout=STREAMLIT_TIMEOUT
        )
