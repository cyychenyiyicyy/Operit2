#!/usr/bin/env python3
"""Add an explicit rootDir to plugin tsconfig.json files that need one.

Why this exists
---------------
The CLI packaging step runs `tsc -p <package>/tsconfig.json` for every plugin
package. A package whose `include` spans both its own sources and files
outside its directory (e.g. `../../../types/**/*.d.ts`) while also setting
`outDir` makes TypeScript complain:

    error TS5011: The common source directory of 'tsconfig.json' is './src'.
    The 'rootDir' setting must be explicitly set to this or another path to
    adjust your output's file layout.

Setting rootDir explicitly satisfies the compiler without weakening any type
checking.

Choosing the value
------------------
The value must preserve the existing output layout, because some packages
compile to `dist/<file>.js` and their build script reads that directory:

  * if the package's include patterns point at `src/...`, use rootDir "src"
    (identical to what sibling packages already declare);
  * otherwise use "." so output stays under the package directory.

Packages that already declare rootDir are left untouched.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path("plugins/packages")
changed = []
skipped = []


def infer_root_dir(options, include):
    """Pick a rootDir that keeps the current output layout."""
    patterns = include if isinstance(include, list) else []
    has_src = any(
        isinstance(p, str) and p.replace("\\", "/").lstrip("./").startswith("src/")
        for p in patterns
    )
    if has_src:
        return "src"
    return "."


for tsconfig in sorted(ROOT.glob("*/tsconfig.json")):
    try:
        data = json.loads(tsconfig.read_text(encoding="utf-8"))
    except Exception as error:
        skipped.append((str(tsconfig), f"unparsable: {error}"))
        continue

    options = data.get("compilerOptions")
    if not isinstance(options, dict):
        skipped.append((str(tsconfig), "no compilerOptions"))
        continue
    if "rootDir" in options:
        continue

    include = data.get("include", [])
    options["rootDir"] = infer_root_dir(options, include)
    tsconfig.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    changed.append(f"{tsconfig} -> rootDir={options['rootDir']}")

print(f"patched {len(changed)} tsconfig file(s):")
for item in changed:
    print(f"  {item}")
for item, why in skipped:
    print(f"skipped {item}: {why}")

sys.exit(0)
