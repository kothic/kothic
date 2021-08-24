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
from mapcss import MapCSS

import gc
gc.disable()

import mapcss.webcolors
whatever_to_hex = mapcss.webcolors.webcolors.whatever_to_hex

import sys
reload(sys)
sys.setdefaultencoding("utf-8")

import os

try:
    import Image
except ImportError:
    pass

from optparse import OptionParser
import ConfigParser
import csv
import math

config = ConfigParser.ConfigParser()


def relaxedFloat(x):
    try:
        return float(x) if int(float(x)) != float(x) else int(x)

    except ValueError:
        return float(str(x).replace(",", "."))

parser = OptionParser()
parser.add_option("-r", "--renderer", dest="renderer", default="mapnik",
                  help="which renderer stylesheet to generate", metavar="ENGINE")
parser.add_option("-s", "--stylesheet", dest="filename",
                  help="read MapCSS stylesheet from FILE", metavar="FILE", action="append")
parser.add_option("-f", "--minzoom", dest="minzoom", default=0, type="int",
                  help="minimal available zoom level", metavar="ZOOM")
parser.add_option("-t", "--maxzoom", dest="maxzoom", default=19, type="int",
                  help="maximal available zoom level", metavar="ZOOM")
parser.add_option("-l", "--locale", dest="locale",
                  help="language that should be used for labels (ru, en, be, uk..)", metavar="LANG")
parser.add_option("-o", "--output-file", dest="outfile", default="-",
                  help="output filename (defaults to stdout)", metavar="FILE")
parser.add_option("-p", "--osm2pgsql-style", dest="osm2pgsqlstyle", default="-",
                  help="osm2pgsql stylesheet filename", metavar="FILE")
parser.add_option("-b", "--background-only", dest="bgonly", action="store_true", default=False,
                  help="Skip rendering of icons and labels", metavar="BOOL")
parser.add_option("-T", "--text-scale", dest="textscale", default=1, type="float",
                  help="text size scale", metavar="SCALE")
parser.add_option("-c", "--config", dest="conffile", default="komap.conf",
                  help="config file name", metavar="FILE")
parser.add_option("-u", "--tiles-url", dest="tiles_url", help="URL of MVT tiles used to render this map style")
parser.add_option("-M", "--tiles-max-zoom", dest="tiles_maxzoom", type="int", help="max available zoom for tiles provided in --tiles-url")
parser.add_option("-g", "--glyphs-url", dest="glyphs_url", help="SDF Font glyphs URL to use in rendering")
parser.add_option("-e", "--sprite-url", dest="sprite_url", help="URL of sprite to use in rendering")
parser.add_option("-a", "--attribution-text", dest="attribution_text", help="Attribution and copyrights text to show on the rendered map")

(options, args) = parser.parse_args()

if (options.filename is None):
    parser.error("MapCSS stylesheet filename is required")


def escape_sql_column(name, type="way", asname=False):
    if name in mapped_cols:
        return name  # already escaped
    name = name.strip().strip('"')
    type = {'line': 'way', 'area': 'way'}.get(type, type)
    if type in osm2pgsql_avail_keys.get(name, ()) or not osm2pgsql_avail_keys:
        return '"' + name + '"'
    elif not asname:
        return "(tags->'" + name + "')"
    else:
        return "(tags->'" + name + "') as \"" + name + '"'

style = MapCSS(options.minzoom, options.maxzoom + 1)  # zoom levels
for style_filename in options.filename:
    style.parse(filename=style_filename)

if options.renderer == "mapbox-style-language":
    if options.tiles_url is None:
        parser.error("tiles url is required")
    if options.tiles_maxzoom is None:
        parser.error("tile maxzoom is required")
    if options.glyphs_url is None:
        parser.error("glyphs url is required")

    from libkomb import *
    komap_mapbox(options, style)
    exit()

if options.renderer == "mvt-sql":
    from mvt_sql import *
    komap_mvt_sql(options, style)
    exit()

if options.renderer == "mapswithme":
    from libkomwm import *
    komap_mapswithme(options, style, options.filename)
    exit()

if options.outfile == "-":
    mfile = sys.stdout
else:
    mfile = open(options.outfile, "w")

if options.renderer == "js":
    from libkojs import *
    komap_js(mfile, style)

