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

import cairo


class Renderer:
  def __init__(self, width, height, zoom, data_projection):
    self.w = width
    self.h = height
    self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.w, self.h)
    self.offset_x = 0
    self.offset_y = 0
    self.center_coord = None
    self.zoomlevel = zoom
    self.zoom = None
    self.data_projection = data_projection
  def screen2lonlat(self, x, y):
    return (x - self.w/2)/(math.cos(self.center_coord[1]*math.pi/180)*self.zoom) + self.center_coord[0], -(y - self.h/2)/self.zoom + self.center_coord[1]
  def lonlat2screen(self, (lon, lat)):
    return (lon - self.center_coord[0])*self.lcc*self.zoom + self.w/2, -(lat - self.center_coord[1])*self.zoom + self.h/2
  def update_surface(self, lonlat, zoom, tilecache, style, lock = None):
    self.zoom = zoom
    self.center_coord = lonlat
    cr = cairo.Context(self.surface)
    cr.rectangle(0, 0, self.w, self.h)
    cr.set_source_rgb(0.7, 0.7, 0.7)
    cr.fill()
    lonmin, latmin = self.screen2lonlat(0, self.h)
    lonmax, latmax = self.screen2lonlat(self.w, 0)
    a,d,c,b = [int(x) for x in projections.tile_by_bbox((lonmin, latmin, lonmax, latmax),self.zoomlevel, self.data_projection)]

    #debug((latmin, lonmin, latmax, lonmax))
    debug(( a, b, c, d))
#FIXME: add time
    active_tile = set([(self.zoomlevel,i,j) for i in range(a, c+1) for j in range(b, d+1)])
    debug("Active tiles in memory: %s" % len(active_tile))
    for k in tilecache.keys():
      if k not in active_tile:
        del tilecache[k]
        debug("del tile: %s" % (k,))
    for k in active_tile:
      if k not in tilecache:
        tilecache[k] = load_tile(k)
    #FIXME add time2
    ww = ways(tilecache)
    debug("ways: %s" % len(ww))
    if lock is not None:
      lock.acquire()
      lock.release()
    self.lcc = math.cos(self.center_coord[1]*math.pi/180)
    ww.sort(key=lambda x: style[x.style][3])
    lcc = math.cos(self.center_coord[1]*math.pi/180)
    for w in ww:
      cs = []
      for k in range(0, len(w.coords), 2):
        x, y = self.lonlat2screen((w.coords[k], w.coords[k+1]));
        cs.append(x)
        cs.append(y)
      w.cs = cs
    for passn in range(1, 4):
      debug("pass %s" % passn)
      for w in ww:
        stn = w.style
        #if lock is not None:
          #lock.acquire()
          #lock.release()
        if stn < len(style) and style[stn] is not None and style[stn][passn-1] is not None:
          st = style[w.style][passn-1]
          cr.set_line_width(st[0])
          cr.set_source_rgb(st[1][0], st[1][1], st[1][2])
          if w.type == "L":
            line(cr, w.cs)
          elif w.type == "P":
            poly(cr, w.cs)