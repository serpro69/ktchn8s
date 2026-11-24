"""Offline template/parser checks; requires SnapRAID 13.0, never the NAS.

Run inside nix develop:
    SNAPRAID_BIN=/path/to/snapraid python3 -m unittest discover \
        -s tests -p 'test_snapraid_config.py' -v

Only status/diff run, with every storage path relocated into a temporary directory.
The test-only device check bypass permits parsing on one filesystem; it does not
establish parity lifecycle behavior (covered separately by Task 12's VM scenario).
"""

from collections import Counter
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

from jinja2 import Environment, StrictUndefined


REPO_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = REPO_ROOT / "metal/roles/storage/templates/snapraid.conf.j2"
DATA_DIRS = ["/mnt/data1", "/mnt/data2", "/mnt/data3"]
PARITY_LINES = [
    "parity /mnt/parity1/snapraid.parity",
    "2-parity /mnt/parity2/snapraid.2-parity",
    "3-parity /mnt/parity3/snapraid.3-parity",
]
INCLUDED = [
    "00_meta/README.md",
    "10_documents/10.01_personal/record.txt",
    "20_photos/20.02_camera/photo.jpg",
    "30_media/30.01_movies/movie.mkv",
    "30_media/30.02_tv/show.mkv",
    "30_media/30.03_music/song.flac",
    "30_media/30.04_audiobooks/book.m4b",
    "90_inbox/incoming.txt",
    "70_backups/70.01_machines/host/downloads/archive.zip",
    "70_backups/70.02_apps/app/appdata/state.db",
    # A full copy of the NAS tree inside a backup must not match root exclusions.
    "70_backups/70.01_machines/host/30_media/rotation/movies/kept.mkv",
    "70_backups/70.01_machines/host/10_documents/inbox/kept.pdf",
    "70_backups/70.01_machines/host/99_tmp/kept.txt",
    "70_backups/70.01_machines/host/tmp/kept.txt",
]
EXCLUDED = [
    "30_media/rotation/downloads/complete/download.mkv",
    "30_media/rotation/downloads/incomplete/download.part",
    "30_media/rotation/movies/movie.mkv",
    "30_media/rotation/shows/show.mkv",
    "10_documents/inbox/scanned.pdf",
    "99_tmp/driveA/staged.txt",
    "tmp/scratch.txt",
    "lost+found/recovered.txt",
    "70_backups/failed.unrecoverable",
    "70_backups/partial.!sync",
    "70_backups/.AppleDouble",
    "70_backups/._AppleDouble",
    "70_backups/.DS_Store",
    "70_backups/._.DS_Store",
    "70_backups/.Thumbs.db",
    "70_backups/.fseventsd",
    "70_backups/.Spotlight-V100",
    "70_backups/.TemporaryItems",
    "70_backups/.Trashes",
    "70_backups/.AppleDB",
]


def render_config(parity_count):
    template = Environment(
        undefined=StrictUndefined, trim_blocks=True, keep_trailing_newline=True
    ).from_string(TEMPLATE.read_text(encoding="utf-8"))
    return template.render(
        parity_devices=[f"fixture-parity-{i}" for i in range(parity_count)],
        disk_directories=DATA_DIRS,
    )


class SnapraidConfigTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.binary = shutil.which(os.environ.get("SNAPRAID_BIN", "snapraid"))
        if cls.binary is None:
            raise RuntimeError("Set SNAPRAID_BIN to a SnapRAID 13.0 executable")
        result = subprocess.run(
            [cls.binary, "--version"], capture_output=True, text=True,
            check=True, timeout=10,
        )
        if not result.stdout.startswith("snapraid v13.0 by "):
            raise RuntimeError(f"Expected SnapRAID 13.0, got: {result.stdout.strip()}")

    def write_config(self, root, rendered):
        """Relocate directive paths only; exclude patterns must remain unchanged."""
        lines = []
        for line in rendered.splitlines():
            fields = line.split()
            if fields and fields[0] in {
                "parity", "1-parity", "2-parity", "3-parity", "content", "data"
            }:
                original = Path(fields[-1])
                self.assertTrue(original.is_absolute(), line)
                self.assertNotIn("..", original.parts, line)
                target = root / original.relative_to("/")
                if fields[0] == "data":
                    target.mkdir(parents=True, exist_ok=True)
                else:
                    target.parent.mkdir(parents=True, exist_ok=True)
                fields[-1] = str(target)
                line = " ".join(fields)
            lines.append(line)
        config = root / "snapraid.conf"
        config.write_text("\n".join(lines) + "\n", encoding="utf-8")
        return config

    def run_snapraid(self, config, command):
        self.assertIn(command, {"status", "diff"})
        return subprocess.run(
            [self.binary, "--test-skip-device", "--conf", str(config), command],
            cwd=config.parent, capture_output=True, text=True, timeout=30,
            env={**os.environ, "LC_ALL": "C"},
        )

    def seed(self, root, paths):
        for directory in DATA_DIRS:
            for relative in paths:
                target = root / directory.lstrip("/") / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(f"fixture: {relative}\n", encoding="utf-8")

    def test_parity_directives_and_paths(self):
        for count in (1, 2, 3):
            with self.subTest(parity_count=count):
                lines = render_config(count).splitlines()
                self.assertEqual(
                    [line for line in lines if line.startswith("parity ")
                     or "-parity " in line], PARITY_LINES[:count],
                )
                self.assertEqual(
                    [line for line in lines if line.startswith("content ")],
                    ["content /mnt/data1/snapraid.content",
                     "content /mnt/data2/snapraid.content",
                     "content /mnt/data3/snapraid.content",
                     "content /var/snapraid.content"],
                )

    def test_parser_and_exclusion_behavior(self):
        for count in (1, 2, 3):
            with self.subTest(parity_count=count), tempfile.TemporaryDirectory(
                prefix="snapraid-config-"
            ) as directory:
                root = Path(directory)
                config = self.write_config(root, render_config(count))
                status = self.run_snapraid(config, "status")
                self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
                self.seed(root, EXCLUDED)
                excluded = self.run_snapraid(config, "diff")
                self.assertEqual(excluded.returncode, 0, excluded.stdout + excluded.stderr)
                self.seed(root, INCLUDED)
                diff = self.run_snapraid(config, "diff")
                # SnapRAID diff returns 2 when it successfully finds pending changes.
                self.assertEqual(diff.returncode, 2, diff.stdout + diff.stderr)
                added = Counter(line[4:] for line in diff.stdout.splitlines()
                                if line.startswith("add "))
                expected = {path: len(DATA_DIRS) for path in INCLUDED}
                self.assertEqual(added, expected, diff.stdout + diff.stderr)
                self.assertFalse(list(root.rglob("snapraid.content")))
                self.assertFalse(list(root.rglob("snapraid.parity")))
                self.assertFalse(list(root.rglob("snapraid.*-parity")))

    def test_duplicate_first_parity_is_rejected(self):
        with tempfile.TemporaryDirectory(prefix="snapraid-invalid-") as directory:
            invalid = render_config(2).replace("2-parity", "1-parity")
            config = self.write_config(Path(directory), invalid)
            result = self.run_snapraid(config, "status")
            self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
            self.assertIn("Multiple '1-parity' specification", result.stderr)


if __name__ == "__main__":
    unittest.main()
