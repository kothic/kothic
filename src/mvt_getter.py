# -*- coding: utf-8 -*-
from twms import projections
from libkomapnik import pixel_size_at_zoom
import json
import psycopg2
from mapcss import MapCSS
import os
import sys

reload(sys)
sys.setdefaultencoding("utf-8")  # a hack to support UTF-8


def get_vectors(bbox, zoom, style, vec="polygon"):
    bbox_p = projections.from4326(bbox, "EPSG:3857")

    geomcolumn = "way"

    database = "dbname=gis user=gis"
    pxtolerance = 1.8
    intscalefactor = 10000
    ignore_columns = set(["way_area", "osm_id", geomcolumn, "tags", "z_order"])
    table = {
        "polygon": "planet_osm_polygon",
        "line": "planet_osm_line",
        "point": "planet_osm_point",
        "coastline": "coastlines",
    }

    a = psycopg2.connect(database)
    b = a.cursor()
    if vec != "coastline":
        b.execute("SELECT * FROM %s LIMIT 1;" % table[vec])
        names = [q[0] for q in b.description]
        for i in ignore_columns:
            if i in names:
                names.remove(i)
        names = ",".join(['"' + i + '"' for i in names])

        taghint = "*"
        types = {"line": "line", "polygon": "area", "point": "node"}
        adp = ""
        if "get_sql_hints" in dir(style):
            sql_hint = style.get_sql_hints(types[vec], zoom)
            adp = []
            for tp in sql_hint:
                add = []
                for j in tp[0]:
                    if j not in names:
                        break
                else:
                    add.append(tp[1])
                if add:
                    add = " OR ".join(add)
                    add = "(" + add + ")"
                    adp.append(add)
            adp = " OR ".join(adp)
            if adp:
                adp = adp.replace("&lt;", "<")
                adp = adp.replace("&gt;", ">")

    if vec == "polygon":
        query = """select ST_AsMVT(tile, '%s', 4096, 'way') from (
                        select ST_AsMVTGeom(way, ST_MakeEnvelope(%s, %s, %s, %s, 3857), 4096, 64, true) as %s, %s from
                        (select (ST_Dump(ST_Multi(ST_SimplifyPreserveTopology(ST_Buffer(way,-%s),%s)))).geom as %s, %s from
                            (select ST_Union(way) as %s, %s from
                            (select ST_Buffer(way, %s) as %s, %s from
                                %s
                                where (%s)
                                and way && ST_MakeEnvelope(%s, %s, %s, %s, 3857)
                                and way_area > %s
                            ) p
                            group by %s
                            ) p
                            where ST_Area(way) > %s
                            order by ST_Area(way)
                        ) p
                    ) as tile where %s is not null
          """ % (
            types[vec],
            bbox_p[0],
            bbox_p[1],
            bbox_p[2],
            bbox_p[3],
            geomcolumn,
            names,
            pixel_size_at_zoom(zoom, pxtolerance),
            pixel_size_at_zoom(zoom, pxtolerance),
            geomcolumn,
            names,
            geomcolumn,
            names,
            pixel_size_at_zoom(zoom, pxtolerance),
            geomcolumn,
            names,
            table[vec],
            adp,
            bbox_p[0],
            bbox_p[1],
            bbox_p[2],
            bbox_p[3],
            (pixel_size_at_zoom(zoom, pxtolerance) ** 2) / pxtolerance,
            names,
            pixel_size_at_zoom(zoom, pxtolerance) ** 2,
            geomcolumn,
        )
    elif vec == "line":
        query = """select ST_AsMVT(tile, '%s', 4096, 'way') from (
                        select ST_AsMVTGeom(way, ST_MakeEnvelope(%s, %s, %s, %s, 3857), 4096, 64, true) as %s, %s from
                        (select (ST_Dump(ST_Multi(ST_SimplifyPreserveTopology(ST_LineMerge(way),%s)))).geom as %s, %s from
                            (select ST_Union(way) as %s, %s from
                                %s
                                where (%s)
                                and way && ST_MakeEnvelope(%s, %s, %s, %s, 3857)

                            group by %s
                            ) p

                        ) p
                    ) as tile where %s is not null
          """ % (
            types[vec],
            bbox_p[0],
            bbox_p[1],
            bbox_p[2],
            bbox_p[3],
            geomcolumn,
            names,
            pixel_size_at_zoom(zoom, pxtolerance),
            geomcolumn,
            names,
            geomcolumn,
            names,
            table[vec],
            adp,
            bbox_p[0],
            bbox_p[1],
            bbox_p[2],
            bbox_p[3],
            names,
            geomcolumn,
        )
    elif vec == "point":
        query = """select ST_AsMVT(tile, '%s', 4096, 'way') from (
                        select ST_AsMVTGeom(way, ST_MakeEnvelope(%s, %s, %s, %s, 3857), 4096, 64, true) as %s, %s
                        from %s where (%s)
                        and way && ST_MakeEnvelope(%s, %s, %s, %s, 3857)
                        limit 10000
                    ) as tile where %s is not null
                 """ % (
            types[vec],
            bbox_p[0],
            bbox_p[1],
            bbox_p[2],
            bbox_p[3],
            geomcolumn,
            names,
            table[vec],
            adp,
            bbox_p[0],
            bbox_p[1],
            bbox_p[2],
            bbox_p[3],
            geomcolumn,
        )
    elif vec == "coastline":
        query = """select ST_AsGeoJSON(ST_TransScale(ST_ForceRHR(ST_Intersection(way,SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913))),%s,%s,%s,%s),0) as %s, 'coastline' as "natural" from
                  (select (ST_Dump(ST_Multi(ST_SimplifyPreserveTopology(ST_Buffer(way,-%s),%s)))).geom as %s from
                    (select ST_Union(way) as %s from
                      (select ST_Buffer(SetSRID(the_geom,900913), %s) as %s from
                         %s
                         where
                            SetSRID(the_geom,900913) && SetSRID('BOX3D(%s %s,%s %s)'::box3d,900913)
                      ) p
                    ) p
                    where ST_Area(way) > %s
                  ) p
          """ % (
            bbox_p[0],
            bbox_p[1],
            bbox_p[2],
            bbox_p[3],
            -bbox_p[0],
            -bbox_p[1],
            intscalefactor / (bbox_p[2] - bbox_p[0]),
            intscalefactor / (bbox_p[3] - bbox_p[1]),
            geomcolumn,
            pixel_size_at_zoom(zoom, pxtolerance),
            pixel_size_at_zoom(zoom, pxtolerance),
            geomcolumn,
            geomcolumn,
            pixel_size_at_zoom(zoom, pxtolerance),
            geomcolumn,
            table[vec],
            bbox_p[0],
            bbox_p[1],
            bbox_p[2],
            bbox_p[3],
            pixel_size_at_zoom(zoom, pxtolerance) ** 2,
        )

    a = psycopg2.connect(database)
    b = a.cursor()
    b.execute(query)
    names = [q[0] for q in b.description]

    mvt = None

    for row in b.fetchall():
        geom = dict(map(None, names, row))
        mvt = geom["st_asmvt"]

    return mvt


z = int(sys.argv[1])
x = int(sys.argv[2])
y = int(sys.argv[3])

bbox = projections.bbox_by_tile(z + 1, x, y, "EPSG:3857")

style = MapCSS(0, 30)
# style.parse(open("styles/osmosnimki-maps.mapcss", "r").read())
style.parse(filename="styles/clear/style-clear/style.mapcss")

mvt = (
    str(get_vectors(bbox, z, style, "polygon"))
    + str(get_vectors(bbox, z, style, "point"))
    + str(get_vectors(bbox, z, style, "line"))
)
sys.stdout.write(mvt)
