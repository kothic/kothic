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

import os
import sys
from lxml import etree
from twms import projections
from style import Styling

try:
  import psyco
  psyco.full()
except ImportError:
  pass

MAXZOOM = 16
proj = "EPSG:4326"

style = Styling()

#  elsif($k eq 'highway' and $v eq 'footway' or $v eq 'path' or $v eq 'track'){

def tilelist_by_geometry(way, start_zoom = 0, ispoly = False):
  """
  Gives a number of (z,x,y) tile numbers that geometry crosses.
  """
  ret = set([])
  tiles_by_zooms = {}  # zoom: set(tile,tile,tile...)
  for t in xrange(0,MAXZOOM+1):
    tiles_by_zooms[t] = set([])
  for point in way:
    tile = projections.tile_by_coords(point, MAXZOOM, proj)
    tile = (MAXZOOM, int(tile[0]),int(tile[1]))
    tiles_by_zooms[MAXZOOM].add(tile)
  for t in xrange(MAXZOOM-1,start_zoom-1,-1):
    for tt in tiles_by_zooms[t+1]:
      tiles_by_zooms[t].add((t, int(tt[1]/2), int(tt[2]/2)))
  for z in tiles_by_zooms.values():
    ret.update(z)
  return ret

def pix_distance(a,b,z):
  """
  Calculates onscreen disatnce between 2 points on given zoom.
  """
  return 2**z*256*(((a[0]-b[0])/360.)**2+((a[1]-b[1])/180.)**2)**0.5


def main ():
  DROPPED_POINTS = 0
  tilefiles = {}
  osm_infile = open("minsk.osm", "rb")
  nodes = {}
  curway = []
  tags = {}
  context = etree.iterparse(osm_infile)
  for action, elem in context:
    items = dict(elem.items())
    if elem.tag == "node":
      nodes[int(items["id"])] = (float(items["lon"]), float(items["lat"]))
    elif elem.tag == "nd":
      curway.append(nodes[int(items["ref"])])
    elif elem.tag == "tag":
      tags[items["k"]] = items["v"]
    elif elem.tag == "way":
      mzoom = 1

      if style.get_style("way", tags, True):            # if way is stylized
        tags = style.filter_tags(tags)
        towrite = ";".join(["%s=%s"%x for x in tags.iteritems()])  ### TODO: sanitize keys and values
        #print towrite
        way_simplified = {MAXZOOM: curway}
        
        for zoom in xrange(MAXZOOM-1,-1,-1):      ########   generalize a bit
                              # TODO: Douglas-Peucker
          prev_point = curway[0]
          way = [prev_point]
          for point in curway:
            if pix_distance(point, prev_point, zoom) > 1.5:
              way.append(point)
              prev_point = point
            else:
              DROPPED_POINTS += 1

          if len(way) == 1:
            mzoom = zoom
            #print zoom
            break
          if len(way) > 1:
            way_simplified[zoom] = way
            #print way
        for tile in tilelist_by_geometry(curway, mzoom+1):
          z, x, y = tile
          path = "tiles/z%s/%s/x%s/%s/"%(z, x/1024, x, y/1024)
          if tile not in tilefiles:

            if not os.path.exists(path):
              os.makedirs(path)
            tilefiles[tile] = "aaa"
            tilefile = open(path+"y"+str(y)+".vtile","wb")
          tilefile = open(path+"y"+str(y)+".vtile","a")
          print >>tilefile, "%s %s" % (towrite, items["id"]), " ".join([str(x[0])+" "+str(x[1]) for x in way_simplified[tile[0]]])
          tilefile.flush()
          tilefile.close()
          
      #print >>corr, "%s %s %s %s %s %s"% (curway[0][0],curway[0][1],curway[1][0],curway[1][1], user, ts )
      curway = []
      tags = {}
      #user = default_user
      #ts = ""
  print "Tiles generated:",len(tilefiles)
  print "Nodes dropped when generalizing:", DROPPED_POINTS
  print "Nodes in memory:", len(nodes)

main()
