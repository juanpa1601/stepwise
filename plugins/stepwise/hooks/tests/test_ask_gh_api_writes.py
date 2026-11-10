"""Tests of ``ask_gh_api_writes.py``: run the real hook through stdin/stdout for each command.

Also checks that the ``ask`` rules of the plugin's data file (``plugins/stepwise/references/ask-rules.json``),
of the ADR (``docs/decisions/bootstrap/business-rules.md``, §3.2) and of this repository's ``.claude/settings.json``
are the same: they are the text backup of the hook.

Standard library only (``unittest``). From the root of this repository::

    python3 -m unittest discover plugins/stepwise/hooks/tests -v
"""

import json
import re
import subprocess
import sys
import unittest
from pathlib import Path

HOOK: Path = Path(__file__).resolve().parents[1] / "ask_gh_api_writes.py"
REPO_ROOT: Path = Path(__file__).resolve().parents[4]
RULES_FILE: Path = Path(__file__).resolve().parents[2] / "references" / "ask-rules.json"


def run_hook(stdin: str) -> subprocess.CompletedProcess[str]:
    """Run the hook with ``stdin`` and return the finished process."""
    return subprocess.run(  # noqa: S603 - fixed interpreter and script
        [sys.executable, str(HOOK)],
        input=stdin,
        capture_output=True,
        text=True,
        check=False
    )


def decide(
    command: str,
    tool: str = "Bash"
) -> str:
    """Run the hook on a shell command and return ``ask`` or ``pass``."""
    payload: str = json.dumps({"hook_event_name": "PreToolUse", "tool_name": tool, "tool_input": {"command": command}})
    completed: subprocess.CompletedProcess[str] = run_hook(payload)
    assert completed.returncode == 0, completed.stderr
    output: dict[str, object] = json.loads(completed.stdout)
    specific: object = output.get("hookSpecificOutput")
    if isinstance(specific, dict) and specific.get("permissionDecision") == "ask":
        assert "gh api" in str(specific.get("permissionDecisionReason"))
        return "ask"
    assert output == {}, output
    return "pass"


# CA-F1: writes, alone or inside &&, ;, | or $(...).
WRITES: list[str] = [
    "gh api -X POST repos/o/r/pulls/1/comments --input /tmp/body.json",
    "gh api repos/o/r/pulls/1/comments -X POST --input /tmp/body.json",
    "gh api -X PATCH repos/o/r/issues/1 -f state=closed",
    "gh api repos/o/r/issues/1 -X patch -f state=closed",
    "gh api -X PUT repos/o/r/pulls/1/merge",
    "gh api repos/o/r/git/refs/heads/x -X DELETE",
    "gh api -XPATCH repos/o/r/issues/1",
    "gh api repos/o/r/issues/1 -XDELETE",
    "gh api --method PUT repos/o/r/pulls/1/merge",
    "gh api repos/o/r/pulls/1/merge --method PUT",
    "gh api --method=DELETE repos/o/r/git/refs/heads/x",
    "gh api repos/o/r/issues/1/comments -f body=hola",
    "gh api repos/o/r/issues/1/comments -F body=@/tmp/b.md",
    "gh api repos/o/r/issues/1/comments --field body=hola",
    "gh api repos/o/r/issues/1/comments --raw-field body=hola",
    "gh api repos/o/r/issues/1/comments --raw-field=body=hola",
    "gh api repos/o/r/issues/1/comments --input /tmp/body.json",
    "gh api repos/o/r/issues/1/comments -fbody=hola",
    "gh.exe api repos/o/r/issues/1/comments -f body=hola",
    "git status && gh api -X POST repos/o/r/issues/1/comments --input b.json",
    "git status; gh api repos/o/r/issues/1/comments -X POST --input b.json",
    "cat b.json | gh api repos/o/r/issues/1/comments --input -",
    "echo $(gh api -X DELETE repos/o/r/git/refs/heads/x)",
    'id="$(gh api repos/o/r/issues/1/comments -f body=x -q .id)"',
    "echo `gh api -X POST repos/o/r/issues/1/comments --input b.json`",
    "GH_TOKEN=x gh api -X POST repos/o/r/issues/1/comments --input b.json",
    "gh api repos/o/r/issues/1 -X GET && gh api -X POST repos/o/r/issues/1/comments --input b.json",
    "gh api repos/o/r/issues/1/comments --input b.json\ncurl -X GET https://example.com",
    "gh api repos/o/r/issues/1/comments \\\n  -X POST --input b.json",
    "echo it\\'s\ngh api -X DELETE repos/o/r/git/refs/heads/x\ncurl -X GET https://e.com",
    'echo \\"hola\ngh api -X DELETE repos/o/r/git/refs/heads/x\ncurl -X GET https://e.com',
]

