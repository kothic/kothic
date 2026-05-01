import sys
import tempfile
import unittest
from pathlib import Path


# Add repository root to the import paths for package-style imports.
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import mapcss_benchmark_parse


class MapcssBenchmarkParseTest(unittest.TestCase):
    def test_parse_style_reports_basic_stats(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            stylesheet = Path(tmpdir) / "fixture.mapcss"
            stylesheet.write_text(
                "node[amenity=cafe] { icon-image: cafe; }\n"
                "way[highway=primary] { width: 2; }\n",
                encoding="utf-8",
            )

            stats = mapcss_benchmark_parse.parse_style(stylesheet)

        self.assertEqual(stats["path"], str(stylesheet))
        self.assertEqual(stats["lines"], 2)
        self.assertGreater(stats["bytes"], 0)
        self.assertEqual(stats["static_tags"], 2)
        self.assertGreaterEqual(stats["seconds"], 0)
        self.assertEqual(stats["choosers"], 2)
        self.assertEqual(stats["rule_chains"], 2)

    def test_infer_static_tags_from_conditions(self):
        self.assertEqual(
            mapcss_benchmark_parse.infer_static_tags("""
                node[amenity=cafe] { icon-image: cafe; }
                way[highway] { width: 2; }
                /* CSS-ish prose can mention ranges like [12, 15]. */
                *[name?] { text: name; }
            """),
            {"amenity": True, "highway": True, "name": True}
        )

    def test_parse_style_infers_tags_from_imports(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            fixture_dir = Path(tmpdir)
            stylesheet = fixture_dir / "main.mapcss"
            stylesheet.write_text('@import("roads.mapcss");\n', encoding="utf-8")
            (fixture_dir / "roads.mapcss").write_text(
                "way[highway=primary] { width: 2; }\n",
                encoding="utf-8",
            )

            stats = mapcss_benchmark_parse.parse_style(stylesheet)

        self.assertEqual(stats["static_tags"], 1)
        self.assertEqual(stats["choosers"], 1)

    def test_format_report_is_copyable(self):
        report = mapcss_benchmark_parse.format_report({
            "path": "style.mapcss",
            "bytes": 123,
            "lines": 4,
            "static_tags": 2,
            "seconds": 0.125,
            "choosers": 2,
            "rule_chains": 3,
        })

        self.assertIn("MapCSS parse benchmark", report)
        self.assertIn("path: style.mapcss", report)
        self.assertIn("static_tags: 2", report)
        self.assertIn("seconds: 0.125000", report)
