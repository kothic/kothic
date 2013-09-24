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
from backend.postgis import PostGisBackend as DataBackend
from mapcss import MapCSS
from twms import bbox, projections
from render import RasterTile
import web
import StringIO

style = MapCSS(1, 26)  # zoom levels
style.parse(open("styles/landuses.mapcss", "r").read())


# bbox = (27.115768874532,53.740327031764,28.028320754378,54.067187302158)

# w,h = 630*4,364*4
# z = 17

db = DataBackend()
# style = Styling()


try:
    import psyco
    psyco.full()
except ImportError:
    pass

OK = 200
ERROR = 500


def handler():
    """
    A handler for web.py.
    """
    data = web.input()
    resp, ctype, content = twms_main(data)
    web.header('Content-type', ctype)
    return content


urls = (
    '/(.*)', 'mainhandler'
)


class mainhandler:
    def GET(self, crap):
        return handler()


if __name__ == "__main__":

    app = web.application(urls, globals())
    app.run()                                                    # standalone run


def twms_main(req):
    resp = ""
    data = req
    srs = data.get("srs", data.get("SRS", "EPSG:4326"))
    content_type = "image/png"
    # layer = data.get("layers",data.get("LAYERS", config.default_layers)).split(",")

    width = 0
    height = 0
    req_bbox = ()
    if data.get("bbox", data.get("BBOX", None)):
        req_bbox = tuple(map(float, data.get("bbox", data.get("BBOX", req_bbox)).split(",")))

    req_bbox = projections.to4326(req_bbox, srs)

    req_bbox, flip_h = bbox.normalize(req_bbox)
    box = req_bbox

    height = int(data.get("height", data.get("HEIGHT", height)))
    width = int(data.get("width", data.get("WIDTH", width)))

    z = bbox.zoom_for_bbox(box, (height, width), {"proj": "EPSG:3857"}, min_zoom=1, max_zoom=25, max_size=(10000, 10000))

    res = RasterTile(width, height, z, db)
    res.update_surface(box, z, style)
    image_content = StringIO.StringIO()

    res.surface.write_to_png(image_content)

    resp = image_content.getvalue()
    return (OK, content_type, resp)
