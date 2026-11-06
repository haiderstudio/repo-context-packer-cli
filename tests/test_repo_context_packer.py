#!/usr/bin/env python3
"""Tests for repo_context_packer. Run: python3 tests/test_repo_context_packer.py

No third-party dependencies. All tests use a small fake repo built in a
temporary folder, never the real filesystem.
"""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from repo_context_packer import build_pack, collect, main  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
CLI = ROOT / "src" / "repo_context_packer.py"


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def make_repo(base):
    """A small fake repo with good files, secrets, and build output."""
    write(base / "README.md", "# demo\n\nA demo repo.\n")
    write(base / "src" / "app.py", "print('hello')\n")
    write(base / "src" / "util.py", "def add(a, b):\n    return a + b\n")
    write(base / "docs" / "guide.md", "# Guide\n\nRead this first.\n")
    write(base / ".env", "API_KEY=example-only-not-a-real-key\n")
    write(base / "id_rsa", "-----BEGIN OPENSSH PRIVATE KEY-----\n")
    write(base / "my-secret-notes.txt", "do not pack me\n")
    write(base / ".git" / "config", "[core]\n")
    write(base / "node_modules" / "fake.js", "module.exports = {};\n")
    write(base / "__pycache__" / "app.pyc", "not real bytecode")
    write(base / ".hidden", "hidden file\n")
    (base / "data.bin").parent.mkdir(parents=True, exist_ok=True)
    (base / "data.bin").write_bytes(b"\x00\x01\x02binary")
    return base


def run_cli(*args, cwd=None):
    return subprocess.run(
        [sys.executable, str(CLI), *args],
        capture_output=True, text=True, cwd=cwd)


class TestCollect(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = make_repo(Path(self.tmp.name) / "demo")

    def tearDown(self):
        self.tmp.cleanup()

    def test_named_files_in_given_order(self):
        files, skipped = collect(self.repo, ["src/util.py", "README.md"], [])
        self.assertEqual([str(r) for r, _ in files],
                         ["src/util.py", "README.md"])
        self.assertEqual(skipped, [])

    def test_named_dir_packs_sorted(self):
        files, _ = collect(self.repo, ["src"], [])
        self.assertEqual([str(r) for r, _ in files],
                         ["src/app.py", "src/util.py"])

    def test_env_named_but_refused(self):
        files, skipped = collect(self.repo, [".env", "README.md"], [])
        self.assertEqual([str(r) for r, _ in files], ["README.md"])
        self.assertEqual(skipped, [(".env", "secret file")])

    def test_secret_patterns_refused(self):
        files, skipped = collect(
            self.repo, ["id_rsa", "my-secret-notes.txt", "README.md"], [])
        self.assertEqual([str(r) for r, _ in files], ["README.md"])
        self.assertEqual([r for r, _ in skipped],
                         ["id_rsa", "my-secret-notes.txt"])

    def test_build_dirs_left_out(self):
        files, skipped = collect(
            self.repo, [".git", "node_modules", "__pycache__", "README.md"], [])
        self.assertEqual([str(r) for r, _ in files], ["README.md"])
        self.assertTrue(all(reason == "build output"
                            for _, reason in skipped))

    def test_binary_file_left_out(self):
        files, skipped = collect(self.repo, ["data.bin", "README.md"], [])
        self.assertEqual([str(r) for r, _ in files], ["README.md"])
        self.assertEqual(skipped, [("data.bin", "binary file")])

    def test_hidden_file_skipped_unless_named(self):
        files, skipped = collect(self.repo, ["src"], [])
        self.assertNotIn(".hidden", [str(r) for r, _ in files])
        files, _ = collect(self.repo, [".hidden"], [])
        self.assertEqual([str(r) for r, _ in files], [".hidden"])

    def test_include_filter(self):
        files, _ = collect(self.repo, ["src", "docs"], ["*.py"])
        self.assertEqual([str(r) for r, _ in files],
                         ["src/app.py", "src/util.py"])

    def test_missing_path_raises(self):
        with self.assertRaises(ValueError):
            collect(self.repo, ["nope.py"], [])

    def test_same_file_twice_packed_once(self):
        files, _ = collect(self.repo, ["README.md", "README.md"], [])
        self.assertEqual(len(files), 1)


class TestPackAndCli(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = make_repo(Path(self.tmp.name) / "demo")

    def tearDown(self):
        self.tmp.cleanup()

    def test_pack_format(self):
        files, _ = collect(self.repo, ["README.md", "src/app.py"], [])
        pack, total = build_pack(self.repo, files)
        self.assertIn("# Files: 2", pack)
        self.assertIn("# Lines: 4", pack)
        self.assertIn("==== README.md ====", pack)
        self.assertIn("A demo repo.", pack)
        self.assertIn("==== src/app.py ====", pack)
        self.assertIn("print('hello')", pack)
        self.assertNotIn("API_KEY", pack)
        self.assertEqual(total, 4)

    def test_cli_stdout(self):
        result = run_cli(str(self.repo), "README.md", "src")
        self.assertEqual(result.returncode, 0)
        self.assertIn("==== src/app.py ====", result.stdout)
        self.assertIn("packed 3 file(s)", result.stderr)
        self.assertNotIn("API_KEY", result.stdout)

    def test_cli_no_paths_exits_2(self):
        result = run_cli(str(self.repo))
        self.assertEqual(result.returncode, 2)

    def test_cli_list_only(self):
        result = run_cli(str(self.repo), "src", "--list")
        self.assertEqual(result.returncode, 0)
        self.assertEqual(result.stdout.splitlines(),
                         ["src/app.py", "src/util.py"])

    def test_cli_output_inside_root_refused(self):
        result = run_cli(str(self.repo), "README.md",
                         "-o", str(self.repo / "pack.txt"))
        self.assertEqual(result.returncode, 2)
        self.assertFalse((self.repo / "pack.txt").exists())

    def test_cli_output_outside_root(self):
        out = Path(self.tmp.name) / "pack.txt"
        result = run_cli(str(self.repo), "README.md", "-o", str(out))
        self.assertEqual(result.returncode, 0)
        self.assertTrue(out.exists())
        self.assertIn("==== README.md ====", out.read_text())
        self.assertFalse((self.repo / "pack.txt").exists())

    def test_cli_nothing_packable_exits_1(self):
        result = run_cli(str(self.repo), ".env")
        self.assertEqual(result.returncode, 1)
        self.assertIn("nothing to pack", result.stderr)

    def test_cli_missing_path_exits_2(self):
        result = run_cli(str(self.repo), "nope.py")
        self.assertEqual(result.returncode, 2)


if __name__ == "__main__":
    unittest.main(verbosity=2)
