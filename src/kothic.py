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
#from style import Styling
from mapcss import MapCSS as Styling
from render import RasterTile



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
    while(True):
      while(True):
        request = self.comm[0].get()
        if(self.comm[0].empty):
          break
      #debug ("  got request:", request)
      res = RasterTile(request.size[0], request.size[1], request.zoom, request.data_backend)
      res.update_surface_by_center(request.center_lonlat, request.zoom, request.style)
      comm[1].put(res)
      comm[0].task_done()
      comm[2].queue_draw()

class Navigator:
  def __init__(self, comm):
    self.comm = comm
    self.center_coord = (27.6749791, 53.8621394)
    self.width, self.height = 800, 480
    self.zoom = 15.
    self.data_projection = "EPSG:4326"
    self.request_d = (0,0)
    self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
    self.data = DataBackend()
    self.dx = 0
    self.dy = 0
    self.drag_x = 0
    self.drag_y = 0
    self.drag = False
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
      if((abs(self.dx) > 1 or abs(self.dy) > 1) and self.f):
      #  self.redraw()
#        self.request_d = (self.dx, self.dy)
      #  self.f = False
        widget.queue_draw()
  def delete_ev(self, widget, event):
    gtk.main_quit()
  def press_ev(self, widget, event):
    if event.button == 1:
      debug("Start drag")
      self.drag = True
      self.drag_x = event.x
      self.drag_y = event.y
      self.timer = Timer("Drag")
    elif event.button == 2:
      debug("Button2")
    elif event.button == 3:
      debug("Button3")
  def release_ev(self, widget, event):
    if event.button == 1:
      debug("Stop drag")
      self.drag = False
      self.timer.stop()
      debug("dd: %s,%s "%(self.dx, self.dy))
      self.center_coord = self.rastertile.screen2lonlat(self.rastertile.w/2 - self.dx, self.rastertile.h/2 - self.dy);
      self.f = True
      self.redraw()
  def scroll_ev(self, widget, event):
    # Zoom test :3
    if event.direction == gtk.gdk.SCROLL_UP:
      #self.zoom *= 2.**0.5
      self.zoom += 0.5
      debug("Zoom in")
    elif event.direction == gtk.gdk.SCROLL_DOWN:
      if self.zoom >= 0: ## negative zooms are nonsense
        #self.zoom /= 2.**0.5
        self.zoom -= 0.5
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
    com.zoom = self.zoom
    com.size = (self.width*3, self.height*3)
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
      self.rastertile = RasterTile(self.width*3, self.height*3, self.zoom, self.data)
      self.rastertile.update_surface_by_center(self.center_coord, self.zoom, self.style, None)
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
    cr.set_source_surface(self.rastertile.surface, self.dx-self.width + self.rastertile.offset_x, self.dy - self.height + self.rastertile.offset_y)
    cr.paint()
    self.comm[3].release()

  def main(self):
    self.window.show_all()
    gtk.main()
    exit()

class MessageContainer:
  """
  A class to keep messages to render-threads in.
  """
  pass


if __name__ == "__main__":

  gtk.gdk.threads_init()
  comm = [Queue.Queue(), Queue.Queue()]
  nav = Navigator(comm)
  r = Renderer(comm)
  r.daemon = True
  r.start()
  nav.main()
