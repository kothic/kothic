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
from twms import projections

from debug import debug, Timer
#debug = lambda a: None


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
			res = RasterTile(request.size[0], request.size[1], request.zoomlevel, request.data_projection)
			res.update_surface(request.center_lonlat[0], request.center_lonlat[1], request.zoom, self.tc, request.style)
			t.stop()
			comm[1].put(res)

class Navigator:
	def __init__(self, comm):
		self.comm = comm
		self.lon_c = 27.6749791
                self.lat_c = 53.8621394
		self.width, self.height = 640, 480
                self.zoomlevel = 17
                self.data_projection = "EPSG:4326"
		self.zoom = self.width/0.09;
		self.window = gtk.Window(gtk.WINDOW_TOPLEVEL)
		self.dx = 0
		self.dy = 0
		self.drag = False
		self.tilecache = {}
		self.border = 200
		self.rastertile = None
		self.f = True
		undef = None
		self.style = [ 
[None, None, None, 0],
[undef, [6.0, [0,0,0]], [4.0, [1, 1, .7]], 1], 
[undef, [4.5, [0,0,0]], [2.5, [1, 1, .7]], 2], 
[undef, [3.5, [0,0,0]], [2.5, [1, 1, .7]], 3],
[undef, [2.8, [0,0,0]], [2.0, [1, 1, 1]], 4], 
[undef, undef, [1.0, [1, 1, 1]], 5], 
[undef, [0, [0.7, 0.4, 0.4]], undef, 6], 
[[1, [0.30, 0.5, 0.30]], undef, undef, 7], 
[undef, undef, [2, [1, 0.3, 0.3]], 8], 
[[0, [0.7, 0.6, 0.6]], undef, undef, 9], 
[[0, [0.4, 0.4, 1.0]], undef, undef, 10], 
[[0, [0.6, 0.6, 0.6]], undef, undef, 11], 
[undef, [3.5, [0.4, 0.4, 1.0]], undef, 12], 
[undef, [2, [0.4, 0.4, 1.0]], undef, 13], 
[[0, [0.72, 0.51, 0.32]], undef, undef, 14], 
[[0, [1, 0.0, 0.0]], undef, undef, 0] #unknown landuse
] 
		da = gtk.DrawingArea()
		da.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
		da.add_events(gtk.gdk.POINTER_MOTION_MASK)
		da.add_events(gtk.gdk.BUTTON_PRESS_MASK)
		da.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
		da.add_events(gtk.gdk.SCROLL)
#		self.window.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
		da.connect("expose_event",self.expose_ev)
		da.connect("motion_notify_event",self.motion_ev)
		da.connect("button_press_event",self.press_ev)
		da.connect("button_release_event",self.release_ev)
		da.connect("scroll_event",self.scroll_ev)
		self.da = da
#		self.surface = cairo.ImageSurfaceicreate(gtk.RGB24, self.width, self.height)
		self.window.set_size_request(self.width, self.height)
		self.window.add(da)
		self.window.connect("delete_event", self.delete_ev)
	def motion_ev(self, widget, event):
#		debug("Motion")
		if self.drag:
			self.dx = event.x - self.drag_x
			self.dy = event.y - self.drag_y
			if((abs(self.dx) > 100 or abs(self.dy) > 100) and self.f):
                                com = MessageContainer()
                                com.center_lonlat = self.rastertile.screen2lonlat(self.rastertile.w/2 - self.dx, self.rastertile.h/2 - self.dy)
                                com.data_projection = self.data_projection
                                com.zoomlevel = self.zoomlevel
                                com.zoom = self.zoom
                                com.size = (self.width + self.border*2, self.height + self.border*2)
                                com.style = self.style
				self.comm[0].put(com)
				self.request_d = (self.dx, self.dy)
				self.f = False 
			if not self.comm[1].empty():
				self.rastertile = self.comm[1].get()
				self.f = True
				self.drag_x += self.request_d[0]
				self.drag_y += self.request_d[1]
				self.dx = event.x - self.drag_x
				self.dy = event.y - self.drag_y
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
	#		debug("ll:", self.latcenter, self.loncenter)
			debug("LL before: %s, %s" % (self.lon_c, self.lat_c))
			debug("dd: %s,%s "%(self.dx, self.dy))
			self.lon_c, self.lat_c = self.rastertile.screen2lonlat(self.rastertile.w/2 - self.dx, self.rastertile.h/2 - self.dy);
			self.dx = self.dy = 0
			self.f = True
			debug("LL after: %s, %s" % (self.lon_c, self.lat_c))
			
			com = MessageContainer()
			com.center_lonlat = (self.lon_c,self.lat_c)
			com.data_projection = self.data_projection
			com.zoomlevel = self.zoomlevel
			com.zoom = self.zoom
			com.size = (self.width + self.border*2, self.height + self.border*2)
			com.style = self.style
			self.comm[0].put(com)
	#		self.rastertile.update_surface( self.lat_c, self.lon_c, self.zoom, self.tilecache, self.style)
			widget.queue_draw()
	def scroll_ev(self, widget, event):
		# Zoom test :3
		if event.direction == gtk.gdk.SCROLL_UP:
			self.zoom *= 2
			debug("Zoom in")
		elif event.direction == gtk.gdk.SCROLL_DOWN:
			debug("Zoom out")
	def expose_ev(self, widget, event):
