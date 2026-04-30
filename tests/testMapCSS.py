import unittest
import sys
from pathlib import Path

# Add `src` directory to the import paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from mapcss import parseDeclaration, MapCSS, _test_feature_compatibility


class MapCSSTest(unittest.TestCase):
    def test_feature_compatibility_export_for_legacy_helpers(self):
        self.assertTrue(_test_feature_compatibility("line", "way"))
        self.assertTrue(_test_feature_compatibility("area", "way"))
        self.assertFalse(_test_feature_compatibility("node", "line"))

    def test_declarations(self):
        decl = parseDeclaration(""" linejoin: round; """)
        self.assertEqual(len(decl), 1)
        self.assertEqual(decl[0], {"linejoin": "round"})

        decl = parseDeclaration("""\tlinejoin :\nround ; """)
        self.assertEqual(len(decl), 1)
        self.assertEqual(decl[0], {"linejoin": "round"})

        decl = parseDeclaration(""" icon-image: parking_private-s.svg; text: "name"; """)
        self.assertEqual(len(decl), 1)
        self.assertEqual(decl[0], {
            "icon-image": "parking_private-s.svg",
            "text": "name"
        })

        decl = parseDeclaration("""
            pattern-offset: 90\t;
            pattern-image:\tarrow-m.svg   ;
            pattern-spacing: @trunk0 ;""")
        self.assertEqual(len(decl), 1)
        self.assertEqual(decl[0], {
            "pattern-offset": "90",
            "pattern-image": "arrow-m.svg",
            "pattern-spacing": "@trunk0",
        })

    def test_parse_variables(self):
        parser = MapCSS()
        parser.parse("""
@city_label: #999999;
@country_label: #444444;
@wave_length: 25;
""")
        self.assertEqual(parser.variables, {
            "city_label": "#999999",
            "country_label": "#444444",
            "wave_length": "25"
        })

    def test_parse_colors(self):
        parser = MapCSS()
        parser.parse("""
@city_label : #999999;
@country_label: #444444 ;
  @wave_length: 25;
""")
        self.assertEqual(parser.variables, {
            "city_label": "#999999",
            "country_label": "#444444",
            "wave_length": "25"
        })

    def test_parse_import(self):
        parser = MapCSS()
        mapcssFile = Path(__file__).parent / 'assets' / 'case-1-import' / 'main.mapcss'
        parser.parse(filename=str(mapcssFile))

        colors = parser.get_colors()
        self.assertEqual(colors, {
            "GuiText-color": (1.0, 1.0, 1.0),
            "GuiText-opacity": 0.7,
            "Route-color": (0.0, 0.0, 1.0),
            "Route-opacity": 0.5,
        })

    def test_parse_basic_chooser(self):
        parser = MapCSS()
        static_tags = {"tourism": True, "office": True,
                        "craft": True, "amenity": True}
        parser.parse("""
node|z17-[tourism],
area|z17-[tourism],
node|z18-[office],
area|z18-[office],
node|z18-[craft],
area|z18-[craft],
node|z19-[amenity],
area|z19-[amenity],
{text: name; text-color: #000030; text-offset: 1;}
""", static_tags=static_tags)

        self.assertEqual(len(parser.choosers), 1)
        self.assertEqual(len(parser.choosers[0].ruleChains), 8)

    def test_parse_basic_chooser_2(self):
        parser = MapCSS()
        static_tags = {"highway": True}
        parser.parse("""
@trunk0: #FF7326;

line|z6[highway=trunk],
line|z6[highway=motorway],
{color: @trunk0; opacity: 0.3;}
line|z7-9[highway=trunk],
line|z7-9[highway=motorway],
{color: @trunk0; opacity: 0.7;}
""", static_tags=static_tags)

        self.assertEqual(len(parser.choosers), 2)
        self.assertEqual(len(parser.choosers[0].ruleChains), 2)
        self.assertEqual(parser.choosers[0].ruleChains[0].subject, 'line')
        self.assertEqual(parser.choosers[0].selzooms, [6, 6])
        self.assertEqual(parser.choosers[1].selzooms, [7, 9])

        rule, object_id = parser.choosers[0].testChains({"highway": "trunk"})
        self.assertEqual(object_id, "::default")

    def test_build_choosers_tree_matches_any_class_tag(self):
        parser = MapCSS(0, 10)
        parser.parse("""
line|z5[name] { width: 3; }
""", static_tags={"name": True})

        parser.build_choosers_tree(
            "amenity-cafe",
            "line",
            {"amenity": "cafe", "name": "Corner Cafe"}
        )
        parser.finalize_choosers_tree()

        style = parser.get_style_dict(
            "amenity-cafe",
            "line",
            {"amenity": "cafe", "name": "Corner Cafe"},
            zoom=5,
        )
        self.assertEqual(style["::default"]["width"], 3.0)

    def test_parse_legacy_zindex_keeps_negative_offset(self):
        parser = MapCSS()
        parser.parse("""
line|z5[highway=service]::low { z-index: -10; width: 1; }
line|z5[highway=service]::mid { z-index: 0; width: 2; }
line|z5[highway=service]::high { z-index: 10; width: 3; }
""", static_tags={"highway": True}, stretch=False, legacy_zindex=True)

        zindexes = [
            style["z-index"]
            for chooser in parser.choosers
            for style in chooser.styles
        ]
        self.assertEqual(zindexes, [-1, 0, 1])

    def test_parse_basic_chooser_3(self):
        parser = MapCSS()
        static_tags = {"addr:housenumber": True, "addr:street": False}
        parser.parse("""
/* Some Comment Here */

/*
   This sample is borrowed from Organic Maps Basemap_label.mapcss file
 */
node|z18-[addr:housenumber][addr:street]::int_name
{text: int_name; text-color: #65655E; text-position: center;}
""", static_tags=static_tags)

        building_tags = {"building": "yes", "addr:housenumber": "12", "addr:street": "Baker street"}

        # Check that mapcss parsed correctly
        self.assertEqual(len(parser.choosers), 1)
        styleChooser = parser.choosers[0]
        self.assertEqual(len(styleChooser.ruleChains), 1)
        self.assertEqual(styleChooser.selzooms, [18, 19])
        rule, object_id = styleChooser.testChains(building_tags)
        self.assertEqual(object_id, "::int_name")

        rule = styleChooser.ruleChains[0]
        self.assertEqual(rule.subject, 'node')
        self.assertEqual(rule.extract_tags(), {'addr:housenumber', 'addr:street'})

    def test_parse_basic_chooser_class(self):
        parser = MapCSS()
        parser.parse("""
way|z-13::*
{
  linejoin: round;
}
""")

        # Check that mapcss parsed correctly
        self.assertEqual(len(parser.choosers), 1)
        styleChooser = parser.choosers[0]
        self.assertEqual(len(styleChooser.ruleChains), 1)
        self.assertEqual(styleChooser.selzooms, [0, 13])
        rule, object_id = styleChooser.testChains({})
        self.assertEqual(object_id, "::*")

        rule = styleChooser.ruleChains[0]
        self.assertEqual(rule.subject, 'way')
        self.assertEqual(rule.extract_tags(), {'*'})

    def test_parse_basic_chooser_class_2(self):
        parser = MapCSS()
        parser.parse("""
way|z10-::*
{
  linejoin: round;
}
""")

        # Check that mapcss parsed correctly
        self.assertEqual(len(parser.choosers), 1)
        styleChooser = parser.choosers[0]
        self.assertEqual(len(styleChooser.ruleChains), 1)
        self.assertEqual(styleChooser.selzooms, [10, 19])
        rule, object_id = styleChooser.testChains({})
        self.assertEqual(object_id, "::*")

        rule = styleChooser.ruleChains[0]
        self.assertEqual(rule.subject, 'way')
        self.assertEqual(rule.extract_tags(), {'*'})

    def test_parse_basic_chooser_colors(self):
        parser = MapCSS()
        parser.parse("""
way|z-6::*
{
  linejoin: round;
}

colors {
  GuiText-color: #FFFFFF;
  GuiText-opacity: 0.7;
  MyPositionAccuracy-color: #FFFFFF;
  MyPositionAccuracy-opacity: 0.06;
  Selection-color: #FFFFFF;
  Selection-opacity: 0.64;
  Route-color: #0000FF;
  RouteOutline-color: #00FFFF;
}
""")

        # Check that colors from mapcss parsed correctly
        colors = parser.get_colors()
        self.assertEqual(colors, {
            "GuiText-color": (1.0, 1.0, 1.0),
            "GuiText-opacity": 0.7,
            "MyPositionAccuracy-color": (1.0, 1.0, 1.0),
            "MyPositionAccuracy-opacity": 0.06,
            "Selection-color": (1.0, 1.0, 1.0),
            "Selection-opacity": 0.64,
            "Route-color": (0.0, 0.0, 1.0),
            "RouteOutline-color": (0.0, 1.0, 1.0)
        })

    def test_parser_choosers_tree(self):
        parser = MapCSS()
        static_tags = {"tourism": True, "office": True,
                       "craft": True, "amenity": True}

        parser.parse("""
node|z17-[office=lawyer],
area|z17-[office=lawyer],
{text: name;text-color: #444444;text-offset: 1;font-size: 10;}

node|z17-[tourism],
area|z17-[tourism],
node|z18-[office],
area|z18-[office],
node|z18-[craft],
area|z18-[craft],
node|z19-[amenity],
area|z19-[amenity],
{text: name; text-color: #000030; text-offset: 1;}

node|z18-[office],
area|z18-[office],
node|z18-[craft],
area|z18-[craft],
{font-size: 11;}

node|z17-[office=lawyer],
area|z17-[office=lawyer]
{icon-image: lawyer-m.svg;}
""", static_tags=static_tags)

        for obj_type in ["line", "area", "node"]:
            parser.build_choosers_tree("tourism", obj_type, "tourism")
            parser.build_choosers_tree("office", obj_type, "office")
            parser.build_choosers_tree("craft", obj_type, "craft")
            parser.build_choosers_tree("amenity", obj_type, "amenity")

        parser.finalize_choosers_tree()

        # Pick style for zoom = 17
        styles18 = parser.get_style("office", "node", {"office": "lawyer"},
                                    zoom=18, xscale=1, zscale=1, filter_by_runtime_conditions=False)

        self.assertEqual(len(styles18), 1),
        self.assertEqual(styles18[0], {'object-id': '::default',
            'font-size': '11',
            'text': 'name',
            'text-color': (0, 0, 16*3/255),
            'text-offset': 1.0,
            'icon-image': 'lawyer-m.svg'})

        # Pick style for zoom = 17
        styles17 = parser.get_style("office", "node", {"office": "lawyer"},
                                    zoom=17, xscale=1, zscale=1, filter_by_runtime_conditions=False)

        self.assertEqual(len(styles17), 1),
        self.assertEqual(styles17[0], {'object-id': '::default',
            'font-size': '10',
            'text': 'name',
            'text-color': (68/255, 68/255, 68/255),
            'text-offset': 1.0,
            'icon-image': 'lawyer-m.svg'})

        # Pick style for zoom = 15
        styles15 = parser.get_style("office", "node", {"office": "lawyer"},
                                    zoom=15, xscale=1, zscale=1, filter_by_runtime_conditions=False)

        self.assertEqual(styles15, []),

    def test_parser_choosers_tree_with_classes(self):
        parser = MapCSS()
        static_tags = {"highway": True}

        parser.parse("""
line|z10-[highway=motorway]::shield,
line|z10-[highway=trunk]::shield,
line|z10-[highway=motorway_link]::shield,
line|z10-[highway=trunk_link]::shield,
line|z10-[highway=primary]::shield,
line|z11-[highway=primary_link]::shield,
line|z12-[highway=secondary]::shield,
line|z13-[highway=tertiary]::shield,
line|z15-[highway=residential]::shield,
{
  shield-font-size: 9;
  shield-text-color: #000000;
  shield-text-halo-radius: 0;
  shield-color: #FFFFFF;
  shield-outline-radius: 1;
}

line|z12-[highway=residential],
line|z12-[highway=tertiary],
line|z18-[highway=tertiary_link]
{
  text: name;
  text-color: #333333;
  text-halo-opacity: 0.8;
  text-halo-radius: 1;
}

line|z12-13[highway=residential],
line|z12-13[highway=tertiary]
{
    font-size: 12;
    text-color: #444444;
}
""", static_tags=static_tags)

        parser.build_choosers_tree("highway", "line", "highway")
        parser.finalize_choosers_tree()

        # Pick style for zoom = 10
        styles10 = parser.get_style("highway", "line", {"highway": "primary"},
                                    zoom=10, xscale=1, zscale=1, filter_by_runtime_conditions=False)

        self.assertEqual(len(styles10), 1),
        self.assertEqual(styles10[0], {'object-id': '::shield',
            'shield-font-size': '9',
            'shield-text-color': (0.0, 0.0, 0.0),
            'shield-text-halo-radius': 0.0,
            'shield-color': (1.0, 1.0, 1.0),
            'shield-outline-radius': 1.0})

        # Pick style for zoom = 15. Expecting two `object-id` values: '::shield' and '::default'
        styles15 = parser.get_style("highway", "line", {"highway": "tertiary"},
                                    zoom=15, xscale=1, zscale=1, filter_by_runtime_conditions=False)

        self.assertEqual(len(styles15), 2),
        self.assertEqual(styles15[0], {'object-id': '::shield',
            'shield-font-size': '9',
            'shield-text-color': (0.0, 0.0, 0.0),
            'shield-text-halo-radius': 0.0,
            'shield-color': (1.0, 1.0, 1.0),
            'shield-outline-radius': 1.0})
        self.assertEqual(styles15[1], {'object-id': '::default',
            'text': 'name',
            'text-color': (51/255, 51/255, 51/255),
            'text-halo-opacity': 0.8,
            'text-halo-radius': 1.0})

if __name__ == '__main__':
    unittest.main()
