# Kothic JS lineage and migration notes

Kothic has several JavaScript-related branches of history.  They are related,
but they are not interchangeable implementations.

This document records the current technical map so parser and converter work can
move in small reviewed steps.

## Components

| Component | Repository/path | Role | Current status |
| --- | --- | --- | --- |
| Python Kothic core | `kothic/kothic` | MapCSS parser, legacy renderer helpers, MVT/Mapbox helpers, and fork-compatible drules generation. | Active source of truth for the modern Python code. |
| Removed in-tree JS converter | `src/libkojs.py` | Emitted a bare `restyle(prop, zoom, type)` JavaScript function from the current Python `MapCSS` object. | Removed after `komap.py --renderer js` moved to `src/kothic_js.py`; it was too small for full `kothic-js` style modules. |
| Current JS converter path | `src/kothic_js.py` | Collects metadata and emits `kothic-js` style modules from the in-tree parser. | New compatibility path; currently covers style declarations and a guarded subset of `eval()` expressions. |
| Removed in-tree JS demo/runtime files | `src/javascript/*` | Old browser rendering/demo surface checked into the Python repository. | Removed as stale; use `kothic/kothic-js` as the browser runtime target. |
| Browser renderer | `kothic/kothic-js` | Original HTML5 Canvas renderer.  Styles are registered through `MapCSS.loadStyle(...)`. | Legacy but still the compatibility target for generated JS style modules. |
| Standalone style preprocessor | `kothic/kothic-js-mapcss` | Python 2 era converter from MapCSS into `kothic-js` JavaScript style modules. | Useful behavior should move into this repository before that repo is archived. |
| Node parser/renderer stack | `kothic/mapcss-node`, `kothic/kothic-node` | Separate Node.js MapCSS parser and server-side rendering path. | Related lineage, not a drop-in replacement for the Python parser or `kothic-js-mapcss`. |

## What `kothic-js` Expects

The browser renderer does not only need a `restyle` function.  A normal generated
style module calls:

```js
MapCSS.loadStyle(
    name,
    restyle,
    sprite_images,
    external_images,
    presence_tags,
    value_tags
);
```

Those metadata arrays and image maps are used by `kothic-js` for style loading,
image preloading, and style cache keys.  The replacement in `src/kothic_js.py`
therefore preserves at least:

- `MapCSS.loadStyle(...)` output shape;
- `sprite_images`;
- `external_images`;
- `presence_tags`;
- `value_tags`;
- subpart-aware style output;
- documented behavior for eval expressions and unsupported legacy cases.

The new in-tree converter entry point is:

```sh
PYTHONPATH=src python3 src/kothic_js.py \
  --mapcss tests/assets/kothic-js-mapcss/surface.mapcss \
  --name surface
```

The main `komap.py` CLI also routes JavaScript output through this converter:

```sh
python3 -m src.komap \
  --renderer js \
  --stylesheet tests/assets/kothic-js-mapcss/surface.mapcss \
  --style-name surface
```

The converter infers selector tags before parsing so legacy MapCSS files do not
need a manually maintained tag list.  Use `--static-tag key:true|false` only as
an override, and `--dynamic-tag` for runtime-dynamic tags.

## Historical Styles

This repository no longer bundles the old `osmosnimki-*` style files.  They were
only used by stale in-tree demo paths, which now point at `styles/default.mapcss`.
Compatibility tests that compare against historical `kothic-js-mapcss` output use
external legacy checkout paths, so the historical style corpus can stay in its
own repository until that repository is explicitly retired.

## Why `src/libkojs.py` Was Removed

`src/libkojs.py` walked the Python `style.choosers` structure and wrote a small
JavaScript `restyle` function.  It did not emit a complete
`kothic-js` style module and does not generate the metadata that `kothic-js`
uses around `restyle`.

The useful migration target is therefore not "keep `libkojs.py` as-is".  The
target is:

1. keep the parser source of truth in `kothic/kothic`;
2. port the useful `kothic-js-mapcss` converter behavior onto that parser,
   starting with `src/kothic_js.py`;
3. keep `komap.py --renderer js` routed to the complete `kothic-js` style module
   converter;
4. validate generated output against `kothic-js`.

## Parser Direction

The current Python MapCSS parser is the compatibility-critical path for:

- MVT/Mapbox style output;
- MapsMe, Organic Maps, and CoMaps drules generation;
- the current `kothic-js` style converter.

Parser work should start with characterization tests, then move internals toward
a clearer AST and parser boundary.  Useful ideas from
`Miroff/mapcss-parser` include:

- first-class AST nodes;
- lexer/parser separation;
- imports;
- subparts;
- eval expressions;
- `set` statements;
- `@supports`;
- parser fixtures.

Do not copy the old runtime shape blindly: it is Python 2 era code and the old
converter extends it by monkey-patching AST classes externally.

## Migration Order

1. Add parser and converter characterization tests.
2. Refactor the parser behind the existing public `MapCSS` and `StyleChooser`
   behavior.
3. Keep `komap.py --renderer js` backed by the complete `kothic-js` style module
   converter.
4. Test generated modules with `kothic-js`, including image metadata and cache
   tag metadata.
5. Update `kothic-js-mapcss` to point to the new home and archive it only after
   the replacement path works.

## Compatibility Rule

Do not archive `kothic-js-mapcss` before the new converter in `kothic/kothic`
can produce output that `kothic-js` can consume.  Until then, the standalone
repository remains the discoverable historical implementation for that workflow.
