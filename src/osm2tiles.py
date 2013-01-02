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
import sqlite3
import sys
from lxml import etree
from twms import projections
from style import Styling

reload(sys)
sys.setdefaultencoding("utf-8")          # a hack to support UTF-8 

try:
  import psyco
  psyco.full()
except ImportError:
  pass

MAXZOOM = 16
TEMPORARY_FILE_PATH = 'temp_file.bin'

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
  Calculates onscreen distance between 2 points on given zoom.
  """
  return 2**z*256*(((a[0]-b[0])/360.)**2+((a[1]-b[1])/180.)**2)**0.5

def sanitize(string):
  string=string.replace(" ", "_")
  string=string.replace(";", ",")
  string=string.replace("=", "###")
  return string

print sanitize (" ;=")

def initDB(filename):
  conn = sqlite3.connect(filename)
  c = conn.cursor()
  # create table
  c.execute('''CREATE TABLE nodes (id integer, lat real, lon real)''')
  # create index in the id column
  # - this makes node id lookup MUCH faster
  c.execute('''CREATE INDEX id_idx ON nodes(id)''')
  return conn

def storeNode(conn, id, lat, lon):
#  conn.execute("INSERT INTO nodes VALUES ('%d', %f, %f)" % (id, lat, lon))
  conn.execute("INSERT INTO nodes(id, lat, lon) values (?, ?, ?)", (id, lat, lon))

def getNode(conn, id):
#  conn.execute("SELECT * FROM nodes WHERE id = '%s'" % id)
  return conn.execute("SELECT lat, lon FROM nodes WHERE id = '%s'" % id).fetchone()

def main ():
  DROPPED_POINTS = 0
  WAYS_WRITTEN = 0
  NODES_READ = 0
  WAYS_READ = 0
  tilefiles = {}
  tilefiles_hist = []
  #osm_infile = open("minsk.osm", "rb")
  osm_infile = sys.stdin

  # remove any stale temporary files
  if os.path.exists(TEMPORARY_FILE_PATH):
    os.remove(TEMPORARY_FILE_PATH)
  conn = initDB(TEMPORARY_FILE_PATH)

#  nodes = {}
  curway = []
  tags = {}
  context = etree.iterparse(osm_infile)
  for action, elem in context:
    items = dict(elem.items())
    if elem.tag == "node":
      NODES_READ += 1
      if NODES_READ % 10000 == 0:
        print "Nodes read:", NODES_READ
        print len(curway), len(tags), len(tilefiles), len(tilefiles_hist)
      if NODES_READ % 100000 == 0:
        conn.commit()
        print "flushing to temporary storage"

#      nodes[str(items["id"])] = (float(items["lon"]), float(items["lat"]))
      storeNode(conn, int(items["id"]), float(items["lon"]), float(items["lat"]))
      tags = {}
    elif elem.tag == "nd":
      result = getNode(conn, int(items["ref"]))
      if result:
        curway.append(result)
#      try:
#        curway.append(nodes[str(items["ref"])])
#      except KeyError:
#        pass
    elif elem.tag == "tag":
      tags[sanitize(items["k"])] = sanitize(items["v"])
    elif elem.tag == "way":
      WAYS_READ += 1
      if WAYS_READ % 1000 == 0:
        print "Ways read:", WAYS_READ
        
      mzoom = 1
      #tags = style.filter_tags(tags)
      if tags:
        if True:#style.get_style("way", tags, True):            # if way is stylized
          towrite = ";".join(["%s=%s"%x for x in tags.iteritems()])  ### TODO: sanitize keys and values
          #print towrite
          way_simplified = {MAXZOOM: curway}

          for zoom in xrange(MAXZOOM-1,-1,-1):      ########   generalize a bit
                                # TODO: Douglas-Peucker
            prev_point = curway[0]
            way = [prev_point]
            for point in way_simplified[zoom+1]:
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
              tilefiles[tile] = open(path+"y"+str(y)+".vtile","wb")
              tilefiles_hist.append(tile)
            else:
              if not tilefiles[tile]:
                tilefiles[tile] = open(path+"y"+str(y)+".vtile","a")
                tilefiles_hist.append(tile)
            tilefiles_hist.remove(tile)
            tilefiles_hist.append(tile)
            print >>tilefiles[tile], "%s %s" % (towrite, items["id"]), " ".join([str(x[0])+" "+str(x[1]) for x in way_simplified[tile[0]]])
            if len(tilefiles_hist) > 400:
              print "Cleaned up tiles. Wrote by now:", len(tilefiles),"active:",len(tilefiles_hist)
              for tile in tilefiles_hist[0:len(tilefiles_hist)-100]:


                tilefiles_hist.remove(tile)
                tilefiles[tile].flush()
                tilefiles[tile].close()
                tilefiles[tile] = None


        #print >>corr, "%s %s %s %s %s %s"% (curway[0][0],curway[0][1],curway[1][0],curway[1][1], user, ts )
        WAYS_WRITTEN += 1
        if WAYS_WRITTEN % 10000 == 0:
          print WAYS_WRITTEN
      curway = []
      tags = {}
    elem.clear()
    # extra insurance
    del elem
        #user = default_user
        #ts = ""
  print "Tiles generated:",len(tilefiles)
  print "Nodes dropped when generalizing:", DROPPED_POINTS
#  print "Nodes in memory:", len(nodes)
  c = conn.cursor()
  c.execute('SELECT * from nodes')
  print "Nodes in memory:", len(c.fetchall())

  # report temporary file size
  print "Temporary file size:", os.path.getsize(TEMPORARY_FILE_PATH)

  # remove temporary files
  os.remove(TEMPORARY_FILE_PATH)

main()
