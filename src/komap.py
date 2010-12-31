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
from libkomapnik import *
from optparse import OptionParser

try:
        import psyco
        psyco.full()
except ImportError:
        pass


parser = OptionParser()
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

(options, args) = parser.parse_args()
#print (options, args)

minzoom = options.minzoom
maxzoom = options.maxzoom+1
locale = options.locale


if options.outfile == "-":
  mfile = sys.stdout
else:
  mfile = open(options.outfile,"w")


style = MapCSS(minzoom, maxzoom)     #zoom levels
style.parse(open(options.filename,"r").read())

columnmap = {}

if locale == "en":
  columnmap["name"] = ("""(CASE WHEN "name:en" IS NOT NULL THEN "name:en" ELSE CASE WHEN "int_name" IS NOT NULL THEN "int_name" ELSE replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(replace(translate("name",'абвгдезиклмнопрстуфьАБВГДЕЗИКЛМНОПРСТУФЬ','abvgdeziklmnoprstuf’ABVGDEZIKLMNOPRSTUF’'),'х','kh'),'Х','Kh'),'ц','ts'),'Ц','Ts'),'ч','ch'),'Ч','Ch'),'ш','sh'),'Ш','Sh'),'щ','shch'),'Щ','Shch'),'ъ','”'),'Ъ','”'),'ё','yo'),'Ё','Yo'),'ы','y'),'Ы','Y'),'э','·e'),'Э','E'),'ю','yu'),'Ю','Yu'),'й','y'),'Й','Y'),'я','ya'),'Я','Ya'),'ж','zh'),'Ж','Zh') END END) AS name""",('name:en','int_name',))
elif locale:
  columnmap["name"] =  ('(CASE WHEN "name:'+locale+'" IS NOT NULL THEN "name:'+locale+'" ELSE name END) AS name',('name:'+locale,))
  
numerics = set()  # set of number-compared things, like "population<10000" needs population as number, not text
mapniksheet = {}

# {zoom: {z-index: [{sql:sql_hint, cond: mapnikfiltercondition, subject: subj, style: {a:b,c:d..}},{r2}...]...}...}

coast = {}
for zoom in range (minzoom, maxzoom):
  mapniksheet[zoom] = {}
  zsheet = mapniksheet[zoom]
  for chooser in style.choosers:
    if chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)[1]:
      sys.stderr.write(str(chooser.get_sql_hints(chooser.ruleChains[0][0].subject, zoom)[1])+"\n")
      styles = chooser.styles[0]
      zindex = styles.get("z-index",0)
      if zindex not in zsheet:
        zsheet[zindex] = []
      chooser_entry = {}
      chooser_entry["sql"] = "("+ chooser.get_sql_hints(chooser.ruleChains[0][0].subject,zoom)[1] +")"
      chooser_entry["style"] = styles
      chooser_entry["type"] = chooser.ruleChains[0][0].subject
      chooser_entry["rule"] = [i.conditions for i in chooser.ruleChains[0] if i.test_zoom(zoom)]
      numerics.update(chooser.get_numerics())
      chooser_entry["rulestring"] = " or ".join([ "("+ " and ".join([i.get_mapnik_filter() for i in rule if i.get_mapnik_filter()!='']) + ")" for rule in chooser_entry["rule"]])
      chooser_entry["chooser"] = chooser
      if chooser_entry["type"] == "area" and "[natural] = 'coastline'" in chooser_entry["rulestring"]:
          coast[zoom] = chooser_entry["style"]
      else:
        zsheet[zindex].append(chooser_entry)





sys.stderr.write(str(numerics)+"\n")
#print mapniksheet

def add_numerics_to_itags(itags):
  tt = set()
  nitags = set()
  for i in itags:
    if i in numerics:
      tt.add("""(CASE WHEN "%s" ~ E'^[[:digit:]]+([.][[:digit:]]+)?$' THEN CAST ("%s" AS FLOAT) ELSE NULL END) as %s__num"""%(i,i,i))
    kav = ""
    if '"' not in i:
      kav = '"'
    nitags.add(kav+i+kav)
  itags = nitags
  itags.update(tt)
  return itags
    



