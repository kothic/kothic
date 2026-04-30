import sys
import unittest
from pathlib import Path


# Add repository root to the import paths for package-style imports.
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import libkomb
from src import mvt_sql
from src.mapcss import Condition


class KothicMvtHelpersTest(unittest.TestCase):
    def tearDown(self):
        mvt_sql.mapped_cols.clear()
        mvt_sql.osm2pgsql_avail_keys.clear()

    def test_mapbox_expression_collapses_repeated_zoom_values(self):
        self.assertEqual(
            libkomb.to_mapbox_expression({1: "minor", 2: "minor", 3: "major"}),
            ["step", ["zoom"], "minor", 1, "minor", 3, "major"]
        )

        self.assertEqual(
            libkomb.to_mapbox_expression({1: "same", 2: "same"}),
            "same"
        )

    def test_mapbox_condition_converts_basic_tag_checks(self):
        self.assertEqual(
            libkomb.to_mapbox_condition(Condition("eq", ("highway", "primary"))),
            ["==", ["get", "highway"], "primary"]
        )
        self.assertEqual(
            libkomb.to_mapbox_condition(Condition("set", ("name",))),
            ["to-boolean", ["get", "name"]]
        )

    def test_mvt_sql_uses_hstore_fallback_for_unavailable_columns(self):
        mvt_sql.osm2pgsql_avail_keys["name"] = ("point",)

        self.assertEqual(
            mvt_sql.escape_sql_column("name", "line"),
            "(tags->'name')"
        )
        self.assertEqual(
            mvt_sql.escape_sql_column("name", "line", asname=True),
            "(tags->'name') as \"name\""
        )

    def test_pixel_size_scales_by_zoom_and_pixel_count(self):
        self.assertAlmostEqual(
            mvt_sql.pixel_size_at_zoom(1, 2),
            mvt_sql.pixel_size_at_zoom(1) * 2
        )
        self.assertAlmostEqual(
            mvt_sql.pixel_size_at_zoom(2),
            mvt_sql.pixel_size_at_zoom(1) / 2
        )


if __name__ == '__main__':
    unittest.main()
