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
from vtiles_backend import QuadTileBackend as DataBackend
from style import Styling
from render import RasterTile



bbox = (27.115768874532,53.740327031764,28.028320754378,54.067187302158)

w,h = 630,364
z = 14

db = DataBackend()
style = Styling()

res = RasterTile(w, h, z, db)
res.update_surface(bbox, z, style)

res.surface.write_to_png("test.png")