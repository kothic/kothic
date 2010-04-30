#!/usr/bin/env python
#use Cairo;
#import cairo
#use Gtk2 '-init';
import pygtk
pygtk.require('2.0')
import gtk
import cairo
import math
import string
import threading
import time
import Queue

#use Glib qw(TRUE FALSE);
#use Time::HiRes qw(gettimeofday tv_interval);
#use strict;
#use POSIX qw(ceil floor);
#use style qw(@style);
#use navigator_lib;

#my $dbname = "moscow.db";
#my $dbargs = {AutoCommit => 0,
#	PrintError => 1,
#};
#

#my $latmin;
#my $latmax;
#my $lonmin;
#my $lonmax;

#my $latcenter = 55.6304; 
#my $loncenter = 37.49305; 

class Renderer(threading.Thread):
	def __init__(self, comm):
		self.comm = comm
		threading.Thread.__init__(self)
	def run(self):
		print ("Thread started")
		self.tc = {}
		while(True):
			while(True):
				request = self.comm[0].get()
				if(self.comm[0].empty):
					break
			print ("  got request:", request)
			res = RasterTile(request[2][0], request[2][1]) 
			res.update_surface(request[0][0], request[0][1], request[1], self.tc, request[3])
			print ("  render complete")
			comm[1].put(res)
#			comm[2].get_window().invalidate_rect(None, True)
			comm[2].queue_draw()

class Navigator:
	def __init__(self, comm):
		self.comm = comm
		self.lat_c = 55.6304
		self.lon_c = 37.49305
		self.width, self.height = 640, 480
		self.zoom = self.width/0.02;
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
#		self.window.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
		da.connect("expose_event",self.expose_ev)
		da.connect("motion_notify_event",self.motion_ev)
		da.connect("button_press_event",self.press_ev)
		da.connect("button_release_event",self.release_ev)
		self.da = da
#		self.surface = cairo.ImageSurfaceicreate(gtk.RGB24, self.width, self.height)
		self.window.set_size_request(self.width, self.height)
		self.window.add(da)
		self.window.connect("delete_event", self.delete_ev)
		self.comm.append(da)
	def motion_ev(self, widget, event):
#		print("Motion")
		if self.drag:
			self.dx = event.x - self.drag_x
			self.dy = event.y - self.drag_y
			if((abs(self.dx) > 100 or abs(self.dy) > 100) and self.f):
				self.comm[0].put((self.rastertile.screen2latlon(self.rastertile.w/2 - self.dx, self.rastertile.h/2 - self.dy), self.zoom, (self.width + self.border*2, self.height + self.border*2), self.style))
				self.request_d = (self.dx, self.dy)
				self.f = False 
			widget.queue_draw()
	def delete_ev(self, widget, event):
		gtk.main_quit()
	def press_ev(self, widget, event):
		print("Start drag")
		self.drag = True
		self.drag_x = event.x
		self.drag_y = event.y
	def release_ev(self, widget, event):
		print("Stop drag")
		self.drag = False
#		print("ll:", self.latcenter, self.loncenter)
		print("LL before: ",self.lat_c, self.lon_c)
		print("dd: ",self.dx, self.dy)
		self.lat_c, self.lon_c = self.rastertile.screen2latlon(self.rastertile.w/2 - self.dx, self.rastertile.h/2 - self.dy);
#		self.dx = self.dy = 0
		self.f = True
		print("LL after: ",self.lat_c, self.lon_c)
#		self.rastertile.update_surface( self.lat_c, self.lon_c, self.zoom, self.tilecache, self.style)
		self.comm[0].put(((self.lat_c, self.lon_c), self.zoom, (self.width + self.border*2, self.height + self.border*2), self.style))
		widget.queue_draw()
	def expose_ev(self, widget, event):
