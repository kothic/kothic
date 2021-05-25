# -*- coding: utf-8 -*-
import json
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


def get_vectors(minzoom, maxzoom, x, y, style, vec):
    geomcolumn = "way"

    pxtolerance = 1.8
    table = {
        "polygon": "planet_osm_polygon",
        "line": "planet_osm_line",
        "point": "planet_osm_point",
    }

    types = {"line": "line", "polygon": "area", "point": "node"}

    names = set()
    adp = ""

    if "get_sql_hints" in dir(style):
        adp = []

        for zoom in range(minzoom, maxzoom):
            names.update(style.get_interesting_tags(types[vec], zoom))

            sql_hint = style.get_sql_hints(types[vec], zoom)
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

    select = ",".join(["tags->" + "'" + i + "'" + ' as "' + i + '"' for i in names])
    groupby = ",".join(['"' + i + '"' for i in names])

    if vec == "polygon":
        query = """select ST_AsMVTGeom(w.way, ST_TileEnvelope(%s, %s, %s), 4096, 64, true) as %s, %s from
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
                        ) p, lateral (values (p.way), (ST_PointOnSurface(p.way))) w(way)
          """ % (
            minzoom,
            x,
            y,
            geomcolumn,
            groupby,
            pixel_size_at_zoom(maxzoom, pxtolerance),
            pixel_size_at_zoom(maxzoom, pxtolerance),
            geomcolumn,
            groupby,
            geomcolumn,
            groupby,
            pixel_size_at_zoom(maxzoom, pxtolerance),
            geomcolumn,
            select,
            table[vec],
            adp,
            minzoom,
            x,
            y,
            (pixel_size_at_zoom(maxzoom, pxtolerance) ** 2) / pxtolerance,
            groupby,
            pixel_size_at_zoom(maxzoom, pxtolerance) ** 2,
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
            minzoom,
            x,
            y,
            geomcolumn,
            groupby,
            pixel_size_at_zoom(maxzoom, pxtolerance),
            geomcolumn,
            groupby,
            geomcolumn,
            select,
            table[vec],
            adp,
            minzoom,
            x,
            y,
            ",".join(["tags->" + "'" + i + "'" for i in names]),
        )
    elif vec == "point":
        query = """select ST_AsMVTGeom(way, ST_TileEnvelope(%s, %s, %s), 4096, 64, true) as %s, %s
                        from %s where (%s)
                        and way && ST_TileEnvelope(%s, %s, %s)
                        limit 10000
                 """ % (
            minzoom,
            x,
            y,
            geomcolumn,
            select,
            table[vec],
            adp,
            minzoom,
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

    zooms = [
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 4),
        (4, 5),
        (5, 6),
        (7, 8),
        (9, 10),
        (10, 11),
        (11, 12),
        (12, 13),
        (13, 14),
        (14, 30)
    ]

    for (minzoom, maxzoom) in zooms:
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
                minzoom,
                get_vectors(minzoom, maxzoom, "x", "y", style, "polygon"),
                get_vectors(minzoom, maxzoom, "x", "y", style, "line"),
                get_vectors(minzoom, maxzoom, "x", "y", style, "point"),
            )
        )

    # print(
    #     """create or replace function public.basemap(z integer, x integer, y integer)
    #     returns bytea
    #     as $$
    #     begin
    #         case
    #             when z = 0 then
    #                 return public.basemap_z0(x, y);
    #             when z = 1 then
    #                 return public.basemap_z1(x, y);
    #             when z = 2 then
    #                 return public.basemap_z2(x, y);
    #             when z = 3 then
    #                 return public.basemap_z3(x, y);
    #             when z = 4 then
    #                 return public.basemap_z4(x, y);
    #             when z = 5 then
    #                 return public.basemap_z5(x, y);
    #             when z = 6 then
    #                 return public.basemap_z6(x, y);
    #             when z = 7 then
    #                 return public.basemap_z7(x, y);
    #             when z = 8 then
    #                 return public.basemap_z8(x, y);
    #             when z = 9 then
    #                 return public.basemap_z9(x, y);
    #             when z = 10 then
    #                 return public.basemap_z10(x, y);
    #             when z = 11 then
    #                 return public.basemap_z11(x, y);
    #             when z = 12 then
    #                 return public.basemap_z12(x, y);
    #             when z = 13 then
    #                 return public.basemap_z13(x, y);
    #             when z = 14 then
    #                 return public.basemap_z14(x, y);
    #             when z = 15 then
    #                 return public.basemap_z15(x, y);
    #             when z = 16 then
    #                 return public.basemap_z16(x, y);
    #             when z = 17 then
    #                 return public.basemap_z17(x, y);
    #             when z = 18 then
    #                 return public.basemap_z18(x, y);
    #             when z = 19 then
    #                 return public.basemap_z19(x, y);
    #             when z = 20 then
    #                 return public.basemap_z20(x, y);
    #             when z = 21 then
    #                 return public.basemap_z21(x, y);
    #             when z = 22 then
    #                 return public.basemap_z22(x, y);
    #             when z = 23 then
    #                 return public.basemap_z23(x, y);
    #             when z = 24 then
    #                 return public.basemap_z24(x, y);
    #             else
    #                 raise exception 'invalid tile coordinate (%, %, %)', z, x, y;
    #         end case;
    #     end
    #     $$
    #     language plpgsql immutable strict parallel safe;"""
    # )
