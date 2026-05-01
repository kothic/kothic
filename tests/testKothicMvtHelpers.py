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
        libkomapnik.icons_path = ""
        libkomapnik.text_scale = 1
        libkomapnik.default_font_family = ""
        libkomapnik.max_char_angle_delta = ""
        libkomapnik.font_tracking = 0

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

    def test_mapnik_point_and_line_marker_symbolizers_keep_expected_attributes(self):
        libkomapnik.icons_path = "/icons"

        point = libkomapnik.xml_pointsymbolizer(
            "poi.svg",
            width="12",
            height="14",
            opacity="0.5",
            overlap="true",
        )
        line_marker = libkomapnik.xml_linemarkerssymbolizer(
            "dash.svg",
            spacing="64",
            allow_overlap="true",
        )
        line_pattern = libkomapnik.xml_linepatternsymbolizer("pattern.svg")

        self.assertIn('<MarkersSymbolizer file="/icons/poi.svg"', point)
        self.assertIn('width="12"', point)
        self.assertIn('height="14"', point)
        self.assertIn('opacity="0.5"', point)
        self.assertIn('allow-overlap="true"', point)
        self.assertIn('placement="point"', point)
        self.assertIn('<MarkersSymbolizer file="/icons/dash.svg"', line_marker)
        self.assertIn('spacing="64"', line_marker)
        self.assertIn('placement="line"', line_marker)
        self.assertIn('<LinePatternSymbolizer file="/icons/pattern.svg"', line_pattern)

    def test_mapnik_text_and_shield_symbolizers_keep_spacing_and_scaling(self):
        libkomapnik.icons_path = "/icons/"
        libkomapnik.text_scale = 2

        text = libkomapnik.xml_textsymbolizer(
            text="name",
            face="Inter",
            size="8,12",
            color="red",
            halo_color="white",
            halo_radius="1",
            character_spacing="3",
            placement="center",
            offset="4",
            overlap="true",
            distance="32",
            wrap_width="120",
            align="left",
            opacity="0.8",
            pos="exact",
            transform="uppercase",
            spacing="128",
            angle="30",
        )
        shield = libkomapnik.xml_shieldsymbolizer(
            path="shield.svg",
            width="16",
            height="18",
            text="ref",
            face="Inter",
            size="7,11",
            color="blue",
            halo_color="white",
            halo_radius="2",
            placement="center",
            offset="5",
            overlap="true",
            distance="42",
            wrap_width="90",
            align="center",
            opacity="0.7",
            transform="lowercase",
            unlock_image="false",
            spacing="256",
        )

        self.assertIn('fontset-name="Inter"', text)
        self.assertIn('size="16.0"', text)
        self.assertIn('fill="#FF0000"', text)
        self.assertIn('character-spacing="3"', text)
        self.assertIn('placement="interior"', text)
        self.assertIn('dx="4"', text)
        self.assertIn('dy="0"', text)
        self.assertIn('max-char-angle-delta="30"', text)
        self.assertIn('placements="X,16,24"', text)
        self.assertIn('text-transform="uppercase"', text)
        self.assertIn('[name]', text)

        self.assertIn('<ShieldSymbolizer file="/icons/shield.svg"', shield)
        self.assertIn('width="16"', shield)
        self.assertIn('height="18"', shield)
        self.assertIn('fontset-name="Inter"', shield)
        self.assertIn('size="14.0"', shield)
        self.assertIn('fill="#0000FF"', shield)
        self.assertIn('placement="point"', shield)
        self.assertIn('dy="5"', shield)
        self.assertIn('horizontal-alignment="middle"', shield)
        self.assertIn('unlock-image="false"', shield)
        self.assertIn('spacing="256"', shield)
        self.assertIn('[ref]', shield)


if __name__ == '__main__':
    unittest.main()
