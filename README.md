Kothic MapCSS renderer and style/drules processor.

This branch keeps the original Kothic/Kontur renderer and MVT/Mapbox helpers,
while also carrying the MapsMe, Organic Maps, and CoMaps style compiler
behaviour in the shared MapCSS/libkomwm path.

Dependencies:
* Python >= 3.8

Python dependencies:
```bash
pip3 install -r requirements.txt
```

## Running unittests

To run all unittests execute next command from project root folder:

```bash
python3 -m unittest discover -s tests
```

this will search for all `test*.py` files within `tests` directory
and execute tests from those files.

## Running integration tests

File `integration-tests/full_drules_gen.py` is intended to generate drules
files for all 6 themes from main CoMaps repo. It could be used to understand
which parts of the project are actually used by CoMaps repo.

Usage:

```shell
cd integration-tests
python3 full_drules_gen.py -d ../../../data -o drules --txt
```

This command will run generation for styles - default light, default dark,
outdoors light, outdoors dark, vehicle light, vehicle dark and put `*.bin`
and `*.txt` files into 'drules' subfolder.

## Compatibility notes

The repository intentionally supports several consumers that diverged in forks:

* `src/libkomwm.py` keeps MapsMe/Organic Maps/CoMaps drules generation,
  including priority file imports and `--format-priorities-only`.
* `src/libkomb.py` and `src/mvt_sql.py` keep the original Kothic MVT/Mapbox
  paths. The MapCSS package still exports `_test_feature_compatibility` for
  these legacy helpers.
* Runtime-condition filtering is opt-in: callers that pass no runtime filter get
  the old unfiltered Kothic style resolution, while drules generation can ask
  for exact runtime-selector variants.
