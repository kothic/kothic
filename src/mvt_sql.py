# -*- coding: utf-8 -*-
import sys
import math
from mapcss import _test_feature_compatibility

reload(sys)
sys.setdefaultencoding("utf-8")  # a hack to support UTF-8

mapped_cols = {}
osm2pgsql_avail_keys = {}


def escape_sql_column(name, type, asname=False):
    if name in mapped_cols:
        if asname:
            return mapped_cols[name][1] + ' as "%s"' % mapped_cols[name][0]
        else:
            return mapped_cols[name][1]

    name = name.strip().strip('"')
    type = {"line": "way", "area": "way"}.get(type, type)
    if type in osm2pgsql_avail_keys.get(name, ()) or not osm2pgsql_avail_keys:
        return '"' + name + '"'
    elif not asname:
        return "(tags->'" + name + "')"
    else:
        return "(tags->'" + name + "') as \"" + name + '"'


def pixel_size_at_zoom(z, l=1):
    """
    Converts l pixels on tiles into length on zoom z
    """
    return int(math.ceil(l * 20037508.342789244 / 512 * 2 / (2 ** z)))


def get_sql(condition, obj):
    # params = [re.escape(x) for x in self.params]
    params = condition.params
    t = condition.type
    if t == "eq":  # don't compare tags against sublayers
        if params[0][:2] == "::":
            return ("", "")
    try:
        column_name = escape_sql_column(params[0], type=obj)

        if t == "eq":
            return params[0], "%s = '%s'" % (column_name, params[1])
        if t == "ne":
            return (
                params[0],
                "(%s is distinct from '%s')" % (column_name, params[1]),
            )
        if t == "regex":
            return params[0], "%s ~ '%s'" % (column_name, params[1].replace("'", "\\'"))
        if t == "true":
            return params[0], "%s = 'yes'" % (column_name)
        if t == "untrue":
            return params[0], "%s = 'no'" % (column_name)
        if t == "set":
            return params[0], "%s is not null" % (column_name)
        if t == "unset":
            return params[0], "%s is null" % (column_name)
        if t in ("<", "<=", ">", ">="):
            return (
                params[0],
                """(case when %s  ~  E'^[-]?[[:digit:]]+([.][[:digit:]]+)?$' then cast (%s as float) %s %s else false end) """
                % (column_name, column_name, t, params[1]),
            )
    except KeyError:
        pass


def get_sql_hints(choosers, obj, zoom):
    needed = set(
        [
            "width",
            "fill-color",
            "fill-image",
            "icon-image",
            "text",
            "extrude",
            "background-image",
            "background-color",
            "pattern-image",
            "shield-text",
        ]
    )

    hints = []
    for chooser in choosers:
        tags = set()
        qs = []
        if not needed.isdisjoint(set(chooser.styles[0].keys())):
            for rule in chooser.ruleChains:
                if obj:
                    if (rule.subject != "") and not _test_feature_compatibility(
                        obj, rule.subject
                    ):
                        continue
                if not rule.test_zoom(zoom):
                    continue
                b = set()
                for condition in rule.conditions:
                    q = get_sql(condition, obj)
                    if q and len(q) > 1:
                            tags.add(q[0])
                            b.add(q[1])

                if b:
                    qs.append("(" + " AND ".join(b) + ")")

        if qs:
            hints.append((tags, " OR ".join(qs)))

    return hints


