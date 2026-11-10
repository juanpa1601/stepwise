"""Alignment of a project's ``.claude/settings.json`` with the ``stepwise`` plugin.

Usage, from the project root::

    python3 <path to this script> [<settings file>]

Reads ``.claude/settings.json`` (or the given file) and compares its ``permissions.ask`` list with the plugin's
rules (``references/ask-rules.json`` at the plugin root), ignoring order and repeats. Also checks that
``enabledPlugins`` enables ``stepwise@stepwise`` and that ``extraKnownMarketplaces`` declares
``stepwise`` with ``ref: main``. Prints at most 5 lines: ``ok`` or ``desalineado``, then only the
lines that apply (``Faltan:``, ``Extra (info):``, ``Plugin:``, ``Marketplace:``).

Exit codes: 0 aligned (extra rules are information only), 1 misaligned, 2 the file does not exist, is not valid
JSON or has an invalid structure (the message goes to stderr). Read-only: it never writes a file.

Standard library only (Python 3.10 or later).
"""

import json
import sys
from pathlib import Path

RULES_FILE: Path = Path(__file__).resolve().parents[3] / "references" / "ask-rules.json"
SETTINGS: str = ".claude/settings.json"
PLUGIN: str = "stepwise@stepwise"
MARKETPLACE: str = "stepwise"
REF: str = "main"


class SettingsError(Exception):
    """The settings file cannot be checked: it does not exist, is not valid JSON or has an invalid structure."""


def plugin_rules() -> list[str]:
    """Return the plugin's ``ask`` rules, from its data file."""
    data: object = json.loads(RULES_FILE.read_text(encoding="utf-8"))
    if not isinstance(data, dict) or "ask" not in data:
        raise ValueError("the root is not an object with 'ask'")
    rules: object = data["ask"]
    if not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules):
        raise ValueError("'ask' is not a list of text")
    return rules


def load_settings(path: Path) -> dict[str, object]:
    """Return the settings in ``path`` as an object; raise ``SettingsError`` naming the case and the path."""
    if not path.is_file():
        raise SettingsError(f"no existe: {path.as_posix()}")
    try:
        settings: object = json.loads(path.read_text(encoding="utf-8-sig"))  # with or without a BOM
    except (json.JSONDecodeError, UnicodeDecodeError) as error:
        raise SettingsError(f"no es JSON válido: {path.as_posix()} ({error})") from error
    except OSError as error:
        raise SettingsError(f"no se pudo leer: {path.as_posix()} ({error.strerror or error})") from error
    if not isinstance(settings, dict):
        raise SettingsError(f"estructura inválida: {path.as_posix()} (la raíz no es un objeto)")
    return settings


def project_rules(
    settings: dict[str, object],
    path: Path
) -> list[str]:
    """Return ``permissions.ask`` of ``settings`` (empty when absent); raise ``SettingsError`` if it is invalid."""
    permissions: object = settings.get("permissions", {})
    if not isinstance(permissions, dict):
        raise SettingsError(f"estructura inválida: {path.as_posix()} (permissions no es un objeto)")
    rules: object = permissions.get("ask", [])
    if not isinstance(rules, list) or not all(isinstance(rule, str) for rule in rules):
        raise SettingsError(f"estructura inválida: {path.as_posix()} (permissions.ask no es una lista de textos)")
    return rules


def marketplace_status(settings: dict[str, object]) -> str | None:
    """Return what is wrong with the plugin's marketplace in ``settings``, or ``None`` when it reads ``main``."""
    marketplaces: object = settings.get("extraKnownMarketplaces")
    entry: object = marketplaces.get(MARKETPLACE) if isinstance(marketplaces, dict) else None
    if not isinstance(entry, dict):
        return "no declarado"
    source: object = entry.get("source")
    ref: object = source.get("ref") if isinstance(source, dict) else None
    if ref is None:
        return f"sin ref (se espera {REF})"
    if ref != REF:
        return f"ref {ref} (se espera {REF})"
    return None


def report(
    settings: dict[str, object],
    path: Path
) -> tuple[list[str], int]:
    """Return the report lines for ``settings`` and the exit code (0 aligned, 1 misaligned)."""
    expected: list[str] = plugin_rules()
    declared: list[str] = project_rules(settings, path)
    missing: list[str] = [rule for rule in expected if rule not in declared]
    extra: list[str] = list(dict.fromkeys(rule for rule in declared if rule not in expected))
    plugins: object = settings.get("enabledPlugins")
    enabled: bool = isinstance(plugins, dict) and plugins.get(PLUGIN) is True
    marketplace: str | None = marketplace_status(settings)
    misaligned: bool = bool(missing) or not enabled or marketplace is not None
    lines: list[str] = ["desalineado" if misaligned else "ok"]
    if missing:
        lines.append(f"Faltan: {', '.join(missing)}")
    if extra:
        lines.append(f"Extra (info): {', '.join(extra)}")
    if not enabled:
        lines.append("Plugin: no habilitado")
    if marketplace is not None:
        lines.append(f"Marketplace: {marketplace}")
    return lines, 1 if misaligned else 0


def main(argv: list[str]) -> int:
    """Print the alignment report of ``argv`` (``[<settings file>]``) and return the exit code."""
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8")  # type: ignore[union-attr] - the messages carry accents
    if len(argv) > 1:
        print("Usage: settings_alignment.py [<settings file>]", file=sys.stderr)
        return 2
    path: Path = Path(argv[0] if argv else SETTINGS)
    try:
        lines, code = report(load_settings(path), path)
    except SettingsError as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    except (OSError, ValueError) as error:
        print(f"error: no se pudo leer la lista del plugin {RULES_FILE.as_posix()} ({error})", file=sys.stderr)
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
