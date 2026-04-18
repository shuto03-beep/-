def test_create_app_registers_all_blueprints(app):
    expected = {'auth', 'dashboard', 'calendar', 'reservations', 'blocks', 'admin', 'notifications'}
    assert expected <= set(app.blueprints.keys())


def test_home_redirects_when_anonymous(client):
    resp = client.get('/', follow_redirects=False)
    assert resp.status_code in (301, 302)


def test_missing_secret_key_raises(monkeypatch):
    import importlib
    import app.config as config_module

    monkeypatch.delenv('SECRET_KEY', raising=False)
    with __import__('pytest').raises(RuntimeError):
        importlib.reload(config_module)

    # Restore for subsequent tests
    monkeypatch.setenv('SECRET_KEY', 'test-secret-key')
    importlib.reload(config_module)
