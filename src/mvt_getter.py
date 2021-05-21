# -*- coding: utf-8 -*-
import json
import psycopg2
from mapcss import MapCSS
import os
import sys
import math
from optparse import OptionParser

reload(sys)
sys.setdefaultencoding("utf-8")  # a hack to support UTF-8


def pixel_size_at_zoom(z, l=1):
    """
    Converts l pixels on tiles into length on zoom z
    """
    return int(math.ceil(l * 20037508.342789244 / 512 * 2 / (2 ** z)))


def get_vectors(zoom, x, y, style, vec="polygon"):
    geomcolumn = "way"

    database = "dbname=project user=kalenik"
    pxtolerance = 1.8
    intscalefactor = 10000
    ignore_columns = set(["way_area", "osm_id", geomcolumn, "tags", "z_order"])
    table = {
        "polygon": "planet_osm_polygon",
        "line": "planet_osm_line",
        "point": "planet_osm_point",
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
        query = """select ST_AsMVTGeom(way, ST_TileEnvelope(%s, %s, %s), 4096, 64, true) as %s, %s from
                        (select (ST_Dump(ST_Multi(ST_SimplifyPreserveTopology(ST_Buffer(way,-%s),%s)))).geom as %s, %s from
                            (select ST_Union(way) as %s, %s from
                            (select ST_Buffer(way, %s) as %s, %s from
                                %s
                                where (%s)
                                and way && ST_TileEnvelope(%s, %s, %s)
                                and way_area > %s
                            ) p
                            group by %s
                            ) p
                            where ST_Area(way) > %s
                            order by ST_Area(way)
                        ) p
          """ % (
            zoom,
            x,
            y,
            geomcolumn,
            names,
            pixel_size_at_zoom(z, pxtolerance),
            pixel_size_at_zoom(z, pxtolerance),
            geomcolumn,
            names,
            geomcolumn,
            names,
            pixel_size_at_zoom(z, pxtolerance),
            geomcolumn,
            names,
            table[vec],
            adp,
            zoom,
            x,
            y,
            (pixel_size_at_zoom(z, pxtolerance) ** 2) / pxtolerance,
            names,
            pixel_size_at_zoom(z, pxtolerance) ** 2,
        )
    elif vec == "line":
        query = """select ST_AsMVTGeom(way, ST_TileEnvelope(%s, %s, %s), 4096, 64, true) as %s, %s from
                        (select (ST_Dump(ST_Multi(ST_SimplifyPreserveTopology(ST_LineMerge(way),%s)))).geom as %s, %s from
                            (select ST_Union(way) as %s, %s from
                                %s
                                where (%s)
                                and way && ST_TileEnvelope(%s, %s, %s)
                            group by %s
                            ) p
                        ) p
          """ % (
            zoom,
            x,
            y,
            geomcolumn,
            names,
            pixel_size_at_zoom(z, pxtolerance),
            geomcolumn,
            names,
            geomcolumn,
            names,
            table[vec],
            adp,
            zoom,
            x,
            y,
            names,
        )
    elif vec == "point":
        query = """select ST_AsMVTGeom(way, ST_TileEnvelope(%s, %s, %s), 4096, 64, true) as %s, %s
                        from %s where (%s)
                        and way && ST_TileEnvelope(%s, %s, %s)
                        limit 10000
                 """ % (
            zoom,
            x,
            y,
            geomcolumn,
            names,
            table[vec],
            adp,
            zoom,
            x,
            y,
        )

    return query


if __name__ == "__main__":
    parser = OptionParser()
    parser.add_option("-s", "--stylesheet", dest="filename", metavar="FILE")

    (options, args) = parser.parse_args()

    style = MapCSS(0, 30)
    style.parse(filename=options.filename)

    for z in range(0, 24):
        print(
            """create or replace function public.basemap_z%s(x integer, y integer)
        returns bytea
        as $$
        declare
            area_mvt bytea;
            line_mvt bytea;
            node_mvt bytea;
            result bytea;
        begin
            select into area_mvt
                ST_AsMVT(tile, 'area', 4096, 'way')
                from (%s) as tile;
            
            select into line_mvt
                ST_AsMVT(tile, 'line', 4096, 'way')
                from (%s) as tile;
            
            select into node_mvt
                ST_AsMVT(tile, 'node', 4096, 'way')
                from (%s) as tile;

            return area_mvt || line_mvt || node_mvt;
        end
        $$
        language plpgsql immutable strict parallel safe;
        """
            % (
                z,
                get_vectors(z, "x", "y", style, "polygon"),
                get_vectors(z, "x", "y", style, "line"),
                get_vectors(z, "x", "y", style, "point"),
            )
        )

    print(
        """create or replace function public.basemap(z integer, x integer, y integer)
        returns bytea
        as $$
        begin
            case
                when z = 0 then
                    return public.basemap_z0(x, y);
                when z = 1 then
                    return public.basemap_z1(x, y);
                when z = 2 then
                    return public.basemap_z2(x, y);
                when z = 3 then
                    return public.basemap_z3(x, y);
                when z = 4 then
                    return public.basemap_z4(x, y);
                when z = 5 then
                    return public.basemap_z5(x, y);
                when z = 6 then
                    return public.basemap_z6(x, y);
                when z = 7 then
                    return public.basemap_z7(x, y);
                when z = 8 then
                    return public.basemap_z8(x, y);
                when z = 9 then
                    return public.basemap_z9(x, y);
                when z = 10 then
                    return public.basemap_z10(x, y);
                when z = 11 then
                    return public.basemap_z11(x, y);
                when z = 12 then
                    return public.basemap_z12(x, y);
                when z = 13 then
                    return public.basemap_z13(x, y);
                when z = 14 then
                    return public.basemap_z14(x, y);
                when z = 15 then
                    return public.basemap_z15(x, y);
                when z = 16 then
                    return public.basemap_z16(x, y);
                when z = 17 then
                    return public.basemap_z17(x, y);
                when z = 18 then
                    return public.basemap_z18(x, y);
                when z = 19 then
                    return public.basemap_z19(x, y);
                when z = 20 then
                    return public.basemap_z20(x, y);
                when z = 21 then
                    return public.basemap_z21(x, y);
                when z = 22 then
                    return public.basemap_z22(x, y);
                when z = 23 then
                    return public.basemap_z23(x, y);
                when z = 24 then
                    return public.basemap_z24(x, y);
                else
                    raise exception 'invalid tile coordinate (%, %, %)', z, x, y;
            end case;
        end
        $$
        language plpgsql immutable strict parallel safe;"""
    )
