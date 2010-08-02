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
import threading, thread

from twms import projections
import config

#from vtiles_backend import QuadTileBackend as DataBackend
from backend.postgis import PostGisBackend as DataBackend
from mapcss import MapCSS
from render import RasterTile
from tempfile import NamedTemporaryFile

style = MapCSS(1,19)
style.parse(open("/home/kom/osm/kothic/src/styles/default.mapcss","r").read())
os.chdir("/home/kom/osm/kothic/src/")

metatiles_in_progress = {}

renderlock = threading.Lock()

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

   
def kothic_metatile(z, x, y, this_layer):
  
  print z, x, y
  global metatiles_in_progress
  if "max_zoom" in this_layer:
    if z >= this_layer["max_zoom"]:
      return None
  if z<5:
    return None
  
  metatile_id = (z,int(x/8), int(y/8))

  try:
    metatiles_in_progress[metatile_id].join()
  except KeyError:
    metatiles_in_progress[metatile_id] = threading.Thread(None, gen_metatile, None, (metatile_id, this_layer))
    metatiles_in_progress[metatile_id].start()
    metatiles_in_progress[metatile_id].join()
  except RuntimeError:
    pass
  
  
  local = config.tiles_cache + this_layer["prefix"] + "/z%s/%s/x%s/%s/y%s."%(z, x/1024, x, y/1024,y)
  ext = this_layer["ext"]
  if os.path.exists(local+ext):                     # First, look for tile in cache
    try:
        im1 = Image.open(local+ext)
        del metatiles_in_progress[metatile_id]
        return im1
    except IOError:
        os.remove(local+ext)

def gen_metatile(metatile_id, this_layer):
  #renderlock.acquire()
  z, x, y = metatile_id
  z -= 3
  wh = 2560
  bb1 = projections.coords_by_tile(z, x-0.125, y-0.125, "EPSG:3857")
  bb2 = projections.coords_by_tile(z, x+1.125, y+1.125, "EPSG:3857")
  bbox = (bb1[0],bb2[1],bb2[0],bb1[1])
  db = DataBackend()
  res = RasterTile(wh, wh, 1, db, "EPSG:3857")
  res.update_surface(bbox, z+3, style)
  f = NamedTemporaryFile()
  f.close()
  res.surface.write_to_png(f.name)
  del res
  del db
  im = Image.open(f.name)
  os.unlink(f.name)
  im = im.convert("RGBA")
  x*=8
  y*=8
  z+=3
  ext = this_layer["ext"]
  for i in range(x,x+9):
    for j in range(y,y+9):
      local = config.tiles_cache + this_layer["prefix"] + "/z%s/%s/x%s/%s/y%s."%(z, i/1024, i, j/1024,j)
      box = (256*(i-x+1),256*(j-y+1),256*(i-x+2),256*(j-y+2))
      im1 = im.crop(box)
      if not os.path.exists("/".join(local.split("/")[:-1])):
        os.makedirs("/".join(local.split("/")[:-1]))
      im1.save(local+ext)
      del im1
  #renderlock.release()
