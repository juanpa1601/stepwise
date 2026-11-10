"""CA-I1: ninguna ruta versionada supera 72 caracteres.

`marketplace add` clona el repo completo; en Windows, con la configuración
en una ruta profunda, una ruta larga falla con `Filename too long`.
"""

import subprocess
import unittest
from pathlib import Path

MAX_LEN = 72
REPO_ROOT = Path(__file__).resolve().parent.parent


def tracked_paths():
    out = subprocess.run(
        ["git", "-c", "core.quotepath=false", "ls-files", "-z"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    ).stdout
    return [p for p in out.split("\0") if p]


class PathLengthTest(unittest.TestCase):
    def test_no_tracked_path_exceeds_limit(self):
        paths = tracked_paths()
        self.assertTrue(paths, "git ls-files no devolvió rutas")
        too_long = [f"{len(p)} {p}" for p in paths if len(p) > MAX_LEN]
        self.assertEqual(
            too_long, [], f"rutas de más de {MAX_LEN} caracteres"
        )


if __name__ == "__main__":
    unittest.main()
