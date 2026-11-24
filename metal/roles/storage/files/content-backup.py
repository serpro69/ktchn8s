#!/usr/bin/python3
"""Publish complete SnapRAID content generations and prune only complete backups."""

import argparse
from datetime import datetime, timezone
import filecmp
from pathlib import Path
import re
import shutil
import tempfile


def backup(config: Path, directory: Path, keep: int) -> Path:
    if keep < 1:
        raise ValueError("keep at least one complete generation")
    sources = [Path(fields[1]) for line in config.read_text().splitlines()
               if (fields := line.split(maxsplit=1)) and fields[0] == "content"]
    if not sources or len(set(sources)) != len(sources):
        raise ValueError("expected a nonempty list of distinct content sources")
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    generation = directory / stamp
    # An incomplete generation never replaces a good one or triggers retention.
    with tempfile.TemporaryDirectory(dir=directory, prefix=".pending-") as tmp:
        stage = Path(tmp) / "files"
        stage.mkdir()
        for path in sources:
            if not path.is_absolute() or ".." in path.parts or not path.is_file() or path.stat().st_size == 0:
                raise ValueError(f"invalid content source: {path}")
            target = stage / path.relative_to("/")
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            if not filecmp.cmp(path, target, shallow=False):
                raise OSError(f"verification failed for {path}")
        stage.rename(generation)
    generations = sorted(p for p in directory.iterdir() if p.is_dir() and re.fullmatch(r"[0-9]{8}T[0-9]{12}Z", p.name))
    for old in generations[:-keep]:
        shutil.rmtree(old)
    return generation


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("keep", type=int)
    args = parser.parse_args()
    print(backup(Path("/etc/snapraid.conf"), Path("/var/backups/snapraid"), args.keep))
