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
from twms import projections
import cairo
import math


def line(cr, c):
  cr.move_to(*c[0])
  for k in c:
    cr.line_to(*k)
  cr.stroke()

def poly(cr, c):
  cr.move_to(*c[0])
  for k in c:
    cr.line_to(*k)
  cr.fill()





class RasterTile:
  def __init__(self, width, height, zoomlevel, data_backend, raster_proj="EPSG:3395"):
    self.w = width
    self.h = height
    self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.w, self.h)
    self.offset_x = 0
    self.offset_y = 0
    self.bbox = (0.,0.,0.,0.)
    self.bbox_p = (0.,0.,0.,0.)
    self.zoomlevel = zoomlevel
    self.zoom = None
    self.data = data_backend
    self.proj = raster_proj
  def screen2lonlat(self, lon, lat):
    lo1, la1, lo2, la2 = self.bbox_p
    
    #debug ("%s %s %s"%(lon, lat, repr(self.bbox_p)))
    return projections.to4326(((lon)/(self.w-1)*(lo2-lo1)+lo2, la2+((lat)/(self.h-1)*(la2-la1))),self.proj)
  #  return (x - self.w/2)/(math.cos(self.center_coord[1]*math.pi/180)*self.zoom) + self.center_coord[0], -(y - self.h/2)/self.zoom + self.center_coord[1]
  def lonlat2screen(self, (lon, lat)):
    lo1, la1, lo2, la2 = self.bbox_p
    return ((lon-lo1)*(self.w-1)/abs(lo2-lo1), ((la2-lat)*(self.h-1)/(la2-la1)))
  #  return (lon - self.center_coord[0])*self.lcc*self.zoom + self.w/2, -(lat - self.center_coord[1])*self.zoom + self.h/2
  def update_surface_by_center(self, lonlat, zoom, style, lock = None):
    self.zoom = zoom
    xy = projections.from4326(lonlat, self.proj)
    xy1 = projections.to4326((xy[0]-40075016*0.5**self.zoom/256*self.w, xy[1]-40075016*0.5**self.zoom/256*self.h), self.proj)
    xy2 = projections.to4326((xy[0]+40075016*0.5**self.zoom/256*self.w, xy[1]+40075016*0.5**self.zoom/256*self.h), self.proj)
    bbox = (xy1[0],xy1[1],xy2[0],xy2[1])
    debug (bbox)
    return self.update_surface(bbox, zoom, style, lock)

    
  def update_surface(self, bbox, zoom, style, lock = None):
    rendertimer = Timer("Rendering image")
    timer = Timer("Getting data")
    self.zoom = zoom
    print self.zoom, self.zoomlevel
    self.bbox = bbox
    self.bbox_p = projections.from4326(bbox,self.proj)
    debug(zoom)
    bgs = style.get_style("canvas", {}, self.zoom)[0]
    cr = cairo.Context(self.surface)
    cr.rectangle(0, 0, self.w, self.h)
    color = bgs.get("fill-color",(0.7, 0.7, 0.7))
    cr.set_source_rgba(color[0], color[1], color[2], bgs.get("fill-opacity", 1))
    #cr.set_source_rgb(0, 0, 0)
    cr.fill()
    datatimer = Timer("Asking backend and styling")
    vectors = self.data.get_vectors(bbox,self.zoom).values()
    ww = []
    for way in vectors:
      st = style.get_style("way", way.tags, self.zoom)
      if st:
       for fpt in st:
        ww.append((way, fpt))
    #ww = [ (x, style.get_style("way", x.tags, self.zoom)) for x in self.data.get_vectors(bbox,self.zoom).values()]
    datatimer.stop()
    #ww1 = []
    #for way in ww:
    #  if way[1]:
    #    ww1.append(way)
    debug( "%s objects on screen (%s in dataset)"%(len(ww),len(vectors)) )
    #ww = ww1

    if lock is not None:
      lock.acquire()
      lock.release()
    for w in ww:
      w[0].cs = [self.lonlat2screen(coord) for coord in projections.from4326(w[0].coords, self.proj)]
      #debug(w[0].cs)
      

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
          cr.set_line_width (1)
          excoords = [(a[0],a[1]+hgt) for a in obj[0].cs]
          for c in excoords:
            line(cr, [(c[0],c[1]),(c[0],c[1]-hgt)])
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
            c = obj[0].cs
            text = unicode(text,"utf-8")
            # - calculate line length
            length = reduce(lambda x,y: (x[0]+((y[0]-x[1])**2 + (y[1]-x[2])**2 )**0.5, y[0], y[1]), c, (0,c[0][0],c[0][1]))[0]
            print length, text, cr.text_extents(text)
            if length > cr.text_extents(text)[2]:

              # - function to get (x, y, normale) from (c, length_along_c)
              def get_xy_from_len(c,length_along_c):
                x0, y0 = c[0]
                for x,y in c:
                  seg_len = ((x-x0)**2+(y-y0)**2)**0.5
                  if length_along_c < seg_len:
                    normed =  length_along_c /seg_len
                    return (x-x0)*normed+x0, (y-y0)*normed+y0, math.atan2(y-y0,x-x0)
                  else:
                    length_along_c -= seg_len
                    x0,y0 = x,y
                else:
                  return None
              da = 0
              os = 1
              z = length/2-cr.text_extents(text)[2]/2
              print get_xy_from_len(c,z)
              if c[0][0] < c[1][0] and get_xy_from_len(c,z)[2]<math.pi/2 and get_xy_from_len(c,z)[2] > -math.pi/2:
                da = 0
                os = 1
                z = length/2-cr.text_extents(text)[2]/2
              else:
                da = math.pi
                os = -1
                z = length/2+cr.text_extents(text)[2]/2
              z1=z
              if "text-halo-color" in obj[1] or "text-halo-radius" in obj[1]:
                cr.set_line_width (obj[1].get("text-halo-radius", 1))
                color = obj[1].get("text-halo-color", (1.,1.,1.))
                cr.set_source_rgb(color[0], color[1], color[2])
                for letter in text:
                  cr.new_path()
                  xy = get_xy_from_len(c,z)
                  #print letter, cr.text_extents(letter)
                  cr.move_to(xy[0],xy[1])
                  cr.save()
                  cr.rotate(xy[2]+da)
                  cr.text_path(letter)
                  cr.restore()
                  cr.stroke()
                  z += os*cr.text_extents(letter)[4]

              color = obj[1].get("text-color", (0.,0.,0.))
              cr.set_source_rgb(color[0], color[1], color[2])
              z = z1
              for letter in text:
                cr.new_path()
                xy = get_xy_from_len(c,z)
                #print letter, cr.text_extents(letter)
                cr.move_to(xy[0],xy[1])
                cr.save()
                cr.rotate(xy[2]+da)
                cr.text_path(letter)
                cr.restore()
                cr.fill()
                z += os*cr.text_extents(letter)[4]

      texttimer.stop()

    timer.stop()
    rendertimer.stop()
    debug(self.bbox)