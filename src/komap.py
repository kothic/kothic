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
import sys
import os
import Image
from libkomapnik import *
from optparse import OptionParser

try:
  import psyco
  psyco.full()
except ImportError:
  pass


def relaxedFloat(x):
  try:
    return float(x) if int(float(x)) != float(x) else int(x)

  except ValueError:
    return float(str(x).replace(",", "."))

parser = OptionParser()
parser.add_option("-r", "--renderer", dest="renderer", default="mapnik",
    help="which renderer stylesheet to generate", metavar="ENGINE")
parser.add_option("-s", "--stylesheet", dest="filename",
    help="read MapCSS stylesheet from FILE", metavar="FILE")
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





(options, args) = parser.parse_args()
#print (options, args)

minzoom = options.minzoom
maxzoom = options.maxzoom+1
locale = options.locale


if options.outfile == "-":
  mfile = sys.stdout
else:
  mfile = open(options.outfile,"w")




osm2pgsql_avail_keys = {} # "column" : ["node", "way"]
if options.osm2pgsqlstyle != "-":
  mf = open(options.osm2pgsqlstyle, "r")
  for line in mf:
    line = line.strip().split()
    if line and line[0][0] != "#":
      osm2pgsql_avail_keys[line[1]] = tuple(line[0].split(","))


def escape_sql_column(name, type="way", asname = False):
  if name in mapped_cols:
    return name # already escaped
  name = name.strip().strip('"')
  type = {'line':'way', 'area':'way'}.get(type,type)
  if type in osm2pgsql_avail_keys.get(name, ()) or not osm2pgsql_avail_keys:
    return '"'+name+'"'
  elif not asname:
    return "(tags->'"+name+"')"
  else:
    return "(tags->'"+name+"') as \"" +name+'"'







style = MapCSS(minzoom, maxzoom)     #zoom levels
style.parse(open(options.filename,"r").read())

if options.renderer == "js":
  subjs = {"canvas": ("canvas",),"way": ("Polygon","LineString"), "line":("Polygon","LineString"), "area": ("Polygon",), "node": ("Point",), "*":("Point","Polygon","LineString") }
  mfile.write("function restyle (prop, zoom, type){")
  mfile.write("style = new Object;")
  mfile.write('style["default"] = new Object;')
  for chooser in style.choosers:
    condition = ""
    subclass = "default"
    for i in chooser.ruleChains[0]:
        if condition:
          condition += "||"
        rule = " zoom >= %s && zoom <= %s"%(i.minZoom, i.maxZoom)
        for z in  i.conditions:
          t = z.type
          params = z.params
          if params[0] == "::class":
            subclass = params[1][2:]
            continue
          if rule:
            rule += " && "
          if t == 'eq':
            rule += 'prop["%s"] == "%s"'%(params[0], params[1])
          if t == 'ne':
            rule += 'prop["%s"] != "%s"'%(params[0], params[1])
          if t == 'regex':
            rule += 'prop["%s"].match(RegExp("%s"))'%(params[0], params[1])
          if t == 'true':
            rule += 'prop["%s"] == "yes"'%(params[0])
          if t == 'untrue':
            rule += 'prop["%s"] != "yes"'%(params[0])
          if t == 'set':
            rule += '"%s" in prop'%(params[0])
          if t == 'unset':
            rule += '!("%s"in prop)'%(params[0])
          if t == '<':
            rule += 'prop["%s"] < %s'%(params[0], params[1])
          if t == '<=':
            rule += 'prop["%s"] <= %s'%(params[0], params[1])
          if t == '>':
            rule += 'prop["%s"] > %s'%(params[0], params[1])
          if t == '>=':
            rule += 'prop["%s"] >= %s'%(params[0], params[1])
        if rule:
          rule = "&&" + rule
        condition += "(("+"||".join(['type == "%s"'%z for z in subjs[i.subject]])+") "+ rule + ")"
    #print chooser.styles
    styles = ""
    if subclass != "default":
      styles = 'if(!("%s" in style)){style["%s"] = new Object;}'%(subclass,subclass)
    for k, v in chooser.styles[0].iteritems():
      
      if type(v) == str:
        try:
          v = str(float(v))
          styles += 'style["'+subclass+'"]["'+k+'"] = '+v + ';'
        except:
          styles += 'style["'+subclass+'"]["'+k+'"] = "' + v + '";'

    mfile.write("if(%s) {%s};\n"%(condition,styles))
  mfile.write("return style;}")


