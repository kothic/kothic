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


from debug import debug, Timer
from mapcss import MapCSS

style = MapCSS(1, 19)     #zoom levels
style.parse(open("styles/openstreetinfo.mapcss","r").read())

t = ("way", "node")
dct = {}

for a in t:
  for tag in style.get_interesting_tags(type=a):
    if tag not in dct:
      dct[tag] = set()
    dct[tag].add(a)


print dct
print """
# OsmType  Tag                DataType      Flags
node,way   note               text          delete   # These tags can be long but are useless for rendering
node,way   source             text          delete   # This indicates that we shouldn't store them"""
for k,v in dct.iteritems():
  s = ""
  for i in v:
    s += i
    s += ","
  s = s[:-1]
  print "%-10s %-18s %-13s %s"%(s, k, "text", "linear")