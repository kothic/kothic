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


from twms import projections
import twms.bbox

class Empty:
    def copy(self):
        a = Empty()
        a.tags = self.tags.copy()
        a.coords = self.coords[:]
        a.center = self.center
        a.cs = self.cs[:]
        a.bbox = self.bbox
        return a

class Way:
    def __init__(self, tags, coords):

        self.cs = []
        #print [x.split("=") for x in tags.split(";")]
        self.tags = dict((x.split("=") for x in tags.split(";")))
        # calculating center point
        c= coords
        sumz = [(c[0],c[1])]
        for k in range(2, len(c), 2):
            sumz.append((c[k], c[k + 1]))
        self.coords = sumz
        #  left for the better times:
        self.center = reduce(lambda x, y: (x[0]+y[0],x[1]+y[1]), self.coords)
        self.center = (self.center[0]/len(self.coords),self.center[1]/len(self.coords))
        self.bbox = reduce(lambda x,y: (min(x[0],y[0]),min(x[1],y[1]),max(x[2],y[0]),max(x[3],y[1])), self.coords, (9999,9999,-9999,-9999))
        #debug(self.center)
    def copy(self):
        a = Empty()
        a.tags = self.tags.copy()
        a.coords = self.coords[:]
        a.center = self.center
        a.cs = self.cs[:]
        a.bbox = self.bbox
        return a


class QuadTileBackend:
    """
    A class that gives out vector data on demand.
    """


    def __init__(self,max_zoom = 16,proj = "EPSG:4326", path = "tiles", lang = "ru"):


        self.max_zoom = max_zoom            # no better tiles available
        self.path = path                    # path to tile files
        self.lang = lang                    # map language to use
        self.tiles = {}                     # loaded vector tiles go here
        self.proj = proj         # which projection used to cut map in tiles
        self.keep_tiles = 15                # a number of tiles to cache in memory
        self.tile_load_log = []             # used when selecting which tile to unload


    def filename(self, (z,x,y)):

        return "%s/z%s/%s/x%s/%s/y%s.vtile"%(self.path, z, x/1024, x, y/1024, y)
    def load_tile(self, k):
        #debug("loading tile: %s"% (k,))
        try:
            f = open(self.filename(k))
        except IOError:
            print ( "Failed open: '%s'" % self.filename(k) )
            return {}
        t = {}
        for line in f:
            #debug(line)
            a = line.split(" ")
            w = Way(a[0], [float(x) for x in a[2:]])
            t[int(a[1])] = w
        f.close()
        return t
    def collect_garbage(self):
        """
        Cleans up some RAM by removing least accessed tiles.
        """
        if len(self.tiles) > self.keep_tiles:
            #debug("Now %s tiles cached, trying to kill %s"%(len(self.tiles),len(self.tiles)-self.keep_tiles))
            for tile in self.tile_load_log[0:len(self.tiles)-self.keep_tiles]:
                try:
                    del self.tiles[tile]
                    self.tile_load_log.remove(tile)
                    #debug ("killed tile: %s" % (tile,))
                except KeyError, ValueError:
                    pass
                    #debug ("tile killed not by us: %s" % (tile,))

    def get_vectors (self, bbox, zoom, sql_hint = None, itags = None):
        zoom = int(zoom)
        zoom = min(zoom, self.max_zoom)     ## If requested zoom is better than the best, take the best
        zoom = max(zoom, 0)                 ## Negative zooms are nonsense
        a,d,c,b = [int(x) for x in projections.tile_by_bbox(bbox,zoom, self.proj)]
        resp = {}

        hint = set()
        for j in [x[0] for x in sql_hint]:
            hint.update(j)

        for tile in set([(zoom,i,j) for i in range(a, c+1) for j in range(b, d+1)]):
            # Loading current vector tile
            try:
                ti = self.tiles[tile]
            except KeyError:
                ti = self.load_tile(tile)
                self.tiles[tile] = ti
            try:
                self.tile_load_log.remove(tile)
            except ValueError:
                pass
            self.tile_load_log.append(tile)

            for obj in ti:
                "filling response with interesting-tagged objects"
                need = False
                for tag in ti[obj].tags:
                    #if tag in hint:
                    need = True
                    break
                if need:
                    if twms.bbox.bbox_is_in(bbox, ti[obj].bbox, fully=False):
                        resp[obj] = ti[obj]

        self.collect_garbage()
        return resp