if options.renderer == "mapnik":

  columnmap = {}

  if locale == "en":
    columnmap["name"] = ("""COALESCE("name:en","int_name", replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(translate("name",'абвгдезиклмнопрстуфьАБВГДЕЗИКЛМНОПРСТУФЬ','abvgdeziklmnoprstuf’ABVGDEZIKLMNOPRSTUF’'),'х','kh'),'Х','Kh'),'ц','ts'),'Ц','Ts'),'ч','ch'),'Ч','Ch'),'ш','sh'),'Ш','Sh'),'щ','shch'),'Щ','Shch'),'ъ','”'),'Ъ','”'),'ё','yo'),'Ё','Yo'),'ы','y'),'Ы','Y'),'э','·e'),'Э','E'),'ю','yu'),'Ю','Yu'),'й','y'),'Й','Y'),'я','ya'),'Я','Ya'),'ж','zh'),'Ж','Zh')) AS name""",('name:en','int_name',))
  elif locale == "be":
    columnmap["name"] =  ('COALESCE("name:be", "name:ru", "int_name", "name:en", "name") AS name',('name:be', "name:ru", "int_name", "name:en"))    
  elif locale:
    columnmap["name"] =  ('COALESCE("name:'+locale+'", "name") AS name',('name:'+locale,))
  mapped_cols = [i[0] for i in columnmap.values()]
  numerics = set()  # set of number-compared things, like "population<10000" needs population as number, not text
  mapniksheet = {}

  # {zoom: {z-index: [{sql:sql_hint, cond: mapnikfiltercondition, subject: subj, style: {a:b,c:d..}},{r2}...]...}...}
  coast = {}
  fonts = set()
  for zoom in range (minzoom, maxzoom):
    mapniksheet[zoom] = {}
    zsheet = mapniksheet[zoom]
    for chooser in style.choosers:
      if chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)[1]:
        #sys.stderr.write(str(chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)[1])+"\n")
        styles = chooser.styles[0]
        zindex = styles.get("z-index",0)
        if zindex not in zsheet:
          zsheet[zindex] = []
        chooser_entry = {}
        
        chooser_entry["type"] = chooser.ruleChains[0][0].subject
        
        sql = "("+ chooser.get_sql_hints(chooser.ruleChains[0][0].subject,zoom)[1] +")"
        sql = sql.split('"')
        sq = ""
        odd = True
        for i in sql:
          if not odd:
            sq += escape_sql_column(i, chooser_entry["type"])
          else:
            sq += i
          odd = not odd
        
        chooser_entry["sql"] = sq
        chooser_entry["style"] = styles
        fonts.add(styles.get("font-family","DejaVu Sans Book"))
        
        chooser_entry["rule"] = [i.conditions for i in chooser.ruleChains[0] if i.test_zoom(zoom)]
        numerics.update(chooser.get_numerics())
        #print chooser_entry["rule"]
        chooser_entry["rulestring"] = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule if i.get_mapnik_filter()]) + ")" for rule in chooser_entry["rule"]])
        chooser_entry["chooser"] = chooser
        if chooser_entry["type"] == "area" and "[natural] = 'coastline'" in chooser_entry["rulestring"]:
            coast[zoom] = chooser_entry["style"]
        else:
          zsheet[zindex].append(chooser_entry)





  #sys.stderr.write(str(numerics)+"\n")
  #print mapniksheet

  def add_numerics_to_itags(itags, escape = True):
    tt = set()
    nitags = set()
    if escape:
      escape = escape_sql_column
    else:
      escape = lambda i:'"'+i+'"'
    for i in itags:
      if i in numerics:
        tt.add("""(CASE WHEN %s ~ E'^[[:digit:]]+([.][[:digit:]]+)?$' THEN CAST (%s AS FLOAT) ELSE NULL END) as %s__num"""%(escape(i),escape(i),i))
      nitags.add(escape(i, asname = True))
    itags = nitags
    itags.update(tt)
    return itags



  bgcolor = style.get_style("canvas", {}, maxzoom)[0].get("fill-color", "")
  opacity = style.get_style("canvas", {}, maxzoom)[0].get("opacity", 1)
  demhack = style.get_style("canvas", {}, maxzoom)[0].get("-x-mapnik-dem-hack", False)

  if (opacity == 1) and bgcolor:
    mfile.write(xml_start(bgcolor))
  else:
    mfile.write(xml_start("transparent"))


  conf_full_layering = style.get_style("canvas", {}, maxzoom)[0].get("-x-mapnik-true-layers", "true").lower() == 'true'


  for font in fonts:
    mfile.write(xml_fontset(font, True))

  for zoom, zsheet in mapniksheet.iteritems():
    x_scale = xml_scaledenominator(zoom)
    ta = zsheet.keys()
    ta.sort(key=float)
    if demhack and zoom >= 7:
      xml="""
<Style name="elevation1z%s">
  <Rule>%s
    <RasterSymbolizer>
      <RasterColorizer default-mode="linear" epsilon="0.001">
        <stop value="701"  color="#98b7f5"/>
        <stop value="1701"  color="#9fbcf5"/>
        <stop value="2701"  color="#a6c1f5"/>
        <stop value="3701"  color="#abc4f5"/>
        <stop value="4701"  color="#b0c7f5"/>
        <stop value="5701"  color="#b5caf5"/>
        <stop value="6701"  color="#bacef5"/>
        <stop value="7701"  color="#bfd1f5"/>
        <stop value="8701"  color="#c4d4f5"/>
        <stop value="9701"  color="#c6d6f5"/>
        <stop value="10201"  color="#c9d7f5"/>
        <!--stop value="10501"  color="#cbd9f5"/-->
        <!-- stop value="10701"  color="cedbf5"/ -->
        <stop value="10502"  color="rgba(231, 209, 175, 0.1)"/>
        <!--stop value="10701" color="rgba(50, 180, 50, 0.0)"/ -->
        <stop value="10901"  color="rgba(231, 209, 175, 0.2)"/>
        <stop value="11201"  color="rgba(226, 203, 170, 0.2)"/>
        <stop value="11701" color="rgba(217, 194, 159, 0.3)"/>
        <stop value="12701" color="rgba(208, 184, 147, 0.4)"/>
        <stop value="13701" color="rgba(197, 172, 136, 0.5)"/>
        <stop value="14701" color="rgba(188, 158, 120, 0.55)"/>
        <stop value="15701" color="rgba(179, 139, 102, 0.6)"/>
        <stop value="16701" color="rgba(157, 121, 87, 0.7)"/>
        <stop value="17701" color="rgba(157, 121, 87, 0.8)"/>
        <stop value="18701" color="rgba(144, 109, 77, 0.9)"/>
     </RasterColorizer>
    </RasterSymbolizer>
  </Rule>
</Style>

<Layer name="ele-raster1z%s">
    <StyleName>elevation1z%s</StyleName>
    <Datasource>
        <Parameter name="file">/raid/srtm/Full/CleanTOPO2merc.tif</Parameter>
        <Parameter name="type">gdal</Parameter>
        <Parameter name="band">1</Parameter>
        <Parameter name="srid">4326</Parameter>
    </Datasource>
</Layer>
      """ 
      xml = xml%(zoom, x_scale, zoom, zoom)
      mfile.write(xml)
    if zoom in coast:
      xml = xml_style_start()
      xml += xml_rule_start()
      xml += x_scale
      if "fill-color" in coast[zoom]:
        xml += xml_polygonsymbolizer(coast[zoom].get("fill-color", "#ffffff"), relaxedFloat(coast[zoom].get("fill-opacity", "1")))
      if "fill-image" in coast[zoom]:
        xml += xml_polygonpatternsymbolizer(coast[zoom].get("fill-image", ""))
      xml += xml_rule_end()
      xml += xml_style_end()
      xml += xml_layer("coast", zoom=zoom)
      mfile.write(xml)
    
    if demhack and zoom < 7:
      xml="""
<Style name="elevationz%s">
  <Rule>%s
    <RasterSymbolizer>
      <RasterColorizer default-mode="linear" epsilon="0.001">
        <stop value="701"  color="#98b7f5"/>
        <stop value="1701"  color="#9fbcf5"/>
        <stop value="2701"  color="#a6c1f5"/>
        <stop value="3701"  color="#abc4f5"/>
        <stop value="4701"  color="#b0c7f5"/>
        <stop value="5701"  color="#b5caf5"/>
        <stop value="6701"  color="#bacef5"/>
        <stop value="7701"  color="#bfd1f5"/>
        <stop value="8701"  color="#c4d4f5"/>
        <stop value="9701"  color="#c6d6f5"/>
        <stop value="10201"  color="#c9d7f5"/>
        <!--stop value="10501"  color="#cbd9f5"/-->
        <!-- stop value="10701"  color="cedbf5"/ -->
        <stop value="10502"  color="rgba(231, 209, 175, 0.1)"/>
        <!--stop value="10701" color="rgba(50, 180, 50, 0.0)"/ -->
        <stop value="10901"  color="rgba(231, 209, 175, 0.2)"/>
        <stop value="11201"  color="rgba(226, 203, 170, 0.2)"/>
        <stop value="11701" color="rgba(217, 194, 159, 0.3)"/>
        <stop value="12701" color="rgba(208, 184, 147, 0.4)"/>
        <stop value="13701" color="rgba(197, 172, 136, 0.5)"/>
        <stop value="14701" color="rgba(188, 158, 120, 0.55)"/>
        <stop value="15701" color="rgba(179, 139, 102, 0.6)"/>
        <stop value="16701" color="rgba(157, 121, 87, 0.7)"/>
        <stop value="17701" color="rgba(157, 121, 87, 0.8)"/>
        <stop value="18701" color="rgba(144, 109, 77, 0.9)"/>
     </RasterColorizer>
    </RasterSymbolizer>
  </Rule>
</Style>

<Layer name="ele-rasterz%s">
    <StyleName>elevationz%s</StyleName>
    <Datasource>
        <Parameter name="file">/raid/srtm/Full/CleanTOPO2merc.tif</Parameter>
        <Parameter name="type">gdal</Parameter>
        <Parameter name="band">1</Parameter>
        <Parameter name="srid">4326</Parameter>
    </Datasource>
</Layer>
      """ 
      xml = xml%(zoom, x_scale, zoom, zoom)
      mfile.write(xml)

    
    if demhack and zoom >= 7:
      xml="""
<Style name="elevationz%s">
  <Rule>%s
    <RasterSymbolizer>
      <RasterColorizer default-mode="linear" epsilon="0.001">
        <stop value="-100"  color="rgba(231, 209, 175, 0.1)"/>
        <stop value="200"  color="rgba(231, 209, 175, 0.2)"/>
        <stop value="500"  color="rgba(226, 203, 170, 0.2)"/>
        <stop value="1000" color="rgba(217, 194, 159, 0.3)"/>
        <stop value="2000" color="rgba(208, 184, 147, 0.4)"/>
        <stop value="3000" color="rgba(197, 172, 136, 0.5)"/>
        <stop value="4000" color="rgba(188, 158, 120, 0.55)"/>
        <stop value="5000" color="rgba(179, 139, 102, 0.6)"/>
        <stop value="6000" color="rgba(157, 121, 87, 0.7)"/>
        <stop value="7000" color="rgba(157, 121, 87, 0.8)"/>
        <stop value="8000" color="rgba(144, 109, 77, 0.9)"/>
     </RasterColorizer>
    </RasterSymbolizer>
  </Rule>
</Style>

<Layer name="ele-rasterz%s">
    <StyleName>elevationz%s</StyleName>
    <Datasource>
        <Parameter name="file">/raid/srtm/srtmm.vrt</Parameter>
        <Parameter name="type">gdal</Parameter>
        <Parameter name="band">1</Parameter>
        <Parameter name="srid">4326</Parameter>
    </Datasource>
</Layer>
      """ 
      xml = xml%(zoom, x_scale, zoom, zoom)
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
          if "background-color" in entry["style"] or "background-image" in entry["style"]:
            xml += xml_rule_start()
            xml += x_scale

            xml += xml_filter(entry["rulestring"])
            if "background-color" in entry["style"]:
              xml += xml_polygonsymbolizer(entry["style"].get("background-color", "black"), entry["style"].get("background-opacity", "1"))
            if "background-image" in entry["style"]:
              xml += xml_polygonpatternsymbolizer(entry["style"].get("background-image", ""))
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
      sql = "(" + " OR ".join(sql) + ")"# and way &amp;&amp; !bbox!"
      itags = add_numerics_to_itags(itags)
      mfile.write(xml_layer("postgis", "polygon", itags, sql, zoom=zoom ))
    else:
      xml_nolayer()
    
    if demhack and zoom<6:
      xml = """
      <Style name="hillshadez%s">
  <Rule>
  %s
    <RasterSymbolizer opacity="1" scaling="bilinear" mode="multiply">
      <RasterColorizer  default-mode="linear">
        <stop value="0"   color="rgba(0,0,0,0.2)" />
        <stop value="255" color="rgba(255,255,255,0)" />
      </RasterColorizer>
    </RasterSymbolizer>
  </Rule>
</Style>
<Layer name="datarasterz%s"> 
    <StyleName>hillshadez%s</StyleName>
    <Datasource>
        <Parameter name="file">/raid/srtm/Full/CleanTOPO2merchs.tif</Parameter>
        <Parameter name="type">gdal</Parameter>
        <Parameter name="band">1</Parameter>
    </Datasource>
</Layer>
      """
      xml = xml%(zoom, x_scale, zoom, zoom)
      mfile.write(xml)
    
    index_range = range(-6,7)
    full_layering = conf_full_layering
    if (zoom < 9) or not conf_full_layering :
      index_range = (-6,0,6)
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
      for r in roads:
        if r in rulestring:
          return True
      return False
    for zlayer in index_range:
      for layer_type, entry_types in [("line",("way", "line")),("polygon",("way","area"))]:
        sql_g = set()
        there_are_dashed_lines = False
        itags_g = set()
        xml_g = ""
        roads = (layer_type == 'line') and (zoom < 9) # whether to use planet_osm_roads
        ## casings pass
        for zindex in ta:
          sql = set()
          itags = set()
          xml = xml_style_start()
          for entry in zsheet[zindex]:
            if entry["type"] in entry_types:
              if "-x-mapnik-layer" in entry["style"]:
                if zlayer != -6 and entry["style"]["-x-mapnik-layer"] == "bottom":
                  continue
                if zlayer != 6 and entry["style"]["-x-mapnik-layer"] == "top":
                  continue
              elif zlayer not in range(-5,6):
                continue
              if "casing-width" in entry["style"]:
                xml += xml_rule_start()
                xml += x_scale
                xml += xml_filter(entry["rulestring"])
                if not check_if_roads_table(entry["rulestring"]):
                  roads = False
                twidth = 2*float(entry["style"].get("casing-width", 1))+float(entry["style"].get("width", 0));
                tlinejoin = "round"
                if twidth < 3:
                  tlinejoin = "miter"
                xml += xml_linesymbolizer(color=entry["style"].get("casing-color", "black"),
                  width=twidth,
                  opacity=relaxedFloat(entry["style"].get("casing-opacity", entry["style"].get("opacity","1"))),
                  linecap=entry["style"].get("casing-linecap", entry["style"].get("linecap","butt")),
                  linejoin=entry["style"].get("casing-linejoin", entry["style"].get("linejoin", "round")),
                  dashes=entry["style"].get("casing-dashes",entry["style"].get("dashes", "")),
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
          sql = "(" + " OR ".join(sql) + ")"# and way &amp;&amp; !bbox!"
          if zlayer == 0 and full_layering:
            sql = "("+ sql +') and ("layer" not in ('+ ", ".join(['\'%s\''%i for i in range(-5,6) if i != 0])+") or \"layer\" is NULL)"
          elif zlayer <=5 and zlayer >= -5 and full_layering:
            sql = "("+ sql +') and "layer" = \'%s\''%zlayer
          itags = add_numerics_to_itags(itags)
          if roads:
            layer_type = 'roads'
          mfile.write(xml_layer("postgis", layer_type, itags, sql, zoom=zoom ))
        else:
          xml_nolayer()

      for zindex in ta:
        for layer_type, entry_types in [("line",("way", "line")),("polygon",("way","area"))]:
          ## lines and polygons pass
          sql_g = set()
          there_are_dashed_lines = False
          there_are_line_patterns = False
          itags_g = set()
          roads = (layer_type == 'line') and (zoom < 9) # whether to use planet_osm_roads
          xml_g = ""
        
          sql = set()
          itags = set()
          xml = xml_style_start()
          for entry in zsheet[zindex]:
            if entry["type"] in entry_types:
              if "-x-mapnik-layer" in entry["style"]:
                if zlayer != -6 and entry["style"]["-x-mapnik-layer"] == "bottom":
                  continue
                if zlayer != 6 and entry["style"]["-x-mapnik-layer"] == "top":
                  continue
              elif zlayer not in range(-5,6):
                continue
              if "width" in entry["style"] or "pattern-image" in entry["style"] or (("fill-color" in entry["style"] or "fill-image" in entry["style"]) and layer_type == "polygon"):
                xml += xml_rule_start()
                xml += x_scale
                xml += xml_filter(entry["rulestring"])
                if not check_if_roads_table(entry["rulestring"]):
                  roads = False
                if layer_type == "polygon":
                  if "fill-color" in entry["style"]:
                    xml += xml_polygonsymbolizer(entry["style"].get("fill-color", "black"), entry["style"].get("fill-opacity", "1"))
                  if "fill-image" in entry["style"]:
                    xml += xml_polygonpatternsymbolizer(entry["style"].get("fill-image", ""))
                if "width" in entry["style"]:
                  twidth = relaxedFloat(entry["style"].get("width", "1"))
                  tlinejoin = "round"
                  if twidth <= 2:
                    tlinejoin = "miter"
                  xml += xml_linesymbolizer(color=entry["style"].get("color", "black"),
                    width=twidth,
                    opacity=relaxedFloat(entry["style"].get("opacity", "1")),
                    linecap=entry["style"].get("linecap", "round"),
                    linejoin=entry["style"].get("linejoin", "round"),
                    dashes=entry["style"].get("dashes", ""),
                    zoom=zoom)
                  if entry["style"].get("dashes", ""):
                    there_are_dashed_lines = True
                    #print "dashes!!!"
                if "pattern-image" in entry["style"]:
                  there_are_line_patterns = True
                  if entry["style"]["pattern-image"] == "arrows":
                    xml += xml_hardcoded_arrows()
                  else:
                    if "pattern-rotate" in entry["style"] or "pattern-spacing" in entry["style"]:
                      fname = entry["style"]["pattern-image"]
                      im = Image.open(icons_path + fname).convert("RGBA")
                      fname = "f"+fname
                      if "pattern-rotate" in entry["style"]:
                        im = im.rotate(relaxedFloat(entry["style"]["pattern-rotate"]))
                        fname = "r"+str(relaxedFloat(entry["style"]["pattern-rotate"]))+fname
                      if "pattern-scale" in entry["style"]:
                        sc = relaxedFloat(entry["style"]["pattern-scale"])*1.
                        ns = (max(int(round(im.size[0]*sc)),1), max(int(round(im.size[1]*sc)),1))
                        im = im.resize(ns, Image.BILINEAR)
                        fname = "z"+str(sc)+fname
                      if "pattern-spacing" in entry["style"]:
                        im2 = Image.new("RGBA", (im.size[0]+int(relaxedFloat(entry["style"]["pattern-spacing"])),im.size[1]))
                        im2.paste(im,(0,0))
                        im = im2
                        fname = "s"+str(int(relaxedFloat(entry["style"]["pattern-spacing"])))+fname
                      try:
                        if not os.path.exists(icons_path+"komap/"):
                          os.makedirs(icons_path+"komap/")
                        if not os.path.exists(icons_path+"komap/"+fname):
                          im.save(icons_path+"komap/"+fname, "PNG")
                        xml += xml_linepatternsymbolizer("komap/"+fname)
                        
                      except OSError, IOError:
                        print >> sys.stderr, "Error writing to ", icons_path+"komap/"+fname
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
            sql = "(" + " OR ".join(sql) + ")"# and way &amp;&amp; !bbox!"
            if zlayer == 0 and full_layering:
              sql = "("+ sql +') and ("layer" not in ('+ ", ".join(['\'%s\''%i for i in range(-5,6) if i != 0])+") or \"layer\" is NULL)"
            elif zlayer <=5 and zlayer >= -5 and full_layering:
              sql = "("+ sql +') and "layer" = \'%s\''%zlayer
            oitags = itags
            itags = add_numerics_to_itags(itags)
            if layer_type == "polygon" and there_are_line_patterns:
              itags = ", ".join(itags)
              oitags = '"'+ "\", \"".join(oitags) +'"'
              sqlz = """SELECT %s, ST_ForceRHR(way) as way from planet_osm_polygon where (%s) and way &amp;&amp; !bbox! and ST_IsValid(way)"""%(itags,sql)
              mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom=zoom ))


            #### FIXME: Performance degrades painfully on large lines ST_Union. Gotta find workaround :(
            #if layer_type == "polygon" and there_are_dashed_lines:
              #itags = ", ".join(itags)
              #oitags = '"'+ "\", \"".join(oitags) +'"'
              #sqlz = """select %s, ST_LineMerge(ST_Union(way)) as way from
                              #(SELECT %s, ST_Boundary(way) as way from planet_osm_polygon where (%s) and way &amp;&amp; !bbox! and ST_IsValid(way)  ) tex
                #group by %s
                #"""%(itags,oitags,sql,oitags)
              ##elif layer_type == "line" and there_are_dashed_lines:
              ##  sqlz = """select %s, ST_Union(way) as way from (SELECT * from planet_osm_line where way &amp;&amp; !bbox! #and (%s)) as tex
              ##  group by %s
              ##  """%(itags,sql,oitags)
              #mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom=zoom ))
            else:
              if roads:
                layer_type = 'roads'
              mfile.write(xml_layer("postgis", layer_type, itags, sql, zoom=zoom ))
          else:
            xml_nolayer()


    ## icons pass
    sql_g = set()
    itags_g = set()
    xml_g = ""
    prevtype = ""
    for zindex in ta:
      for layer_type, entry_types in [("point", ("node", "point")),("line",("way", "line")), ("polygon",("way","area"))]:
        sql = set()
        itags = set()
        style_started = False
        for entry in zsheet[zindex]:
          if entry["type"] in entry_types:
            if "icon-image" in entry["style"] and ("text" not in entry["style"] or ("text" in entry["style"] and entry["style"].get("text-position","center")!='center')):
              if not prevtype:
                prevtype = layer_type
              if prevtype != layer_type:
                if sql_g:
                  mfile.write(xml_g)
                  sql_g = "(" + " OR ".join(sql_g) + ")"# and way &amp;&amp; !bbox!"
                  itags_g = add_numerics_to_itags(itags_g)
                  mfile.write(xml_layer("postgis", prevtype, itags_g, sql_g, zoom=zoom ))
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
      sql_g = "(" + " OR ".join(sql_g) + ")"# and way &amp;&amp; !bbox!"
      itags_g = add_numerics_to_itags(itags_g)
      mfile.write(xml_layer("postgis", prevtype, itags_g, sql_g, zoom=zoom ))
    else:
      xml_nolayer()

    ta.reverse()
    for zindex in ta:
      for layer_type, entry_types in [ ("polygon",("way","area")),("point", ("node", "point")),("line",("way", "line"))]:
        for placement in ("center","line"):
          ## text pass
          collhere = set()
          for entry in zsheet[zindex]:
            if entry["type"] in entry_types:#, "node", "line", "point"):
              if "text" in entry["style"] and entry["style"].get("text-position","center")==placement:
                csb = entry["style"].get("collision-sort-by",None)
                cso = entry["style"].get("collision-sort-order","desc")
                collhere.add((csb,cso))
          for snap_to_street in ('true', 'false'):
            for (csb, cso) in collhere:
              sql = set()
              itags = set()
              texttags = set()
              xml = xml_style_start()
              for entry in zsheet[zindex]:
                if entry["type"] in entry_types and csb == entry["style"].get("collision-sort-by",None) and cso == entry["style"].get("collision-sort-order","desc") and snap_to_street == entry["style"].get("-x-mapnik-snap-to-street","false"):
                  if "text" in entry["style"] and entry["style"].get("text-position","center")==placement:
                    ttext = entry["style"]["text"].extract_tags().pop()
                    texttags.add(ttext)
                    tface = entry["style"].get("font-family","DejaVu Sans Book")
                    tsize = entry["style"].get("font-size","10")
                    tcolor = entry["style"].get("text-color","#000000")
                    thcolor= entry["style"].get("text-halo-color","#ffffff")
                    thradius= relaxedFloat(entry["style"].get("text-halo-radius","0"))
                    tplace= entry["style"].get("text-position","center")
                    toffset= relaxedFloat(entry["style"].get("text-offset","0"))
                    toverlap= entry["style"].get("text-allow-overlap",entry["style"].get("allow-overlap","false"))
                    tdistance= relaxedFloat(entry["style"].get("-x-mapnik-min-distance","20"))
                    twrap= relaxedFloat(entry["style"].get("max-width",256))
                    talign= entry["style"].get("text-align","center")
                    topacity= relaxedFloat(entry["style"].get("text-opacity",entry["style"].get("opacity","1")))
                    tpos = entry["style"].get("text-placement","X")
                    ttransform = entry["style"].get("text-transform","none")

                    xml += xml_rule_start()
                    xml += x_scale

                    xml += xml_filter(entry["rulestring"])
                    if "icon-image" in entry["style"] and entry["style"].get("text-position","center")=='center':
                      xml += xml_shieldsymbolizer(
                                  entry["style"].get("icon-image", ""),
                                  entry["style"].get("icon-width", ""),
                                  entry["style"].get("icon-height", ""),
                                  ttext,tface,tsize,tcolor, thcolor, thradius, tplace,
                                  toffset,toverlap,tdistance,twrap,talign,topacity, ttransform)
                    else:
                      xml += xml_textsymbolizer(ttext,tface,tsize,tcolor, thcolor, thradius, tplace, toffset,toverlap,tdistance,twrap,talign,topacity,tpos,ttransform)
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
                  order = """ order by (CASE WHEN "%s" ~ E'^[[:digit:]]+([.][[:digit:]]+)?$' THEN to_char(CAST ("%s" AS FLOAT) ,'000000000000000.99999999999') else "%s" end) %s nulls last """%(csb,csb,csb,cso)

                mfile.write(xml)

                add_tags = set()
                for t in itags:
                  if t in columnmap:
                    add_tags.update(columnmap[t][1])
                    texttags.update(columnmap[t][1])
                oitags = itags.union(add_tags)

                oitags = [ escape_sql_column(i) for i in oitags]
                oitags = ", ".join(oitags)

                ttext = " OR ".join(['"'+i+ "\" is not NULL " for i in texttags])
                itags = [columnmap.get(i, (i,))[0] for i in itags]
                itags = add_numerics_to_itags(itags, escape = False)
                if placement == "center" and layer_type == "polygon" and snap_to_street == 'false':
                  sqlz = " OR ".join(sql)
                  itags = ", ".join(itags)
                  if not order:
                    order = "order by"
                  else:
                    order += ", "
                  if zoom > 13 or zoom < 6:
                    sqlz = """select %s, way
                          from planet_osm_%s
                          where (%s) and (%s) and (way_area > %s) and way &amp;&amp; ST_Expand(!bbox!,3000) %s way_area desc
                  """%(itags,layer_type,ttext,sqlz,pixel_size_at_zoom(zoom,3)**2, order)
                  else:
                    sqlz = """select %s, way
                  from (
                    select (ST_Dump(ST_Multi(ST_Buffer(ST_Collect(p.way),0)))).geom as way, %s
                      from (
                        select ST_Buffer(way, %s) as way, %s
                          from planet_osm_%s p
                          where (%s) and way_area > %s and p.way &amp;&amp; ST_Expand(!bbox!,%s) and (%s)) p
                        group by %s) p %s ST_Area(p.way) desc
                  """%(itags,oitags,pixel_size_at_zoom(zoom,10),oitags,layer_type,ttext,pixel_size_at_zoom(zoom,5)**2,max(pixel_size_at_zoom(zoom,20),3000),sqlz,oitags,order)
                  mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom ))
                elif layer_type == "line" and zoom < 16 and snap_to_street == 'false':
                  sqlz = " OR ".join(sql)
                  itags = ", ".join(itags)
                  #itags = "\""+ itags+"\""
                  sqlz = """select %s, ST_LineMerge(ST_Union(way)) as way from (SELECT * from planet_osm_line where way &amp;&amp; ST_Expand(!bbox!,%s) and (%s) and (%s)) as tex
                  group by %s
                  %s
                  """%(itags,max(pixel_size_at_zoom(zoom,20),3000),ttext,sqlz,oitags,order)
                  mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom=zoom ))





                elif snap_to_street == 'true':
                  sqlz = " OR ".join(sql)
                  itags = ", ".join(itags)

                  sqlz = """select %s, 

                  coalesce(
                    (select
                      ST_Intersection(
                        ST_Translate(
                          ST_Rotate(
                            ST_GeomFromEWKT('SRID=900913;LINESTRING(-50 0, 50 0)'),
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
                      from planet_osm_line l 
                      where 
                        l.way &amp;&amp; ST_Expand(h.way, 600) and
                        ST_IsValid(l.way) and
                        l."name" = h."addr:street" and
                        l.highway is not NULL and
                        l."name" is not NULL
                      order by ST_Distance(ST_Buffer(h.way,0.1), l.way) asc
                      limit 1
                    ),
                    (select
                      ST_Intersection(
                        ST_Translate(
                          ST_Rotate(
                            ST_GeomFromEWKT('SRID=900913;LINESTRING(-50 0, 50 0)'),
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
                      from planet_osm_polygon l 
                      where 
                        l.way &amp;&amp; ST_Expand(h.way, 600) and
                        ST_IsValid(l.way) and
                        l."name" = h."addr:street" and
                        l.highway is not NULL and
                        l."name" is not NULL
                      order by ST_Distance(ST_Buffer(h.way,0.1), l.way) asc
                      limit 1
                    ),
                    ST_Intersection(
                      ST_MakeLine(  ST_Translate(ST_PointOnSurface(ST_Buffer(h.way,0.1)),-50,0),
                                    ST_Translate(ST_PointOnSurface(ST_Buffer(h.way,0.1)), 50,0)
                      ),
                      ST_Buffer(h.way,20)
                    )
                  ) as way

                          from planet_osm_%s h
                          where (%s) and (%s) and way &amp;&amp; ST_Expand(!bbox!,3000) %s
                  """%(itags,layer_type,ttext,sqlz, order)
                  mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz, zoom ))










                else:
                  sql = "(" + " OR ".join(sql) + ")  %s"%(order)#and way &amp;&amp; ST_Expand(!bbox!,%s), max(pixel_size_at_zoom(zoom,20),3000),
                  mfile.write(xml_layer("postgis", layer_type, itags, sql, zoom=zoom ))
              else:
                xml_nolayer()

  mfile.write(xml_end())