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

from debug import debug
from twms import projections

class Way:
  def __init__(self, tags, coords):
    self.coords = coords
    self.cs = None
    #print [x.split("=") for x in tags.split(";")]
    self.tags = dict((x.split("=") for x in tags.split(";")))

class QuadTileBackend:
  """
  A class that gives out vector data on demand.
  """
  

  def __init__(self,max_zoom = 16,proj = "EPSG:4326", path = "tiles", lang = "ru"):

    debug("Bakend created")
    self.max_zoom = max_zoom            # no better tiles available
    self.path = path                    # path to tile files
    self.lang = lang                    # map language to use
    self.tiles = {}                     # loaded vector tiles go here
    self.data_projection = proj         # which projection used to cut map in tiles
    self.keep_tiles = 90                # a number of tiles to cache in memory
    self.tile_load_log = []             # used when selecting which tile to unload
    
  def filename(self, (z,x,y)):
    return "%s/z%s/%s/x%s/%s/y%s.vtile"%(self.path, z, x/1024, x, y/1024, y)
  def load_tile(self, k):
    debug("loading tile: %s"% (k,))
    try:
      f = open(self.filename(k))
    except IOError:
      debug ( "Failed open: %s" % self.filename(k) )
      return {}
    t = {}
    for line in f:
      a = line.split(" ")
      w = Way(a[0], [float(x) for x in a[2:]])
      t[int(a[1])] = w
    f.close()
    return t
  def collect_garbage(self):
    """
    Cleans up some RAM by removing least accessed tiles.
    """
    if len(self.tiles) > self.keep_tiles:
      debug("Now %s tiles cached, trying to kill %s"%(len(self.tiles),len(self.tiles)-self.keep_tiles))
      for tile in self.tile_load_log[0:len(self.tiles)-self.keep_tiles]:
        try:
          del self.tiles[tile]
          self.tile_load_log.remove(tile)
          debug ("killed tile: %s" % (tile,))
        except KeyError, ValueError:
          debug ("tile killed not by us: %s" % (tile,))

  def get_vectors (self, bbox, zoom):
    zoom = min(zoom, self.max_zoom)     ## If requested zoom is better than the best, take the best
    zoom = max(zoom, 0)                 ## Negative zooms are nonsense
    a,d,c,b = [int(x) for x in projections.tile_by_bbox(bbox,zoom, self.data_projection)]
    resp = {}
    for tile in set([(zoom,i,j) for i in range(a, c+1) for j in range(b, d+1)]):
      if tile not in self.tiles:
        self.tiles[tile] = self.load_tile(tile)
      try:
        self.tile_load_log.remove(tile)
      except ValueError:
        pass
      self.tile_load_log.append(tile)
      resp.update(self.tiles[tile])
    self.collect_garbage()
    return resp