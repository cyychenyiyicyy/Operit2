#!/usr/bin/env python3
"""Patch plugin tsconfig.json files that trip TypeScript error TS5011.

TS5011: "The common source directory of 'tsconfig.json' is './src'. The
'rootDir' setting must be explicitly set to this or another path to adjust
your output's file layout."

It is a config-level rule (not a type error) and it fires on plugin packages
during `pnpm run check`, which the CLI packaging step runs before bundling.

Cause in this repo: a package whose `include` spans its own sources *and*
`../../../types/**/*.d.ts` (files outside the package directory) while also
setting `outDir`. TypeScript then cannot infer a single common source
directory and requires an explicit `rootDir`.

Fix: set `rootDir` to "." for affected configs that lack it. "." keeps the
output layout under the package directory (dist/<relative path>), matching
what `scripts/build.mjs` already expects, and does not weaken type checking.

Only files under plugins/packages/*/tsconfig.json are touched, and only when
they are missing "rootDir".
"""
import json
import pathlib
import sys

ROOT = pathlib.Path("plugins/packages")
changed = []
skipped = []

for tsconfig in sorted(ROOT.glob("*/tsconfig.json")):
    try:
        raw = tsconfig.read_text(encoding="utf-8")
        data = json.loads(raw)
    except Exception as error:
        skipped.append((str(tsconfig), f"unparsable: {error}"))
        continue

    options = data.get("compilerOptions")
    if not isinstance(options, dict):
        skipped.append((str(tsconfig), "no compilerOptions"))
        continue
    if "rootDir" in options:
        continue

    options["rootDir"] = "."
    tsconfig.write_text(
        json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    changed.append(str(tsconfig))

print(f"patched {len(changed)} tsconfig file(s):")
for item in changed:
    print(f"  {item}")
for item, why in skipped:
    print(f"skipped {item}: {why}")

sys.exit(0)
