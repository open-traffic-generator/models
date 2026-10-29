"""Walk every $ref / x-include in public_api_otg/ and confirm the target file exists.

Reports broken refs grouped by source file.  Does NOT validate that the referenced
schema path inside the target file exists; that level of check is best left to
openapiart's bundle step.

Usage:
    python public_api_otg/scripts/check_refs.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parent              # public_api_otg/

# Generated output — skip; its bundle uses only internal #/ refs anyway.
EXCLUDE_DIRS = {"artifacts"}


def _source_yaml(root: Path):
    return [p for p in sorted(root.rglob("*.yaml"))
            if not any(part in EXCLUDE_DIRS for part in p.relative_to(root).parts)]


def walk_refs(node, src_dir: Path, src_path: Path, broken: list[tuple[Path, str]]) -> None:
    if isinstance(node, dict):
        for key in ("$ref", "x-include"):
            val = node.get(key)
            if isinstance(val, str) and "#" in val:
                file_part = val.split("#", 1)[0]
                if file_part:                   # relative ref like ../foo/bar.yaml
                    tgt = (src_dir / file_part).resolve()
                    if not tgt.exists():
                        broken.append((src_path, val))
                # internal #/... refs are not checked here
        for v in node.values():
            walk_refs(v, src_dir, src_path, broken)
    elif isinstance(node, list):
        for v in node:
            walk_refs(v, src_dir, src_path, broken)


def main() -> int:
    broken: list[tuple[Path, str]] = []
    yaml_files = _source_yaml(ROOT)
    for path in yaml_files:
        with path.open() as f:
            try:
                doc = yaml.safe_load(f)
            except Exception as e:
                print(f"PARSE FAIL {path.relative_to(ROOT)}: {e}", file=sys.stderr)
                return 2
        walk_refs(doc, path.parent, path, broken)

    if not broken:
        print(f"OK: every $ref / x-include in {len(yaml_files)} yaml files targets an existing file.")
        return 0

    print(f"BROKEN: {len(broken)} dangling refs:", file=sys.stderr)
    for src, ref in broken:
        print(f"  {src.relative_to(ROOT)}: {ref}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
