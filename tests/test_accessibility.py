def test_skip_link_present(client, login_admin):
    resp = client.get('/dashboard')
    html = resp.data.decode('utf-8')
    assert 'class="skip-link"' in html
    assert 'href="#main-content"' in html


def test_main_element_has_id(client, login_admin):
    resp = client.get('/dashboard')
    html = resp.data.decode('utf-8')
    assert 'id="main-content"' in html


def test_nav_has_aria_label(client, login_admin):
    resp = client.get('/dashboard')
    html = resp.data.decode('utf-8')
    assert 'aria-label="メインメニュー"' in html


def test_flash_messages_use_aria_live(client):
    # Trigger a flash via login failure
    resp = client.post('/login', data={'username': 'nope', 'password': 'nope'}, follow_redirects=True)
    html = resp.data.decode('utf-8')
    assert 'aria-live="polite"' in html


def test_404_template_used(client):
    resp = client.get('/definitely-not-a-real-route')
    assert resp.status_code == 404
    html = resp.data.decode('utf-8')
    assert 'ページが見つかりません' in html
    # Ensure it extends base.html (skip link appears)
    assert 'class="skip-link"' in html
