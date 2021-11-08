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
            return mapped_cols[name] + ' as "%s"' % name
        else:
            return mapped_cols[name]

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
    return l * 20037508.342789244 / 512 * 2 / (2 ** z)


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

    hints = set()
    for chooser in choosers:
        tags = set()
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
                    if q and len(q) > 1 and len(q[1]) > 0:
                            tags.add(q[0])
                            b.add(q[1])

                if b:
                    hints.add("(" + " AND ".join(b) + ")")

    return (tags, hints)


def get_vectors(minzoom, maxzoom, x, y, style, vec, extent, locales):
    geomcolumn = "way"

    pxtolerance = 0.5
    table = {
        "polygon": "planet_osm_polygon",
        "line": "planet_osm_line",
        "point": "planet_osm_point",
    }

    types = {"line": "line", "polygon": "area", "point": "node"}

    column_names_needed = set()
    column_names_all = style.get_all_tags(types[vec])

    adp = set()
    for zoom in range(minzoom, maxzoom + 1):
        column_names_needed.update(style.get_interesting_tags(types[vec], zoom))

        tp = get_sql_hints(style.choosers, types[vec], zoom)
        for j in tp[0]:
            if j not in column_names_needed:
                break
        else:
            adp = adp.union(tp[1])

    if "name" in column_names_needed:
        for locale in locales:
            column_names_needed.add("name:%s" % (locale))
        
        if "en" in locales:
            column_names_needed.add("int_name")
    
    if "name:en" in column_names_needed:
        mapped_cols[
            "name:en"
        ] = """coalesce(
        tags->'name:en',
        tags->'int_name',
        replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace
        (replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace
        (replace(replace
        (replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(translate(tags->'name:be','АБВГДЖЗІЙКЛМНОПРСТУЎФЦЧШЫЭабвгджзійклмнопрстуўфцчшыэ', 'ABVHDŽZIJKLMNOPRSTUŬFСČŠYEabvhdžzijklmnoprstuŭfсčšye'), 'х', 'ch'), 'Х', 'Ch'), 'BЕ', 'BIe'), 'BЁ', 'BIo'), 'BЮ', 'BIu'), 'BЯ', 'BIa'), 'Bе', 'Bie'), 'Bё', 'Bio'), 'Bю', 'Biu'), 'Bя', 'Bia'), 'VЕ', 'VIe'), 'VЁ', 'VIo'), 'VЮ', 'VIu'), 'VЯ', 'VIa'), 'Vе', 'Vie'), 'Vё', 'Vio'), 'Vю', 'Viu'), 'Vя', 'Via'), 'HЕ',
        'HIe'), 'HЁ',
        'HIo'), 'HЮ', 'HIu'), 'HЯ', 'HIa'), 'Hе', 'Hie'), 'Hё', 'Hio'), 'Hю', 'Hiu'), 'Hя', 'Hia'), 'DЕ', 'DIe'), 'DЁ', 'DIo'), 'DЮ', 'DIu'), 'DЯ', 'DIa'), 'Dе', 'Die'), 'Dё', 'Dio'), 'Dю', 'Diu'), 'Dя', 'Dia'), 'ŽЕ', 'ŽIe'), 'ŽЁ', 'ŽIo'), 'ŽЮ', 'ŽIu'), 'ŽЯ', 'ŽIa'), 'Žе', 'Žie'), 'Žё', 'Žio'), 'Žю', 'Žiu'), 'Žя', 'Žia'), 'ZЕ', 'ZIe'), 'ZЁ', 'ZIo'), 'ZЮ', 'ZIu'), 'ZЯ', 'ZIa'), 'Zе', 'Zie'), 'Zё', 'Zio'), 'Zю', 'Ziu'), 'Zя', 'Zia'), 'JЕ', 'JIe'), 'JЁ', 'JIo'), 'JЮ', 'JIu'), 'JЯ', 'JIa'), 'Jе', 'Jie'), 'Jё', 'Jio'), 'Jю', 'Jiu'),
        'Jя', 'Jia'), 'КЕ', 'КIe'), 'КЁ', 'КIo'), 'КЮ', 'КIu'), 'КЯ', 'КIa'), 'Ке', 'Кie'), 'Кё', 'Кio'), 'Кю', 'Кiu'), 'Кя', 'Кia'), 'LЕ', 'LIe'), 'LЁ', 'LIo'), 'LЮ', 'LIu'), 'LЯ', 'LIa'), 'Lе', 'Lie'), 'Lё', 'Lio'), 'Lю', 'Liu'), 'Lя', 'Lia'), 'MЕ', 'MIe'), 'MЁ', 'MIo'), 'MЮ', 'MIu'), 'MЯ', 'MIa'), 'Mе', 'Mie'), 'Mё', 'Mio'), 'Mю', 'Miu'), 'Mя', 'Mia'), 'NЕ', 'NIe'), 'NЁ', 'NIo'), 'NЮ', 'NIu'), 'NЯ', 'NIa'), 'Nе', 'Nie'), 'Nё', 'Nio'), 'Nю', 'Niu'), 'Nя', 'Nia'), 'PЕ', 'PIe'), 'PЁ', 'PIo'), 'PЮ',
        'PIu'), 'PЯ', 'PIa'), 'Pе', 'Pie'), 'Pё', 'Pio'), 'Pю', 'Piu'), 'Pя', 'Pia'), 'RЕ', 'RIe'), 'RЁ', 'RIo'), 'RЮ', 'RIu'), 'RЯ', 'RIa'), 'Rе', 'Rie'), 'Rё', 'Rio'), 'Rю', 'Riu'), 'Rя', 'Ria'), 'SЕ', 'SIe'), 'SЁ', 'SIo'), 'SЮ', 'SIu'), 'SЯ', 'SIa'), 'Sе', 'Sie'), 'Sё', 'Sio'), 'Sю', 'Siu'), 'Sя', 'Sia'), 'TЕ', 'TIe'), 'TЁ', 'TIo'), 'TЮ', 'TIu'), 'TЯ', 'TIa'), 'Tе', 'Tie'), 'Tё', 'Tio'), 'Tю', 'Tiu'), 'Tя', 'Tia'), 'ŬЕ', 'ŬIe'), 'ŬЁ', 'ŬIo'), 'ŬЮ', 'ŬIu'), 'ŬЯ', 'ŬIa'), 'Ŭе', 'Ŭie'), 'Ŭё', 'Ŭio'), 'Ŭю', 'Ŭiu'), 'Ŭя', 'Ŭia'), 'FЕ', 'FIe'), 'FЁ', 'FIo'), 'FЮ', 'FIu'), 'FЯ', 'FIa'), 'Fе', 'Fie'), 'Fё', 'Fio'), 'Fю', 'Fiu'), 'Fя', 'Fia'), 'СЕ', 'СIe'), 'СЁ', 'СIo'), 'СЮ', 'СIu'),
        'СЯ', 'СIa'), 'Се', 'Сie'), 'Сё', 'Сio'), 'Сю', 'Сiu'), 'Ся', 'Сia'), 'ČЕ', 'ČIe'), 'ČЁ', 'ČIo'), 'ČЮ', 'ČIu'), 'ČЯ', 'ČIa'), 'Čе', 'Čie'), 'Čё', 'Čio'), 'Čю', 'Čiu'), 'Čя', 'Čia'), 'ŠЕ', 'ŠIe'), 'ŠЁ', 'ŠIo'), 'ŠЮ', 'ŠIu'), 'ŠЯ', 'ŠIa'), 'Šе', 'Šie'), 'Šё', 'Šio'), 'Šю', 'Šiu'), 'Šя', 'Šia'), 'bЕ', 'bIe'), 'bЁ', 'bIo'), 'bЮ', 'bIu'), 'bЯ',
        'bIa'), 'bе', 'bie'), 'bё', 'bio'), 'bю', 'biu'), 'bя', 'bia'), 'vЕ', 'vIe'), 'vЁ', 'vIo'), 'vЮ', 'vIu'), 'vЯ', 'vIa'), 'vе', 'vie'), 'vё', 'vio'), 'vю', 'viu'), 'vя', 'via'), 'hЕ', 'hIe'), 'hЁ', 'hIo'), 'hЮ', 'hIu'), 'hЯ', 'hIa'), 'hе', 'hie'), 'hё', 'hio'), 'hю', 'hiu'), 'hя', 'hia'), 'dЕ', 'dIe'), 'dЁ', 'dIo'), 'dЮ', 'dIu'), 'dЯ', 'dIa'), 'dе', 'die'), 'dё', 'dio'), 'dю', 'diu'), 'dя', 'dia'), 'žЕ', 'žIe'), 'žЁ', 'žIo'), 'žЮ', 'žIu'), 'žЯ', 'žIa'), 'žе', 'žie'), 'žё', 'žio'), 'žю', 'žiu'), 'žя', 'žia'), 'zЕ', 'zIe'), 'zЁ', 'zIo'), 'zЮ', 'zIu'), 'zЯ', 'zIa'), 'zе', 'zie'), 'zё', 'zio'), 'zю', 'ziu'), 'zя', 'zia'), 'jЕ', 'jIe'), 'jЁ', 'jIo'), 'jЮ', 'jIu'), 'jЯ', 'jIa'), 'jе', 'jie'), 'jё', 'jio'), 'jю', 'jiu'), 'jя', 'jia'), 'кЕ', 'кIe'), 'кЁ', 'кIo'), 'кЮ', 'кIu'), 'кЯ', 'кIa'), 'ке', 'кie'), 'кё', 'кio'), 'кю', 'кiu'), 'кя', 'кia'), 'lЕ', 'lIe'),
        'lЁ', 'lIo'), 'lЮ', 'lIu'), 'lЯ', 'lIa'), 'lе', 'lie'), 'lё', 'lio'), 'lю', 'liu'), 'lя', 'lia'), 'mЕ', 'mIe'), 'mЁ', 'mIo'), 'mЮ', 'mIu'), 'mЯ', 'mIa'), 'mе', 'mie'), 'mё', 'mio'), 'mю', 'miu'), 'mя', 'mia'), 'nЕ', 'nIe'), 'nЁ', 'nIo'), 'nЮ', 'nIu'), 'nЯ', 'nIa'), 'nе', 'nie'), 'nё', 'nio'), 'nю', 'niu'), 'nя', 'nia'), 'pЕ', 'pIe'), 'pЁ', 'pIo'), 'pЮ', 'pIu'), 'pЯ', 'pIa'), 'pе', 'pie'), 'pё', 'pio'), 'pю', 'piu'), 'pя', 'pia'), 'rЕ', 'rIe'), 'rЁ', 'rIo'), 'rЮ', 'rIu'), 'rЯ', 'rIa'), 'rе', 'rie'), 'rё', 'rio'), 'rю', 'riu'), 'rя', 'ria'), 'sЕ', 'sIe'), 'sЁ',
        'sIo'), 'sЮ', 'sIu'), 'sЯ', 'sIa'), 'sе', 'sie'), 'sё', 'sio'), 'sю', 'siu'), 'sя', 'sia'), 'tЕ', 'tIe'), 'tЁ', 'tIo'), 'tЮ', 'tIu'), 'tЯ', 'tIa'), 'tе', 'tie'), 'tё', 'tio'), 'tю', 'tiu'), 'tя', 'tia'), 'ŭЕ', 'ŭIe'), 'ŭЁ', 'ŭIo'), 'ŭЮ', 'ŭIu'), 'ŭЯ', 'ŭIa'), 'ŭе', 'ŭie'), 'ŭё', 'ŭio'), 'ŭю', 'ŭiu'), 'ŭя', 'ŭia'), 'fЕ', 'fIe'), 'fЁ', 'fIo'), 'fЮ', 'fIu'), 'fЯ', 'fIa'), 'fе', 'fie'), 'fё', 'fio'), 'fю', 'fiu'), 'fя', 'fia'), 'сЕ', 'сIe'), 'сЁ', 'сIo'), 'сЮ', 'сIu'), 'сЯ', 'сIa'), 'се', 'сie'), 'сё', 'сio'), 'сю', 'сiu'), 'ся', 'сia'), 'čЕ', 'čIe'), 'čЁ', 'čIo'), 'čЮ', 'čIu'), 'čЯ', 'čIa'), 'čе', 'čie'), 'čё',
        'čio'), 'čю', 'čiu'), 'čя', 'čia'), 'šЕ', 'šIe'), 'šЁ', 'šIo'), 'šЮ', 'šIu'), 'šЯ', 'šIa'), 'šе', 'šie'), 'šё', 'šio'), 'šю', 'šiu'), 'šя', 'šia'), 'Е', 'Je'), 'Ё', 'Jo'), 'Ю', 'Ju'), 'Я', 'Ja'), 'е', 'je'), 'ё', 'jo'), 'ю', 'ju'), 'я', 'ja'), 'Ь', E'\u0301'), 'ь', E'\u0301'),'’', ''),
        replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(translate(tags->'name:ru','абвгдезиклмнопрстуфьАБВГДЕЗИКЛМНОПРСТУФЬ','abvgdeziklmnoprstuf’ABVGDEZIKLMNOPRSTUF’'),'х','kh'),'Х','Kh'),'ц','ts'),'Ц','Ts'),'ч','ch'),'Ч','Ch'),'ш','sh'),'Ш','Sh'),'щ','shch'),'Щ','Shch'),'ъ','”'),'Ъ','”'),'ё','yo'),'Ё','Yo'),'ы','y'),'Ы','Y'),'э','·e'),'Э','E'),'ю','yu'),'Ю','Yu'),'й','y'),'Й','Y'),'я','ya'),'Я','Ya'),'ж','zh'),'Ж','Zh'))"""

    adp = " OR ".join(adp)
    if adp:
        adp = adp.replace("&lt;", "<")
        adp = adp.replace("&gt;", ">")
    if not adp:
        adp = 'false'

    select = ",".join(
        [escape_sql_column(name, type=types[vec], asname=True) for name in column_names_needed]
    )
    groupby = ",".join(['"%s"' % name for name in column_names_needed])
    """
    complete list of tags used in a style is preserved across all zoom levels.
    it is required to make tiles containing the same feature on different zoom levels be the same.
    this property allows to skip rendering of tile subtree if parent and child tiles are equal.
    to avoid tile bloating unneeded tags are always filled with NULLs.
    """
    groupby_all = ",".join([('"%s"' % name if name in column_names_needed else 'null as "%s"' % name) for name in column_names_all])

    if not select:
        return "select "

    if vec == "polygon":
        coastline_query = """select ST_AsMVTGeom(geom, ST_TileEnvelope(%s, %s, %s), %s, 64, true) as way, %s from
                (select ST_SimplifyVW(ST_Union(geom), %s) as geom from
                    (select geom from
                        land_polygons_vector
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
                    for name in column_names_all
                ]
            ),
            pixel_size_at_zoom(maxzoom, pxtolerance) ** 2,
            minzoom,
            x,
            y,
            pixel_size_at_zoom(maxzoom, pxtolerance) ** 2,
        )
        polygons_query = """select ST_Buffer(way, -%s, 0) as %s, %s from
                                (select ST_Union(way) as %s, %s from
                                    (select ST_Buffer(way, %s) as %s, %s from %s
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
            pixel_size_at_zoom(maxzoom, 1) ** 2,
            groupby,
            pixel_size_at_zoom(maxzoom, 1) ** 2,
        )

        if maxzoom >= 7:
            polygons_query = """select ST_Simplify(way, %s) as %s, %s from %s
                                    where (%s)
                                    and way && ST_TileEnvelope(%s, %s, %s)
                                    and way_area > %s
                                    order by way_area desc""" % (
                    pixel_size_at_zoom(maxzoom, pxtolerance),
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
            groupby_all,
            polygons_query,
            coastline_query,
        )
    elif vec == "line":
        query = """select ST_AsMVTGeom(way, ST_TileEnvelope(%s, %s, %s), %s, 64, true) as %s, %s from
                        (select ST_Simplify(ST_LineMerge(way), %s) as %s, %s from
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
            extent,
            geomcolumn,
            groupby_all,
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
            ",".join(
                [
                    escape_sql_column(name, type=types[vec], asname=False)
                    for name in column_names_needed
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


def basemap_sql(minzoom, maxzoom, extent, style, options):
    return """(
            (select coalesce(ST_AsMVT(tile, 'area', %s, 'way'), '') from (%s) as tile) ||
            (select coalesce(ST_AsMVT(tile, 'line', %s, 'way'), '') from (%s) as tile) ||
            (select coalesce(ST_AsMVT(tile, 'node', %s, 'way'), '') from (%s) as tile)
        )""" % (
        extent,
        get_vectors(
            minzoom,
            maxzoom,
            "$2",
            "$3",
            style,
            "polygon",
            extent,
            options.locale.split(","),
        ),
        extent,
        get_vectors(
            minzoom,
            maxzoom,
            "$2",
            "$3",
            style,
            "line",
            extent,
            options.locale.split(","),
        ),
        extent,
        get_vectors(
            minzoom,
            maxzoom,
            "$2",
            "$3",
            style,
            "point",
            extent,
            options.locale.split(","),
        ),
    )


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

    print(
        """select
        case when $1 = 0 then %s
             when $1 = 1 then %s
             when $1 = 2 then %s
             when $1 = 3 then %s
             when $1 = 4 then %s
             when $1 = 5 then %s
             when $1 = 6 then %s
             when $1 = 7 then %s
             when $1 = 8 then %s
             when $1 = 9 then %s
             when $1 = 10 then %s
             when $1 = 11 then %s
             when $1 = 12 then %s
             when $1 = 13 then %s
             when $1 = 14 then %s
             else null
        end"""
        % (
            basemap_sql(0, 0, 4096, style, options),
            basemap_sql(1, 1, 4096, style, options),
            basemap_sql(2, 2, 4096, style, options),
            basemap_sql(3, 3, 4096, style, options),
            basemap_sql(4, 4, 4096, style, options),
            basemap_sql(5, 5, 4096, style, options),
            basemap_sql(6, 6, 4096, style, options),
            basemap_sql(7, 7, 4096, style, options),
            basemap_sql(8, 8, 4096, style, options),
            basemap_sql(9, 9, 4096, style, options),
            basemap_sql(10, 10, 4096, style, options),
            basemap_sql(11, 11, 4096, style, options),
            basemap_sql(12, 12, 4096, style, options),
            basemap_sql(13, 13, 4096, style, options),
            basemap_sql(14, 23, 8192, style, options),
        )
    )
