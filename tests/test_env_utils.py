import os
import tempfile
import unittest
from pathlib import Path

from src.env_utils import EnvFilePermissionError, ensure_secure_env_permissions, resolve_env_path


class EnvUtilsTests(unittest.TestCase):
    def test_resolve_env_path_expanduser(self) -> None:
        path = resolve_env_path("~/tmp/secrets.env")
        self.assertTrue(str(path).startswith(str(Path.home())))

    def test_permission_600_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "secrets.env"
            env_path.write_text("A=1\n", encoding="utf-8")
            os.chmod(env_path, 0o600)
            ensure_secure_env_permissions(env_path)

    def test_permission_not_600_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            env_path = Path(tmp) / "secrets.env"
            env_path.write_text("A=1\n", encoding="utf-8")
            os.chmod(env_path, 0o644)
            with self.assertRaises(EnvFilePermissionError):
                ensure_secure_env_permissions(env_path)


if __name__ == "__main__":
    unittest.main()