#		print("Expose")
		if(widget.allocation.width != self.width):
			print("Rrresize!")
			self.width = widget.allocation.width
			self.height = widget.allocation.height
			self.rastertile = None
		if self.rastertile is None:
			self.rastertile = RasterTile(self.width + self.border*2, self.height + self.border*2)
			self.rastertile.update_surface(self.lat_c, self.lon_c, self.zoom, self.tilecache, self.style)
		if not self.comm[1].empty():
			ort = self.rastertile
			nrt = self.comm[1].get()
			lat, lon = ort.screen2latlon(ort.w/2 - self.dx, ort.h/2 - self.dy)
			ox, oy = nrt.latlon2screen(lat, lon, nrt.zoom)
			ox -= nrt.w/2
			oy -= nrt.h/2
			print (ox, oy)
			self.rastertile.offset_x = ox
			self.rastertile.offset_y = oy
			self.f = True
			self.rastertile = nrt

		cr = widget.window.cairo_create()
		cr.set_source_surface(self.rastertile.surface, self.dx-self.border + self.rastertile.offset_x, self.dy - self.border + self.rastertile.offset_y)
		cr.paint()

	def main(self):
		self.window.show_all()
		gtk.main()

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
	print("loading tile: ", k)
	f = open(key_to_filename(k))
	t = {}
	while True:
		str = f.readline()
		if str is None or str == "":
			break
		str = str.rstrip("\n")
		a = str.split(" ")
		w = Way(a[0], int(a[1]), int(a[2]), map(lambda x: float(x), a[3:]))
		t[w.id] = w 
	f.close()
	return t

class RasterTile:
	def __init__(self, width, height):
		self.w = width
		self.h = height
		self.surface = cairo.ImageSurface(cairo.FORMAT_RGB24, self.w, self.h)
		self.offset_x = 0
		self.offset_y = 0 
		self.lat_c = None
		self.lon_c = None
		self.zoom = None 
	def screen2latlon(self, x, y):
		return -(y - self.h/2)/self.zoom + self.lat_c, (x - self.w/2)/(math.cos(self.lat_c*math.pi/180)*self.zoom) + self.lon_c
	def latlon2screen(self, lat, lon, lcc):
		return (lon - self.lon_c)*lcc*self.zoom + self.w/2, -(lat - self.lat_c)*self.zoom + self.h/2
	def update_surface(self, lat, lon, zoom, tilecache, style):
		self.zoom = zoom
		self.lat_c = lat
		self.lon_c = lon
		cr = cairo.Context(self.surface)
		cr.rectangle(0, 0, self.w, self.h)
		cr.set_source_rgb(0.7, 0.7, 0.7)
		cr.fill()
		latmin, lonmin = self.screen2latlon(0, self.h)
		latmax, lonmax = self.screen2latlon(self.w, 0)
		latkey_min = int(latmin*100)
		latkey_max = int(latmax*100)
		lonkey_min = int(lonmin*100)
		lonkey_max = int(lonmax*100)
		print(latmin, lonmin, latmax, lonmax)
		print( latkey_min, latkey_max, lonkey_min, lonkey_max)
#FIXME: add time
		active_tile = set([(i,j) for i in range(latkey_min, latkey_max+1) for j in range(lonkey_min, lonkey_max+1)])
		print(active_tile)
		for k in tilecache.keys():
			if k not in active_tile:
				del tilecache[k]
				print("del tile:", k)
		for k in active_tile:
			if k not in tilecache:
				tilecache[k] = load_tile(k)
		#FIXME add time2
		ww = ways(tilecache)
		print("ways: ", len(ww))

		ww.sort(key=lambda x: style[x.style][3])
		lcc = math.cos(self.lat_c*math.pi/180)
		for w in ww:
			cs = []
			for k in range(0, len(w.coords), 2):
				x, y = self.latlon2screen(w.coords[k], w.coords[k+1], lcc);
				cs.append(x)
				cs.append(y)
			w.cs = cs
		for passn in range(1, 4):
			print("pass ",passn)
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

def key_to_filename(k):
	return "data/" + str(k[0]//100) + "/" + str(k[1]//100) + "/" + str(k[0]%100) + "/" + str(k[1]%100) + ".map"

if __name__ == "__main__":
	gtk.gdk.threads_init()
	comm = [Queue.Queue(), Queue.Queue()]
	nav = Navigator(comm)
	r = Renderer(comm)
	r.daemon = True
	r.start()
	nav.main()
