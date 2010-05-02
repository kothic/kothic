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
import pygtk
pygtk.require('2.0')
import gtk
import cairo
import math
import string
import threading
import time
import Queue



from debug import debug, Timer
from vtiles_backend import QuadTileBackend as DataBackend
from style import Styling



try:
  import psyco
  psyco.full()
except ImportError:
  debug("Psyco import failed. Program may run slower. Ir you run it on i386 machine, please install Psyco to get best performance.")


class Renderer(threading.Thread):
  def __init__(self, comm):
    self.comm = comm
    threading.Thread.__init__(self)
  def run(self):
    debug("Thread started")
    self.tc = {}
    while(True):
      while(True):
        request = self.comm[0].get()
        if(self.comm[0].empty):
          break
      #debug ("  got request:", request)
      t = Timer("Rendering screen")
      res = RasterTile(request.size[0], request.size[1], request.zoomlevel, request.data_backend)
      res.update_surface(request.center_lonlat, request.zoom, self.tc, request.style)
      t.stop()
      comm[1].put(res)
      comm[0].task_done()
      comm[2].queue_draw()

class Navigator:
  def __init__(self, comm):
    self.comm = comm
    self.center_coord = (27.6749791, 53.8621394)
    self.width, self.height = 800, 480
    self.zoomlevel = 15
    self.data_projection = "EPSG:4326"
    self.zoom = self.width/0.02;
    self.request_d = (0,0)
    self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    self.data = DataBackend()
    self.dx = 0
    self.dy = 0
    self.drag_x = 0
    self.drag_y = 0
    self.drag = False
    self.tilecache = {}
    self.border = 200
    self.rastertile = None
    self.f = True
    undef = None
    self.style = Styling()
    
    da = gtk.DrawingArea()
    da.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
    da.add_events(gtk.gdk.POINTER_MOTION_MASK)
    da.add_events(gtk.gdk.BUTTON_PRESS_MASK)
    da.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
    da.add_events(gtk.gdk.SCROLL)
#       self.window.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
    da.connect("expose_event",self.expose_ev)
    da.connect("motion_notify_event",self.motion_ev)
    da.connect("button_press_event",self.press_ev)
    da.connect("button_release_event",self.release_ev)
    da.connect("scroll_event",self.scroll_ev)
    self.da = da
#       self.surface = cairo.ImageSurfaceicreate(gtk.RGB24, self.width, self.height)
    self.window.set_size_request(self.width, self.height)
    self.window.add(da)
    self.window.connect("delete_event", self.delete_ev)
    self.comm.append(da)
    self.comm.append(threading.Lock())
  def motion_ev(self, widget, event):
#       debug("Motion")
    if self.drag:
      self.dx = event.x - self.drag_x
      self.dy = event.y - self.drag_y
      if((abs(self.dx) > 150 or abs(self.dy) > 150) and self.f):
        self.redraw()
#        self.request_d = (self.dx, self.dy)
        self.f = False
      widget.queue_draw()
  def delete_ev(self, widget, event):
    gtk.main_quit()
  def press_ev(self, widget, event):
    if event.button == 1:
      debug("Start drag")
      self.drag = True
      self.drag_x = event.x
      self.drag_y = event.y
    elif event.button == 2:
      debug("Button2")
    elif event.button == 3:
      debug("Button3")
  def release_ev(self, widget, event):
    if event.button == 1:
      debug("Stop drag")
      self.drag = False
  #       debug("ll:", self.latcenter, self.loncenter)
      debug("LL before: %s, %s" % self.center_coord)
      debug("dd: %s,%s "%(self.dx, self.dy))
      self.center_coord = self.rastertile.screen2lonlat(self.rastertile.w/2 - self.dx, self.rastertile.h/2 - self.dy);
      #self.dx = self.dy = 0
      self.f = True
      debug("LL after: %s, %s" % self.center_coord)
      self.redraw()
     # widget.queue_draw()
  def scroll_ev(self, widget, event):
    # Zoom test :3
    if event.direction == gtk.gdk.SCROLL_UP:
      self.zoom *= 2
      self.zoomlevel += 1
      debug("Zoom in")
    elif event.direction == gtk.gdk.SCROLL_DOWN:
      if self.zoomlevel >= 0: ## negative zooms are nonsense
        self.zoom /= 2
        self.zoomlevel -= 1
        debug("Zoom out")
    self.redraw()
   # widget.queue_draw()
  def redraw(self):
    """
    Force screen redraw.
    """
    com = MessageContainer()
    com.center_lonlat = self.center_coord
    com.data_backend = self.data
    com.zoomlevel = self.zoomlevel
    com.zoom = self.zoom
    com.size = (self.width + self.border*2, self.height + self.border*2)
    com.style = self.style
    self.comm[0].put(com)

  def expose_ev(self, widget, event):
