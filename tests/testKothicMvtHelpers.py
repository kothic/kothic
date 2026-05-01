import sys
import unittest
from pathlib import Path


# Add repository root to the import paths for package-style imports.
sys.path.insert(0, str(Path(__file__).parent.parent))

from src import libkomb
from src import libkomapnik
from src import mvt_sql
from src.mapcss import Condition


class KothicMvtHelpersTest(unittest.TestCase):
    def tearDown(self):
        mvt_sql.mapped_cols.clear()
        mvt_sql.osm2pgsql_avail_keys.clear()
        libkomapnik.db_password = ""
        libkomapnik.db_host = ""
        libkomapnik.db_port = ""

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

    def test_georgian_romanization_sql_uses_readable_mapping(self):
        sql = mvt_sql.georgian_romanization_sql("tags->'name:ka'")

        self.assertIn(
            "translate(tags->'name:ka','აბგდევზთიკლმნოპრსტუფქყჯჰ','abgdevztiklmnoprstupkqjh')",
            sql
        )
        self.assertIn("'ძ','dz'", sql)
        self.assertIn("'ხ','kh'", sql)
        self.assertIn("'ჟ','zh'", sql)
        self.assertNotIn("ts’", sql)

    def test_english_name_fallback_includes_georgian_romanization(self):
        class Style:
            choosers = []

            def get_all_tags(self, _obj):
                return {"name"}

            def get_interesting_tags(self, _obj, _zoom):
                return {"name"}

        mvt_sql.get_vectors(0, 0, 0, 0, Style(), "point", 4096, ["en"])

        name_en_sql = mvt_sql.mapped_cols["name:en"]

        self.assertIn("tags->'name:ka'", name_en_sql)
        self.assertIn("'ხ','kh'", name_en_sql)
        self.assertLess(
            name_en_sql.index("tags->'name:ka'"),
            name_en_sql.index("tags->'name:be'")
        )

    def test_postgis_connection_parameters_are_optional(self):
        layer = libkomapnik.xml_layer("postgis", "point", ["name"], "true", zoom=10)

        self.assertNotIn('<Parameter name="password">', layer)
        self.assertNotIn('<Parameter name="host">', layer)
        self.assertNotIn('<Parameter name="port">', layer)

    def test_postgis_connection_parameters_are_rendered_when_configured(self):
        libkomapnik.db_password = "secret&safe"
        libkomapnik.db_host = "db.example.test"
        libkomapnik.db_port = "5433"

        layer = libkomapnik.xml_layer(
            "postgis-process",
            "polygon",
            ["name"],
            "select way, name from planet_osm_polygon",
            zoom=10
        )

        self.assertIn('<Parameter name="password">secret&amp;safe</Parameter>', layer)
        self.assertIn('<Parameter name="host">db.example.test</Parameter>', layer)
        self.assertIn('<Parameter name="port">5433</Parameter>', layer)


if __name__ == '__main__':
    unittest.main()
