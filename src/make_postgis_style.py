#!/usr/bin/env python
# -*- coding: utf-8 -*-
#    This file is part of kothic, the realtime map renderer.

#   kothic is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   kothic is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with kothic.  If not, see <http://www.gnu.org/licenses/>.

import sys

from debug import debug, Timer
from mapcss import MapCSS


langs = ['int_name', 'name:af', 'name:am', 'name:ar', 'name:be', 'name:bg', 'name:br', 'name:ca', 'name:cs', 'name:cy', 'name:de', 'name:el', 'name:en', 'name:eo', 'name:es', 'name:et', 'name:eu', 'name:fa', 'name:fi', 'name:fr', 'name:fur', 'name:fy', 'name:ga', 'name:gd', 'name:gsw', 'name:he', 'name:hi', 'name:hr', 'name:hsb', 'name:hu', 'name:hy', 'name:it', 'name:ja', 'name:ja_kana', 'name:ja_rm', 'name:ka', 'name:kk', 'name:kn', 'name:ko', 'name:ko_rm', 'name:ku', 'name:la', 'name:lb', 'name:lt', 'name:lv', 'name:mk', 'name:mn', 'name:nl', 'name:pl', 'name:pt', 'name:ro', 'name:ru', 'name:sk', 'name:sl', 'name:sq', 'name:sr', 'name:sv', 'name:th', 'name:tr', 'name:uk', 'name:vi', 'name:zh', 'name:zh_pinyin']

if len(sys.argv) < 2:
    print "Usage: make_postgis_style.py [stylesheet] [additional_tag,tag2,tag3]"
    exit()

style = MapCSS(1, 19)  # zoom levels
style.parse(open(sys.argv[1], "r").read())

dct = {}

if len(sys.argv) >= 3:
    langs.extend(sys.argv[2].split(","))
    dct = dict([(k, set([("node", "linear"), ('way', 'linear')])) for k in langs])

t = {"node": ("node", "linear"), "line": ("way", "linear"), "area": ("way", "polygon")}

for a in t:
    for tag in style.get_interesting_tags(type=a):
        if tag not in dct:
            dct[tag] = set()
        dct[tag].add(t[a])

print """
# OsmType  Tag                DataType      Flags"""
for t in ("z_order", "way_area", ":area"):
    if t in dct:
        del dct[t]

keys = dct.keys()
keys.sort()

for k in keys:
    v = dct[k]
    s = ",".join(set([i[0] for i in v]))
    pol = "linear"
    if "polygon" in set([i[1] for i in v]):
        pol = "polygon"
    print "%-10s %-20s %-13s %s" % (s, k, "text", pol)
print """
node,way   z_order              int4          linear # This is calculated during import
way        way_area             real                 # This is calculated during import"""
