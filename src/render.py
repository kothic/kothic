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
import cairo
import math


def line(cr, c):
  cr.move_to(c[0], c[1])
  for k in range(2, len(c), 2):
    cr.line_to(c[k], c[k + 1])
  cr.stroke()

def poly(cr, c):
  cr.move_to(c[0], c[1])
  for k in range(2, len(c), 2):
    cr.line_to(c[k], c[k + 1])
  cr.fill()





class RasterTile:
  def __init__(self, width, height, zoom, data_backend):
    self.w = width
    self.h = height
    self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.w, self.h)
    self.offset_x = 0
    self.offset_y = 0
    self.center_coord = None
    self.zoomlevel = zoom
    self.zoom = None
    self.data = data_backend
  def screen2lonlat(self, x, y):
    return (x - self.w/2)/(math.cos(self.center_coord[1]*math.pi/180)*self.zoom) + self.center_coord[0], -(y - self.h/2)/self.zoom + self.center_coord[1]
  def lonlat2screen(self, (lon, lat)):
    return (lon - self.center_coord[0])*self.lcc*self.zoom + self.w/2, -(lat - self.center_coord[1])*self.zoom + self.h/2
  def update_surface(self, lonlat, zoom, tilecache, style, lock = None):
    rendertimer = Timer("Rendering image")
    timer = Timer("Gettimg data")
    self.zoom = zoom
    self.center_coord = lonlat
    cr = cairo.Context(self.surface)
    cr.rectangle(0, 0, self.w, self.h)
    cr.set_source_rgb(0.7, 0.7, 0.7)
    cr.fill()
    lonmin, latmin = self.screen2lonlat(0, self.h)
    lonmax, latmax = self.screen2lonlat(self.w, 0)
    datatimer = Timer("Asking backend and styling")
    ww = [ (x, style.get_style("way", x.tags)) for x in self.data.get_vectors((lonmin,latmin,lonmax,latmax),self.zoomlevel).values()]
    datatimer.stop()
    ww1 = []
    for way in ww:
      if way[1]:
        ww1.append(way)
    debug( "%s objects on screen (%s in dataset)"%(len(ww1),len(ww)) )
    ww = ww1

    if lock is not None:
      lock.acquire()
      lock.release()
    self.lcc = math.cos(self.center_coord[1]*math.pi/180)


    #debug(objs_by_layers)
    #ww = [x[0] for x in ww]

    lcc = math.cos(self.center_coord[1]*math.pi/180)
    for w in ww:
      cs = []
      for k in range(0, len(w[0].coords), 2):
        x, y = self.lonlat2screen((w[0].coords[k], w[0].coords[k+1]));
        cs.append(x)
        cs.append(y)
      w[0].cs = cs

    ww.sort(key=lambda x: x[1]["layer"])
    layers = list(set([int(x[1]["layer"]/100.) for x in ww]))
    layers.sort()
    objs_by_layers = {}
    for layer in layers:
      objs_by_layers[layer] = []
    for obj in ww:
    #  debug(obj)
      objs_by_layers[int(obj[1]["layer"]/100.)].append(obj)
      #debug ((obj[1]["layer"], obj[0].tags))
    del ww
    timer.stop()
    timer = Timer("Rasterizing image")
    linecaps = {"butt":0, "round":1, "square":2}
    linejoin = {"miter":0, "round":1, "bevel":2}

    text_rendered_at = set([(-100,-100)])
    #cr.set_antialias(2)
    for layer in layers:
      data = objs_by_layers[layer]
      # - fill polygons
      for obj in data:
        if "fill-color" in obj[1]:   ## TODO: fill-image
          color = obj[1]["fill-color"]
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("fill-opacity", 1))

          if not "extrude" in obj[1]:
            poly(cr, obj[0].cs)
          else:
            line(cr, obj[0].cs)
        if "extrude" in obj[1]:
          hgt = obj[1]["extrude"]
          c = obj[0].cs
          excoords = [c[0], c[1]-hgt]
          #pp = (c[0],c[1])
          cr.set_line_width (1)
          for k in range(2, len(c), 2):
            excoords.append(c[k])
            excoords.append(c[k + 1]-hgt)

            line(cr, [c[k],c[k+1],c[k],c[k+1]-hgt],)
          poly(cr,excoords)
          #line(cr, obj[0].cs)



      # - draw casings on layer
      for obj in data:
        ### Extras: casing-linecap, casing-linejoin
        if "casing-width" in obj[1] or "casing-color" in obj[1]:
          cr.set_dash(obj[1].get("casing-dashes",obj[1].get("dashes", [])))
          cr.set_line_join(linejoin.get(obj[1].get("casing-linejoin",obj[1].get("linejoin", "round")),1))
          color = obj[1].get("casing-color", (0,0,0))
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("casing-opacity", 1))
                ## TODO: good combining of transparent lines and casing
                ## Probable solution: render casing, render way as mask and put casing with mask chopped out onto image


          cr.set_line_width (obj[1].get("casing-width", obj[1].get("width",0)+1 ))
          cr.set_line_cap(linecaps.get(obj[1].get("casing-linecap", obj[1].get("linecap", "butt")),0))
          line(cr, obj[0].cs)
      # - draw line centers
      for obj in data:
        if "width" in obj[1] or "color" in obj[1]:
          cr.set_dash(obj[1].get("dashes", []))
          cr.set_line_join(linejoin.get(obj[1].get("linejoin", "round"),1))
          color = obj[1].get("color", (0,0,0))
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("opacity", 1))
                ## TODO: better overlapping of transparent lines.
                ## Probable solution: render them (while they're of the same opacity and layer) on a temporary canvas that's merged into main later
          cr.set_line_width (obj[1].get("width", 1))
          cr.set_line_cap(linecaps.get(obj[1].get("linecap", "butt"),0))
          line(cr, obj[0].cs)
      # - render text labels
      texttimer = Timer("Text rendering")
      cr.set_line_join(1)  # setting linejoin to "round" to get less artifacts on halo render
      for obj in data:
        if "text" in obj[1]:

          text = obj[1]["text"]

          cr.set_line_width (obj[1].get("width", 1))
          cr.set_font_size(obj[1].get("font-size", 9))
          if obj[1].get("text-position", "center") == "center":
            where = self.lonlat2screen(obj[0].center)
            for t in text_rendered_at:
              if ((t[0]-where[0])**2+(t[1]-where[1])**2)**(0.5) < 15:
                break
            else:
                text_rendered_at.add(where)
            #debug ("drawing text: %s at %s"%(text, where))
                if "text-halo-color" in obj[1] or "text-halo-radius" in obj[1]:
                  cr.new_path()
                  cr.move_to(where[0], where[1])
                  cr.set_line_width (obj[1].get("text-halo-radius", 1))
                  color = obj[1].get("text-halo-color", (1.,1.,1.))
                  cr.set_source_rgb(color[0], color[1], color[2])
                  cr.text_path(text)
                  cr.stroke()
                cr.new_path()
                cr.move_to(where[0], where[1])
                cr.set_line_width (obj[1].get("text-halo-radius", 1))
                color = obj[1].get("text-color", (0.,0.,0.))
                cr.set_source_rgb(color[0], color[1], color[2])
                cr.text_path(text)
                cr.fill()
          else:  ### render text along line
            pass
      texttimer.stop()

    timer.stop()
    rendertimer.stop()