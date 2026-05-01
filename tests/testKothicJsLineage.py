import sys
import unittest
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

# Add `src` directory to the import paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from mapcss import MapCSS
from mapcss.Eval import Eval
from kothic_js import collect_metadata, convert_file, generate_style_module, infer_static_tags, prepare_css_for_js_conversion


class KothicJsLineageTest(unittest.TestCase):
    def parse_fixture(self, name, static_tags, **parse_kwargs):
        parser = MapCSS()
        parser.parse(
            filename=str(Path(__file__).parent / "assets" / "kothic-js-mapcss" / name),
            static_tags=static_tags,
            **parse_kwargs,
        )
        return parser

    def test_parser_exposes_inputs_needed_by_kothic_js_converter(self):
        parser = MapCSS()
        parser.parse("""
@road_width: 2;

line|z10-12[highway=primary]::casing {
  width: eval(num(tag("lanes")) + @road_width);
  color: #ffffff;
}

node|z14-[amenity] {
  icon-image: cafe.svg;
  text: name;
}
""", static_tags={
            "amenity": True,
            "highway": True,
        })

        self.assertEqual(len(parser.choosers), 2)

        line_chooser = parser.choosers[0]
        line_rule = line_chooser.ruleChains[0]
        self.assertEqual(line_rule.subject, "line")
        self.assertEqual(line_rule.minZoom, 10)
        self.assertEqual(line_rule.maxZoom, 12)
        self.assertEqual(line_rule.test({"highway": "primary"}), "::casing")
        self.assertIn("line", line_chooser.compatible_types)
        self.assertIn("area", line_chooser.compatible_types)
        self.assertEqual(line_chooser.extract_tags(), {"highway", "lanes"})
        self.assertIsInstance(line_chooser.styles[0]["width"], Eval)
        self.assertEqual(line_chooser.styles[0]["color"], (1.0, 1.0, 1.0))

        point_chooser = parser.choosers[1]
        point_rule = point_chooser.ruleChains[0]
        self.assertEqual(point_rule.subject, "node")
        self.assertEqual(point_rule.minZoom, 14)
        self.assertEqual(point_rule.maxZoom, 19)
        self.assertEqual(point_chooser.extract_tags(), {"amenity"})
        self.assertEqual(point_chooser.styles[0]["icon-image"], "cafe.svg")
        self.assertEqual(point_chooser.styles[0]["text"], "name")

    def test_collect_metadata_matches_kothic_js_style_module_contract(self):
        parser = MapCSS()
        parser.parse("""
line|z10-[highway=primary][bridge]::casing {
  width: eval(num(tag("lanes")) + 2);
}

node|z14-[amenity] {
  icon-image: cafe.svg;
  text: name;
}
""", static_tags={
            "amenity": True,
            "bridge": False,
            "highway": True,
        })

        metadata = collect_metadata(parser)

        self.assertEqual(metadata.sprite_images, {})
        self.assertEqual(metadata.external_images, ["cafe.svg"])
        self.assertEqual(metadata.presence_tags, ["amenity", "bridge"])
        self.assertEqual(metadata.value_tags, ["highway", "lanes", "name"])
        self.assertEqual(metadata.subparts, ["casing", "default"])

    def test_generate_style_module_emits_kothic_js_loadstyle_shape(self):
        parser = MapCSS()
        parser.parse("""
line|z10-12[highway=primary]::casing {
  width: 2;
  color: #ffffff;
}

node|z14-[amenity] {
  icon-image: cafe.svg;
  text: name;
}
""", static_tags={
            "amenity": True,
            "highway": True,
        })

        js = generate_style_module(parser, "fixture")

        self.assertIn("function restyle(style, tags, zoom, type, selector)", js)
        self.assertIn("var s_casing = {}, s_default = {};", js)
        self.assertIn(
            'if ((type === "way" && zoom >= 10 && zoom <= 12 && tags["highway"] === "primary"))',
            js,
        )
        self.assertIn('s_casing["width"] = 2;', js)
        self.assertIn('s_casing["color"] = "#ffffff";', js)
        self.assertIn('s_default["icon-image"] = "cafe.svg";', js)
        self.assertIn('s_default["text"] = MapCSS.e_localize(tags, "name");', js)
        self.assertIn('external_images = ["cafe.svg"]', js)
        self.assertIn('presence_tags = ["amenity"]', js)
        self.assertIn('value_tags = ["highway", "name"]', js)
        self.assertIn('MapCSS.loadStyle("fixture", restyle, sprite_images, external_images, presence_tags, value_tags);', js)
        self.assertIn('MapCSS.preloadExternalImages("fixture");', js)

    def test_generate_style_module_emits_eval_expressions(self):
        parser = MapCSS()
        parser.parse("""
line|z10-[highway=primary]::casing {
  width: eval(num(tag("lanes")) + 2);
  text-offset: eval(cond(boolean(tag("name")), metric("4m"), 0));
}
""", static_tags={
            "highway": True,
        })

        js = generate_style_module(parser, "fixture")

        self.assertIn(
            's_casing["width"] = (MapCSS.e_num(MapCSS.e_tag(tags, "lanes")) + 2);',
            js,
        )
        self.assertIn(
            's_casing["text-offset"] = (MapCSS.e_boolean(MapCSS.e_tag(tags, "name")) ? '
            'MapCSS.e_metric("4m") : 0);',
            js,
        )
        self.assertIn('value_tags = ["highway", "lanes", "name"]', js)

    def test_generate_style_module_handles_historical_surface_fixture(self):
        parser = self.parse_fixture("surface.mapcss", {
            "highway": True,
            "surface": False,
        }, clamp=False)

        js = generate_style_module(parser, "surface")
        metadata = collect_metadata(parser)

        self.assertEqual(metadata.presence_tags, ["surface"])
        self.assertEqual(metadata.value_tags, ["highway"])
        self.assertEqual(metadata.subparts, ["default", "overlay"])
        self.assertIn(
            'if ((type === "way" && tags["highway"] === "primary" && !tags.hasOwnProperty("surface")))',
            js,
        )
        self.assertIn('s_overlay["color"] = "#ff0000";', js)
        self.assertIn('s_overlay["width"] = 1;', js)
        self.assertIn('s_overlay["z-index"] = 100;', js)
        self.assertIn('style["overlay"] = s_overlay;', js)
        self.assertIn('MapCSS.loadStyle("surface", restyle, sprite_images, external_images, presence_tags, value_tags);', js)

    def test_convert_file_handles_historical_surface_fixture(self):
        fixture = Path(__file__).parent / "assets" / "kothic-js-mapcss" / "surface.mapcss"

        js = convert_file(
            fixture,
            name="surface",
        )

        self.assertIn('MapCSS.loadStyle("surface", restyle, sprite_images, external_images, presence_tags, value_tags);', js)
        self.assertIn('s_overlay["z-index"] = 100;', js)

    def test_convert_file_handles_historical_osmosnimki_poi_fixture(self):
        fixture = Path(__file__).parent / "assets" / "kothic-js-mapcss" / "osmosnimki-poi.mapcss"

        js = convert_file(
            fixture,
            name="osmosnimki-poi",
        )

        self.assertIn('external_images = ["cinema_14x14.png", "hotell_14x14.png"]', js)
        self.assertIn('value_tags = ["amenity", "name", "tourism"]', js)
        self.assertIn('s_default["icon-image"] = "cinema_14x14.png";', js)
        self.assertIn('s_default["icon-image"] = "hotell_14x14.png";', js)
        self.assertIn('s_default["text"] = MapCSS.e_localize(tags, "name");', js)
        self.assertIn('s_default["text-offset"] = 3;', js)
        self.assertIn('s_default["font-size"] = "9";', js)
        self.assertIn('s_default["text-color"] = "#623f00";', js)
        self.assertIn('MapCSS.loadStyle("osmosnimki-poi", restyle, sprite_images, external_images, presence_tags, value_tags);', js)

    def test_infer_static_tags_from_historical_fixtures(self):
        fixture = Path(__file__).parent / "assets" / "kothic-js-mapcss" / "osmosnimki-poi.mapcss"

        self.assertEqual(infer_static_tags(fixture), {
            "amenity": False,
            "tourism": False,
        })

    def test_generate_style_module_preserves_yes_no_condition_semantics(self):
        parser = MapCSS()
        parser.parse("""
line|z12-[oneway?] {
  width: 3;
}

line|z12-[!bridge?] {
  width: 2;
}
""", static_tags={
            "bridge": True,
            "oneway": True,
        })

        js = generate_style_module(parser, "boolean-tags")
        metadata = collect_metadata(parser)

        self.assertEqual(metadata.presence_tags, [])
        self.assertEqual(metadata.value_tags, ["bridge", "oneway"])
        self.assertIn(
            'tags["oneway"] === \'1\' || tags["oneway"] === \'true\' || tags["oneway"] === \'yes\'',
            js,
        )
        self.assertIn(
            '!tags.hasOwnProperty("bridge") || tags["bridge"] === \'-1\' || '
            'tags["bridge"] === \'false\' || tags["bridge"] === \'no\'',
            js,
        )

    def test_parser_and_js_converter_handle_hyphenated_subparts(self):
        parser = MapCSS()
        parser.parse("""
way|z13-14[waterway=stream][!tunnel?]::water_lines-casing,
way|z13-14[waterway=ditch][!tunnel?]::water_lines-casing {
  color: white;
  width: 1.5;
}
""", static_tags={
            "tunnel": True,
            "waterway": True,
        }, clamp=False)

        metadata = collect_metadata(parser)
        js = generate_style_module(parser, "hyphenated")

        self.assertEqual(metadata.subparts, ["default", "water_lines_casing"])
        self.assertIn("var s_default = {}, s_water_lines_casing = {};", js)
        self.assertIn('s_water_lines_casing["color"] = "#ffffff";', js)
        self.assertIn('style["water_lines_casing"] = s_water_lines_casing;', js)

    def test_js_converter_neutralizes_unsupported_parent_selectors(self):
        fixture = Path(__file__).parent / "assets" / "kothic-js-mapcss" / "parent-selector.mapcss"

        prepared = prepare_css_for_js_conversion(fixture)
        self.assertIn("__kothic_js_unsupported_parent_selector__", prepared)

        js = convert_file(fixture, name="parent-selector")

        self.assertIn('selector === "__kothic_js_unsupported_parent_selector__"', js)
        self.assertIn('s_turning_circle_casing["icon-image"] = "symbols/turning_circle-tert-casing.18.png";', js)

    def test_js_converter_ignores_single_colon_pseudoclasses_as_subparts(self):
        parser = MapCSS()
        parser.parse("""
way:closed {
  width: 1;
}
""", clamp=False)

        metadata = collect_metadata(parser)
        js = generate_style_module(parser, "pseudoclass")

        self.assertEqual(metadata.subparts, ["default"])
        self.assertIn("var s_default = {};", js)
        self.assertNotIn("s_:closed", js)

    def test_generated_surface_style_runs_in_kothic_js_runtime(self):
        fixture = Path(__file__).parent / "assets" / "kothic-js-mapcss" / "surface.mapcss"
        payload = self.run_in_kothic_js_runtime(
            convert_file(fixture, name="surface"),
            "surface",
            [{
                "tags": {"highway": "primary"},
                "zoom": 12,
                "type": "way",
                "selector": "line",
            }],
        )

        self.assertEqual(payload["availableStyles"], ["surface"])
        self.assertEqual(payload["presenceTags"], ["surface"])
        self.assertEqual(payload["valueTags"], ["highway"])
        self.assertEqual(payload["results"], [{
            "overlay": {
                "color": "#ff0000",
                "width": 1,
                "z-index": 100,
            },
        }])

    def test_generated_poi_style_runs_in_kothic_js_runtime(self):
        fixture = Path(__file__).parent / "assets" / "kothic-js-mapcss" / "osmosnimki-poi.mapcss"
        payload = self.run_in_kothic_js_runtime(
            convert_file(fixture, name="osmosnimki-poi"),
            "osmosnimki-poi",
            [{
                "tags": {"tourism": "hotel", "name": "Central"},
                "zoom": 17,
                "type": "node",
                "selector": "node",
            }],
        )

        self.assertEqual(payload["availableStyles"], ["osmosnimki-poi"])
        self.assertEqual(payload["presenceTags"], [])
        self.assertEqual(payload["valueTags"], ["amenity", "name", "tourism"])
        self.assertEqual(payload["results"], [{
            "default": {
                "icon-image": "hotell_14x14.png",
                "text": "Central",
                "text-offset": 3,
                "font-size": "9",
                "text-halo-radius": 1,
                "text-color": "#623f00",
                "text-halo-color": "#ffffff",
            },
        }])

    def test_generated_surface_style_matches_legacy_runtime_behavior(self):
        fixture = Path(__file__).parent / "assets" / "kothic-js-mapcss" / "surface.mapcss"
        legacy_style = Path("/home/kom/tmp/kothic-audit-kothic-js/debug/styles/surface.js")
        if not legacy_style.exists():
            self.skipTest("legacy kothic-js surface style is required for comparison")

        cases = [{
            "tags": {"highway": "primary"},
            "zoom": 12,
            "type": "way",
            "selector": "line",
        }, {
            "tags": {"highway": "primary", "surface": "asphalt"},
            "zoom": 12,
            "type": "way",
            "selector": "line",
        }]

        generated = self.run_in_kothic_js_runtime(
            convert_file(fixture, name="surface"),
            "surface",
            cases,
        )
        legacy = self.run_in_kothic_js_runtime(
            legacy_style.read_text(),
            "surface",
            cases,
        )

        self.assertEqual(
            self.normalize_runtime_payload(generated),
            self.normalize_runtime_payload(legacy),
        )

    def test_generated_osmosnimki_style_matches_legacy_poi_runtime_behavior(self):
        legacy_mapcss = Path(os.environ.get(
            "KOTHIC_JS_LEGACY_OSMOSNIMKI_MAPCSS",
            "/home/kom/tmp/kothic-js-mapcss-cleanup/styles/osmosnimki-maps.mapcss",
        ))
        legacy_style = Path(os.environ.get(
            "KOTHIC_JS_LEGACY_OSMOSNIMKI_STYLE",
            "/home/kom/tmp/kothic-audit-kothic-js/debug/styles/osmosnimki.js",
        ))
        if not legacy_mapcss.exists() or not legacy_style.exists():
            self.skipTest("legacy osmosnimki MapCSS and generated JS are required for comparison")

        cases = [{
            "tags": {"amenity": "cinema", "name": "Cinema"},
            "zoom": 16,
            "type": "node",
            "selector": "node",
        }, {
            "tags": {"tourism": "hotel", "name": "Hotel"},
            "zoom": 17,
            "type": "node",
            "selector": "node",
        }]

        generated = self.run_in_kothic_js_runtime(
            convert_file(legacy_mapcss, name="osmosnimki"),
            "osmosnimki",
            cases,
        )
        legacy = self.run_in_kothic_js_runtime(
            legacy_style.read_text(),
            "osmosnimki",
            cases,
        )

        self.assertEqual(generated["results"], legacy["results"])
        self.assertEqual(generated["presenceTags"], legacy["presenceTags"])
        self.assertEqual(
            set(legacy["valueTags"]) - set(generated["valueTags"]),
            {"building "},
        )
        self.assertEqual(set(generated["valueTags"]) - set(legacy["valueTags"]), set())

    def test_generated_osmosnimki_style_matches_legacy_mixed_runtime_behavior(self):
        legacy_mapcss = Path(os.environ.get(
            "KOTHIC_JS_LEGACY_OSMOSNIMKI_MAPCSS",
            "/home/kom/tmp/kothic-js-mapcss-cleanup/styles/osmosnimki-maps.mapcss",
        ))
        legacy_style = Path(os.environ.get(
            "KOTHIC_JS_LEGACY_OSMOSNIMKI_STYLE",
            "/home/kom/tmp/kothic-audit-kothic-js/debug/styles/osmosnimki.js",
        ))
        if not legacy_mapcss.exists() or not legacy_style.exists():
            self.skipTest("legacy osmosnimki MapCSS and generated JS are required for comparison")

        cases = [{
            "tags": {"natural": "glacier", "name": "Ice"},
            "zoom": 12,
            "type": "way",
            "selector": "area",
        }, {
            "tags": {"leisure": "park", "name": "Park"},
            "zoom": 10,
            "type": "way",
            "selector": "area",
        }, {
            "tags": {"building": "yes", "addr:housenumber": "12"},
            "zoom": 15,
            "type": "way",
            "selector": "area",
        }, {
            "tags": {"shop": "bakery", "name": "Bakery"},
            "zoom": 17,
            "type": "node",
            "selector": "node",
        }]

        generated = self.run_in_kothic_js_runtime(
            convert_file(legacy_mapcss, name="osmosnimki"),
            "osmosnimki",
            cases,
        )
        legacy = self.run_in_kothic_js_runtime(
            legacy_style.read_text(),
            "osmosnimki",
            cases,
        )

        self.assertEqual(
            self.normalize_runtime_payload(generated)["results"],
            self.normalize_runtime_payload(legacy)["results"],
        )

    def test_full_legacy_mapnik_style_generates_valid_javascript(self):
        legacy_mapcss = Path(os.environ.get(
            "KOTHIC_JS_LEGACY_MAPNIK_MAPCSS",
            "/home/kom/tmp/kothic-js-mapcss-cleanup/styles/mapnik.mapcss",
        ))
        if shutil.which("node") is None:
            self.skipTest("node is required for generated JavaScript syntax checks")
        if not legacy_mapcss.exists():
            self.skipTest("legacy mapnik MapCSS is required for full-style syntax check")

        js = convert_file(legacy_mapcss, name="mapnik")
        with tempfile.NamedTemporaryFile(mode="w", suffix=".js") as generated:
            generated.write(js)
            generated.flush()
            subprocess.run(
                ["node", "--check", generated.name],
                check=True,
                text=True,
                capture_output=True,
            )

    def test_generated_mapnik_style_matches_legacy_mixed_runtime_behavior(self):
        legacy_mapcss = Path(os.environ.get(
            "KOTHIC_JS_LEGACY_MAPNIK_MAPCSS",
            "/home/kom/tmp/kothic-js-mapcss-cleanup/styles/mapnik.mapcss",
        ))
        legacy_style = Path(os.environ.get(
            "KOTHIC_JS_LEGACY_MAPNIK_STYLE",
            "/home/kom/tmp/kothic-audit-kothic-js/debug/styles/mapnik.js",
        ))
        if not legacy_mapcss.exists() or not legacy_style.exists():
            self.skipTest("legacy mapnik MapCSS and generated JS are required for comparison")

        cases = [{
            "tags": {"leisure": "swimming_pool"},
            "zoom": 14,
            "type": "way",
            "selector": "area",
        }, {
            "tags": {"waterway": "stream"},
            "zoom": 15,
            "type": "way",
            "selector": "line",
        }, {
            "tags": {"amenity": "cinema", "name": "Cinema"},
            "zoom": 17,
            "type": "node",
            "selector": "node",
        }, {
            "tags": {"natural": "peak", "name": "Peak", "ele": "1234"},
            "zoom": 14,
            "type": "node",
            "selector": "node",
        }]

        generated = self.run_in_kothic_js_runtime(
            convert_file(legacy_mapcss, name="mapnik"),
            "mapnik",
            cases,
        )
        legacy = self.run_in_kothic_js_runtime(
            legacy_style.read_text(),
            "mapnik",
            cases,
        )

        self.assertEqual(
            self.normalize_runtime_payload(generated)["results"],
            self.normalize_runtime_payload(legacy)["results"],
        )
        self.assertEqual(
            set(legacy["presenceTags"]) - set(generated["presenceTags"]),
            {"bridge?", "captial?", "oneway?", "tunnel?"},
        )
        self.assertEqual(set(generated["presenceTags"]) - set(legacy["presenceTags"]), set())

    def normalize_runtime_payload(self, payload):
        color_names = {
            "black": "#000000",
            "blue": "#0000ff",
            "brown": "#a52a2a",
            "green": "#008000",
            "red": "#ff0000",
            "white": "#ffffff",
        }

        def normalize(value):
            if isinstance(value, dict):
                return {key: normalize(item) for key, item in value.items()}
            if isinstance(value, list):
                return [normalize(item) for item in value]
            if isinstance(value, str):
                if re.fullmatch(r"-?\d+\.0", value):
                    return value[:-2]
                if value == "#f00":
                    return "#ff0000"
                if re.fullmatch(r"#[0-9a-fA-F]{6}", value):
                    return value.lower()
                if value in color_names:
                    return color_names[value]
            return value

        return normalize(payload)

    def run_in_kothic_js_runtime(self, js, style_name, cases):
        runtime = Path(os.environ.get(
            "KOTHIC_JS_MAPCSS_RUNTIME",
            "/home/kom/tmp/kothic-audit-kothic-js/src/style/mapcss.js",
        ))
        smoke = Path(__file__).parent / "assets" / "kothic-js-mapcss" / "runtime_smoke.js"
        if shutil.which("node") is None:
            self.skipTest("node is required for kothic-js runtime smoke")
        if not runtime.exists():
            self.skipTest("set KOTHIC_JS_MAPCSS_RUNTIME to kothic-js src/style/mapcss.js")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".js") as generated:
            generated.write(js)
            generated.flush()
            result = subprocess.run(
                [
                    "node",
                    str(smoke),
                    str(runtime),
                    generated.name,
                    style_name,
                    json.dumps(cases),
                ],
                check=True,
                text=True,
                capture_output=True,
            )

        return json.loads(result.stdout)


if __name__ == "__main__":
    unittest.main()
