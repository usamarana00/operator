def test_productivity_routes_are_registered():
    from main import app

    paths = {route.path for route in app.routes}

    assert "/briefing" in paths
    assert "/proposal" in paths
    assert "/proposal/{session_id}/pdf" in paths