#       debug("Expose")

    self.comm[3].acquire()
    if(widget.allocation.width != self.width or widget.allocation.height != self.height ):
      debug("Rrresize!")
      self.width = widget.allocation.width
      self.height = widget.allocation.height
      self.rastertile = None
    if self.rastertile is None:
      self.rastertile = RasterTile(self.width + self.border*2, self.height + self.border*2, self.zoomlevel, self.data)
      self.rastertile.update_surface(self.center_coord, self.zoom, self.tilecache, self.style, None)
    nrt = None
    while(not self.comm[1].empty()):
      nrt = self.comm[1].get()
      self.comm[1].task_done()
    if nrt is not None:
      ort = self.rastertile
      #nrt = self.comm[1].get()
      lonlat = ort.screen2lonlat(ort.w/2, ort.h/2)
      ox, oy = nrt.lonlat2screen(lonlat)
      ox -= nrt.w/2
      oy -= nrt.h/2
      self.drag_x += ox
      self.drag_y += oy
      self.dx -= ox
      self.dy -= oy
      #debug( (lat, lon, ox, oy) )
      self.rastertile.offset_x = -ox
      self.rastertile.offset_y = -oy
      self.f = True
      self.rastertile = nrt

    cr = widget.window.cairo_create()
    cr.set_source_surface(self.rastertile.surface, self.dx-self.border + self.rastertile.offset_x, self.dy - self.border + self.rastertile.offset_y)
    cr.paint()
    self.comm[3].release()
#       cr.

  def main(self):
    self.window.show_all()
    gtk.main()
    exit()

class MessageContainer:
  """
  A class to keep messages to render-threads in.
  """
  pass


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
    self.zoom = zoom
    self.center_coord = lonlat
    cr = cairo.Context(self.surface)
    cr.rectangle(0, 0, self.w, self.h)
    cr.set_source_rgb(0.7, 0.7, 0.7)
    cr.fill()
    lonmin, latmin = self.screen2lonlat(0, self.h)
    lonmax, latmax = self.screen2lonlat(self.w, 0)
###########################################3
#FIXME: add time
    
    #FIXME add time2
    #ww = ways(tilecache)
    #debug("ways: %s" % len(ww))
    ww = [ (x, style.get_style("way", x.tags)) for x in self.data.get_vectors((lonmin,latmin,lonmax,latmax),self.zoomlevel).values()]
    ww1 = []
    for way in ww:
      if way[1]:
        ww1.append(way)
    ww = ww1
    if lock is not None:
      lock.acquire()
      lock.release()
    self.lcc = math.cos(self.center_coord[1]*math.pi/180)
    #ww = dict([(int(x[1]["layer"]/100), x) for x in ww])

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
    layers = list(set([int(x[1]["layer"]/100) for x in ww]))
    layers.sort()
    objs_by_layers = {}
    for layer in layers:
      objs_by_layers[layer] = []
    for obj in ww:
    #  debug(obj)
      objs_by_layers[int(obj[1]["layer"]/100)].append(obj)
    del ww
    for layer in layers:
      data = objs_by_layers[layer]
      # - fill polygons
      for obj in data:
        #debug(obj[1])
        if "fill-color" in obj[1]:
          color = gtk.gdk.Color(obj[1]["fill-color"])
          cr.set_source_rgb(color.red, color.green, color.blue)
          cr.set_line_width (0)
          #debug("poly!")
          poly(cr, obj[0].cs)
      # - draw casings on layer
      for obj in data:
        if "casing-width" in obj[1] or "casing-color" in obj[1]:
          color = gtk.gdk.Color(obj[1].get("casing-color", "#000"))
          cr.set_source_rgb(color.red, color.green, color.blue)
          cr.set_line_width (obj[1].get("casing-width", obj[1].get("width",0)+1 ))
          line(cr, obj[0].cs)
      # - draw line centers
      for obj in data:
        if "width" in obj[1] or "color" in obj[1]:
          color = gtk.gdk.Color(obj[1].get("color", "#000"))
          cr.set_source_rgb(color.red, color.green, color.blue)
          cr.set_line_width (obj[1].get("width", 1))
          line(cr, obj[0].cs)
      #debug("pass %s" % passn)
      #for w in ww:
        #stn = w.style
        #if lock is not None:
          #lock.acquire()
          #lock.release()
        #if stn < len(style) and style[stn] is not None and style[stn][passn-1] is not None:
          #st = style[w.style][passn-1]
          #cr.set_line_width(st[0])
          #cr.set_source_rgb(st[1][0], st[1][1], st[1][2])
          #if w.type == "L":
            #line(cr, w.cs)
          #elif w.type == "P":
            #poly(cr, w.cs)



if __name__ == "__main__":

  gtk.gdk.threads_init()
  comm = [Queue.Queue(), Queue.Queue()]
  nav = Navigator(comm)
  r = Renderer(comm)
  r.daemon = True
  r.start()
  nav.main()
