import unittest
import sys
from pathlib import Path

from mapcss.Rule import Rule

# Add `src` directory to the import paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from mapcss import parseCondition, Condition
from mapcss.Eval import Eval
from mapcss.StyleChooser import StyleChooser, make_nice_style


class StyleChooserTest(unittest.TestCase):
    def test_rules_chain(self):
        sc = StyleChooser((0, 16))

        sc.newObject()
        sc.addCondition(parseCondition("highway=footway"))
        sc.addCondition(parseCondition("footway=sidewalk"))

        sc.newObject()
        sc.addCondition(parseCondition("highway=footway"))
        sc.addCondition(parseCondition("footway=crossing"))
        sc.addCondition(Condition("eq", ("::class", "::*")))

        self.assertTrue( sc.testChains({ "highway": "footway", "footway": "sidewalk" }) )
        self.assertTrue( sc.testChains({ "highway": "footway", "footway": "crossing" }) )
        self.assertFalse( sc.testChains({ "highway": "footway"}) )
        self.assertFalse( sc.testChains({ "highway": "residential", "footway": "crossing" }) )

        rule1, tt = sc.testChains({ "highway": "footway", "footway": "sidewalk" })
        self.assertEqual(tt, "::default")

        rule2, tt = sc.testChains({ "highway": "footway", "footway": "crossing" })
        self.assertEqual(tt, "::*")

        self.assertNotEqual(rule1, rule2)

    def test_zoom(self):
        sc = StyleChooser((0, 16))

        sc.newObject()
        sc.addZoom( (10, 19) )
        sc.addCondition(parseCondition("railway=station"))
        sc.addCondition(parseCondition("transport=subway"))
        sc.addCondition(parseCondition("city=yerevan"))

        sc.newObject()
        sc.addZoom( (4, 15) )
        sc.addCondition(parseCondition("railway=station"))
        sc.addCondition(parseCondition("transport=subway"))
        sc.addCondition(parseCondition("city=yokohama"))

        rule1, tt = sc.testChains({ "railway": "station", "transport": "subway", "city": "yerevan" })
        self.assertEqual(rule1.minZoom, 10)
        self.assertEqual(rule1.maxZoom, 19)

        rule2, tt = sc.testChains({ "railway": "station", "transport": "subway", "city": "yokohama" })
        self.assertEqual(rule2.minZoom, 4)
        self.assertEqual(rule2.maxZoom, 15)

    def test_extract_tags(self):
        sc = StyleChooser((0, 16))

        sc.newObject()
        sc.addCondition(parseCondition("aerialway=rope_tow"))

        sc.newObject()
        sc.addCondition(parseCondition("piste:type=downhill"))

        self.assertSetEqual(sc.extract_tags(), {"aerialway", "piste:type"})

        sc = StyleChooser((0, 16))

        sc.newObject()
        sc.addCondition(parseCondition("aeroway=terminal"))
        sc.addCondition(parseCondition("building"))

        sc.newObject()
        sc.addCondition(parseCondition("waterway=dam"))
        sc.addCondition(parseCondition("building:part"))

        self.assertSetEqual(sc.extract_tags(), {"waterway", "building:part", "building", "aeroway"})

    def test_make_nice_style(self):
        style = make_nice_style({
            "outline-color": "none",
            "bg-color": "red",
            "dash-color": "#ffff00",
            "front-color": "rgb(0, 255, 255)",
            "line-width": Eval("""eval(min(tag("line_width"), 10))"""),
            "outline-width": "2.5",
            "arrow-opacity": "0.5",
            "offset-2": "20",
            "border-radius": "4",
            "line-extrude": "16",
            "dashes": "3,3,1.5,3",
            "wrong-dashes": "yes, yes, yes, no",
            "make-nice": True,
            "additional-len": 44.5
        })

        expectedStyle = {
            "outline-color": "none",
            "bg-color": (1.0, 0.0, 0.0),
            "dash-color": (1.0, 1.0, 0.0),
            "front-color": (0.0, 1.0, 1.0),
            "line-width": Eval("""eval(min(tag("line_width"), 10))"""),
            "outline-width": 2.5,
            "arrow-opacity": 0.5,
            "offset-2": 20.0,
            "border-radius": 4.0,
            "line-extrude": 16.0,
            "dashes": [3.0, 3.0, 1.5, 3.0],
            "wrong-dashes": [],
            "make-nice": True,
            "additional-len": 44.5
        }

        self.assertEqual(style, expectedStyle)

    def test_add_styles(self):
        sc = StyleChooser((15, 19))
        sc.newObject()
        sc.addStyles([{
            "width": "1.3",
            "opacity": "0.6",
            "bg-color": "blue"
        }])
        sc.addStyles([{
            "color": "#FFFFFF",
            "casing-width": "+10"
        }])

        self.assertEqual(len(sc.styles), 2)
        self.assertEqual(sc.styles[0], {
            "width": 1.3,
            "opacity": 0.6,
            "bg-color": (0.0, 0.0, 1.0)
        })
        self.assertEqual(sc.styles[1], {
            "color": (1.0, 1.0, 1.0),
            "casing-width": 5.0
        })

    def test_update_styles(self):
        styles = [{"primary_color": (1.0, 1.0, 1.0)}]

        sc = StyleChooser((15, 19))
        sc.newObject()
        sc.addStyles([{
            "width": "1.3",
            "opacity": "0.6",
            "bg-color": """eval( prop("primary_color") )""", # Check that property from `styles` is applied
            "text-offset": """eval( cond( boolean(tag("oneway")), 10, 5) )""" # Check that tags are applied
        }])

        object_tags = {"highway": "service",
                       "oneway": "yes"}
        new_styles = sc.updateStyles(styles, object_tags, 1.0, 1.0, False)
        expected_new_styles = {
            "width": 1.3,
            "opacity": 0.6,
            "bg-color": (1.0, 1.0, 1.0),
            "text-offset": 10.0,
            "object-id": "::default"
        }

        self.assertEqual(len(new_styles), 2)
        self.assertEqual(new_styles[-1], expected_new_styles)

    def test_update_styles_2(self):
        styles = []

        sc = StyleChooser((15, 19))

        sc.newObject()
        sc.addCondition(Condition("eq", ("::class", "::int_name") )) # Class should be added to the style
        sc.addCondition(parseCondition("oneway?"))

        sc.addStyles([{
            "width": "1.3",
            "bg-color": "black"
        }])

        object_tags = {"highway": "service", "oneway": "yes"}
        new_styles = sc.updateStyles(styles, object_tags, 1.0, 1.0, False)
        expected_new_styles = {
            "width": 1.3,
            "bg-color": (0.0, 0.0, 0.0),
            "object-id": "::int_name" # Check that class from sc.ruleChains is added to the style
        }

        self.assertEqual(len(new_styles), 1)
        self.assertEqual(new_styles[-1], expected_new_styles)


    def test_update_styles_by_class(self):
        # Predefined styles
        styles = [{
            "some-width": 2.5,
            "object-id": "::flats"
        },
        {
            "some-width": 3.5,
            "object-id": "::bridgeblack"
        },
        {
            "some-width": 4.5,
            "object-id": "::default"
        }]

        sc = StyleChooser((15, 19))

        sc.newObject()
        sc.addCondition(Condition("eq", ("::class", "::flats") )) # `sc` styles should apply only to `::flats` class
        sc.addCondition(parseCondition("oneway?"))

        sc.newObject()
        sc.addCondition(Condition("eq", ("::class", "::bridgeblack") )) # This class is ignored by StyleChooser
        sc.addCondition(parseCondition("oneway?"))

        sc.addStyles([{
            "some-width": "1.5",
            "other-offset": "4"
        }])

        object_tags = {"highway": "service", "oneway": "yes"}

        # Apply new style to predefined styles with filter by class
        new_styles = sc.updateStyles(styles, object_tags, 1.0, 1.0, False)

        expected_new_styles = [{ # The first style changes
            "some-width": 1.5,
            "other-offset": 4.0,
            "object-id": "::flats"
        },
        { # Style not changed (class is not `::flats`)
            "some-width": 3.5,
            "object-id": "::bridgeblack"
        },
        { # Style not changed (class is not `::flats`)
            "some-width": 4.5,
            "object-id": "::default"
        }]

        self.assertEqual(len(new_styles), 3)
        self.assertEqual(new_styles, expected_new_styles)


    def test_update_styles_by_class_all(self):
        # Predefined styles
        styles = [{ # This is applied to StyleChooser styles
            "some-width": 2.5,
            "corner-radius": 2.5,
            "object-id": "::*"
        },
        {
            "some-width": 3.5,
            "object-id": "::bridgeblack"
        }]

        sc = StyleChooser((15, 19))

        sc.newObject()
        sc.addCondition(parseCondition("tunnel"))

        sc.addStyles([{
            "some-width": "1.5",
            "other-offset": "4"
        }])
        object_tags = {"highway": "service", "tunnel": "yes"}

        # Apply new style to predefined styles with filter by class
        new_styles = sc.updateStyles(styles, object_tags, 1.0, 1.0, False)

        # Check that new style with new `object-id` is added.
        # This style is built from `styles[0]` and styles from `sc`
        expected_new_style = {
            "some-width": 1.5,
            "corner-radius": 2.5,
            "other-offset": 4.0,
            "object-id": "::default"  # New class, never listed in `styles`
        }

        self.assertEqual(len(new_styles), 3)
        self.assertEqual(new_styles[-1], expected_new_style)


    def test_runtime_conditions(self):
        sc = StyleChooser((15, 19))

        sc.newObject()
        sc.addCondition(parseCondition("highway=primary"))
        runtime_condition = Condition("eq", ("extra_tag", "route"))
        sc.addRuntimeCondition(runtime_condition)
        sc.addStyles([{
            "width": "4"
        }])

        object_tags = {"highway": "primary"}

        unfiltered_styles = sc.updateStyles([], object_tags, 1.0, 1.0, None)
        self.assertEqual(len(unfiltered_styles), 1)
        self.assertEqual(unfiltered_styles[0]["width"], 4.0)

        matching_styles = sc.updateStyles([], object_tags, 1.0, 1.0, [runtime_condition])
        self.assertEqual(len(matching_styles), 1)
        self.assertEqual(matching_styles[0]["width"], 4.0)

        mismatching_styles = sc.updateStyles([], object_tags, 1.0, 1.0, [
            Condition("eq", ("extra_tag", "bridge"))
        ])
        self.assertEqual(mismatching_styles, [])

if __name__ == '__main__':
    unittest.main()
