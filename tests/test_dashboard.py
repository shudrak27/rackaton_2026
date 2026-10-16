from pathlib import Path

import pytest

DATA = Path(__file__).resolve().parents[1] / "reports" / "ui" / "data.json"


@pytest.mark.skipif(not DATA.exists(), reason="run `python -m screening export-ui` first")
def test_dashboard_renders_all_tabs_without_errors():
    pytest.importorskip("streamlit")
    pytest.importorskip("plotly")
    from streamlit.testing.v1 import AppTest

    at = AppTest.from_file(str(DATA.parents[2] / "app" / "dashboard.py"), default_timeout=120).run()
    assert not at.exception and not at.error
    assert len(at.tabs) == 5