POWERSHELL_WRITES: list[str] = [
    "gh api -X POST repos/o/r/issues/1/comments --input $env:TEMP\\b.json",
    "git status; gh api repos/o/r/issues/1 --method PATCH -f state=closed",
    "gh api repos/o/r/issues/1/comments -f body=hola | ConvertFrom-Json",
    "C:\\tools\\gh.exe api -X POST repos/o/r/issues/1/comments --input b.json",
    "gh api repos/o/r/issues/1/comments `\n  -X POST --input b.json",
    "C:\\tools\\gh api -X POST repos/o/r/issues/1/comments --input b.json",
    'echo "it`"s"\ngh api -X DELETE repos/o/r/git/refs/heads/x\ncurl -X GET https://e.com',
    'echo "a`"b"\ngh api -X DELETE repos/o/r/git/refs/heads/x\necho "c`"d"',
    'dir "C:\\tools\\"\ngh api -X DELETE repos/o/r/git/refs/heads/x\ndir "C:\\other\\"',
]

# CA-F2: graphql with a mutation or a query read from a file.
GRAPHQL_ASK: list[str] = [
    "gh api graphql -f query='mutation { resolveReviewThread(input: {threadId: \"x\"}) { thread { id } } }'",
    "gh api graphql -f query='mutation($id: ID!) { resolveReviewThread(input: {threadId: $id}) { thread { id } } }'"
    " -f id=PRRT_1",
    'gh api graphql -F query=@/tmp/resolve.graphql -f id=PRRT_1',
    "gh api graphql --input /tmp/body.json",
    "Q='mutation { resolveReviewThread(input: {threadId: \"x\"}) { thread { id } } }'; gh api graphql -f query=\"$Q\"",
    "gh api graphql -f query=\"${QUERY}\"",
    "gh api graphql -f query=\"mu${X}ion { resolveReviewThread(input: {threadId: \\\"x\\\"}) { thread { id } } }\"",
    "gh api graphql -f query=hola",
    "gh api graphql -f query='mu$X{ a }'",
]

GRAPHQL_READ: list[str] = [
    "gh api graphql -f query='query { repository(owner: \"o\", name: \"r\") { pullRequest(number: 1) { id } } }'",
    "gh api graphql -F owner=o -F name=r -f query='"
    "query($owner: String!, $name: String!) { repository(owner: $owner, name: $name) { id } }'",
    "gh api graphql --paginate -f query='{ viewer { login } }'",
    "gh api graphql -f query='\nquery {\n  viewer { login }\n}\n'",
]

# CA-F3: reads and commands that only mention gh api.
READS: list[str] = [
    "gh api repos/o/r/branches/develop -q .commit.sha",
    'gh api "repos/o/r/contents/a/b.py?ref=abc123" -H "Accept: application/vnd.github.raw"',
    'gh api "repos/o/r/git/trees/abc123?recursive=1"',
    "gh api --paginate repos/o/r/pulls/1/comments",
    "gh api -X GET repos/o/r/pulls -f per_page=100",
    "gh api repos/o/r/pulls -f per_page=100 -X GET",
    "gh api --method GET repos/o/r/pulls -F per_page=100",
    "gh api -XGET search/issues -f q=repo:o/r",
    'grep "gh api -X POST" x.md',
    "grep -rn 'gh api graphql' docs",
    "git commit -F /tmp/msg.txt",
    "git commit -F /tmp/msg.txt && git push",
    "gh pr view 1 --json body",
    "gh api repos/o/r/pulls/1\ncurl -X POST https://example.com -d x",
    "echo gh-api -X POST",
    "gh api search/issues -X GET -f q=laugh --paginate",
    "",
]


