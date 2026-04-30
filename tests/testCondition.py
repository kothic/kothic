import re
import unittest
import sys
from pathlib import Path

# Add `src` directory to the import paths
sys.path.insert(0, str(Path(__file__).parent.parent / 'src'))

from mapcss import parseCondition
from mapcss.Condition import Condition

class ConditionTest(unittest.TestCase):

    def test_parser_eq(self):
        cond:Condition = parseCondition("natural=coastline")
        self.assertEqual(cond.type, "eq")
        self.assertEqual(cond.params, ("natural", "coastline"))
        self.assertTrue(cond.test({'natural': 'coastline'}))
        self.assertFalse(cond.test({'Natural': 'Coastline'}))

        cond = parseCondition("  highway\t=\tprimary")
        self.assertEqual(cond.type, "eq")
        self.assertEqual(cond.params, ("highway", "primary"))
        self.assertTrue(cond.test({'highway': 'primary'}))
        self.assertFalse(cond.test({'highway': 'secondary'}))

        cond = parseCondition("  admin_level  =   3")
        self.assertEqual(cond.type, "eq")
        self.assertEqual(cond.params, ("admin_level", "3"))
        self.assertTrue(cond.test({'admin_level': '3'}))
        self.assertFalse(cond.test({'admin_level': '32'}))

        cond = Condition('eq', ("::class", "::*"))
        self.assertEqual(cond.type, "eq")
        self.assertEqual(cond.params, ("::class", "::*"))
        self.assertEqual(cond.extract_tag(), "*")
        self.assertEqual(cond.test({'any_key': 'any_value'}), "::*")
        self.assertTrue(cond.test({'any_key': 'any_value'}))

        cond = Condition('eq', ("::class", "::int_name"))
        self.assertEqual(cond.type, "eq")
        self.assertEqual(cond.params, ("::class", "::int_name"))
        self.assertEqual(cond.extract_tag(), "*")
        self.assertEqual(cond.test({'any_key': 'any_value'}), "::int_name")
        self.assertTrue(cond.test({'any_key': 'any_value'}))

    def test_parser_regex(self):
        """ Test conditions in format natural =~/water.+/
            Note that such conditions are not used by Organic Maps styles.
        """
        cond:Condition = parseCondition("natural =~/water.+/")
        self.assertEqual(cond.type, "regex")
        self.assertEqual(cond.params, ("natural", "water.+"))
        self.assertEqual(type(cond.regex), re.Pattern)
        self.assertTrue(cond.test({"natural": "waterway"}))
        self.assertTrue(cond.test({"natural": "water123"}))
        self.assertFalse(cond.test({"natural": "water"}))
        self.assertFalse(cond.test({"natural": " waterway "}))

    def test_parser_ge(self):
        cond:Condition = parseCondition("population>=0")
        self.assertEqual(cond.type, ">=")
        self.assertEqual(cond.params, ("population", "0"))
        self.assertTrue(cond.test({"population": "0"}))
        self.assertTrue(cond.test({"population": "100000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"population": "-1"}))

        cond:Condition = parseCondition("population >= 150000")
        self.assertEqual(cond.type, ">=")
        self.assertEqual(cond.params, ("population", "150000"))
        self.assertTrue(cond.test({"population": "150000"}))
        self.assertTrue(cond.test({"population": "250000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"population": "10000"}))

        cond:Condition = parseCondition("\tbbox_area  >= 4000000")
        self.assertEqual(cond.type, ">=")
        self.assertEqual(cond.params, ("bbox_area", "4000000"))
        self.assertTrue(cond.test({"bbox_area": "4000000"}))
        self.assertTrue(cond.test({"bbox_area": "8000000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"bbox_area": "999"}))

    def test_parser_gt(self):
        """ Test conditions in format population > 100000
            Note that such conditions are not used by Organic Maps styles.
        """
        cond:Condition = parseCondition("population>0")
        self.assertEqual(cond.type, ">")
        self.assertEqual(cond.params, ("population", "0"))
        self.assertTrue(cond.test({"population": "100"}))
        self.assertFalse(cond.test({"population": "000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"population": "-1"}))

        cond:Condition = parseCondition("population > 150000")
        self.assertEqual(cond.type, ">")
        self.assertEqual(cond.params, ("population", "150000"))
        self.assertTrue(cond.test({"population": "250000"}))
        self.assertFalse(cond.test({"population": "150000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"population": "10000"}))

        cond:Condition = parseCondition("\tbbox_area > 4000000 ")
        self.assertEqual(cond.type, ">")
        self.assertEqual(cond.params, ("bbox_area", "4000000 ")) # TODO fix parser to exclude trailing space
        self.assertTrue(cond.test({"bbox_area": "8000000"}))
        self.assertFalse(cond.test({"bbox_area": "4000000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"bbox_area": "999"}))

    def test_parser_lt(self):
        cond:Condition = parseCondition("population<40000")
        self.assertEqual(cond.type, "<")
        self.assertEqual(cond.params, ("population", "40000"))
        self.assertTrue(cond.test({"population": "100"}))
        self.assertTrue(cond.test({"population": "-1"}))
        self.assertFalse(cond.test({"population": "40000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"population": "500000"}))

        cond:Condition = parseCondition("\tbbox_area < 4000000\n")
        self.assertEqual(cond.type, "<")
        self.assertEqual(cond.params, ("bbox_area", "4000000\n")) # TODO fix parser to exclude trailing \n
        self.assertTrue(cond.test({"bbox_area": "100"}))
        self.assertTrue(cond.test({"bbox_area": "-1"}))
        self.assertTrue(cond.test({"bbox_area": "000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"bbox_area": "4000000"}))
        self.assertFalse(cond.test({"bbox_area": "8000000"}))

    def test_parser_le(self):
        """ Test conditions in format population <= 100000
            Note that such conditions are not used by Organic Maps styles.
        """
        cond:Condition = parseCondition("population<=40000")
        self.assertEqual(cond.type, "<=")
        self.assertEqual(cond.params, ("population", "40000"))
        self.assertTrue(cond.test({"population": "100"}))
        self.assertTrue(cond.test({"population": "-1"}))
        self.assertTrue(cond.test({"population": "40000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"population": "500000"}))

        cond:Condition = parseCondition("\tbbox_area <= 4000000\n")
        self.assertEqual(cond.type, "<=")
        self.assertEqual(cond.params, ("bbox_area", "4000000\n")) # TODO fix parser to exclude trailing \n
        self.assertTrue(cond.test({"bbox_area": "100"}))
        self.assertTrue(cond.test({"bbox_area": "-1"}))
        self.assertTrue(cond.test({"bbox_area": "000"}))
        self.assertTrue(cond.test({"bbox_area": "4000000"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"bbox_area": "8000000"}))

    def test_parser_ne(self):
        cond:Condition = parseCondition("capital!=2")
        self.assertEqual(cond.type, "ne")
        self.assertEqual(cond.params, ("capital", "2"))
        self.assertTrue(cond.test({"capital": "1"}))
        self.assertTrue(cond.test({"capital": "22"}))
        self.assertTrue(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"capital": "2"}))

        cond:Condition = parseCondition("\tcapital  !=  2")
        self.assertEqual(cond.type, "ne")
        self.assertEqual(cond.params, ("capital", "2"))
        self.assertTrue(cond.test({"capital": "1"}))
        self.assertTrue(cond.test({"capital": "22"}))
        self.assertTrue(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"capital": "2"}))

        cond:Condition = parseCondition("garden:type != residential")
        self.assertEqual(cond.type, "ne")
        self.assertEqual(cond.params, ("garden:type", "residential"))
        self.assertTrue(cond.test({"garden:type": "public"}))
        self.assertTrue(cond.test({"garden:type": "res"}))
        self.assertTrue(cond.test({"garden:type": "residential_plus"}))
        self.assertTrue(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"garden:type": "residential"}))

    def test_parser_set(self):
        cond:Condition = parseCondition("tunnel")
        self.assertEqual(cond.type, "set")
        self.assertEqual(cond.params, ("tunnel", ))
        self.assertTrue(cond.test({"tunnel": "yes"}))
        self.assertTrue(cond.test({"tunnel": "maybe"}))
        self.assertTrue(cond.test({"tunnel": "+1"}))
        self.assertFalse(cond.test({"highway": "secondary"}))

        cond:Condition = parseCondition("building\t")
        self.assertEqual(cond.type, "set")
        self.assertEqual(cond.params, ("building", ))
        self.assertTrue(cond.test({"building": "yes"}))
        self.assertTrue(cond.test({"building": "apartment"}))
        self.assertTrue(cond.test({"building": "1"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"building:part": "yes"}))

        cond:Condition = parseCondition(" addr:housenumber ")
        self.assertEqual(cond.type, "set")
        self.assertEqual(cond.params, ("addr:housenumber", ))
        self.assertTrue(cond.test({"addr:housenumber": "1"}))
        self.assertTrue(cond.test({"addr:housenumber": "yes"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"addr:street": "Baker st"}))

        cond:Condition = parseCondition(" some-tag ")
        self.assertEqual(cond.type, "set")
        self.assertEqual(cond.params, ("some-tag", ))
        self.assertTrue(cond.test({"some-tag": "1"}))
        self.assertTrue(cond.test({"some-tag": "yes"}))
        self.assertFalse(cond.test({"highway": "secondary"}))
        self.assertFalse(cond.test({"some": "tag"}))

    def test_parser_unset(self):
        cond:Condition = parseCondition("!tunnel")
        self.assertEqual(cond.type, "unset")
        self.assertEqual(cond.params, ("tunnel", ))
        self.assertTrue(cond.test({"capital": "1"}))
        self.assertFalse(cond.test({"tunnel": "yes"}))
        self.assertFalse(cond.test({"tunnel": "no"}))

        cond:Condition = parseCondition("\t!name  ")
        self.assertEqual(cond.type, "unset")
        self.assertEqual(cond.params, ("name", ))
        self.assertTrue(cond.test({"capital": "1"}))
        self.assertTrue(cond.test({"int_name": "1"}))
        self.assertFalse(cond.test({"name": "London"}))

    def test_parser_false(self):
        """ Test conditions in format some_tag = no
            Note that such conditions are not used by Organic Maps styles.
        """
        cond:Condition = parseCondition("access=no")
        self.assertEqual(cond.type, "false")
        self.assertEqual(cond.params, ("access", ))
        #self.assertTrue(cond.test({"access": "no"}))      # test is not implemented for `false` condition
        #self.assertTrue(cond.test({"access": "private"})) # test is not implemented for `false` condition
        self.assertFalse(cond.test({"tunnel": "yes"}))

    def test_parser_invTrue(self):
        """ Test conditions in format [!some_tag?] It works the same way as [some_tag != yes]
            Note that such conditions are not used by Organic Maps styles.
        """
        cond:Condition = parseCondition("!oneway?")
        self.assertEqual(cond.type, "ne")
        self.assertEqual(cond.params, ("oneway", "yes"))
        self.assertTrue(cond.test({"oneway": "no"}))
        self.assertTrue(cond.test({"oneway": "nobody_knows"}))
        self.assertTrue(cond.test({"access": "private"}))
        self.assertFalse(cond.test({"oneway": "yes"}))

        cond:Condition = parseCondition("\t! intermittent ?\n")
        self.assertEqual(cond.type, "ne")
        self.assertEqual(cond.params, ("intermittent", "yes"))
        self.assertTrue(cond.test({"intermittent": "no"}))
        self.assertTrue(cond.test({"intermittent": "maybe"}))
        self.assertTrue(cond.test({"access": "private"}))
        self.assertFalse(cond.test({"intermittent": "yes"}))

    def test_parser_true(self):
        """ Test conditions in format [some_tag?] It works the same way as [some_tag = yes] """
        cond:Condition = parseCondition("area?")
        self.assertEqual(cond.type, "true")
        self.assertEqual(cond.params, ("area", ))
        self.assertTrue(cond.test({"area": "yes"}))
        self.assertFalse(cond.test({"area": "no"}))
        self.assertFalse(cond.test({"access": "private"}))
        self.assertFalse(cond.test({"oneway": "nobody_knows"}))

        cond:Condition = parseCondition("\tbridge ? ")
        self.assertEqual(cond.type, "true")
        self.assertEqual(cond.params, ("bridge", ))
        self.assertTrue(cond.test({"bridge": "yes"}))
        self.assertFalse(cond.test({"bridge": "no"}))
        self.assertFalse(cond.test({"access": "private"}))
        self.assertFalse(cond.test({"bridge": "maybe"}))

    def test_untrue(self):
        """ parseCondition(...) doesn't support this type of condition.
            Not sure if it's ever used.
        """
        cond:Condition = Condition("untrue", "access")
        self.assertEqual(cond.type, "untrue")
        self.assertEqual(cond.params, ("access", ))
        self.assertTrue(cond.test({"access": "no"}))
        self.assertFalse(cond.test({"access": "private"}))
        self.assertFalse(cond.test({"oneway": "yes"}))

    def test_parser_errors(self):
        with self.assertRaises(Exception):
            parseCondition("! tunnel")
        with self.assertRaises(Exception):
            """ Symbol '-' is only supported in simple 'set' rule. E.g. [key-with-dash]
                But not in 'unset' rule [!key-with-dash] """
            parseCondition("key-with-dash?")

if __name__ == '__main__':
    unittest.main()
