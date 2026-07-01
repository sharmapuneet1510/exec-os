import os
import tempfile
from web.routers.settings import _set_env_var, _sqlite_url_for


def test_set_env_var_updates_existing_key():
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
        f.write("PORT=8080\nDATABASE_URL=sqlite:////old/path.db\n# comment\n")
        path = f.name
    _set_env_var(path, "DATABASE_URL", "sqlite:////new/path.db")
    content = open(path).read()
    assert "DATABASE_URL=sqlite:////new/path.db" in content
    assert "sqlite:////old/path.db" not in content
    assert "PORT=8080" in content          # other keys preserved
    assert "# comment" in content          # comments preserved
    os.unlink(path)


def test_set_env_var_appends_when_missing():
    with tempfile.NamedTemporaryFile("w", suffix=".env", delete=False) as f:
        f.write("PORT=8080\n")
        path = f.name
    _set_env_var(path, "DATABASE_URL", "sqlite:////x.db")
    content = open(path).read()
    assert "PORT=8080" in content
    assert "DATABASE_URL=sqlite:////x.db" in content
    os.unlink(path)


def test_sqlite_url_for_absolute_path():
    assert _sqlite_url_for("/Users/me/data/execos.db") == "sqlite:////Users/me/data/execos.db"
