# -*- coding: utf-8 -*-
#    This file is part of tWMS.

#   tWMS is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.

#   tWMS is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.

#   You should have received a copy of the GNU General Public License
#   along with tWMS.  If not, see <http://www.gnu.org/licenses/>.

import StringIO
import Image
import os

from twms import projections

#from vtiles_backend import QuadTileBackend as DataBackend
from backend.postgis import PostGisBackend as DataBackend
from mapcss import MapCSS
from render import RasterTile
from tempfile import NamedTemporaryFile

style = MapCSS(1,19)
style.parse(open("/home/kom/osm/kothic/src/styles/openstreetinfo.mapcss","r").read())



def kothic_fetcher (z, x, y, this_layer):
   if "max_zoom" in this_layer:
    if z >= this_layer["max_zoom"]:
      return None   
   bbox = projections.bbox_by_tile(z,x,y,"EPSG:3857")
   db = DataBackend(path="/home/kom/osm/kothic/src/tiles")
   res = RasterTile(256, 256, 1, db, "EPSG:3857")
   res.update_surface(bbox, z, style)
   f = NamedTemporaryFile()
   f.close()
   res.surface.write_to_png(f.name)
   del res
   del db
   im = Image.open(f.name)
   os.unlink(f.name)
   im = im.convert("RGBA")

   return im