def get_vectors(minzoom, maxzoom, x, y, style, vec, extent, locales):
    geomcolumn = "way"

    pxtolerance = 0.5
    table = {
        "polygon": "planet_osm_polygon",
        "line": "planet_osm_line",
        "point": "planet_osm_point",
    }

    types = {"line": "line", "polygon": "area", "point": "node"}

    column_names = set()

    adp = []

    for zoom in range(minzoom, maxzoom + 1):
        column_names.update(style.get_interesting_tags(types[vec], zoom))

        sql_hint = get_sql_hints(style.choosers, types[vec], zoom)
        for tp in sql_hint:
            add = []
            for j in tp[0]:
                if j not in column_names:
                    break
            else:
                add.append(tp[1])
            if add:
                add = " OR ".join(add)
                add = "(" + add + ")"
                adp.append(add)

    if "name" in column_names:
        for locale in locales:
            column_names.add("name:%s" % (locale))
        
        if "en" in locales:
            column_names.add("int_name")

    adp = " OR ".join(adp)
    if adp:
        adp = adp.replace("&lt;", "<")
        adp = adp.replace("&gt;", ">")
    if not adp:
        adp = 'false'

    select = ",".join(
        [escape_sql_column(name, type=types[vec], asname=True) for name in column_names]
    )
    groupby = ",".join(['"%s"' % name for name in column_names])

    if vec == "polygon":
        coastline_query = """select ST_AsMVTGeom(geom, ST_TileEnvelope(%s, %s, %s), %s, 64, true) as way, %s from
                (select ST_Simplify(ST_Union(geom, %s), %s) as geom from
                    (select ST_ReducePrecision(geom, %s) geom from
                        water_polygons_vector
                        where geom && ST_TileEnvelope(%s, %s, %s)
                        and ST_Area(geom) > %s
                    ) p
                ) p""" % (
            minzoom,
            x,
            y,
            extent,
            ",".join(
                [
                    '%s as "%s"'
                    % (("'coastline'" if name == "natural" else "null"), name)
                    for name in column_names
                ]
            ),
            pixel_size_at_zoom(maxzoom, pxtolerance),
            pixel_size_at_zoom(maxzoom, pxtolerance),
            pixel_size_at_zoom(maxzoom, pxtolerance),
            minzoom,
            x,
            y,
            pixel_size_at_zoom(maxzoom, pxtolerance) ** 2,
        )
        polygons_query = """select ST_Buffer(way, -%s, 0) as %s, %s from
                                (select ST_Union(way, %s) as %s, %s from
                                    (select ST_Buffer(st_ReducePrecision(way, %s), %s, 0) as %s, %s from %s
                                        where (%s)
                                        and way && ST_TileEnvelope(%s, %s, %s)
                                        and way_area > %s
                                    ) p
                                    group by %s) p
                                where ST_Area(way) > %s
                                order by ST_Area(way) desc""" % (
            pixel_size_at_zoom(maxzoom, pxtolerance),
            geomcolumn,
            groupby,
            pixel_size_at_zoom(maxzoom, pxtolerance),
            geomcolumn,
            groupby,
            pixel_size_at_zoom(maxzoom, pxtolerance),
            pixel_size_at_zoom(maxzoom, pxtolerance),
            geomcolumn,
            select,
            table[vec],
            adp,
            minzoom,
            x,
            y,
            pixel_size_at_zoom(maxzoom, 1) ** 2,
            groupby,
            pixel_size_at_zoom(maxzoom, 1) ** 2,
        )

        #if maxzoom >= 8:
        polygons_query = """select way as %s, %s from %s
                                where (%s)
                                and way && ST_TileEnvelope(%s, %s, %s)
                                and way_area > %s
                                order by way_area desc""" % (
                geomcolumn,
                select,
                table[vec],
                adp,
                minzoom,
                x,
                y,
                pixel_size_at_zoom(maxzoom, 1) ** 2,
            )

        query = """select ST_AsMVTGeom(w.way, ST_TileEnvelope(%s, %s, %s), %s, 64, true) as %s, %s from
                        (%s) p, lateral (values (p.way), (ST_PointOnSurface(p.way))) w(way)
                   union all
                   %s""" % (
            minzoom,
            x,
            y,
            extent,
            geomcolumn,
            groupby,
            polygons_query,
            coastline_query,
        )
    elif vec == "line":
        query = """select ST_AsMVTGeom(way, ST_TileEnvelope(%s, %s, %s), %s, 64, true) as %s, %s from
                        (select ST_Simplify(ST_LineMerge(way), %s) as %s, %s from
                            (select ST_Union(way, %s) as %s, %s from
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
            extent,
            geomcolumn,
            groupby,
            pixel_size_at_zoom(maxzoom, pxtolerance),
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
            ",".join(
                [
                    escape_sql_column(name, type=types[vec], asname=False)
                    for name in column_names
                ]
            ),
        )
    elif vec == "point":
        query = """select ST_AsMVTGeom(way, ST_TileEnvelope(%s, %s, %s), %s, 64, true) as %s, %s
                        from %s
                        where (%s) and way && ST_TileEnvelope(%s, %s, %s)
                        order by
                        (case when "admin_level"  ~  E'^[-]?[[:digit:]]+([.][[:digit:]]+)?$' then cast ("admin_level" as float) else null end) asc nulls last,
                        (case when "population"  ~  E'^[-]?[[:digit:]]+([.][[:digit:]]+)?$' then cast ("population" as float) else null end) desc nulls last
                        limit 10000
                 """ % (
            minzoom,
            x,
            y,
            extent,
            geomcolumn,
            select,
            table[vec],
            adp,
            minzoom,
            x,
            y,
        )

    return query


def komap_mvt_sql(options, style):
    for style_filename in options.filename:
        style.parse(filename=style_filename)

    if options.osm2pgsqlstyle != "-":
        mf = open(options.osm2pgsqlstyle, "r")
        for line in mf:
            line = line.strip()
            if line and line[0] != "#" and not ("nocolumn" in line):
                line = line.split()
                osm2pgsql_avail_keys[line[1]] = tuple(line[0].split(","))
        osm2pgsql_avail_keys["tags"] = ("node", "way")

    zooms = [
        (0, 0, 4096),
        (1, 1, 4096),
        (2, 2, 4096),
        (3, 3, 4096),
        (4, 4, 4096),
        (5, 5, 4096),
        (6, 6, 4096),
        (7, 7, 4096),
        (8, 8, 4096),
        (9, 9, 4096),
        (10, 10, 4096),
        (11, 11, 4096),
        (12, 12, 4096),
        (13, 13, 4096),
        (14, 23, 8192),
    ]

    for (minzoom, maxzoom, extent) in zooms:
        print(
            """create or replace function public.basemap_z%s(x integer, y integer)
        returns bytea
        as $$
        select (
            (select coalesce(ST_AsMVT(tile, 'area', %s, 'way'), '') from (%s) as tile) ||
            (select coalesce(ST_AsMVT(tile, 'line', %s, 'way'), '') from (%s) as tile) ||
            (select coalesce(ST_AsMVT(tile, 'node', %s, 'way'), '') from (%s) as tile)
        )
        $$
        language sql immutable strict parallel safe;

        alter function basemap_z%s set jit=false;
        alter function basemap_z%s set max_parallel_workers_per_gather=0;
        """
            % (
                minzoom,
                extent,
                get_vectors(minzoom, maxzoom, "x", "y", style, "polygon", extent, options.locale.split(',')),
                extent,
                get_vectors(minzoom, maxzoom, "x", "y", style, "line", extent, options.locale.split(',')),
                extent,
                get_vectors(minzoom, maxzoom, "x", "y", style, "point", extent, options.locale.split(',')),
                minzoom,
                minzoom,
            )
        )

    print(
        """create or replace function public.basemap(z integer, x integer, y integer)
        returns bytea
        as $$
        declare
            mvt bytea;
            dirty boolean;
            t timestamp with time zone := clock_timestamp();
        begin
            select basemap_mvts.mvt, basemap_mvts.dirty into mvt, dirty from basemap_mvts
                where basemap_mvts.tile_z = z and basemap_mvts.tile_x = x and basemap_mvts.tile_y = y
                for update;

            if (mvt is not null) and (not dirty) then
                return mvt;
            end if;

            case
                when z = 0 then
                    select public.basemap_z0(x, y) into mvt;
                when z = 1 then
                    select public.basemap_z1(x, y) into mvt;
                when z = 2 then
                    select public.basemap_z2(x, y) into mvt;
                when z = 3 then
                    select public.basemap_z3(x, y) into mvt;
                when z = 4 then
                    select public.basemap_z4(x, y) into mvt;
                when z = 5 then
                    select public.basemap_z5(x, y) into mvt;
                when z = 6 then
                    select public.basemap_z6(x, y) into mvt;
                when z = 7 then
                    select public.basemap_z7(x, y) into mvt;
                when z = 8 then
                    select public.basemap_z8(x, y) into mvt;
                when z = 9 then
                    select public.basemap_z9(x, y) into mvt;
                when z = 10 then
                    select public.basemap_z10(x, y) into mvt;
                when z = 11 then
                    select public.basemap_z11(x, y) into mvt;
                when z = 12 then
                    select public.basemap_z12(x, y) into mvt;
                when z = 13 then
                    select public.basemap_z13(x, y) into mvt;
                when z = 14 then
                    select public.basemap_z14(x, y) into mvt;
                else
                    raise exception 'invalid tile coordinate (%, %, %)', z, x, y;
            end case;

            insert into basemap_mvts(tile_z, tile_x, tile_y, mvt, render_time, updated_at, dirty)
                values (z, x, y, mvt, age(clock_timestamp(), t), now(), false)
                on conflict (tile_z, tile_x, tile_y)
                do update set mvt = excluded.mvt, render_time = excluded.render_time, updated_at = excluded.updated_at, dirty = excluded.dirty;

            return mvt;
        end
        $$
        language plpgsql volatile strict parallel safe;

        alter function basemap set max_parallel_workers_per_gather=0;
        alter function basemap set jit=false;"""
    )
