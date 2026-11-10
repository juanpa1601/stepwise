"""Bloques compartidos entre skills y agentes (ADR skill-shared-blocks).

Un bloque repetido a propósito en varias skills se envuelve con
`<!-- shared:<id> -->` ... `<!-- /shared:<id> -->`. Este test falla si las
copias de un `<id>` dejan de ser idénticas (sin contar los espacios al final
de línea), si un marcador no tiene pareja, si los marcadores se anidan o
solapan, o si un `<id>` aparece en un solo archivo.
"""

import re
import unittest
from collections import defaultdict
from pathlib import Path
from typing import NamedTuple

REPO_ROOT = Path(__file__).resolve().parent.parent
PATTERNS = (
    "plugins/stepwise/skills/*/SKILL.md",
    "plugins/stepwise/agents/*.md",
)
REQUIRED_IDS = {
    "project-commands",
    "test-runner-foreground",
    "git-rules",
    "push-https",
}
MARKER = re.compile(r"<!-- (/?)shared:([a-z0-9-]+) -->")
NO_NESTING = "los bloques compartidos no se anidan ni se solapan"


class Copy(NamedTuple):
    id: str
    path: str
    line: int
    content: str


def _normalize(text: str) -> str:
    return "\n".join(line.rstrip(" \t") for line in text.split("\n"))


def _content(raw: str) -> str:
    """Texto de una copia: sin espacios finales ni los saltos de los marcadores.

    No cuentan el salto justo después de un marcador que abre al final de su
    línea ni el que va justo antes de un marcador que cierra al inicio de la
    suya (su sangría ya la quitó `_normalize`).
    """
    text = _normalize(raw)
    if text.startswith("\n"):
        text = text[1:]
    if text.endswith("\n"):
        text = text[:-1]
    return text


