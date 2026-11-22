"""Shallow-clone pure-Python MIT/BSD/Apache repos for Volet 2 and record exact commit SHAs."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
UPSTREAM = ROOT / "upstream"

REPOS = [
    ("packaging", "https://github.com/pypa/packaging.git", "src", "packaging", "tests"),
    ("itsdangerous", "https://github.com/pallets/itsdangerous.git", "src", "itsdangerous", "tests"),
    ("tomli", "https://github.com/hukkin/tomli.git", "src", "tomli", "tests"),
    ("jmespath", "https://github.com/jmespath/jmespath.py.git", ".", "jmespath", "tests"),
    ("click", "https://github.com/pallets/click.git", "src", "click", "tests"),
    ("markupsafe", "https://github.com/pallets/markupsafe.git", "src", "markupsafe", "tests"),
    ("blinker", "https://github.com/pallets-eco/blinker.git", "src", "blinker", "tests"),
    ("werkzeug", "https://github.com/pallets/werkzeug.git", "src", "werkzeug", "tests"),
    ("jinja", "https://github.com/pallets/jinja.git", "src", "jinja2", "tests"),
    ("flask", "https://github.com/pallets/flask.git", "src", "flask", "tests"),
    ("attrs", "https://github.com/python-attrs/attrs.git", "src", "attr", "tests"),
    ("marshmallow", "https://github.com/marshmallow-code/marshmallow.git", "src", "marshmallow", "tests"),
    ("boltons", "https://github.com/mahmoud/boltons.git", ".", "boltons", "tests"),
    ("urllib3", "https://github.com/urllib3/urllib3.git", "src", "urllib3", "test"),
    ("markdown", "https://github.com/Python-Markdown/markdown.git", ".", "markdown", "tests"),
    ("lark", "https://github.com/lark-parser/lark.git", ".", "lark", "tests"),
    ("rich", "https://github.com/Textualize/rich.git", ".", "rich", "tests"),
    ("more_itertools", "https://github.com/more-itertools/more-itertools.git", ".", "more_itertools", "tests"),
    ("semver", "https://github.com/python-semver/python-semver.git", "src", "semver", "tests"),
    ("humanize", "https://github.com/python-humanize/humanize.git", "src", "humanize", "tests"),
    ("dateutil", "https://github.com/dateutil/dateutil.git", "src", "dateutil", "tests"),
    ("pyyaml", "https://github.com/yaml/pyyaml.git", "lib", "yaml", "tests"),
]


def main() -> int:
    UPSTREAM.mkdir(parents=True, exist_ok=True)
    manifest = []
    for name, url, src_rel, pkg_name, test_rel in REPOS:
        dst = UPSTREAM / name
        if not dst.exists():
            print(f"[fetch] cloning {name} from {url}...", flush=True)
            proc = subprocess.run(
                ["git", "clone", "--depth", "1", "--quiet", url, str(dst)],
                capture_output=True,
                text=True,
            )
            if proc.returncode != 0:
                print(f"[fetch] FAILED {name}: {proc.stderr.strip()[:200]}", file=sys.stderr, flush=True)
                continue
        sha_proc = subprocess.run(
            ["git", "-C", str(dst), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
        )
        sha = sha_proc.stdout.strip()
        manifest.append(
            {
                "name": name,
                "url": url,
                "commit": sha,
                "src_rel": src_rel,
                "pkg_name": pkg_name,
                "test_rel": test_rel,
            }
        )
        print(f"[fetch] OK {name} @ {sha[:12]}", flush=True)

    (ROOT / "upstream_manifest.json").write_text(
        json.dumps(manifest, indent=2), encoding="utf-8"
    )
    print(f"[fetch] DONE: {len(manifest)}/{len(REPOS)} repos ready")
    return 0 if manifest else 1


if __name__ == "__main__":
    raise SystemExit(main())