#		debug("Expose")
		if(widget.allocation.width != self.width):
			debug("Rrresize!")
			self.width = widget.allocation.width
			self.height = widget.allocation.height
			self.rastertile = None
		if self.rastertile is None:
			self.rastertile = RasterTile(self.width + self.border*2, self.height + self.border*2, self.zoomlevel, self.data_projection)
			self.rastertile.update_surface(self.lon_c, self.lat_c, self.zoom, self.tilecache, self.style)
		cr = widget.window.cairo_create()
		cr.set_source_surface(self.rastertile.surface, self.dx-self.border, self.dy - self.border)
		cr.paint()
#		cr.

	def main(self):
		self.window.show_all()
		gtk.main()

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

def ways(t):
#	return [y for x in t.itervalues() for y in x.itervalues()]
	r = {}
	for i in t.values():
		r.update(i)
	return r.values()

def load_tile(k):
	#debug("loading tile: ", k)
	try:
          f = open(key_to_filename(k))
        except IOError:
         # debug ( "Failed open: %s" % key_to_filename(k) )
          return {}
	t = {}
	for line in f:
		a = line.split(" ")
		w = Way(a[0], int(a[1]), int(a[2]), map(lambda x: float(x), a[3:]))
		t[w.id] = w 
	f.close()
	return t

class RasterTile:
        def __init__(self, width, height, zoom, data_projection):
		self.w = width
		self.h = height
		self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.w, self.h)
		self.x_offset = 0
		self.y_offset = 0 
		self.lat_c = None
		self.lon_c = None
		self.zoomlevel = zoom
		self.zoom = None
		self.data_projection = data_projection
	def screen2lonlat(self, x, y):
		return (x - self.w/2)/(math.cos(self.lat_c*math.pi/180)*self.zoom) + self.lon_c, -(y - self.h/2)/self.zoom + self.lat_c
	def lonlat2screen(self, lon, lat, lcc):
		return (lon - self.lon_c)*lcc*self.zoom + self.w/2, -(lat - self.lat_c)*self.zoom + self.h/2
	def update_surface(self, lon, lat, zoom, tilecache, style):
		self.zoom = zoom
		self.lat_c = lat
		self.lon_c = lon
		cr = cairo.Context(self.surface)
		cr.rectangle(0, 0, self.w, self.h)
		cr.set_source_rgb(0.7, 0.7, 0.7)
		cr.fill()
		lonmin, latmin = self.screen2lonlat(0, self.h)
		lonmax, latmax = self.screen2lonlat(self.w, 0)
                a,d,c,b = [int(x) for x in projections.tile_by_bbox((lonmin, latmin, lonmax, latmax),self.zoomlevel, self.data_projection)]

                debug((latmin, lonmin, latmax, lonmax))
                debug(( a, b, c, d))
#FIXME: add time
                active_tile = set([(self.zoomlevel,i,j) for i in range(a, c+1) for j in range(b, d+1)])
		debug(active_tile)
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

		ww.sort(key=lambda x: style[x.style][3])
		lcc = math.cos(self.lat_c*math.pi/180)
		for w in ww:
			cs = []
			for k in range(0, len(w.coords), 2):
				x, y = self.lonlat2screen(w.coords[k], w.coords[k+1], lcc);
				cs.append(x)
				cs.append(y)
			w.cs = cs
		for passn in range(1, 4):
			debug("pass %s" % passn)
			for w in ww: 
				stn = w.style
				if stn < len(style) and style[stn] is not None and style[stn][passn-1] is not None:
					st = style[w.style][passn-1]
					cr.set_line_width(st[0])
					cr.set_source_rgb(st[1][0], st[1][1], st[1][2])
					if w.type == "L":
						line(cr, w.cs)
					elif w.type == "P":
						poly(cr, w.cs)

class Way:
	def __init__(self, type, id, style, coords):
		self.type = type
		self.id = id
		self.coords = coords
		self.style = style
		self.cs = None

def key_to_filename((z,x,y)):
  return "tiles/z%s/%s/x%s/%s/y%s.vtile"%(z, x/1024, x, y/1024, y)

if __name__ == "__main__":
	comm = (Queue.Queue(), Queue.Queue())
	gtk.gdk.threads_init()
	nav = Navigator(comm)
	r = Renderer(comm)
	r.daemon = True
	r.start()
	nav.main()
