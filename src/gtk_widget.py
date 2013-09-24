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
import gobject
import cairo
import math
import string
import threading
import datetime
import time
import Queue
import os
from render import RasterTile
from debug import debug, Timer
import twms.bbox
from twms import projections


class KothicWidget(gtk.DrawingArea):
    def __init__(self, data, style):
        gtk.DrawingArea.__init__(self)
        self.data_backend = data
        self.style_backend = style
        self.request_d = (0, 0)
        self.tiles = TileSource(data, style, callback=self.redraw)
        self.dx = 0
        self.dy = 0
        self.drag_x = 0
        self.drag_y = 0
        self.drag = False
        self.rastertile = None
        self.f = True
        self.width = 0
        self.height = 0
        self.max_zoom = 25

        self.zoom = 0
        self.center_coord = (0.0, 0.0)
        self.old_zoom = 1
        self.old_center_coord = (0.0, 0.1)
        self.tilebox = []  # bbox of currently seen tiles
        self.bbox = []

        self.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
        self.add_events(gtk.gdk.POINTER_MOTION_MASK)
        self.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.add_events(gtk.gdk.BUTTON_RELEASE_MASK)
        self.add_events(gtk.gdk.SCROLL)
#       self.window.add_events(gtk.gdk.BUTTON1_MOTION_MASK)
        self.connect("expose_event", self.expose_ev)
        self.connect("motion_notify_event", self.motion_ev)
        self.connect("button_press_event", self.press_ev)
        self.connect("button_release_event", self.release_ev)
        self.connect("scroll_event", self.scroll_ev)

