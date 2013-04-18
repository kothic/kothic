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

def get_color_lightness(c):
    if c == 0:
        return 0
    return (2*c[0]+c[2]+3*c[1])/6

def compare_order(a, function, b):
    "a is over b on all zooms"
    global TOTAL_TESTS, FAILED_TESTS
    for zoom in range(minzoom, maxzoom+1):
        for typ1 in ['line', 'node', 'area']:
          for typ2 in ['line', 'node', 'area']:
            sa = [x.get('z-index', 0.) for x in style.get_style(typ1, a, zoom)]
            sb = [x.get('z-index', 0.) for x in style.get_style(typ2, b, zoom)]
            if sa and sb:
                mia = min(sa)
                mab = max(sb)
                TOTAL_TESTS += 1
                if (function == "over") and (mia <= mab):
                    print "ORDER: z%s\t[%s %s %s %s %s]\t[%s, %s], " % (zoom, typ1, mia, function, typ2, mab, repr(a), repr(b))
                    FAILED_TESTS += 1

def compare_line_lightness(a, function, b):
    "a darker than b on all zooms"
    global TOTAL_TESTS, FAILED_TESTS
    for zoom in range(minzoom, maxzoom+1):
        for typ1 in ['line', 'node', 'area']:
          for typ2 in ['line', 'node', 'area']:
            sa = [get_color_lightness(x.get('color', 0.)) for x in style.get_style(typ1, a, zoom)]
            sb = [get_color_lightness(x.get('color', 0.)) for x in style.get_style(typ2, b, zoom)]
            if sa and sb:
                mia = min(sa)
                mab = max(sb)
                TOTAL_TESTS += 1
                if (function == "darker") and (mia >= mab):
                    print "LIGHT: z%s\t[%s %s %s %s %s]\t[%s, %s], " % (zoom, typ1, mia, function, typ2, mab, repr(a), repr(b))
                    FAILED_TESTS += 1

def compare_visibility(a, function, b):
    "a is visible with b on all zooms"
    global TOTAL_TESTS, FAILED_TESTS
    for zoom in range(minzoom, maxzoom+1):
        for typ in ['line', 'node', 'area']:
            sa = [x.get('z-index', 0.) for x in style.get_style(typ, a, zoom)]
            sb = [x.get('z-index', 0.) for x in style.get_style(typ, b, zoom)]
            if sa or sb:
                TOTAL_TESTS += 1
                if (function == "both") and not ((sa) and (sb)):
                    print "VISIBILITY: z%s\t[%s %s %s %s %s]\t[%s, %s], " % (zoom, typ, bool(sa), function, typ, bool(sb), repr(a), repr(b))
                    FAILED_TESTS += 1


compare_order(          {'area:highway': 'primary'},   "over",      {'highway': 'primary'})

compare_order(          {'highway': 'primary'},        "over",      {'waterway': 'river'})
compare_order(          {'highway': 'primary'},        "over",      {'waterway': 'canal'})
compare_order(          {'highway': 'path'},           "over",      {'waterway': 'river'})
compare_order(          {"highway": "motorway"},       "over",      {'highway': 'primary'})
compare_line_lightness( {"highway": "motorway"},       "darker",    {'highway': 'primary'})

compare_order(          {"highway": "motorway_link"},  "over",      {'highway': 'primary_link'})
compare_line_lightness( {"highway": "motorway_link"},  "darker",    {'highway': 'primary_link'})
compare_order(          {"highway": "trunk"},          "over",      {'highway': 'primary'})
compare_line_lightness( {"highway": "trunk"},          "darker",    {'highway': 'primary'})
compare_order(          {"highway": "trunk_link"},     "over",      {'highway': 'primary_link'})
compare_order(          {'highway': 'primary'},        "over",      {'highway': 'residential'})
compare_order(          {'highway': 'primary'},        "over",      {'highway': 'secondary'})
compare_order(          {'highway': 'primary_link'},   "over",      {'highway': 'secondary_link'})
compare_order(          {'highway': 'secondary'},      "over",      {'highway': 'tertiary'})
compare_order(          {'highway': 'secondary_link'}, "over",      {'highway': 'tertiary_link'})
compare_order(          {'highway': 'tertiary'},       "over",      {'highway': 'residential'})
compare_order(          {'highway': 'tertiary'},       "over",      {'highway': 'service'})
compare_order(          {'highway': 'tertiary'},       "over",      {'highway': 'unclassified'})

compare_order(          {'highway': 'tertiary'},       "over",      {"highway": "road"})
compare_order(          {'highway': 'residential'},    "over",      {'highway': "track"})
compare_order(          {'highway': 'residential'},    "over",      {"highway": "living_street"})
compare_order(          {'highway': 'unclassified'},   "over",      {'highway': "track"})
compare_order(          {'highway': 'unclassified'},   "over",      {'highway': "construction"})
compare_order(          {'highway': 'residential'},    "over",      {'highway': "path", "bicycle": "yes"})
compare_order(          {'highway': 'track'},          "over",      {'highway': "path"})
compare_order(          {"highway": "steps"},          "over",      {'highway': "pedestrian"})
compare_order(          {"highway": "steps"},          "over",      {'highway': "footway"})
compare_order(          {"highway": "steps"},          "over",      {'highway': "footway", "tunnel": "yes"})
compare_order(          {"highway": "steps"},          "over",      {'highway': "cycleway"})
compare_order(          {"highway": "cycleway"},       "over",      {'highway': "footway"})

compare_order(          {"highway": "service"},        "over",      {'building': "yes"})

compare_order(          {"railway": "rail"},           "over",      {"waterway": "riverbank"})

compare_order(          {"amenity": "cafe"},           "over",      {'amenity': "parking"})
compare_order(          {"amenity": "bank"},           "over",      {'amenity': "atm"})
compare_order(          {"amenity": "bank"},           "over",      {'amenity': "atm"})
compare_order(          {"railway": "station"},        "over",      {'leisure': "park"})
compare_order(          {"railway": "station"},        "over",      {"highway": "bus_stop"})
compare_order(          {"highway": "tertiary"},       "over",      {"highway": "bus_stop"})
compare_order(          {"highway": "secondary"},      "over",      {"highway": "bus_stop"})
compare_order(          {"highway": "bus_stop"},       "over",      {"amenity": "police"})
compare_order(          {"place": "suburb"},           "over",      {'leisure': "park"})

compare_order(          {"highway": "path"},           "over",      {'man_made': "cut_line"})
compare_order(          {"highway": "footway"},        "over",      {'man_made': "cut_line"})
#compare_order(         {"highway": "bus_stop"},       "over",      {'highway': "trunk"})

#compare_visibility(     {"highway": "motorway"},       "both",      {'highway': 'motorway_link'})
#compare_visibility(     {"highway": "trunk"},          "both",      {'highway': 'trunk_link'})
compare_visibility(     {"highway": "primary"},        "both",      {'highway': 'primary_link'})
compare_visibility(     {"highway": "primary"},        "both",      {'highway': 'trunk_link'})
compare_visibility(     {"highway": "secondary"},      "both",      {'highway': 'secondary_link'})
compare_visibility(     {"highway": "secondary"},      "both",      {'highway': 'primary_link'})
compare_visibility(     {"highway": "tertiary"},       "both",      {'highway': 'tertiary_link'})

print "Failed tests: %s (%s%%)" % (FAILED_TESTS, 100*FAILED_TESTS/TOTAL_TESTS)
print "Passed tests:", TOTAL_TESTS - FAILED_TESTS
print "Total tests:", TOTAL_TESTS