if options.renderer == "mapnik":
    import libkomapnik

    config.read(['komap.conf', os.path.expanduser('~/.komap/komap.conf'), options.conffile])
    libkomapnik.map_proj = config.get("mapnik", "map_proj")
    libkomapnik.db_proj = config.get("mapnik", "db_proj")
    libkomapnik.table_prefix = config.get("mapnik", "table_prefix")
    libkomapnik.db_user = config.get("mapnik", "db_user")
    libkomapnik.db_name = config.get("mapnik", "db_name")
    libkomapnik.db_srid = config.get("mapnik", "db_srid")
    libkomapnik.icons_path = config.get("mapnik", "icons_path")
    libkomapnik.world_bnd_path = config.get("mapnik", "world_bnd_path")
    libkomapnik.cleantopo_dem_path = config.get("mapnik", "cleantopo_dem_path")
    libkomapnik.srtm_dem_path = config.get("mapnik", "srtm_dem_path")
    libkomapnik.cleantopo_hs_path = config.get("mapnik", "cleantopo_hs_path")
    libkomapnik.srtm_hs_path = config.get("mapnik", "srtm_hs_path")
    libkomapnik.text_scale = options.textscale
    libkomapnik.default_font_family = config.get("mapnik", "default_font_family")
    libkomapnik.max_char_angle_delta = config.get("mapnik", "max_char_angle_delta")
    libkomapnik.font_tracking = config.get("mapnik", "font_tracking")

    from libkomapnik import *

    osm2pgsql_avail_keys = {}  # "column" : ["node", "way"]
    if options.osm2pgsqlstyle != "-":
        mf = open(options.osm2pgsqlstyle, "r")
        for line in mf:
            line = line.strip().split()
            if line and line[0][0] != "#" and not ("phstore" in line):
                osm2pgsql_avail_keys[line[1]] = tuple(line[0].split(","))
        osm2pgsql_avail_keys["tags"] = ("node", "way")

    columnmap = {}

    if options.locale == "en":
        columnmap["name"] = (u"""COALESCE(
        "name:en",
        "int_name",
        replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace
        (replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace
        (replace(replace
        (replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(translate("name:be",'АБВГДЖЗІЙКЛМНОПРСТУЎФЦЧШЫЭабвгджзійклмнопрстуўфцчшыэ', 'ABVHDŽZIJKLMNOPRSTUŬFСČŠYEabvhdžzijklmnoprstuŭfсčšye'), 'х', 'ch'), 'Х', 'Ch'), 'BЕ', 'BIe'), 'BЁ', 'BIo'), 'BЮ', 'BIu'), 'BЯ', 'BIa'), 'Bе', 'Bie'), 'Bё', 'Bio'), 'Bю', 'Biu'), 'Bя', 'Bia'), 'VЕ', 'VIe'), 'VЁ', 'VIo'), 'VЮ', 'VIu'), 'VЯ', 'VIa'), 'Vе', 'Vie'), 'Vё', 'Vio'), 'Vю', 'Viu'), 'Vя', 'Via'), 'HЕ',
        'HIe'), 'HЁ',
        'HIo'), 'HЮ', 'HIu'), 'HЯ', 'HIa'), 'Hе', 'Hie'), 'Hё', 'Hio'), 'Hю', 'Hiu'), 'Hя', 'Hia'), 'DЕ', 'DIe'), 'DЁ', 'DIo'), 'DЮ', 'DIu'), 'DЯ', 'DIa'), 'Dе', 'Die'), 'Dё', 'Dio'), 'Dю', 'Diu'), 'Dя', 'Dia'), 'ŽЕ', 'ŽIe'), 'ŽЁ', 'ŽIo'), 'ŽЮ', 'ŽIu'), 'ŽЯ', 'ŽIa'), 'Žе', 'Žie'), 'Žё', 'Žio'), 'Žю', 'Žiu'), 'Žя', 'Žia'), 'ZЕ', 'ZIe'), 'ZЁ', 'ZIo'), 'ZЮ', 'ZIu'), 'ZЯ', 'ZIa'), 'Zе', 'Zie'), 'Zё', 'Zio'), 'Zю', 'Ziu'), 'Zя', 'Zia'), 'JЕ', 'JIe'), 'JЁ', 'JIo'), 'JЮ', 'JIu'), 'JЯ', 'JIa'), 'Jе', 'Jie'), 'Jё', 'Jio'), 'Jю', 'Jiu'),
        'Jя', 'Jia'), 'КЕ', 'КIe'), 'КЁ', 'КIo'), 'КЮ', 'КIu'), 'КЯ', 'КIa'), 'Ке', 'Кie'), 'Кё', 'Кio'), 'Кю', 'Кiu'), 'Кя', 'Кia'), 'LЕ', 'LIe'), 'LЁ', 'LIo'), 'LЮ', 'LIu'), 'LЯ', 'LIa'), 'Lе', 'Lie'), 'Lё', 'Lio'), 'Lю', 'Liu'), 'Lя', 'Lia'), 'MЕ', 'MIe'), 'MЁ', 'MIo'), 'MЮ', 'MIu'), 'MЯ', 'MIa'), 'Mе', 'Mie'), 'Mё', 'Mio'), 'Mю', 'Miu'), 'Mя', 'Mia'), 'NЕ', 'NIe'), 'NЁ', 'NIo'), 'NЮ', 'NIu'), 'NЯ', 'NIa'), 'Nе', 'Nie'), 'Nё', 'Nio'), 'Nю', 'Niu'), 'Nя', 'Nia'), 'PЕ', 'PIe'), 'PЁ', 'PIo'), 'PЮ',
        'PIu'), 'PЯ', 'PIa'), 'Pе', 'Pie'), 'Pё', 'Pio'), 'Pю', 'Piu'), 'Pя', 'Pia'), 'RЕ', 'RIe'), 'RЁ', 'RIo'), 'RЮ', 'RIu'), 'RЯ', 'RIa'), 'Rе', 'Rie'), 'Rё', 'Rio'), 'Rю', 'Riu'), 'Rя', 'Ria'), 'SЕ', 'SIe'), 'SЁ', 'SIo'), 'SЮ', 'SIu'), 'SЯ', 'SIa'), 'Sе', 'Sie'), 'Sё', 'Sio'), 'Sю', 'Siu'), 'Sя', 'Sia'), 'TЕ', 'TIe'), 'TЁ', 'TIo'), 'TЮ', 'TIu'), 'TЯ', 'TIa'), 'Tе', 'Tie'), 'Tё', 'Tio'), 'Tю', 'Tiu'), 'Tя', 'Tia'), 'ŬЕ', 'ŬIe'), 'ŬЁ', 'ŬIo'), 'ŬЮ', 'ŬIu'), 'ŬЯ', 'ŬIa'), 'Ŭе', 'Ŭie'), 'Ŭё', 'Ŭio'), 'Ŭю', 'Ŭiu'), 'Ŭя', 'Ŭia'), 'FЕ', 'FIe'), 'FЁ', 'FIo'), 'FЮ', 'FIu'), 'FЯ', 'FIa'), 'Fе', 'Fie'), 'Fё', 'Fio'), 'Fю', 'Fiu'), 'Fя', 'Fia'), 'СЕ', 'СIe'), 'СЁ', 'СIo'), 'СЮ', 'СIu'),
        'СЯ', 'СIa'), 'Се', 'Сie'), 'Сё', 'Сio'), 'Сю', 'Сiu'), 'Ся', 'Сia'), 'ČЕ', 'ČIe'), 'ČЁ', 'ČIo'), 'ČЮ', 'ČIu'), 'ČЯ', 'ČIa'), 'Čе', 'Čie'), 'Čё', 'Čio'), 'Čю', 'Čiu'), 'Čя', 'Čia'), 'ŠЕ', 'ŠIe'), 'ŠЁ', 'ŠIo'), 'ŠЮ', 'ŠIu'), 'ŠЯ', 'ŠIa'), 'Šе', 'Šie'), 'Šё', 'Šio'), 'Šю', 'Šiu'), 'Šя', 'Šia'), 'bЕ', 'bIe'), 'bЁ', 'bIo'), 'bЮ', 'bIu'), 'bЯ',
        'bIa'), 'bе', 'bie'), 'bё', 'bio'), 'bю', 'biu'), 'bя', 'bia'), 'vЕ', 'vIe'), 'vЁ', 'vIo'), 'vЮ', 'vIu'), 'vЯ', 'vIa'), 'vе', 'vie'), 'vё', 'vio'), 'vю', 'viu'), 'vя', 'via'), 'hЕ', 'hIe'), 'hЁ', 'hIo'), 'hЮ', 'hIu'), 'hЯ', 'hIa'), 'hе', 'hie'), 'hё', 'hio'), 'hю', 'hiu'), 'hя', 'hia'), 'dЕ', 'dIe'), 'dЁ', 'dIo'), 'dЮ', 'dIu'), 'dЯ', 'dIa'), 'dе', 'die'), 'dё', 'dio'), 'dю', 'diu'), 'dя', 'dia'), 'žЕ', 'žIe'), 'žЁ', 'žIo'), 'žЮ', 'žIu'), 'žЯ', 'žIa'), 'žе', 'žie'), 'žё', 'žio'), 'žю', 'žiu'), 'žя', 'žia'), 'zЕ', 'zIe'), 'zЁ', 'zIo'), 'zЮ', 'zIu'), 'zЯ', 'zIa'), 'zе', 'zie'), 'zё', 'zio'), 'zю', 'ziu'), 'zя', 'zia'), 'jЕ', 'jIe'), 'jЁ', 'jIo'), 'jЮ', 'jIu'), 'jЯ', 'jIa'), 'jе', 'jie'), 'jё', 'jio'), 'jю', 'jiu'), 'jя', 'jia'), 'кЕ', 'кIe'), 'кЁ', 'кIo'), 'кЮ', 'кIu'), 'кЯ', 'кIa'), 'ке', 'кie'), 'кё', 'кio'), 'кю', 'кiu'), 'кя', 'кia'), 'lЕ', 'lIe'),
        'lЁ', 'lIo'), 'lЮ', 'lIu'), 'lЯ', 'lIa'), 'lе', 'lie'), 'lё', 'lio'), 'lю', 'liu'), 'lя', 'lia'), 'mЕ', 'mIe'), 'mЁ', 'mIo'), 'mЮ', 'mIu'), 'mЯ', 'mIa'), 'mе', 'mie'), 'mё', 'mio'), 'mю', 'miu'), 'mя', 'mia'), 'nЕ', 'nIe'), 'nЁ', 'nIo'), 'nЮ', 'nIu'), 'nЯ', 'nIa'), 'nе', 'nie'), 'nё', 'nio'), 'nю', 'niu'), 'nя', 'nia'), 'pЕ', 'pIe'), 'pЁ', 'pIo'), 'pЮ', 'pIu'), 'pЯ', 'pIa'), 'pе', 'pie'), 'pё', 'pio'), 'pю', 'piu'), 'pя', 'pia'), 'rЕ', 'rIe'), 'rЁ', 'rIo'), 'rЮ', 'rIu'), 'rЯ', 'rIa'), 'rе', 'rie'), 'rё', 'rio'), 'rю', 'riu'), 'rя', 'ria'), 'sЕ', 'sIe'), 'sЁ',
        'sIo'), 'sЮ', 'sIu'), 'sЯ', 'sIa'), 'sе', 'sie'), 'sё', 'sio'), 'sю', 'siu'), 'sя', 'sia'), 'tЕ', 'tIe'), 'tЁ', 'tIo'), 'tЮ', 'tIu'), 'tЯ', 'tIa'), 'tе', 'tie'), 'tё', 'tio'), 'tю', 'tiu'), 'tя', 'tia'), 'ŭЕ', 'ŭIe'), 'ŭЁ', 'ŭIo'), 'ŭЮ', 'ŭIu'), 'ŭЯ', 'ŭIa'), 'ŭе', 'ŭie'), 'ŭё', 'ŭio'), 'ŭю', 'ŭiu'), 'ŭя', 'ŭia'), 'fЕ', 'fIe'), 'fЁ', 'fIo'), 'fЮ', 'fIu'), 'fЯ', 'fIa'), 'fе', 'fie'), 'fё', 'fio'), 'fю', 'fiu'), 'fя', 'fia'), 'сЕ', 'сIe'), 'сЁ', 'сIo'), 'сЮ', 'сIu'), 'сЯ', 'сIa'), 'се', 'сie'), 'сё', 'сio'), 'сю', 'сiu'), 'ся', 'сia'), 'čЕ', 'čIe'), 'čЁ', 'čIo'), 'čЮ', 'čIu'), 'čЯ', 'čIa'), 'čе', 'čie'), 'čё',
        'čio'), 'čю', 'čiu'), 'čя', 'čia'), 'šЕ', 'šIe'), 'šЁ', 'šIo'), 'šЮ', 'šIu'), 'šЯ', 'šIa'), 'šе', 'šie'), 'šё', 'šio'), 'šю', 'šiu'), 'šя', 'šia'), 'Е', 'Je'), 'Ё', 'Jo'), 'Ю', 'Ju'), 'Я', 'Ja'), 'е', 'je'), 'ё', 'jo'), 'ю', 'ju'), 'я', 'ja'), 'Ь', '\u0301'), 'ь', '\u0301'),'’', ''),
        replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(translate("name",'абвгдезиклмнопрстуфьАБВГДЕЗИКЛМНОПРСТУФЬ','abvgdeziklmnoprstuf’ABVGDEZIKLMNOPRSTUF’'),'х','kh'),'Х','Kh'),'ц','ts'),'Ц','Ts'),'ч','ch'),'Ч','Ch'),'ш','sh'),'Ш','Sh'),'щ','shch'),'Щ','Shch'),'ъ','”'),'Ъ','”'),'ё','yo'),'Ё','Yo'),'ы','y'),'Ы','Y'),'э','·e'),'Э','E'),'ю','yu'),'Ю','Yu'),'й','y'),'Й','Y'),'я','ya'),'Я','Ya'),'ж','zh'),'Ж','Zh')) AS name""", ('name:en', 'int_name', 'name:be'))

    elif options.locale == "be":
        columnmap["name"] =  ("""COALESCE("name:be",
          "name:ru",
          "int_name",
          "name:en",
          "name"
        ) AS name""", ('name:be', "name:ru", "int_name", "name:en"))
    elif options.locale and ("name:" + options.locale in osm2pgsql_avail_keys or not osm2pgsql_avail_keys):
        columnmap["name"] = ('COALESCE("name:' + options.locale + '", "name") AS name', ('name:' + options.locale,))
    elif options.locale:
        columnmap["name"] = ("COALESCE(tags->'name:" + options.locale + '\', "name") AS name', ('tags',))

    mapped_cols = [i[0] for i in columnmap.values()]
    numerics = set()  # set of number-compared things, like "population<10000" needs population as number, not text
    mapniksheet = {}

    # {zoom: {z-index: [{sql:sql_hint, cond: mapnikfiltercondition, subject: subj, style: {a:b,c:d..}},{r2}...]...}...}
    coast = {}
    fonts = set()
    demhack = False
    for zoom in xrange(options.minzoom, options.maxzoom + 1):
        mapniksheet[zoom] = {}
        zsheet = mapniksheet[zoom]
        for chooser in style.choosers:
            if chooser.get_sql_hints(chooser.ruleChains[0].subject, zoom)[1]:
                # sys.stderr.write(str(chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)[1])+"\n")
                styles = chooser.styles[0]
                zindex = styles.get("z-index", 0)
                if zindex not in zsheet:
                    zsheet[zindex] = []
                chooser_entry = {}

                ttypes = list(set([x.subject for x in chooser.ruleChains]))

                sql = "(" + chooser.get_sql_hints(chooser.ruleChains[0].subject, zoom)[1] + ")"
                sql = sql.split('"')
                sq = ""
                odd = True
                for i in sql:
                    if not odd:
                        sq += escape_sql_column(i)
                    else:
                        sq += i
                    odd = not odd

                chooser_entry["sql"] = sq
                chooser_entry["style"] = styles
                fonts.add(styles.get("font-family", libkomapnik.default_font_family))

                chooser_entry["rule"] = [i.conditions for i in chooser.ruleChains if i.test_zoom(zoom)]
                numerics.update(chooser.get_numerics())
                # print chooser_entry["rule"]
                chooser_entry["rulestring"] = " or ".join(["(" + " and ".join([i.get_mapnik_filter() for i in rule if i.get_mapnik_filter()]) + ")" for rule in chooser_entry["rule"]])
                chooser_entry["chooser"] = chooser
                for ttype in ttypes:
                    if ttype == "ele":
                        demhack = True
                    if ttype == "area" and "[natural] = 'coastline'" in chooser_entry["rulestring"]:
                        coast[zoom] = chooser_entry["style"]
                    else:
                        che = chooser_entry.copy()
                        che["type"] = ttype
                        zsheet[zindex].append(che)

    # sys.stderr.write(str(numerics)+"\n")
    # print mapniksheet

    def add_numerics_to_itags(itags, escape=True):
        tt = set()
        nitags = set()
        if escape:
            escape = escape_sql_column
        else:
            def escape(i, asname=False):
                if i in mapped_cols:
                    return i  # already escaped
                return '"' + i + '"'
        for i in itags:
            if i in numerics:
                tt.add("""(CASE WHEN %s ~ E'^[[:digit:]]+([.][[:digit:]]+)?$' THEN CAST (%s AS FLOAT) ELSE NULL END) as %s__num""" % (escape(i), escape(i), i))
            nitags.add(escape(i, asname=True))
        itags = nitags
        itags.update(tt)
        return itags

    bgcolor = style.get_style("canvas", {}, options.maxzoom + 1)[0].get("fill-color", "")
    opacity = style.get_style("canvas", {}, options.maxzoom + 1)[0].get("opacity", 1)
    hshack = style.get_style("canvas", {}, options.maxzoom + 1)[0].get("-x-kot-hs-hack", False)

    if (opacity == 1) and bgcolor:
        mfile.write(xml_start(bgcolor))
    else:
        mfile.write(xml_start("transparent"))

    conf_full_layering = style.get_style("canvas", {}, options.maxzoom + 1)[0].get("-x-kot-true-layers", "true").lower() == 'true'

    for font in fonts:
        mfile.write(xml_fontset(font, True))

    for zoom, zsheet in mapniksheet.iteritems():
        x_scale = xml_scaledenominator(zoom)
        ta = zsheet.keys()
        ta.sort(key=float)
        demcolors = {}
        demramp = {"ground": "", "ocean": ""}

        if demhack:
            for zindex in ta:
                for entry in zsheet[zindex]:
                    if entry["type"] in ("ele",):
                        ele = int(entry["rule"][0][0].params[0])
                        demcolors[ele] = (whatever_to_hex(entry["style"].get('fill-color', '#ffffff')), entry["style"].get('fill-opacity', '1'))
            dk = demcolors.keys()
            dk.sort()
            for ele in dk:
                (color, opacity) = demcolors[ele]
                demramp["ocean"] += '<stop value="%s"  color="rgba(%s,%s,%s,%s)"/>' % (ele + 10701, int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), opacity)
                demramp["ground"] += '<stop value="%s"  color="rgba(%s,%s,%s,%s)"/>' % (ele, int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16), opacity)

        if demhack and zoom >= 7:
            xml = xml_cleantopo(zoom, x_scale, demramp["ocean"])
            mfile.write(xml)
        if zoom in coast:
            xml = xml_style_start()
            xml += xml_rule_start()
            xml += x_scale
            if "fill-color" in coast[zoom]:
                xml += xml_polygonsymbolizer(coast[zoom].get("fill-color", "#ffffff"), relaxedFloat(coast[zoom].get("fill-opacity", "1")), relaxedFloat(coast[zoom].get("smooth", "0")))
            if "fill-image" in coast[zoom]:
                xml += xml_polygonpatternsymbolizer(coast[zoom].get("fill-image", ""))
            xml += xml_rule_end()
            xml += xml_style_end()
            xml += xml_layer("coast", zoom=zoom)
            mfile.write(xml)

        if demhack and zoom < 7:
            xml = xml_cleantopo(zoom, x_scale, demramp["ocean"])
            mfile.write(xml)

        if demhack and zoom >= 7:
            xml = xml_srtm(zoom, x_scale, demramp["ground"])
            mfile.write(xml)

        sql_g = set()
        there_are_dashed_lines = False
        itags_g = set()
        xml_g = ""
        for zindex in ta:
            ## background areas pass
            sql = set()
            itags = set()
            xml = xml_style_start()
            for entry in zsheet[zindex]:
                if entry["type"] in ("way", "area", "polygon"):
                    if ("fill-color" in entry["style"] or "fill-image" in entry["style"]) and (entry["style"].get("fill-position", "foreground") == "background"):
                        xml += xml_rule_start()
                        xml += x_scale
                        xml += xml_filter(entry["rulestring"])
                        if "fill-color" in entry["style"]:
                            xml += xml_polygonsymbolizer(entry["style"].get("fill-color", "black"), relaxedFloat(entry["style"].get("fill-opacity", "1")), relaxedFloat(entry["style"].get("smooth", "0")))
                        if "fill-image" in entry["style"]:
                            xml += xml_polygonpatternsymbolizer(entry["style"].get("fill-image", ""))
                        sql.add(entry["sql"])
                        itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
                        xml += xml_rule_end()
            xml += xml_style_end()
            sql.discard("()")
            if sql:
                sql_g.update(sql)
                xml_g += xml
                itags_g.update(itags)
            else:
                xml_nosubstyle()
        sql = sql_g
        itags = itags_g
        if sql:
            mfile.write(xml_g)
            sql = "(" + " OR ".join(sql) + ")"  # and way &amp;&amp; !bbox!"
            itags = add_numerics_to_itags(itags)
            mfile.write(xml_layer("postgis", "polygon", itags, sql, zoom=zoom))
        else:
            xml_nolayer()

        if hshack:
            xml = xml_hillshade(zoom, x_scale)
            mfile.write(xml)

        index_range = range(-6, 7)
        full_layering = conf_full_layering
        if (zoom < 9) or not conf_full_layering:
            index_range = (-6, 0, 6)
            full_layering = False

        def check_if_roads_table(rulestring):
            roads = set([
                        "[highway] = 'secondary'",
                        "[highway] = 'secondary_link'",
                        "[highway] = 'primary'",
                        "[highway] = 'primary_link'",
                        "[highway] = 'trunk'",
                        "[highway] = 'trunk_link'",
                        "[highway] = 'motorway'",
                        "[highway] = 'motorway_link'",
                        "[boundary] = 'administrative'",
                        "[railway] "
                        ])
            for a in rulestring.split(') or ('):
                for r in roads:
                    if r not in a:
                        return False
            return True
        for zlayer in index_range:
            for layer_type, entry_types in [("line", ("way", "line")), ("polygon", ("way", "area"))]:
                sql_g = set()
                there_are_dashed_lines = False
                itags_g = set()
                xml_g = ""
                roads = (layer_type == 'line')  # whether to use planet_osm_roads
                ## casings pass
                for zindex in ta:
                    sql = set()
                    itags = set()
                    xml = xml_style_start()
                    for entry in zsheet[zindex]:
                        if entry["type"] in entry_types:
                            if "-x-kot-layer" in entry["style"]:
                                if zlayer != -6 and entry["style"]["-x-kot-layer"] == "bottom":
                                    continue
                                if zlayer != 6 and entry["style"]["-x-kot-layer"] == "top":
                                    continue
                            elif zlayer not in range(-5, 6):
                                continue
                            if "casing-width" in entry["style"]:
                                xml += xml_rule_start()
                                xml += x_scale
                                xml += xml_filter(entry["rulestring"])
                                if not check_if_roads_table(entry["rulestring"]):
                                    roads = False
                                twidth = 2 * float(entry["style"].get("casing-width", 1)) + float(entry["style"].get("width", 0))
                                tlinejoin = "round"
                                if twidth < 3:
                                    tlinejoin = "miter"
                                xml += xml_linesymbolizer(color=entry["style"].get("casing-color", "black"),
                                                          width=twidth,
                                                          opacity=relaxedFloat(entry["style"].get("casing-opacity", entry["style"].get("opacity", "1"))),
                                                          linecap=entry["style"].get("casing-linecap", entry["style"].get("linecap", "butt")),
                                                          linejoin=entry["style"].get("casing-linejoin", entry["style"].get("linejoin", "round")),
                                                          dashes=entry["style"].get("casing-dashes", entry["style"].get("dashes", "")),
                                                          smooth=relaxedFloat(entry["style"].get("smooth", "0")),
                                                          zoom=zoom)

                                sql.add(entry["sql"])
                                itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
                                xml += xml_rule_end()

                    xml += xml_style_end()
                    sql.discard("()")
                    if sql:
                        sql_g.update(sql)
                        xml_g += xml
                        itags_g.update(itags)
                    else:
                        xml_nosubstyle()

                sql = sql_g
                itags = itags_g
                if sql:
                    mfile.write(xml_g)
                    sql = "(" + " OR ".join(sql) + ")"  # and way &amp;&amp; !bbox!"
                    if zlayer == 0 and full_layering:
                        sql = "(" + sql + ') and ("layer" not in (' + ", ".join(['\'%s\'' % i for i in range(-5, 6) if i != 0]) + ") or \"layer\" is NULL)"
                    elif zlayer <= 5 and zlayer >= -5 and full_layering:
                        sql = "(" + sql + ') and "layer" = \'%s\'' % zlayer
                    itags = add_numerics_to_itags(itags)
                    if roads:
                        layer_type = 'roads'
                    mfile.write(xml_layer("postgis", layer_type, itags, sql, zoom=zoom))
                else:
                    xml_nolayer()

            for zindex in ta:
                for layer_type, entry_types in [("line", ("way", "line")), ("polygon", ("way", "area"))]:
                    ## lines and polygons pass
                    sql_g = set()
                    there_are_dashed_lines = False
                    there_are_line_patterns = False
                    itags_g = set()
                    roads = (layer_type == 'line')  # whether to use planet_osm_roads
                    xml_g = ""

                    sql = set()
                    itags = set()
                    xml = xml_style_start()
                    for entry in zsheet[zindex]:
                        if entry["type"] in entry_types:
                            if "-x-kot-layer" in entry["style"]:
                                if zlayer != -6 and entry["style"]["-x-kot-layer"] == "bottom":
                                    continue
                                if zlayer != 6 and entry["style"]["-x-kot-layer"] == "top":
                                    continue
                            elif zlayer not in range(-5, 6):
                                continue
                            if "width" in entry["style"] or "pattern-image" in entry["style"] or (("fill-color" in entry["style"] or "fill-image" in entry["style"]) and (layer_type == "polygon") and (entry["style"].get("fill-position", "foreground") == "foreground")):
                                xml += xml_rule_start()
                                xml += x_scale
                                xml += xml_filter(entry["rulestring"])
                                if not check_if_roads_table(entry["rulestring"]):
                                    roads = False
                                if layer_type == "polygon" and (entry["style"].get("fill-position", "foreground") == "foreground"):
                                    if "fill-color" in entry["style"]:
                                        xml += xml_polygonsymbolizer(entry["style"].get("fill-color", "black"), relaxedFloat(entry["style"].get("fill-opacity", "1")), relaxedFloat(entry["style"].get("smooth", "0")))
                                    if "fill-image" in entry["style"]:
                                        xml += xml_polygonpatternsymbolizer(entry["style"].get("fill-image", ""))
                                if "width" in entry["style"]:
                                    twidth = relaxedFloat(entry["style"].get("width", "1"))

                                    # linejoins are round, but for thin roads they're miter
                                    tlinejoin = "round"
                                    if twidth <= 2:
                                        tlinejoin = "miter"
                                    tlinejoin = entry["style"].get("linejoin", tlinejoin)

                                    # linecaps are round for roads, and butts for roads on non-default layer=
                                    tlinecap = "round"
                                    if zlayer != 0:
                                        tlinecap = "butt"
                                    tlinecap = entry["style"].get("linecap", tlinecap)

                                    xml += xml_linesymbolizer(color=entry["style"].get("color", "black"),
                                                              width=twidth,
                                                              opacity=relaxedFloat(entry["style"].get("opacity", "1")),
                                                              linecap=tlinecap,
                                                              linejoin=tlinejoin,
                                                              dashes=entry["style"].get("dashes", ""),
                                                              smooth=relaxedFloat(entry["style"].get("smooth", "0")),
                                                              zoom=zoom)
                                    if entry["style"].get("dashes", ""):
                                        there_are_dashed_lines = True
                                        # print "dashes!!!"
                                if "pattern-image" in entry["style"]:
                                    there_are_line_patterns = True
                                    if entry["style"]["pattern-image"] == "arrows":
                                        xml += xml_hardcoded_arrows()
                                    else:
                                        if "pattern-rotate" in entry["style"] or "pattern-spacing" in entry["style"]:
                                            fname = entry["style"]["pattern-image"]
                                            try:
                                                im = Image.open(icons_path + fname).convert("RGBA")
                                                fname = "f" + fname
                                                if "pattern-rotate" in entry["style"]:
                                                    im = im.rotate(relaxedFloat(entry["style"]["pattern-rotate"]))
                                                    fname = "r" + str(relaxedFloat(entry["style"]["pattern-rotate"])) + fname
                                                if "pattern-scale" in entry["style"]:
                                                    sc = relaxedFloat(entry["style"]["pattern-scale"]) * 1.
                                                    ns = (max(int(round(im.size[0] * sc)), 1), max(int(round(im.size[1] * sc)), 1))
                                                    im = im.resize(ns, Image.BILINEAR)
                                                    fname = "z" + str(sc) + fname
                                                if "pattern-spacing" in entry["style"]:
                                                    im2 = Image.new("RGBA", (im.size[0] + int(relaxedFloat(entry["style"]["pattern-spacing"])), im.size[1]))
                                                    im2.paste(im, (0, 0))
                                                    im = im2
                                                    fname = "s" + str(int(relaxedFloat(entry["style"]["pattern-spacing"]))) + fname
                                                if not os.path.exists(icons_path + "komap/"):
                                                    os.makedirs(icons_path + "komap/")
                                                if not os.path.exists(icons_path + "komap/" + fname):
                                                    im.save(icons_path + "komap/" + fname, "PNG")
                                                xml += xml_linepatternsymbolizer("komap/" + fname)
                                            except:
                                                print >> sys.stderr, "Error writing to ", icons_path + "komap/" + fname
                                        else:
                                            if entry["style"].get("-x-kot-render", "none") == "svg":
                                                xml += xml_linemarkerssymbolizer(entry["style"]["pattern-image"], entry["style"].get("spacing","100"), entry["style"].get("allow-overlap","false"))
                                            else:
                                                xml += xml_linepatternsymbolizer(entry["style"]["pattern-image"])
                                sql.add(entry["sql"])
                                itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
                                xml += xml_rule_end()

                    xml += xml_style_end()
                    sql.discard("()")
                    if sql:
                        sql_g.update(sql)
                        xml_g += xml
                        itags_g.update(itags)
                    else:
                        xml_nosubstyle()
                    sql = sql_g
                    itags = itags_g
                    if sql:
                        mfile.write(xml_g)
                        sql = "(" + " OR ".join(sql) + ")"  # and way &amp;&amp; !bbox!"
                        if zlayer == 0 and full_layering:
                            sql = "(" + sql + ') and ("layer" not in (' + ", ".join(['\'%s\'' % i for i in range(-5, 6) if i != 0]) + ") or \"layer\" is NULL)"
                        elif zlayer <= 5 and zlayer >= -5 and full_layering:
                            sql = "(" + sql + ') and "layer" = \'%s\'' % zlayer
                        oitags = itags
                        itags = add_numerics_to_itags(itags)
                        if layer_type == "polygon" and there_are_line_patterns:
                            itags = ", ".join(itags)
                            oitags = '"' + "\", \"".join(oitags) + '"'
                            sqlz = """SELECT %s, ST_ForceRHR(way) as way from %spolygon where (%s) and way &amp;&amp; !bbox! and ST_IsValid(way)""" % (itags, libkomapnik.table_prefix , sql)
                            mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom=zoom))

                        #### FIXME: Performance degrades painfully on large lines ST_Union. Gotta find workaround :(
                        # if layer_type == "polygon" and there_are_dashed_lines:
                            # itags = ", ".join(itags)
                            # oitags = '"'+ "\", \"".join(oitags) +'"'
                            # sqlz = """select %s, ST_LineMerge(ST_Union(way)) as way from
                                            #(SELECT %s, ST_Boundary(way) as way from planet_osm_polygon where (%s) and way &amp;&amp; !bbox! and ST_IsValid(way)  ) tex
                                # group by %s
                                #"""%(itags,oitags,sql,oitags)
                        elif layer_type == "line" and there_are_dashed_lines and zoom < 10:
                            itags = ", ".join(itags)  # FIXME: wrong when working with hstore
                            oitags = '"' + "\", \"".join(oitags) + '"'
                            sqlz = """select %s, ST_LineMerge(ST_Union(way)) as way from (SELECT %s, ST_SnapToGrid(way, %s) as way from %sline where way &amp;&amp; !bbox! and (%s)) as tex
                            group by %s
                            """ % (oitags, itags, pixel_size_at_zoom(zoom, 1.5), libkomapnik.table_prefix, sql, oitags)
                            mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom=zoom))
                        else:
                            if roads:
                                layer_type = 'roads'
                            mfile.write(xml_layer("postgis", layer_type, itags, sql, zoom=zoom))
                    else:
                        xml_nolayer()

        if not options.bgonly:
            ## icons pass
            sql_g = set()
            itags_g = set()
            xml_g = ""
            prevtype = ""
            for zindex in ta:
                for layer_type, entry_types in [("point", ("node", "point")), ("line", ("way", "line")), ("polygon", ("way", "area"))]:
                    sql = set()
                    itags = set()
                    style_started = False
                    for entry in zsheet[zindex]:
                        if entry["type"] in entry_types:
                            if "icon-image" in entry["style"]:
                                if not prevtype:
                                    prevtype = layer_type
                                if prevtype != layer_type:
                                    if sql_g:
                                        mfile.write(xml_g)
                                        sql_g = "(" + " OR ".join(sql_g) + ")"  # and way &amp;&amp; !bbox!"
                                        itags_g = add_numerics_to_itags(itags_g)
                                        mfile.write(xml_layer("postgis", prevtype, itags_g, sql_g, zoom=zoom))
                                        sql_g = set()
                                        itags_g = set()
                                        xml_g = ""
                                        sql = set()
                                        itags = set()
                                    else:
                                        xml_nolayer()
                                    prevtype = layer_type
                                if not style_started:
                                    xml = xml_style_start()
                                    style_started = True
                                xml += xml_rule_start()
                                xml += x_scale
                                xml += xml_filter(entry["rulestring"])
                                xml += xml_pointsymbolizer(
                                    path=entry["style"].get("icon-image", ""),
                                    width=entry["style"].get("icon-width", ""),
                                    height=entry["style"].get("icon-height", ""),
                                    opacity=relaxedFloat(entry["style"].get("opacity", "1")))
                                if ("text" in entry["style"] and entry["style"].get("text-position", "center") == 'center'):
                                    ttext = entry["style"]["text"].extract_tags().pop()
                                    sql.add("((" + entry["sql"] + ") and " + escape_sql_column(ttext) + " is NULL)")
                                    itags.add(ttext)
                                    if ttext in columnmap:
                                        itags.update(columnmap[ttext][1])
                                else:
                                    sql.add(entry["sql"])

                                itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
                                xml += xml_rule_end()
                    if style_started:
                        xml += xml_style_end()
                        style_started = False
                        sql.discard("()")
                        if sql:
                            sql_g.update(sql)
                            xml_g += xml
                            itags_g.update(itags)
                        else:
                            xml_nosubstyle()
            if sql_g:
                mfile.write(xml_g)
                sql_g = "(" + " OR ".join(sql_g) + ")"  # and way &amp;&amp; !bbox!"
                itags_g = add_numerics_to_itags(itags_g)
                mfile.write(xml_layer("postgis", prevtype, itags_g, sql_g, zoom=zoom))
            else:
                xml_nolayer()

            ta.reverse()
            for zindex in ta:
                for layer_type, entry_types in [("point", ("node", "point")), ("polygon", ("way", "area")), ("line", ("way", "line"))]:
                    for placement in ("center", "line"):
                        ## text pass
                        collhere = set()
                        for entry in zsheet[zindex]:
                            if entry["type"] in entry_types:  # , "node", "line", "point"):
                                if ("text" in entry["style"] or "shield-text" in entry["style"]) and entry["style"].get("text-position", "center") == placement:
                                    csb = entry["style"].get("collision-sort-by", None)
                                    cso = entry["style"].get("collision-sort-order", "desc")
                                    collhere.add((csb, cso))
                        for snap_to_street in ('true', 'false'):
                            for (csb, cso) in collhere:
                                sql = set()
                                itags = set()
                                texttags = set()
                                xml = xml_style_start()
                                for entry in zsheet[zindex]:
                                    if entry["type"] in entry_types and csb == entry["style"].get("collision-sort-by", None) and cso == entry["style"].get("collision-sort-order", "desc") and snap_to_street == entry["style"].get("-x-kot-snap-to-street", "false"):
                                        if "shield-text" in entry["style"] and "shield-image" in entry["style"]:
                                            ttext = entry["style"]["shield-text"].extract_tags().pop()
                                            texttags.add(ttext)
                                            tface = entry["style"].get("shield-font-family", libkomapnik.default_font_family)
                                            tsize = entry["style"].get("shield-font-size", "10")
                                            tcolor = entry["style"].get("shield-text-color", "#000000")
                                            toverlap = entry["style"].get("text-allow-overlap", entry["style"].get("allow-overlap", "false"))
                                            tdistance = relaxedFloat(entry["style"].get("-x-kot-min-distance", "20"))
                                            twrap = relaxedFloat(entry["style"].get("shield-max-width", 25))
                                            talign = entry["style"].get("shield-text-align", "center")
                                            topacity = relaxedFloat(entry["style"].get("shield-text-opacity", entry["style"].get("opacity", "1")))
                                            toffset = relaxedFloat(entry["style"].get("shield-text-offset", "0"))
                                            ttransform = entry["style"].get("shield-text-transform", "none")
                                            tspacing = entry["style"].get("shield-spacing", "500")
                                            xml += xml_rule_start()
                                            xml += x_scale

                                            xml += xml_filter(entry["rulestring"])

                                            xml += xml_shieldsymbolizer(
                                                entry["style"].get("shield-image", ""),
                                                "",
                                                "",
                                                ttext, tface, tsize, tcolor, "#000000", 0, "center",
                                                toffset, toverlap, tdistance, twrap, talign, topacity, ttransform, "false", tspacing)
                                            sql.add(entry["sql"])
                                            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
                                            xml += xml_rule_end()

                                        if "text" in entry["style"] and entry["style"].get("text-position", "center") == placement:
                                            ttext = entry["style"]["text"].extract_tags().pop()
                                            texttags.add(ttext)
                                            tface = entry["style"].get("font-family", libkomapnik.default_font_family)
                                            tsize = entry["style"].get("font-size", "10")
                                            tcolor = entry["style"].get("text-color", "#000000")
                                            thcolor = entry["style"].get("text-halo-color", "#ffffff")
                                            thradius = relaxedFloat(entry["style"].get("text-halo-radius", "0"))
                                            tplace = entry["style"].get("text-position", "center")
                                            toffset = relaxedFloat(entry["style"].get("text-offset", "0"))
                                            toverlap = entry["style"].get("text-allow-overlap", entry["style"].get("allow-overlap", "false"))
                                            tdistance = relaxedFloat(entry["style"].get("-x-kot-min-distance", "20"))
                                            twrap = relaxedFloat(entry["style"].get("max-width", 256))
                                            talign = entry["style"].get("text-align", "center")
                                            topacity = relaxedFloat(entry["style"].get("text-opacity", entry["style"].get("opacity", "1")))
                                            tpos = entry["style"].get("text-placement", "X")
                                            ttransform = entry["style"].get("text-transform", "none")
                                            tspacing = entry["style"].get("text-spacing", "4096")
                                            tangle = entry["style"].get("-x-kot-text-angle", libkomapnik.max_char_angle_delta)
                                            tcharspacing = entry["style"].get("-x-kot-font-tracking", libkomapnik.font_tracking)

                                            xml += xml_rule_start()
                                            xml += x_scale

                                            xml += xml_filter(entry["rulestring"])
                                            if "icon-image" in entry["style"] and entry["style"].get("text-position", "center") == 'center':
                                                xml += xml_shieldsymbolizer(
                                                    entry["style"].get("icon-image", ""),
                                                    entry["style"].get("icon-width", ""),
                                                    entry["style"].get("icon-height", ""),
                                                    ttext, tface, tsize, tcolor, thcolor, thradius, tplace,
                                                    toffset, toverlap, tdistance, twrap, talign, topacity, ttransform)
                                            else:
                                                xml += xml_textsymbolizer(ttext, tface, tsize, tcolor, thcolor, thradius, tcharspacing, tplace, toffset, toverlap, tdistance, twrap, talign, topacity, tpos, ttransform, tspacing, tangle)
                                            sql.add(entry["sql"])
                                            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
                                            xml += xml_rule_end()

                                xml += xml_style_end()
                                sql.discard("()")
                                if sql:
                                    order = ""
                                    if csb:
                                        if cso != "desc":
                                            cso = "asc"
                                        itags.add(csb)
                                        order = """ order by (CASE WHEN "%s" ~ E'^[[:digit:]]+([.][[:digit:]]+)?$' THEN to_char(CAST ("%s" AS FLOAT) ,'000000000000000.99999999999') else "%s" end) %s nulls last """ % (csb, csb, csb, cso)

                                    mfile.write(xml)

                                    add_tags = set()
                                    for t in itags:
                                        if t in columnmap:
                                            add_tags.update(columnmap[t][1])
                                            texttags.update(columnmap[t][1])

                                    oitags = itags.union(add_tags)  # SELECT: (tags->'mooring') as "mooring"
                                    oitags = ", ".join([escape_sql_column(i, asname=True) for i in oitags])

                                    goitags = itags.union(add_tags)  # GROUP BY: (tags->'mooring')
                                    goitags = ", ".join([escape_sql_column(i) for i in goitags])

                                    fitags = [columnmap.get(i, (i,))[0] for i in itags]

                                    # fitags = add_numerics_to_itags(itags)
                                    itags = add_numerics_to_itags(fitags)  # population => {population, population__num}
                                    neitags = add_numerics_to_itags(fitags, escape=False)  # for complex polygons, no escapng needed
                                    del fitags

                                    ttext = " OR ".join([escape_sql_column(i) + " is not NULL" for i in texttags])

                                    if placement == "center" and layer_type == "polygon" and snap_to_street == 'false':
                                        sqlz = " OR ".join(sql)
                                        itags = ", ".join(itags)
                                        neitags = ", ".join(neitags)
                                        if not order:
                                            order = "order by"
                                        else:
                                            order += ", "
                                        if zoom > 11 or zoom < 6:
                                            sqlz = """select %s, way
                                                  from %s%s
                                                  where (%s) and (%s) and (way_area > %s) and way &amp;&amp; ST_Expand(!bbox!,3000) %s way_area desc
                                          """ % (itags, libkomapnik.table_prefix, layer_type, ttext, sqlz, pixel_size_at_zoom(zoom, 3) ** 2, order)
                                        else:
                                            sqlz = """select %s, way
                                          from (
                                            select (ST_Dump(ST_Multi(ST_Buffer(ST_Simplify(ST_Collect(p.way),%s),%s)))).geom as way, %s
                                              from (
                                                select *
                                                  from %s%s p
                                                  where (%s) and way_area > %s and p.way &amp;&amp; ST_Expand(!bbox!,%s) and (%s)) p
                                                group by %s) p %s ST_Area(p.way) desc
                                          """ % (neitags, pixel_size_at_zoom(zoom, 9), pixel_size_at_zoom(zoom, 10), oitags,
                                                 libkomapnik.table_prefix, layer_type, ttext, pixel_size_at_zoom(zoom, 5) ** 2, max(pixel_size_at_zoom(zoom, 20), 3000), sqlz, goitags, order)

                                        mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom))
                                    elif layer_type == "line" and zoom < 16 and snap_to_street == 'false':
                                        sqlz = " OR ".join(sql)
                                        itags = ", ".join(itags)
                                        if not order:
                                            order = "order by"
                                        else:
                                            order += ", "
                                        # itags = "\""+ itags+"\""
                                        sqlz = """select * from (select %s, ST_Simplify(ST_LineMerge(ST_Union(way)),%s) as way from (SELECT * from %sline where way &amp;&amp; ST_Expand(!bbox!,%s) and (%s) and (%s)) as tex
                                        group by %s) p
                                        where ST_Length(p.way) > %s
                                        %s ST_Length(p.way) desc
                                        """ % (itags, pixel_size_at_zoom(zoom, 3), libkomapnik.table_prefix, max(pixel_size_at_zoom(zoom, 20), 3000), ttext, sqlz, goitags, pixel_size_at_zoom(zoom, 4), order)
                                        mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom=zoom))

                                    elif snap_to_street == 'true':
                                        sqlz = " OR ".join(sql)
                                        itags = ", ".join(itags)

                                        sqlz = """select %s,

                                        coalesce(
                                          (select
                                            ST_Intersection(
                                              ST_Translate(
                                                ST_Rotate(
                                                  ST_GeomFromEWKT('SRID=%s;LINESTRING(-50 0, 50 0)'),
                                                  -1*ST_Azimuth(ST_PointN(ST_ShortestLine(l.way, ST_PointOnSurface(ST_Buffer(h.way,0.1))),1),
                                                                ST_PointN(ST_ShortestLine(l.way, ST_PointOnSurface(ST_Buffer(h.way,0.1))),2)
                                                              )
                                                ),
                                                ST_X(ST_PointOnSurface(ST_Buffer(h.way,0.1))),
                                                ST_Y(ST_PointOnSurface(ST_Buffer(h.way,0.1)))
                                              ),
                                              ST_Buffer(h.way,20)
                                            )
                                            as way
                                            from %sline l
                                            where
                                              l.way &amp;&amp; ST_Expand(h.way, 600) and
                                              ST_IsValid(l.way) and
                                              l."name" = h."addr:street" and
                                              l.highway is not NULL and
                                              l."name" is not NULL
                                            order by ST_Distance(ST_PointOnSurface(ST_Buffer(h.way,0.1)), l.way) asc
                                            limit 1
                                          ),
                                          (select
                                            ST_Intersection(
                                              ST_Translate(
                                                ST_Rotate(
                                                  ST_GeomFromEWKT('SRID=%s;LINESTRING(-50 0, 50 0)'),
                                                  -1*ST_Azimuth(ST_PointN(ST_ShortestLine(ST_Centroid(l.way), ST_PointOnSurface(ST_Buffer(h.way,0.1))),1),
                                                                ST_PointN(ST_ShortestLine(ST_Centroid(l.way), ST_PointOnSurface(ST_Buffer(h.way,0.1))),2)
                                                              )
                                                ),
                                                ST_X(ST_PointOnSurface(ST_Buffer(h.way,0.1))),
                                                ST_Y(ST_PointOnSurface(ST_Buffer(h.way,0.1)))
                                              ),
                                              ST_Buffer(h.way,20)
                                            )
                                            as way
                                            from %spolygon l
                                            where
                                              l.way &amp;&amp; ST_Expand(h.way, 600) and
                                              ST_IsValid(l.way) and
                                              l."name" = h."addr:street" and
                                              l.highway is not NULL and
                                              l."name" is not NULL
                                            order by ST_Distance(ST_PointOnSurface(ST_Buffer(h.way,0.1)), l.way) asc
                                            limit 1
                                          ),
                                          ST_Intersection(
                                            ST_MakeLine(  ST_Translate(ST_PointOnSurface(ST_Buffer(h.way,0.1)),-50,0),
                                                          ST_Translate(ST_PointOnSurface(ST_Buffer(h.way,0.1)), 50,0)
                                            ),
                                            ST_Buffer(h.way,20)
                                          )
                                        ) as way

                                                from %s%s h
                                                where (%s) and (%s) and way &amp;&amp; ST_Expand(!bbox!,3000) %s
                                        """ % (itags, libkomapnik.db_srid,  libkomapnik.table_prefix, libkomapnik.db_srid,  libkomapnik.table_prefix, libkomapnik.table_prefix, layer_type, ttext, sqlz, order)
                                        mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom))

                                    else:
                                        sql = "(" + " OR ".join(sql) + ")  %s" % (order)  # and way &amp;&amp; ST_Expand(!bbox!,%s), max(pixel_size_at_zoom(zoom,20),3000),
                                        mfile.write(xml_layer("postgis", layer_type, itags, sql, zoom=zoom))
                                else:
                                    xml_nolayer()

    mfile.write(xml_end())