#       self.surface = cairo.ImageSurfaceicreate(gtk.RGB24, self.width, self.height)

    def set_zoom(self, zoom):
        self.zoom = zoom
        self.queue_draw()

    def jump_to(self, lonlat):
        self.center_coord = lonlat
        self.queue_draw()

    def zoom_to(self, bbox):
        self.zoom = twms.bbox.zoom_for_bbox(bbox, (self.width, self.height), {"proj": "EPSG:3857", "max_zoom": self.max_zoom}) - 1
        print "Zoom:", self.zoom
        self.center_coord = ((bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2)
        print self.center_coord
        self.redraw()

    def motion_ev(self, widget, event):

        if self.drag:
            self.dx = event.x - self.drag_x
            self.dy = event.y - self.drag_y
            # if((abs(self.dx) > 3 or abs(self.dy) > 3) and self.f):
            if True:
            #  x = event.x
            #  y = event.y
            #  lo1, la1, lo2, la2 = self.tilebox
            #  self.center_coord = projections.coords_by_tile(self.zoom,1.*x/self.width*(lo2-lo1)+lo1, la1+(1.*y/(self.height)*(la2-la1)),"EPSG:3857")
                widget.queue_draw()

    def press_ev(self, widget, event):
        if event.button == 1:
            # debug("Start drag")
            self.drag = True
            self.drag_x = event.x
            self.drag_y = event.y
            self.timer = Timer("Drag")
        # elif event.button == 2:
            # debug("Button2")
        # elif event.button == 3:
            # debug("Button3")

    def release_ev(self, widget, event):
        if event.button == 1:
            # debug("Stop drag")
            self.drag = False
            self.timer.stop()
            # debug("dd: %s,%s "%(self.dx, self.dy))
            x = event.x
            y = event.y
            lo1, la1, lo2, la2 = projections.from4326(self.bbox, "EPSG:3857")
            print lo1, la1, lo2, la2
            # self.center_coord = projections.to4326((0.5*(self.width+self.dx)/self.width*(lo1-lo2)+lo2, la1+(0.5*(self.height+self.dy)/self.height*(la2-la1))),"EPSG:3857")

            self.center_coord = projections.to4326((0.5 * (self.width + 2 * self.dx) / self.width * (lo1 - lo2) + lo2, la1 + (0.5 * (self.height + 2 * self.dy) / self.height * (la2 - la1))), "EPSG:3857")
            # self.rastertile.screen2lonlat(self.rastertile.w/2 - self.dx, self.rastertile.h/2 - self.dy);
            self.dx = 0
            self.dy = 0
            self.redraw()

    def scroll_ev(self, widget, event):
        if event.direction == gtk.gdk.SCROLL_UP:
            if self.zoom + 0.5 <= self.max_zoom:
                self.zoom += 0.5
            # debug("Zoom in")
        elif event.direction == gtk.gdk.SCROLL_DOWN:
            if self.zoom >= 0:  # negative zooms are nonsense
                self.zoom -= 0.5
               # debug("Zoom out")
        # self.redraw()
        debug("new zoom: %s" % (self.zoom))
        widget.queue_draw()

    def redraw(self):
        """
        Force screen redraw.
        """
        # res = RasterTile(3*self.width, 3*self.height, self.zoom, self.data_backend)
        # res.update_surface_by_center(self.center_coord, self.zoom, self.style_backend)
        # self.rastertile = res
        self.queue_draw()

    def expose_ev(self, widget, event):
        if(widget.allocation.width != self.width or widget.allocation.height != self.height):
            # debug("Rrresize!")
            self.width = widget.allocation.width
            self.height = widget.allocation.height

        cr = widget.window.cairo_create()
        if self.old_center_coord != self.center_coord or self.old_zoom != self.zoom:
            # print "Recentered!"
            xy = projections.from4326(self.center_coord, "EPSG:3857")
            xy1 = projections.to4326((xy[0] - 40075016. * (0.5 ** (self.zoom)) / self.tiles.tilewidth * self.width, xy[1] - 40075016. * (0.5 ** (self.zoom)) / self.tiles.tileheight * self.height), "EPSG:3857")
            xy2 = projections.to4326((xy[0] + 40075016. * (0.5 ** (self.zoom)) / self.tiles.tilewidth * self.width, xy[1] + 40075016. * (0.5 ** (self.zoom)) / self.tiles.tileheight * self.height), "EPSG:3857")
            self.bbox = (xy1[0], xy1[1], xy2[0], xy2[1])
            self.tilebox = projections.tile_by_bbox(self.bbox, self.zoom, "EPSG:3857")
            self.old_center_coord = self.center_coord
            self.old_zoom = self.zoom
        from_tile_x, from_tile_y, to_tile_x, to_tile_y = self.tilebox
        dx = 1. * (from_tile_x - int(from_tile_x)) * self.tiles.tilewidth
        dy = 1. * (from_tile_y - int(from_tile_y)) * self.tiles.tileheight
        print dx, dy
        # print self.dx, self.dy
        onscreen_tiles = set()
        for x in range(int(from_tile_x), int(to_tile_x) + 1):
            for y in range(int(to_tile_y), int(from_tile_y) + 1):
                onscreen_tiles.add((self.zoom, x, y))
        self.tiles.onscreen = onscreen_tiles
        for z, x, y in onscreen_tiles:
            tile = self.tiles[(self.zoom, x, y)]
            # print dx+(x-from_tile_x)*self.tiles.tilewidth-self.width
            # print dy+(y-from_tile_y)*self.tiles.tileheight-self.height
            # cr.set_source_surface(tile, int(self.dx-dx+(x-int(from_tile_x))*self.tiles.tilewidth-self.width), int(self.dy-dy-(int(from_tile_y)-y)*self.tiles.tileheight+self.height))
            cr.set_source_surface(tile, int(self.dx - dx + (x - int(from_tile_x)) * self.tiles.tilewidth), int(self.dy - dy - (int(from_tile_y) - y) * self.tiles.tileheight + self.height))
            cr.paint()
        # cr.set_source_surface(self.rastertile.surface, self.dx-self.width + self.rastertile.offset_x, self.dy - self.height + self.rastertile.offset_y)

        # self.comm[3].release()


class TileSource:
    def __init__(self, data, style, callback=lambda: None):
        self.tiles = {}
        self.tilewidth = 2048
        self.tileheight = 2048
        self.max_tiles = 32
        self.data_backend = data
        self.style_backend = style
        self.callback = callback
        self.onscreen = set()
        self._singlethread = False
        self._prerender = True

    def __getitem__(self, (z, x, y), wait=False):

        try:
            # if "surface" in self.tiles[(z,x,y)] and not wait:
            #  self._callback((z,x,y), True)
            print "Tiles count:", len(self.tiles)
            return self.tiles[(z, x, y)]["surface"]
        except:
            self.tiles[(z, x, y)] = {"tile": RasterTile(self.tilewidth, self.tileheight, z, self.data_backend)}
            self.tiles[(z, x, y)]["start_time"] = datetime.datetime.now()
            if self._singlethread:

                self.tiles[(z, x, y)]["surface"] = self.tiles[(z, x, y)]["tile"].surface
                self.tiles[(z, x, y)]["tile"].update_surface(projections.bbox_by_tile(z, x, y, "EPSG:3857"), z, self.style_backend, lambda p=False: self._callback((z, x, y), p))

                del self.tiles[(z, x, y)]["tile"]
            else:
                self.tiles[(z, x, y)]["surface"] = self.tiles[(z, x, y)]["tile"].surface.create_similar(cairo.CONTENT_COLOR_ALPHA, self.tilewidth, self.tileheight)
                self.tiles[(z, x, y)]["thread"] = threading.Thread(None, self.tiles[(z, x, y)]["tile"].update_surface, None, (projections.bbox_by_tile(z, x, y, "EPSG:3857"), z, self.style_backend, lambda p=False: self._callback((z, x, y), p)))
                self.tiles[(z, x, y)]["thread"].start()
                if wait:
                    self.tiles[(z, x, y)]["thread"].join()
            return self.tiles[(z, x, y)]["surface"]

    def _callback(self, (z, x, y), last):
        # if last:
        #  print last, "dddddddddddddddddd"
        if not self._singlethread:
            if ((z, x, y) in self.onscreen or last) and "tile" in self.tiles[(z, x, y)]:
                cr = cairo.Context(self.tiles[(z, x, y)]["surface"])
                cr.set_source_surface(self.tiles[(z, x, y)]["tile"].surface, 0, 0)
                cr.paint()

            if last:
                try:
                    del self.tiles[(z, x, y)]["thread"]
                    del self.tiles[(z, x, y)]["tile"]
                except KeyError:
                    pass
                self.tiles[(z, x, y)]["finish_time"] = datetime.datetime.now() - self.tiles[(z, x, y)]["start_time"]
        gobject.idle_add(self.callback)
        self.collect_grabage()
        if last and self._prerender:
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z - 1, x / 2, y / 2), True)
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z + 1, x * 2, y * 2), True)
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z + 1, x * 2 + 1, y * 2), True)
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z + 1, x * 2, y * 2 + 1), True)
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z + 1, x * 2 + 1, y * 2 + 1), True)
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z, x + 1, y), True)
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z, x, y + 1), True)
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z, x - 1, y), True)
            if (z, x, y) in self.onscreen:
                a = self.__getitem__((z, x, y - 1), True)

    def collect_grabage(self):
        if len(self.tiles) > self.max_tiles:
            # let's kick out the fastest rendered tiles - it's easy to rerender those
            # don't touch onscreen tiles
            cand = set(self.tiles.keys())
            cand.difference_update(self.onscreen)
            cand = [i for i in cand if "finish_time" in self.tiles[i]]
            cand.sort(lambda i, j: self.tiles[i]["finish_time"] < self.tiles[i]["finish_time"])
            while cand:
                if (len(self.tiles) > self.max_tiles):
                    c = cand.pop()
                    try:
                        print "Killed tile ", c, " - finished in ", str(self.tiles[c]["finish_time"]), ", ago:", str(datetime.datetime.now() - self.tiles[c]["start_time"])
                        del self.tiles[c]
                    except KeyError:
                        pass
                else:
                    break


if __name__ == "__main__":

    gtk.gdk.threads_init()
    kap = KothicApp()
    kap.main()