class AskGhApiWritesTest(unittest.TestCase):
    """The hook answers ``ask`` to ``gh api`` writes and stays silent on everything else."""

    def test_writes_ask(self) -> None:
        """CA-F1: every write form asks, in Bash."""
        for command in WRITES:
            with self.subTest(command=command):
                self.assertEqual(decide(command), "ask")

    def test_powershell_writes_ask(self) -> None:
        """CA-F1: the same writes ask in PowerShell."""
        for command in POWERSHELL_WRITES + WRITES[:12]:
            with self.subTest(command=command):
                self.assertEqual(decide(command, tool="PowerShell"), "ask")

    def test_graphql_mutation_or_file_asks(self) -> None:
        """CA-F2: a mutation or a query read from a file asks."""
        for command in GRAPHQL_ASK:
            with self.subTest(command=command):
                self.assertEqual(decide(command), "ask")

    def test_graphql_query_passes(self) -> None:
        """CA-F2: a query without ``mutation`` passes."""
        for command in GRAPHQL_READ:
            with self.subTest(command=command):
                self.assertEqual(decide(command), "pass")

    def test_reads_pass(self) -> None:
        """CA-F3: reads and mentions pass, in Bash and PowerShell."""
        for command in READS:
            for tool in ("Bash", "PowerShell"):
                with self.subTest(command=command, tool=tool):
                    self.assertEqual(decide(command, tool=tool), "pass")

    def test_other_tools_pass(self) -> None:
        """Only Bash and PowerShell are checked."""
        payload: str = json.dumps({"tool_name": "Read", "tool_input": {"command": "gh api -X POST x"}})
        completed: subprocess.CompletedProcess[str] = run_hook(payload)
        self.assertEqual(json.loads(completed.stdout), {})

    def test_reason_shows_method_and_path(self) -> None:
        """The reason names the method and the path of the write."""
        payload: str = json.dumps({
            "tool_name": "Bash",
            "tool_input": {"command": "gh api repos/o/r/issues/1 --method=patch -f state=closed"}
        })
        output: dict[str, dict[str, str]] = json.loads(run_hook(payload).stdout)
        reason: str = output["hookSpecificOutput"]["permissionDecisionReason"]
        self.assertIn("PATCH repos/o/r/issues/1", reason)

    def test_internal_error_prints_empty_and_exits_zero(self) -> None:
        """CA-F3: broken input prints ``{}`` and exits with 0."""
        for stdin in ("not json", "[1, 2]", '{"tool_name": "Bash", "tool_input": {"command": 5}}', ""):
            with self.subTest(stdin=stdin):
                completed: subprocess.CompletedProcess[str] = run_hook(stdin)
                self.assertEqual(completed.returncode, 0)
                self.assertEqual(json.loads(completed.stdout), {})


def adr_ask_rules() -> list[str]:
    """Return the ``ask`` list of the JSON block in §3.2 of the ADR."""
    text: str = (REPO_ROOT / "docs" / "decisions" / "bootstrap" / "business-rules.md").read_text(encoding="utf-8")
    match: re.Match[str] | None = re.search(r'^\s*(\{ "permissions": \{ "ask": \[.*\] \} \})\s*$', text, re.MULTILINE)
    assert match is not None, "no ask list in ADR §3.2"
    return json.loads(match.group(1))["permissions"]["ask"]


def data_ask_rules() -> list[str]:
    """Return the ``ask`` list of the plugin's data file."""
    return json.loads(RULES_FILE.read_text(encoding="utf-8"))["ask"]


def settings_ask_rules() -> list[str]:
    """Return the ``ask`` list of this repository's ``.claude/settings.json``."""
    settings: dict[str, dict[str, list[str]]] = json.loads(
        (REPO_ROOT / ".claude" / "settings.json").read_text(encoding="utf-8")
    )
    return settings["permissions"]["ask"]


class SettingsMatchAdrTest(unittest.TestCase):
    """ADR ``bootstrap`` §3.2: the same ``ask`` rules everywhere."""

    def test_three_lists_equal(self) -> None:
        """The data file, ADR §3.2 and ``.claude/settings.json`` hold the same 11 rules, without repeats."""
        expected: set[str] = set(data_ask_rules())
        sources: dict[str, list[str]] = {
            "ask-rules.json": data_ask_rules(),
            "ADR §3.2": adr_ask_rules(),
            ".claude/settings.json": settings_ask_rules()
        }
        for source, rules in sources.items():
            with self.subTest(source=source):
                self.assertEqual(len(rules), 11)
                self.assertEqual(len(set(rules)), len(rules), "repeated rule")
                self.assertEqual(set(rules), expected)

    def test_gh_api_rules(self) -> None:
        """The list drops the graphql and ``-X POST`` prefixes and holds the four ``gh api`` patterns."""
        rules: list[str] = adr_ask_rules()
        self.assertNotIn("Bash(gh api graphql:*)", rules)
        self.assertNotIn("Bash(gh api -X POST:*)", rules)
        for rule in ("Bash(gh api -X *)", "Bash(gh api * -X *)", "Bash(gh api * --method *)",
                     "Bash(gh api * --input *)"):
            with self.subTest(rule=rule):
                self.assertIn(rule, rules)


if __name__ == "__main__":
    unittest.main()
