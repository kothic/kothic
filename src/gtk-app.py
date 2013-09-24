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


# from backend.postgis import PostGisBackend as DataBackend
from backend.vtile import QuadTileBackend as DataBackend
from mapcss import MapCSS as Styling
from gtk_widget import KothicWidget


try:
    import psyco
    psyco.full()
except ImportError:
    pass
#  debug("Psyco import failed. Program may run slower. Ir you run it on i386 machine, please install Psyco to get best performance.")


class KothicApp:
    def __init__(self):
        self.width, self.height = 800, 480

        self.center_coord = (27.6549791, 53.8698)
        self.zoom = 17.
        self.data_projection = "EPSG:4326"
        self.data = DataBackend()
        self.load_style()

        self.request_d = (0, 0)
        self.window = gtk.Window()

        self.window.set_size_request(self.width, self.height)

        self.window.connect("destroy", gtk.main_quit)

        self.window.set_title("Kothic renderer")
        menu = gtk.MenuBar()

        filemenu = gtk.Menu()
        filem = gtk.MenuItem("File")
        filem.set_submenu(filemenu)
        i = gtk.MenuItem("Reload style")
        i.connect("activate", self.load_style)
        filemenu.append(i)

        stylemenu = gtk.Menu()
        stylem = gtk.MenuItem("Style")
        stylem.set_submenu(stylemenu)
        styles = [name for name in os.listdir("styles") if ".mapcss" in name]
        for style in styles:
            i = gtk.MenuItem(style)
            i.StyleName = style
            i.connect("activate", self.reload_style)
            stylemenu.append(i)

        i = gtk.MenuItem("Exit")
        i.connect("activate", gtk.main_quit)
        filemenu.append(i)

        menu.append(filem)
        menu.append(stylem)

        vbox = gtk.VBox(False, 2)
        vbox.pack_start(menu, False, False, 0)

        self.KothicWidget = KothicWidget(self.data, self.style)
        self.KothicWidget.set_zoom(self.zoom)
        self.KothicWidget.jump_to(self.center_coord)

        vbox.pack_end(self.KothicWidget)

        self.window.add(vbox)

    def load_style(self):
        self.style = Styling(0, 25)
        self.style.parse(open("styles/osmosnimki-maps.mapcss", "r").read())

    def reload_style(self, w):
        self.style = Styling(0, 25)
        self.style.parse(open("styles/%s" % w.StyleName, "r").read())
        self.KothicWidget.style_backend = self.style
        self.KothicWidget.redraw()

    def main(self):

        self.window.show_all()
        gtk.main()
        exit()
if __name__ == "__main__":

    gtk.gdk.threads_init()
    kap = KothicApp()
    kap.main()
