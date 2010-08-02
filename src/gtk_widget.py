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
import os
from render import RasterTile
from debug import debug, Timer

class KothicWidget(gtk.DrawingArea):
  def __init__(self, data, style):
    gtk.DrawingArea.__init__(self)
    self.data_backend = data
    self.style_backend = style
    self.request_d = (0,0)

    self.dx = 0
    self.dy = 0
    self.drag_x = 0
    self.drag_y = 0
    self.drag = False
    self.rastertile = None
    self.f = True
    self.width = 0
    self.height = 0
    
    self.center_coord = (0.0,0.0)
    self.zoom = 0
    
    self.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
    self.add_events(gtk.gdk.POINTER_MOTION_MASK)
    self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
    self.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
    self.add_events(gtk.gdk.SCROLL)
#       self.window.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
    self.connect("expose_event",self.expose_ev)
    self.connect("motion_notify_event",self.motion_ev)
    self.connect("button_press_event",self.press_ev)
    self.connect("button_release_event",self.release_ev)
    self.connect("scroll_event",self.scroll_ev)
#       self.surface = cairo.ImageSurfaceicreate(gtk.RGB24, self.width, self.height)


  def set_zoom(self, zoom):
    self.zoom = zoom
    self.queue_draw()
  def jump_to(self, lonlat):
    self.center_coord = lonlat
    self.queue_draw()
    

  
  def motion_ev(self, widget, event):

    if self.drag:
      self.dx = event.x - self.drag_x
      self.dy = event.y - self.drag_y
      if((abs(self.dx) > 3 or abs(self.dy) > 3) and self.f):
        widget.queue_draw()
  def press_ev(self, widget, event):
    if event.button == 1:
      #debug("Start drag")
      self.drag = True
      self.drag_x = event.x
      self.drag_y = event.y
      self.timer = Timer("Drag")
    #elif event.button == 2:
      #debug("Button2")
    #elif event.button == 3:
      #debug("Button3")
  def release_ev(self, widget, event):
    if event.button == 1:
      #debug("Stop drag")
      self.drag = False
      self.timer.stop()
      #debug("dd: %s,%s "%(self.dx, self.dy))
      self.center_coord = self.rastertile.screen2lonlat(self.rastertile.w/2 - self.dx, self.rastertile.h/2 - self.dy);
      self.f = True
      self.dx = 0
      self.dy = 0
      self.redraw()
      
  def scroll_ev(self, widget, event):
    if event.direction == gtk.gdk.SCROLL_UP:
      self.zoom += 0.5
      #debug("Zoom in")
    elif event.direction == gtk.gdk.SCROLL_DOWN:
      if self.zoom >= 0: ## negative zooms are nonsense
        self.zoom -= 0.5
       # debug("Zoom out")
    self.redraw()
   # widget.queue_draw()
  def redraw(self):
    """
    Force screen redraw.
    """
    res = RasterTile(3*self.width, 3*self.height, self.zoom, self.data_backend)
    res.update_surface_by_center(self.center_coord, self.zoom, self.style_backend)
    self.rastertile = res
    self.queue_draw()


  def expose_ev(self, widget, event):
#       debug("Expose")


    if(widget.allocation.width != self.width or widget.allocation.height != self.height ):
      #debug("Rrresize!")
      self.width = widget.allocation.width
      self.height = widget.allocation.height
      self.rastertile = None
    if self.rastertile is None:
      self.rastertile = RasterTile(self.width*3, self.height*3, self.zoom, self.data_backend)
      self.rastertile.update_surface_by_center(self.center_coord, self.zoom, self.style_backend, None)
    #nrt = None
    #while(not self.comm[1].empty()):
      #nrt = self.comm[1].get()
      #self.comm[1].task_done()
    #if nrt is not None:
      #ort = self.rastertile
      ##nrt = self.comm[1].get()
      #lonlat = ort.screen2lonlat(ort.w/2, ort.h/2)
      #debug(lonlat)
      #debug(self.center_coord)
      #ox, oy = nrt.lonlat2screen(lonlat, epsg4326=True)
      #ox, oy = int(ox),int(oy)
      #ox -= nrt.w/2
      #oy -= nrt.h/2
      #debug(ox)
      #debug(oy)
      
      #self.drag_x += ox
      #self.drag_y += oy
      #self.dx -= ox
      #self.dy -= oy
      ##debug( (lat, lon, ox, oy) )
      #self.rastertile.offset_x = -ox
      #self.rastertile.offset_y = -oy
      #self.f = True
      #self.rastertile = nrt

    cr = widget.window.cairo_create()
    cr.set_source_surface(self.rastertile.surface, self.dx-self.width + self.rastertile.offset_x, self.dy - self.height + self.rastertile.offset_y)
    cr.paint()
    #self.comm[3].release()



if __name__ == "__main__":

  gtk.gdk.threads_init()
  kap = KothicApp()
  kap.main()