def _line_of(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _parse(path: str, text: str, errors: list[str]) -> list[Copy]:
    """Copias de un archivo.

    Ante un error de estructura lo anota y sigue leyendo: un cierre suelto se
    salta, y un anidamiento o un cierre de otro id descarta el bloque abierto.
    """
    copies: list[Copy] = []
    open_id, open_line, open_end = None, 0, 0
    for match in MARKER.finditer(text):
        closing, block_id = match.group(1) == "/", match.group(2)
        line = _line_of(text, match.start())
        if not closing:
            if open_id is not None:
                errors.append(
                    f"shared:{block_id} abre en {path}:{line} dentro de "
                    f"shared:{open_id} ({path}:{open_line}): {NO_NESTING}"
                )
            open_id, open_line, open_end = block_id, line, match.end()
        elif open_id is None:
            errors.append(
                f"shared:{block_id} cierra en {path}:{line} sin haber abierto"
            )
        elif open_id != block_id:
            errors.append(
                f"shared:{block_id} cierra en {path}:{line} con "
                f"shared:{open_id} abierto ({path}:{open_line}): {NO_NESTING}"
            )
            open_id = None
        else:
            content = _content(text[open_end:match.start()])
            copies.append(Copy(block_id, path, open_line, content))
            open_id = None
    if open_id is not None:
        errors.append(f"shared:{open_id} abre en {path}:{open_line} y no cierra")
    return copies


def check_shared_blocks(files: dict[str, str]) -> tuple[list[str], set[str]]:
    """Devuelve (errores, ids encontrados) para `{ruta: texto}`."""
    if not files:
        return ["no se encontraron archivos de skills ni de agentes"], set()
    errors: list[str] = []
    by_id: dict[str, list[Copy]] = defaultdict(list)
    for path, text in files.items():
        for copy in _parse(path, text, errors):
            by_id[copy.id].append(copy)
    if not by_id and not errors:
        errors.append(
            f"ningún bloque compartido en los {len(files)} archivos leídos"
        )
    for block_id, copies in sorted(by_id.items()):
        paths = sorted({c.path for c in copies})
        if len(paths) == 1:
            errors.append(
                f"shared:{block_id} aparece solo en {paths[0]}: un bloque "
                "compartido necesita copias en dos archivos o más"
            )
            continue
        variants: dict[str, list[Copy]] = {}
        for copy in copies:
            variants.setdefault(copy.content, []).append(copy)
        if len(variants) > 1:
            listed = "; ".join(
                f"versión {i}: "
                + ", ".join(f"{c.path}:{c.line}" for c in group)
                for i, group in enumerate(variants.values(), start=1)
            )
            errors.append(
                f"shared:{block_id} tiene {len(variants)} versiones "
                f"distintas ({listed})"
            )
    return errors, set(by_id)


def repo_files() -> dict[str, str]:
    files: dict[str, str] = {}
    for pattern in PATTERNS:
        for path in sorted(REPO_ROOT.glob(pattern)):
            rel = path.relative_to(REPO_ROOT).as_posix()
            files[rel] = path.read_text(encoding="utf-8")
    return files


def block(block_id: str, body: str) -> str:
    return f"<!-- shared:{block_id} -->\n{body}\n<!-- /shared:{block_id} -->"


class CheckSharedBlocksTest(unittest.TestCase):
    def test_identical_except_trailing_whitespace(self) -> None:
        """CA-1"""
        files = {
            "a.md": "intro\n" + block("x", "uno  \n  dos\t\ntres"),
            "b.md": block("x", "uno\n  dos\ntres   ") + "\nfin\n",
        }
        errors, ids = check_shared_blocks(files)
        self.assertEqual(errors, [])
        self.assertEqual(ids, {"x"})

    def test_different_copy_names_id_and_files(self) -> None:
        """CA-2"""
        files = {
            "a.md": block("x", "texto"),
            "b.md": "\n\n" + block("x", "texto"),
            "c.md": "\n" + block("x", "otro texto"),
        }
        errors, _ = check_shared_blocks(files)
        self.assertEqual(len(errors), 1)
        self.assertIn("shared:x", errors[0])
        self.assertIn("versión 1: a.md:1, b.md:3", errors[0])
        self.assertIn("versión 2: c.md:2", errors[0])

    def test_unclosed_marker(self) -> None:
        """CA-3: abre sin cerrar"""
        files = {
            "a.md": block("x", "texto"),
            "b.md": block("x", "texto"),
            "c.md": "uno\n<!-- shared:y -->\ntexto\n",
        }
        errors, _ = check_shared_blocks(files)
        self.assertEqual(errors, ["shared:y abre en c.md:2 y no cierra"])

    def test_closing_without_opening(self) -> None:
        """CA-3: cierra sin abrir"""
        files = {
            "a.md": block("x", "texto") + "\n<!-- /shared:y -->",
            "b.md": block("x", "texto"),
        }
        errors, _ = check_shared_blocks(files)
        self.assertEqual(
            errors, ["shared:y cierra en a.md:4 sin haber abierto"]
        )

    def test_keeps_reading_after_structure_error(self) -> None:
        """CA-3 y regla 3: junta todos los errores de un archivo"""
        files = {
            "a.md": "<!-- /shared:y -->\n"
            + block("x", "texto")
            + "\n<!-- /shared:z -->",
            "b.md": block("x", "texto"),
        }
        errors, ids = check_shared_blocks(files)
        self.assertEqual(
            errors,
            [
                "shared:y cierra en a.md:1 sin haber abierto",
                "shared:z cierra en a.md:5 sin haber abierto",
            ],
        )
        self.assertEqual(ids, {"x"})

    def test_id_in_a_single_file(self) -> None:
        """CA-4: aunque tenga dos copias en ese archivo"""
        files = {
            "a.md": block("x", "texto") + "\n" + block("x", "texto"),
            "b.md": "sin bloques",
        }
        errors, _ = check_shared_blocks(files)
        self.assertEqual(len(errors), 1)
        self.assertIn("shared:x aparece solo en a.md", errors[0])

    def test_inline_and_own_line_markers(self) -> None:
        """CA-5"""
        own_line = "antes\n   <!-- shared:x -->\ntexto\n   <!-- /shared:x -->\n"
        inline = "Haz algo, <!-- shared:x -->texto<!-- /shared:x -->. Fin."
        errors, ids = check_shared_blocks({"a.md": own_line, "b.md": inline})
        self.assertEqual(errors, [])
        self.assertEqual(ids, {"x"})

        different = "Haz <!-- shared:x -->texto distinto<!-- /shared:x -->."
        errors, _ = check_shared_blocks({"a.md": own_line, "b.md": different})
        self.assertEqual(len(errors), 1)
        self.assertIn("shared:x tiene 2 versiones distintas", errors[0])

    def test_nested_markers(self) -> None:
        """CA-6: anidados"""
        nested = (
            "<!-- shared:a -->\n<!-- shared:b -->\nt\n"
            "<!-- /shared:b -->\n<!-- /shared:a -->"
        )
        errors, _ = check_shared_blocks({"a.md": nested, "b.md": nested})
        self.assertEqual(len(errors), 4)
        self.assertIn("shared:b abre en a.md:2 dentro de shared:a (a.md:1)", errors[0])
        self.assertIn(NO_NESTING, errors[0])
        self.assertEqual(errors[1], "shared:a cierra en a.md:5 sin haber abierto")

    def test_overlapping_markers(self) -> None:
        """CA-6: solapados (a abre, b abre, a cierra)"""
        overlap = "<!-- shared:a -->x<!-- shared:b -->y<!-- /shared:a -->"
        errors, _ = check_shared_blocks(
            {"a.md": overlap, "b.md": block("a", "x")}
        )
        self.assertIn(
            "shared:b abre en a.md:1 dentro de shared:a (a.md:1)", errors[0]
        )

    def test_mismatched_closing(self) -> None:
        """CA-6: cierra otro id que el abierto"""
        files = {
            "a.md": "<!-- shared:a -->\nx\n<!-- /shared:b -->",
            "b.md": block("a", "x"),
        }
        errors, _ = check_shared_blocks(files)
        self.assertIn(
            "shared:b cierra en a.md:3 con shared:a abierto (a.md:1)",
            errors[0],
        )

    def test_no_blocks(self) -> None:
        """CA-7: archivos sin bloques"""
        errors, ids = check_shared_blocks({"a.md": "uno", "b.md": "dos"})
        self.assertEqual(
            errors, ["ningún bloque compartido en los 2 archivos leídos"]
        )
        self.assertEqual(ids, set())

    def test_no_files(self) -> None:
        """CA-7: sin archivos"""
        errors, _ = check_shared_blocks({})
        self.assertEqual(
            errors, ["no se encontraron archivos de skills ni de agentes"]
        )


class RepoSharedBlocksTest(unittest.TestCase):
    def test_repo_shared_blocks_are_identical(self) -> None:
        """CA-8"""
        errors, ids = check_shared_blocks(repo_files())
        self.assertEqual(errors, [], "bloques compartidos inválidos")
        self.assertEqual(
            REQUIRED_IDS - ids, set(), "faltan bloques compartidos"
        )


if __name__ == "__main__":
    unittest.main()
