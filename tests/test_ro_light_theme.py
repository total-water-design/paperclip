from app import app


def test_ro_response_is_light_only_without_theme_controls():
    with app.test_client() as client:
        response = client.get('/ro')

    html = response.get_data(as_text=True)
    assert response.status_code == 200
    assert '<html lang="en" data-theme="light">' in html
    assert '<meta name="color-scheme" content="light">' in html
    assert '<meta name="theme-color" content="#f5f8fc">' in html
    assert 'id="themeSelect"' not in html
    assert 'class="theme-control"' not in html


def test_ro_javascript_has_no_theme_initialization_or_persistence():
    with app.test_client() as client:
        response = client.get('/static/app.js')

    javascript = response.get_data(as_text=True)
    assert response.status_code == 200
    assert 'totalrodesign-theme' not in javascript
    assert 'calcospower-theme' not in javascript
    assert 'applyTheme' not in javascript
    assert 'initTheme' not in javascript
    assert 'themeSelect' not in javascript
