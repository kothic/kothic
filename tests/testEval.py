import unittest
import sys
from pathlib import Path

# Add `src` directory to the import paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from mapcss.Eval import Eval

class EvalTest(unittest.TestCase):
    """ Test eval(...) feature for CSS properties.
        NOTE: eval() is not used in Organic Maps styles. We can drop it completely.
    """
    def test_eval_tag(self):
        a = Eval("""eval( tag("lanes") )""")
        self.assertEqual(a.compute({"lanes": "4"}), "4")
        self.assertEqual(a.compute({"natural": "trees"}), "")
        self.assertSetEqual(a.extract_tags(), {"lanes"})

    def test_eval_prop(self):
        a = Eval("""eval( prop("dpi") / 2 )""")
        self.assertEqual(a.compute({"lanes": "4"}, {"dpi": 144}), "72")
        self.assertEqual(a.compute({"lanes": "4"}, {"orientation": "vertical"}), "")
        self.assertSetEqual(a.extract_tags(), set())

    def test_eval_num(self):
        a = Eval("""eval( num(tag("lanes")) + 2 )""")
        self.assertEqual(a.compute({"lanes": "4"}), "6")
        self.assertEqual(a.compute({"lanes": "many"}), "2")
        self.assertSetEqual(a.extract_tags(), {"lanes"})

    def test_eval_metric(self):
        a = Eval("""eval( metric(tag("height")) )""")
        self.assertEqual(a.compute({"height": "512"}), "512")
        self.assertEqual(a.compute({"height": "10m"}), "10")
        self.assertEqual(a.compute({"height": " 10m"}), "10")
        self.assertEqual(a.compute({"height": "500cm"}), "5")
        self.assertEqual(a.compute({"height": "500 cm"}), "5")
        self.assertEqual(a.compute({"height": "250CM"}), "2.5")
        self.assertEqual(a.compute({"height": "250 CM"}), "2.5")
        self.assertEqual(a.compute({"height": "30см"}), "0.3")
        self.assertEqual(a.compute({"height": " 30 см"}), "0.3")
        self.assertEqual(a.compute({"height": "1200 mm"}), "1.2")
        self.assertEqual(a.compute({"height": "2400MM"}), "2.4")
        self.assertEqual(a.compute({"height": "2800 мм"}), "2.8")
        self.assertSetEqual(a.extract_tags(), {"height"})

    def test_eval_metric_with_scale(self):
        a = Eval("""eval( metric(tag("height")) )""")
        self.assertEqual(a.compute({"height": "512"}, xscale=4), "2048")
        self.assertEqual(a.compute({"height": "512"}, zscale=4), "512")
        self.assertEqual(a.compute({"height": "10m"}, xscale=4), "40")
        self.assertEqual(a.compute({"height": " 10m"}, xscale=4), "40")
        self.assertEqual(a.compute({"height": "500cm"}, xscale=4), "20")
        self.assertEqual(a.compute({"height": "500 cm"}, xscale=4), "20")
        self.assertEqual(a.compute({"height": "250CM"}, xscale=4), "10")
        self.assertEqual(a.compute({"height": "250 CM"}, xscale=4), "10")
        self.assertEqual(a.compute({"height": "30см"}, xscale=4), "1.2")
        self.assertEqual(a.compute({"height": " 30 см"}, xscale=4), "1.2")
        self.assertEqual(a.compute({"height": "1200 mm"}, xscale=4), "4.8")
        self.assertEqual(a.compute({"height": "2400MM"}, xscale=4), "9.6")
        self.assertEqual(a.compute({"height": "2800 мм"}, xscale=4), "11.2")
        self.assertSetEqual(a.extract_tags(), {"height"})

    def test_eval_zmetric(self):
        a = Eval("""eval( zmetric(tag("depth")) )""")
        self.assertEqual(a.compute({"depth": "512"}), "256")
        self.assertEqual(a.compute({"depth": "10m"}), "5")
        self.assertEqual(a.compute({"depth": " 10m"}), "5")
        self.assertEqual(a.compute({"depth": "500cm"}), "2.5")
        self.assertEqual(a.compute({"depth": "500 cm"}), "2.5")
        self.assertEqual(a.compute({"depth": "250CM"}), "1.25")
        self.assertEqual(a.compute({"depth": "250 CM"}), "1.25")
        self.assertEqual(a.compute({"depth": "30см"}), "0.15")
        self.assertEqual(a.compute({"depth": " 30 см"}), "0.15")
        self.assertEqual(a.compute({"depth": "1200 mm"}), "0.6")
        self.assertEqual(a.compute({"depth": "2400MM"}), "1.2")
        self.assertEqual(a.compute({"depth": "2800 мм"}), "1.4")
        self.assertSetEqual(a.extract_tags(), {"depth"})

    def test_eval_str(self):
        a = Eval("""eval( str( num(tag("width")) - 200 ) )""")
        self.assertEqual(a.compute({"width": "400"}), "200.0")
        self.assertSetEqual(a.extract_tags(), {"width"})

    def test_eval_any(self):
        a = Eval("""eval( any(tag("building"), tag("building:part"), "no") )""")
        self.assertEqual(a.compute({"building": "apartment"}), "apartment")
        self.assertEqual(a.compute({"building:part": "roof"}), "roof")
        self.assertEqual(a.compute({"junction": "roundabout"}), "no")
        self.assertSetEqual(a.extract_tags(), {"building", "building:part"})

    def test_eval_min(self):
        a = Eval("""eval( min( num(tag("building:levels")) * 3, 50) )""")
        self.assertEqual(a.compute({"natural": "wood"}), "0")
        self.assertEqual(a.compute({"building:levels": "0"}), "0")
        self.assertEqual(a.compute({"building:levels": "10"}), "30")
        self.assertEqual(a.compute({"building:levels": "30"}), "50")
        self.assertSetEqual(a.extract_tags(), {"building:levels"})

    def test_eval_max(self):
        a = Eval("""eval( max( tag("speed:limit"), 60) )""")
        self.assertEqual(a.compute({"natural": "wood"}), "60")
        self.assertEqual(a.compute({"speed:limit": "30"}), "60")
        self.assertEqual(a.compute({"speed:limit": "60"}), "60")
        self.assertEqual(a.compute({"speed:limit": "90"}), "90")
        self.assertSetEqual(a.extract_tags(), {"speed:limit"})

    def test_eval_cond(self):
        a = Eval("""eval( cond( boolean(tag("oneway")), 200, 100) )""")
        self.assertEqual(a.compute({"natural": "wood"}), "100")
        self.assertEqual(a.compute({"oneway": "yes"}), "200")
        self.assertEqual(a.compute({"oneway": "no"}), "100")
        self.assertEqual(a.compute({"oneway": "true"}), "200")
        self.assertEqual(a.compute({"oneway": "probably no"}), "200")
        self.assertSetEqual(a.extract_tags(), {"oneway"})

    def test_complex_eval(self):
        a = Eval(""" eval( any( metric(tag("height")), metric ( num(tag("building:levels")) * 3), metric("1m"))) """)
        self.assertEqual(a.compute({"building:levels": "3"}), "9")
        self.assertSetEqual(a.extract_tags(), {"height", "building:levels"})

if __name__ == '__main__':
    unittest.main()
