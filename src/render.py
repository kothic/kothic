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
import os as os_module


def line(cr, c):
  cr.move_to(*c[0])
  for k in c:
    cr.line_to(*k)
  cr.stroke()

def poly(cr, c, fill=True):
  cr.move_to(*c[0])
  for k in c:
    cr.line_to(*k)
  cr.fill()





class RasterTile:
  def __init__(self, width, height, zoomlevel, data_backend, raster_proj="EPSG:3857"):
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
  def __del__(self):
    del self.surface
    
  def screen2lonlat(self, x, y):
    lo1, la1, lo2, la2 = self.bbox_p
    
    debug ("%s %s - %s %s"%(x,y,self.w, self.h))
    debug(self.bbox_p)
    
    return projections.to4326( (1.*x/self.w*(lo2-lo1)+lo1, la2+(1.*y/(self.h)*(la1-la2))),self.proj)
  #  return (x - self.w/2)/(math.cos(self.center_coord[1]*math.pi/180)*self.zoom) + self.center_coord[0], -(y - self.h/2)/self.zoom + self.center_coord[1]
  def lonlat2screen(self, (lon, lat), epsg4326=False):
    if epsg4326:
      lon, lat = projections.from4326((lon,lat),self.proj)
    lo1, la1, lo2, la2 = self.bbox_p
    return ((lon-lo1)*(self.w)/abs(lo2-lo1), ((la2-lat)*(self.h)/(la2-la1)))
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
    print self.bbox_p
    scale = abs(self.w/(self.bbox_p[0] - self.bbox_p[2])/math.cos(math.pi*(self.bbox[0]+self.bbox[1])/2/180))
    zscale = 0.5*scale
    cr = cairo.Context(self.surface)
    # getting and setting canvas properties
    bgs = style.get_style("canvas", {}, self.zoom, scale, zscale)
    if not bgs:
      bgs = [{}]
    bgs = bgs[0]
    cr.rectangle(0, 0, self.w, self.h)
    # canvas color and opcity
    color = bgs.get("fill-color",(0.7, 0.7, 0.7))
    cr.set_source_rgba(color[0], color[1], color[2], bgs.get("fill-opacity", 1))
    cr.fill()

    # canvas antialiasing
    antialias = bgs.get("antialias", "full")
    if   antialias == "none":
      "no antialiasing enabled"
      cr.set_antialias(1)
      #cr.font_options_set_antialias(1)
    elif antialias == "text":
      "only text antialiased"
      cr.set_antialias(1)
      #cr.font_options_set_antialias(2)
    else:
      "full antialias"
      cr.set_antialias(2)
      #cr.font_options_set_antialias(2)


    
    datatimer = Timer("Asking backend")
    if "get_sql_hints" in dir(style):
      hints = style.get_sql_hints('way', self.zoom)
    else:
      hints = None
    vectors = self.data.get_vectors(bbox,self.zoom,sql_hint = hints).values()
    datatimer.stop()
    datatimer = Timer("Applying styles")
    ww = []

    for way in vectors:
      
      st = style.get_style("way", way.tags, self.zoom, scale, zscale)
      if st:
       for fpt in st:
        #debug(fpt)
        ww.append((way, fpt))
    
    datatimer.stop()
    debug( "%s objects on screen (%s in dataset)"%(len(ww),len(vectors)) )

    if lock is not None:
      lock.acquire()
      lock.release()
    er = Timer("Projecing data")
    if self.data.proj != self.proj:
      for w in ww:
        w[0].cs = [self.lonlat2screen(coord) for coord in projections.transform(w[0].coords, self.data.proj, self.proj)]
    else:
      for w in ww:
        w[0].cs = [self.lonlat2screen(coord) for coord in w[0].coords]

    er.stop()
      

    ww.sort(key=lambda x: x[1]["layer"])
    layers = list(set([int(x[1]["layer"]/100.) for x in ww]))
    layers.sort()
    objs_by_layers = {}
    for layer in layers:
      objs_by_layers[layer] = []
    for obj in ww:
      objs_by_layers[int(obj[1]["layer"]/100.)].append(obj)

    del ww
    timer.stop()
    timer = Timer("Rasterizing image")
    linecaps = {"butt":0, "round":1, "square":2}
    linejoin = {"miter":0, "round":1, "bevel":2}

    text_rendered_at = set([(-100,-100)])
    for layer in layers:
      data = objs_by_layers[layer]
      #data.sort(lambda x,y:cmp(max([x1[1] for x1 in x[0].cs]), max([x1[1] for x1 in y[0].cs])))
      


      # - draw casings on layer
      for obj in data:
        ### Extras: casing-linecap, casing-linejoin
        if "casing-width" in obj[1] or "casing-color" in obj[1] and "extrude" not in obj[1]:
          cr.set_dash(obj[1].get("casing-dashes",obj[1].get("dashes", [])))
          cr.set_line_join(linejoin.get(obj[1].get("casing-linejoin",obj[1].get("linejoin", "round")),1))
          color = obj[1].get("casing-color", (0,0,0))
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("casing-opacity", 1))
                ## TODO: good combining of transparent lines and casing
                ## Probable solution: render casing, render way as mask and put casing with mask chopped out onto image


          cr.set_line_width (obj[1].get("width",0)+obj[1].get("casing-width", 1 ))
          cr.set_line_cap(linecaps.get(obj[1].get("casing-linecap", obj[1].get("linecap", "butt")),0))
          line(cr, obj[0].cs)

      # - fill polygons
      for obj in data:
        if "fill-color" in obj[1] or "fill-image"  in obj[1] and not "extrude" in obj[1]:   ## TODO: fill-image
          color = obj[1]["fill-color"]
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("fill-opacity", 1))
          
          if "fill-image" in obj[1]:
            print obj[1]["fill-image"], os_module.path.exists(obj[1]["fill-image"])
            if os_module.path.exists(obj[1]["fill-image"]):
              image = cairo.ImageSurface.create_from_png (obj[1]["fill-image"]);
              pattern = cairo.SurfacePattern(image)
              pattern.set_extend(cairo.EXTEND_REPEAT)
              cr.set_source(pattern)
          poly(cr, obj[0].cs)
      # - draw line centers
      #for obj in data:
        if "width" in obj[1] or "color" in obj[1] or "image" in obj[1] and "extrude" not in obj[1]:
          cr.set_dash(obj[1].get("dashes", []))
          cr.set_line_join(linejoin.get(obj[1].get("linejoin", "round"),1))
          color = obj[1].get("color", (0,0,0))
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("opacity", 1))
                ## TODO: better overlapping of transparent lines.
                ## Probable solution: render them (while they're of the same opacity and layer) on a temporary canvas that's merged into main later
          cr.set_line_width (obj[1].get("width", 1))
          cr.set_line_cap(linecaps.get(obj[1].get("linecap", "butt"),0))
          if "image" in obj[1]:
            print obj[1]["image"], os_module.path.exists(obj[1]["image"])
            if os_module.path.exists(obj[1]["image"]):
              image = cairo.ImageSurface.create_from_png (obj[1]["image"]);
              pattern = cairo.SurfacePattern(image)
              pattern.set_extend(cairo.EXTEND_REPEAT)
              cr.set_source(pattern)
          line(cr, obj[0].cs)

      # - extruding polygons
      data.sort(lambda x,y:cmp(max([x1[1] for x1 in x[0].cs]), max([x1[1] for x1 in y[0].cs])))
      for obj in data:
        if "extrude" in obj[1]:
          def face_to_poly(face, hgt):
            """
            Converts a line into height-up extruded poly
            """
            return [face[0], face[1], (face[1][0], face[1][1]-hgt), (face[0][0], face[0][1]-hgt), face[0]]
          hgt = obj[1]["extrude"]

          # print "extruding! %s" % hgt
          color = obj[1].get("extrude-edge-color", obj[1].get("color", (0,0,0) ))
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("extrude-edge-opacity", obj[1].get("opacity", 1)))
          cr.set_line_width (1.)
          cr.set_dash([])
          excoords = [(a[0],a[1]-hgt) for a in obj[0].cs]
          faces = []
          
          p_coord = obj[0].cs[-1]
          for coord in obj[0].cs:
            faces.append([coord, p_coord])
            p_coord = coord
          faces.sort(lambda x,y:cmp(max([x1[1] for x1 in x]), max([x1[1] for x1 in y])))
          for face in faces:
            ply = face_to_poly(face,hgt)
            color = obj[1].get("extrude-face-color", obj[1].get("color", (0,0,0) ))
            cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("extrude-face-opacity", obj[1].get("opacity", 1)))
            poly(cr, ply)
            color = obj[1].get("extrude-edge-color", obj[1].get("color", (0,0,0) ))
            cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("extrude-edge-opacity", obj[1].get("opacity", 1)))
            cr.set_line_width (.5)
            line(cr, ply)


          color = obj[1]["fill-color"]
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("fill-opacity", 1))
          poly(cr,excoords)
          color = obj[1].get("extrude-edge-color", obj[1].get("color", (0,0,0) ))
          cr.set_source_rgba(color[0], color[1], color[2], obj[1].get("extrude-edge-opacity", obj[1].get("opacity", 1)))
          line(cr,excoords)

          
      # - render text labels
      texttimer = Timer("Text rendering")
      cr.set_line_join(1)  # setting linejoin to "round" to get less artifacts on halo render
      for obj in data:
        if "text" in obj[1]:
          
          text = obj[1]["text"]
          #cr.set_line_width (obj[1].get("width", 1))
          cr.set_font_size(float(obj[1].get("font-size", 9)))
          if obj[1].get("text-position", "center") == "center":
            where = self.lonlat2screen(projections.transform(obj[0].center,self.data.proj,self.proj))
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
            #print length, text, cr.text_extents(text)
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
           #  print get_xy_from_len(c,z)
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