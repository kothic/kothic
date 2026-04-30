# Fork reconciliation notes

This repository is the upstream Kothic codebase, but several map projects kept
their own Kothic forks.  The modernization branch keeps one Python 3 codebase
and exposes compatibility switches for the places where the forks intentionally
or historically diverged.

## Compatibility modes

`src/libkomwm.py` has two independent knobs:

- `--priority-mode priority_files`
  uses the Organic Maps / CoMaps priority-file pipeline.
- `--priority-mode mapsme`
  uses the legacy MAPS.ME arithmetic priority pipeline.
- `--runtime-condition-mode organicmaps`
  deduplicates runtime-condition variants and uses exact runtime filtering.
- `--runtime-condition-mode comaps`
  deduplicates variants and also emits an unfiltered fallback variant.
- `--runtime-condition-mode mapsme`
  preserves the raw MAPS.ME runtime-condition variants.
- `--runtime-condition-mode mapsme-fallback`
  preserves the raw MAPS.ME variants and also emits an unfiltered fallback.

The default direct CLI max zoom is `20` for priority-file mode and `19` for
`--priority-mode mapsme`.  MAPS.ME's `tools/unix/generate_drules.sh` does not
pass `-t`, and the historical MAPS.ME Kothic default was `19`.

## Upstream Kothic

The original project has the renderer and MapCSS parser surface.  The active
modernization keeps the original renderer/MVT helpers, ports the code to
Python 3, and avoids making fork-specific behavior the default unless a
compatibility switch selects it.

Relevant preservation points:

- `komap.py` remains import-safe and CLI-driven.
- legacy helpers used by `libkomb` / MVT code remain exported.
- generated `drules_struct_pb2.py` is treated as generated code and excluded
  from ruff style enforcement.

## MAPS.ME fork

There are two different MAPS.ME baselines:

1. `mapsme/kothic` latest fork head in this workspace:
   `cbaff545dd5d2343dcbd30285884dd4afa509d93` from 2020.
2. the `tools/kothic` submodule recorded by the checked-out `omim` tree:
   `c32d9c5e22d6f42c582c2234e9881cda5f6db4f5` from 2016.

The `--priority-mode mapsme --runtime-condition-mode mapsme` path targets the
latest `mapsme/kothic` fork behavior.  It intentionally keeps these legacy
details:

- max zoom default `19` when no `-t` is provided directly to `libkomwm.py`;
- legacy z-index clamp with negative z-index offset;
- chooser-tree matching against all classificator tags, not only the first tag;
- raw runtime-condition variant list;
- subset runtime-condition filtering;
- legacy line, casing, icon, circle, text, and area priority arithmetic;
- legacy casing from area styles when the class has lines;
- explicit empty `dashdot {}` serialization for MAPS.ME casing lines;
- old text primary/secondary assignment from the fork code.

Verified regenerated `.bin` outputs matched the latest MAPS.ME fork oracle for
all four style files found in `omim/data/styles`:

- `clear/style-clear/style.mapcss`
- `clear/style-night/style.mapcss`
- `legacy/style-dark/style.mapcss`
- `legacy/style-light/style.mapcss`

The `.txt` output from the temporary Python 3 oracle can differ cosmetically
from current protobuf text formatting (`2.0` versus `2`), so binary protobuf
comparison is the authoritative check for MAPS.ME.

### Checked-in omim drules

The checked-out `omim` tree has checked-in files:

- `data/drules_proto_clear.bin`
- `data/drules_proto_dark.bin`
- `data/drules_proto_legacy.bin`
- `data/drules_proto.bin`
- `data/drules_proto-bw.bin`

`tools/unix/generate_drules.sh` builds only:

- `clear/style-clear/style.mapcss` -> `drules_proto_clear`
- `clear/style-night/style.mapcss` -> `drules_proto_dark`
- `legacy/style-light/style.mapcss` -> `drules_proto_legacy`
- merged `drules_proto` from clear + legacy

The checked-in files do not match regeneration with the latest `mapsme/kothic`
fork behavior.  That is expected from repository history:

- checked-in `drules_proto_clear.bin` last changed at `efbce784d7`
  (`Ran the script`, 2016-06-03);
- current `omim` records `tools/kothic` submodule `c32d9c5`, not the latest
  `mapsme/kothic` head;
- the submodule is not initialized in this checkout;
- the current `mapcss-mapping.csv` contains duplicate active type
  `tourism|information|office`, which the unpatched old MAPS.ME Kothic rejects.

Observed first structural difference for current sources is caption
primary/secondary ordering on `aeroway-aerodrome`; current latest-fork output
places `int_name` in primary for that style ordering, while checked-in omim
drules place the name caption in primary.  There are also class/element count
differences, for example checked-in clear has `586` containers / `4159`
elements while latest-fork regeneration at z0-19 has `585` / `3911`.

Do not treat the checked-in omim drules as the oracle for latest
`mapsme/kothic`.  To reproduce those files exactly, add a separate
`mapsme-2016` compatibility target against submodule `c32d9c5`; do not change
the current `mapsme` mode, because it is already byte-compatible with the
latest MAPS.ME fork.

## Organic Maps fork

Organic Maps uses the priority-file compiler path and six style outputs:

- `default_light`
- `default_dark`
- `outdoors_light`
- `outdoors_dark`
- `vehicle_light`
- `vehicle_dark`

The compatibility path is:

```sh
python3 integration-tests/full_drules_gen.py \
  --runtime-condition-mode organicmaps \
  --name-prefix drules_proto_ \
  -d /path/to/organicmaps/data \
  -o /tmp/ours \
  --compare-baseline /tmp/fork
```

Relevant behavior:

- default max zoom is `20` in the integration generator;
- runtime-condition variants are deduplicated;
- runtime filtering is strict exact-match for priority-file mode;
- priorities come from `*.prio.txt` files;
- `casing-width-add` and priority-file visibility/validation behavior are kept
  in the priority-file path, not in MAPS.ME mode.

The current branch was verified against the Organic Maps fork worktree: all six
`.bin` and `.txt` files matched the fork output.

## CoMaps fork

CoMaps is closest to Organic Maps but keeps a different runtime-condition
fallback convention.  The compatibility path is:

```sh
python3 integration-tests/full_drules_gen.py \
  --runtime-condition-mode comaps \
  -d /path/to/comaps/data \
  -o /tmp/ours \
  --compare-baseline /tmp/fork
```

Relevant behavior:

- default max zoom is `20` in the integration generator;
- runtime-condition variants are deduplicated;
- an unfiltered fallback variant is emitted after the deduplicated runtime
  conditions;
- priority-file behavior remains strict exact filtering.

The current branch was verified against the CoMaps fork worktree: all six
`.bin` and `.txt` files matched the fork output.

## What to test before changing shared compiler code

Run the cheap checks first:

```sh
python3 -m unittest discover -s tests
ruff check src tests integration-tests/full_drules_gen.py --exclude=src/drules_struct_pb2.py --target-version=py39
python3 -m compileall -q src tests integration-tests
git diff --check
```

For behavior changes in `libkomwm.py`, also regenerate and compare the fork
outputs:

- Organic Maps: six `.bin` and `.txt` outputs, `organicmaps` mode.
- CoMaps: six `.bin` and `.txt` outputs, `comaps` mode.
- MAPS.ME latest fork: binary protobuf outputs for all found style files,
  `--priority-mode mapsme --runtime-condition-mode mapsme -t 19`.

Keep checked-in omim drules as a separate historical baseline until a dedicated
`mapsme-2016` mode is added.