mfile.write(xml_start(style.get_style("canvas", {}, maxzoom)[0].get("fill-color", "#000000")))
for zoom, zsheet in mapniksheet.iteritems():
  x_scale = xml_scaledenominator(zoom)
  ta = zsheet.keys()
  ta.sort(key=float)
  if zoom in coast:
    xml = xml_style_start()
    xml += xml_rule_start()
    xml += x_scale
    if "fill-color" in coast[zoom]:
      xml += xml_polygonsymbolizer(coast[zoom].get("fill-color", "#ffffff"), coast[zoom].get("fill-opacity", "1"))
    if "fill-image" in coast[zoom]:
      xml += xml_polygonpatternsymbolizer(coast[zoom].get("fill-image", ""))
    xml += xml_rule_end()
    xml += xml_style_end()
    xml += xml_layer("coast", zoom=zoom)
    mfile.write(xml)

  for zindex in ta:    
    ## areas pass
    sql = set()
    itags = set()
    xml = xml_style_start()
    for entry in zsheet[zindex]:
      if entry["type"] in ("way", "area", "polygon"):
        if "fill-color" in entry["style"] or "fill-image" in entry["style"]:
          xml += xml_rule_start()
          xml += x_scale

          xml += xml_filter(entry["rulestring"])
          if "fill-color" in entry["style"]:
            xml += xml_polygonsymbolizer(entry["style"].get("fill-color", "black"), entry["style"].get("fill-opacity", "1"))
          if "fill-image" in entry["style"]:
            xml += xml_polygonpatternsymbolizer(entry["style"].get("fill-image", ""))
          sql.add(entry["sql"])
          itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
          xml += xml_rule_end()

          

    xml += xml_style_end()
    sql.discard("()")
    if sql:
      mfile.write(xml)
      sql = "(" + " OR ".join(sql) + ") and way &amp;&amp; !bbox!" 
      itags = add_numerics_to_itags(itags)
      mfile.write(xml_layer("postgis", "polygon", itags, sql ))
    else:
      xml_nolayer()
  for layer_type, entry_types in [("polygon",("way","area")),("line",("way", "line"))]:
    for zlayer in range(-6,7):
      for zindex in ta:
        ## casings pass
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
              xml += xml_linesymbolizer(color=entry["style"].get("casing-color", "black"),
                width=2*float(entry["style"].get("casing-width", 1))+float(entry["style"].get("width", 0)),
                opacity=entry["style"].get("casing-opacity", entry["style"].get("opacity","1")),
                linecap=entry["style"].get("casing-linecap", entry["style"].get("linecap","butt")),
                linejoin=entry["style"].get("casing-linejoin", entry["style"].get("linejoin", "round")),
                dashes=entry["style"].get("casing-dashes",entry["style"].get("dashes", "")))

              sql.add(entry["sql"])
              itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
              xml += xml_rule_end()

        xml += xml_style_end()
        sql.discard("()")
        if sql:
          mfile.write(xml)
          sql = "(" + " OR ".join(sql) + ") and way &amp;&amp; !bbox!" 
          if zlayer == 0:
            sql = "("+ sql +') and ("layer" not in ('+ ", ".join(['\'%s\''%i for i in range(-5,6) if i != 0])+") or \"layer\" is NULL)"
          elif zlayer <=5 and zlayer >= -5:
            sql = "("+ sql +') and "layer" = \'%s\''%zlayer
          itags = add_numerics_to_itags(itags)
          mfile.write(xml_layer("postgis", layer_type, itags, sql ))
        else:
          xml_nolayer()

      for zindex in ta:
        ## lines pass
        sql = set()
        there_are_dashed_lines = False
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
            if "width" in entry["style"] or "line-style" in entry["style"]:
              xml += xml_rule_start()
              xml += x_scale
              xml += xml_filter(entry["rulestring"])
              if "width" in entry["style"]:
                xml += xml_linesymbolizer(color=entry["style"].get("color", "black"),
                  width=entry["style"].get("width", "1"),
                  opacity=entry["style"].get("opacity", "1"),
                  linecap=entry["style"].get("linecap", "round"),
                  linejoin=entry["style"].get("linejoin", "round"),
                  dashes=entry["style"].get("dashes", ""))
                if entry["style"].get("dashes", ""):
                  there_are_dashed_lines = True
                  #print "dashes!!!"
              if "line-style" in entry["style"]:
                if entry["style"]["line-style"] == "arrows":
                  xml += xml_hardcoded_arrows()
                else:
                  xml += xml_linepatternsymbolizer(entry["style"]["line-style"])
              sql.add(entry["sql"])
              itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
              xml += xml_rule_end()

        xml += xml_style_end()
        sql.discard("()")
        if sql:
          mfile.write(xml)
          sql = "(" + " OR ".join(sql) + ") and way &amp;&amp; !bbox!" 
          if zlayer == 0:
            sql = "("+ sql +') and ("layer" not in ('+ ", ".join(['\'%s\''%i for i in range(-5,6) if i != 0])+") or \"layer\" is NULL)"
          elif zlayer <=5 and zlayer >= -5:
            sql = "("+ sql +') and "layer" = \'%s\''%zlayer
          oitags = itags
          itags = add_numerics_to_itags(itags)
          #if there_are_dashed_lines:

          if layer_type == "polygon" and there_are_dashed_lines:
            itags = ", ".join(itags)
            oitags = '"'+ "\", \"".join(oitags) +'"'
            sqlz = """select %s, ST_LineMerge(ST_Union(way)) as way from (SELECT %s, ST_Boundary(ST_Buffer(way,0)) as way from planet_osm_polygon where way &amp;&amp; !bbox! and (%s)) as tex
              group by %s
              """%(itags,oitags,sql,oitags)
            #elif layer_type == "line" and there_are_dashed_lines:
            #  sqlz = """select %s, ST_Union(way) as way from (SELECT * from planet_osm_line where way &amp;&amp; !bbox! #and (%s)) as tex
            #  group by %s
            #  """%(itags,sql,oitags)
            mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz ))
          else:
            mfile.write(xml_layer("postgis", layer_type, itags, sql ))
        else:
          xml_nolayer()
  for layer_type, entry_types in [("point", ("node", "point")),("line",("way", "line")), ("polygon",("way","area"))]:
    for zindex in ta:
      ## icons pass
      sql = set()
      itags = set()
      xml = xml_style_start()
      for entry in zsheet[zindex]:
        if entry["type"] in entry_types:
          if "icon-image" in entry["style"]:
            xml += xml_rule_start()
            xml += x_scale
            xml += xml_filter(entry["rulestring"])
            xml += xml_pointsymbolizer(
              path=entry["style"].get("icon-image", ""),
              width=entry["style"].get("icon-width", ""),
              height=entry["style"].get("icon-height", ""),
              
              opacity=entry["style"].get("opacity", "1"))

            sql.add(entry["sql"])
            itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
            xml += xml_rule_end()

      xml += xml_style_end()
      sql.discard("()")
      if sql:
        mfile.write(xml)
        sql = "(" + " OR ".join(sql) + ") and way &amp;&amp; !bbox!" 
        itags = add_numerics_to_itags(itags)
        mfile.write(xml_layer("postgis", layer_type, itags, sql ))
      else:
        xml_nolayer()
  ta.reverse()
  for zindex in ta:
    for layer_type, entry_types in [ ("polygon",("way","area")),("point", ("node", "point")),("line",("way", "line"))]:
      for placement in ("center","line"):
        ## text pass
        sql = set()
        itags = set()
        
        texttags = set()
        xml = xml_style_start()
        for entry in zsheet[zindex]:
          if entry["type"] in entry_types:#, "node", "line", "point"):
            if "text" in entry["style"] and entry["style"].get("text-position","center")==placement:
              ttext = entry["style"]["text"].extract_tags().pop()
              texttags.add(ttext)
              tface = entry["style"].get("font-family","DejaVu Sans Book")
              tsize = entry["style"].get("font-size","10")
              tcolor = entry["style"].get("text-color","#000000")
              thcolor= entry["style"].get("text-halo-color","#ffffff")
              thradius= entry["style"].get("text-halo-radius","0")
              tplace= entry["style"].get("text-position","center")
              toffset= entry["style"].get("text-offset","0")
              toverlap= entry["style"].get("text-allow-overlap",entry["style"].get("allow-overlap","false"))
              tdistance= entry["style"].get("-x-mapnik-min-distance","26")
              twrap= entry["style"].get("max-width",256)
              talign= entry["style"].get("text-align","center")
              topacity= entry["style"].get("text-opacity",entry["style"].get("opacity","1"))

              xml += xml_rule_start()
              xml += x_scale
              
              xml += xml_filter(entry["rulestring"])
              xml += xml_textsymbolizer(ttext,tface,tsize,tcolor, thcolor, thradius, tplace, toffset,toverlap,tdistance,twrap,talign,topacity)
              sql.add(entry["sql"])
              itags.update(entry["chooser"].get_interesting_tags(entry["type"], zoom))
              xml += xml_rule_end()

        xml += xml_style_end()
        sql.discard("()")
        if sql:
          mfile.write(xml)
          
          add_tags = set()
          for t in itags:
            if t in columnmap:
              add_tags.update(columnmap[t][1])
              texttags.update(columnmap[t][1])
          oitags = itags.union(add_tags)
          
          oitags = [ '"'+i+'"' for i in oitags]
          oitags = ", ".join(oitags)
          
          ttext = " OR ".join(['"'+i+ "\" is not NULL " for i in texttags])
          itags = [columnmap.get(i, (i,))[0] for i in itags]
          itags = add_numerics_to_itags(itags)
          if placement == "center" and layer_type == "polygon":
            sqlz = " OR ".join(sql)
            itags = ", ".join(itags)
            #itags = "\""+ itags+"\""
            sqlz = """select %s, ST_PointOnSurface(ST_Buffer(p.way,0)) as way
            from planet_osm_%s p
            where (%s) and p.way &amp;&amp; !bbox! and (%s) order by way_area
            """%(itags,layer_type,ttext,sqlz)
            mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz ))
          elif layer_type == "line":
            sqlz = " OR ".join(sql)
            itags = ", ".join(itags)
            #itags = "\""+ itags+"\""
            sqlz = """select %s, ST_LineMerge(ST_Union(way)) as way from (SELECT * from planet_osm_line where way &amp;&amp; ST_Expand(!bbox!,500) and (%s) and (%s)) as tex
            group by %s
            """%(itags,ttext,sqlz,oitags)
            mfile.write(xml_layer("postgis-process", layer_type, itags, sqlz ))
          else:
            sql = "(" + " OR ".join(sql) + ") and way &amp;&amp; !bbox!" 
            mfile.write(xml_layer("postgis", layer_type, itags, sql ))
        else:
          xml_nolayer()

mfile.write(xml_end())