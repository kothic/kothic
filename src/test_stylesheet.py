#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mapcss import MapCSS
import mapcss.webcolors
whatever_to_hex = mapcss.webcolors.webcolors.whatever_to_hex
import sys

reload(sys)
sys.setdefaultencoding("utf-8")

minzoom = 0
maxzoom = 18

style = MapCSS(minzoom, maxzoom)
style.parse(open(sys.argv[1],"r").read(), clamp=False)
TOTAL_TESTS = 0
FAILED_TESTS = 0

def compare_zoom(a, function, b):
    "a is over b on all zooms"
    global TOTAL_TESTS, FAILED_TESTS
    for zoom in range(minzoom, maxzoom+1):
        for typ1 in ['line', 'node', 'area']:
          for typ2 in ['line', 'node', 'area']:
            sa = [x.get('z-index', 0.) for x in style.get_style(typ1, a, zoom)]
            sb = [x.get('z-index', 0.) for x in style.get_style(typ2, b, zoom)]
            if sa and sb:
                la = min(sa)
                lb = max(sb)
                TOTAL_TESTS += 1
                if la < lb:
                    print "BAD: z%s\t[%s %s %s %s %s]\t[%s, %s], " % (zoom,typ1,la,function, typ2,lb, repr(a), repr(b))
                    FAILED_TESTS += 1



compare_zoom({'area:highway': 'primary'},   "over", {'highway': 'primary'})

compare_zoom({'highway': 'primary'},        "over", {'waterway': 'river'})
compare_zoom({'highway': 'path'},           "over", {'waterway': 'river'})


compare_zoom({"highway": "motorway"},       "over", {'highway': 'primary'})
compare_zoom({"highway": "motorway_link"},  "over", {'highway': 'primary_link'})
compare_zoom({"highway": "trunk"},          "over", {'highway': 'primary'})
compare_zoom({"highway": "trunk_link"},     "over", {'highway': 'primary_link'})
compare_zoom({'highway': 'primary'},        "over", {'highway': 'secondary'})
compare_zoom({'highway': 'primary_link'},   "over", {'highway': 'secondary_link'})
compare_zoom({'highway': 'secondary'},      "over", {'highway': 'tertiary'})
compare_zoom({'highway': 'secondary_link'}, "over", {'highway': 'tertiary_link'})
compare_zoom({'highway': 'tertiary'},       "over", {'highway': 'residential'})
compare_zoom({'highway': 'tertiary'},       "over", {'highway': 'service'})
compare_zoom({'highway': 'tertiary'},       "over", {'highway': 'unclassified'})
compare_zoom({'highway': 'tertiary'},       "over", {"highway": "living_street"})
compare_zoom({'highway': 'tertiary'},       "over", {"highway": "road"})
compare_zoom({'highway': 'residential'},    "over", {'highway': "track"})
compare_zoom({'highway': 'residential'},    "over", {'highway': "service"})
compare_zoom({'highway': 'unclassified'},   "over", {'highway': "track"})
compare_zoom({'highway': 'track'},          "over", {'highway': "path"})
compare_zoom({"highway": "steps"},          "over", {'highway': "pedestrian"})
compare_zoom({"highway": "steps"},          "over", {'highway': "footway"})
compare_zoom({"highway": "steps"},          "over", {'highway': "cycleway"})
compare_zoom({"highway": "cycleway"},       "over", {'highway': "footway"})


compare_zoom({"amenity": "bank"},           "over", {'amenity': "atm"})
compare_zoom({"amenity": "bank"},           "over", {'amenity': "atm"})
compare_zoom({"railway": "station"},        "over", {'leisure': "park"})



print "Failed tests: %s (%s%%)" % (FAILED_TESTS, 100*FAILED_TESTS/TOTAL_TESTS)
print "Passed tests:", TOTAL_TESTS - FAILED_TESTS
print "Total tests:", TOTAL_TESTS