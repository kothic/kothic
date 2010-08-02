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
from backend.vtile import QuadTileBackend as DataBackend
#from backend.postgis import PostGisBackend as DataBackend
#from style import Styling
from mapcss import MapCSS

from render import RasterTile

svg = False

if svg:
  import cairo


style = MapCSS(1, 19)     #zoom levels
style.parse(open("styles/default.mapcss","r").read())


bbox = (27.115768874532,53.740327031764,28.028320754378,54.067187302158)

w,h = 630*4,364*4
z = 10

db = DataBackend()
#style = Styling()

res = RasterTile(w, h, z, db)
if svg:
  file = open("test.svg", "wb")
  res.surface = cairo.SVGSurface(file.name, w,h)
res.update_surface(bbox, z, style)


if not svg:
  res.surface.write_to_png("test.png")
else:
  res.surface.finish()