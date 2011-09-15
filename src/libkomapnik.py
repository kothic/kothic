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

from mapcss.webcolors.webcolors import whatever_to_hex as nicecolor


map_proj = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"
db_proj = "+proj=merc +a=6378137 +b=6378137 +lat_ts=0.0 +lon_0=0.0 +x_0=0.0 +y_0=0 +k=1.0 +units=m +nadgrids=@null +no_defs +over"
table_prefix = "planet_osm_"
db_user = "gis"
db_name = "gis"
db_srid = 900913
icons_path = "/home/gis/mapnik/kosmo/icons/"
world_bnd_path = "/home/gis/mapnik/world_boundaries/"



substyles = []


last_id = 0

def get_id(i = 0):
  global last_id
  last_id += i
  return last_id


def zoom_to_scaledenom(z1,z2=False):
  """
  Converts zoom level to mapnik's scaledenominator pair for EPSG:3857
  """
  if not z2:
    z2 = z1
  s = 279541132.014
  z1 = (s/(2**(z1-1))+s/(2**(z1-2)))/2
  z2 = (s/(2**(z2-1))+s/(2**z2))/2
  #return 100000000000000, 1
  return z1, z2

def pixel_size_at_zoom(z, l=1):
  """
  Converts l pixels on tiles into length on zoom z
  """
  return l* 20037508.342789244 / 256 * 2 / (2**z)


def xml_fontset(name, unicode=True):
  if unicode:
    unicode = '<Font face_name="unifont Medium" />'
  return """
  <FontSet name="%s">
        <Font face_name="%s" />
        %s
  </FontSet>"""%(name, name, unicode)
  

def xml_pointsymbolizer(path="", width="", height="", opacity=1, overlap="false"):
  if width:
    width =' width="%s" '%width
  if height:
    height =' height="%s" '%height
  return """
  <PointSymbolizer file="%s%s" %s %s opacity="%s" allow_overlap="%s" />"""\
          %(icons_path, \
          path, width, height, opacity, overlap)


def xml_linesymbolizer(color="#000000", width="1", opacity="1", linecap="butt", linejoin="round", dashes=""):
  color = nicecolor(color)
  linecap  = {"none":"butt",}.get(linecap.lower(),  linecap)
  if dashes:
    dashes = '<CssParameter name="stroke-dasharray">%s</CssParameter>'%(dashes)
  else:
    dashes = ""
  return """
  <LineSymbolizer>
    <CssParameter name="stroke">%s</CssParameter>
    <CssParameter name="stroke-width">%s</CssParameter>
    <CssParameter name="stroke-opacity">%s</CssParameter>
    <CssParameter name="stroke-linejoin">%s</CssParameter>
    <CssParameter name="stroke-linecap">%s</CssParameter>
    %s
  </LineSymbolizer>"""%(color, float(width), float(opacity), linejoin, linecap, dashes)


def xml_polygonsymbolizer(color="#000000", opacity="1"):
  color = nicecolor(color)
  
  return """
  <PolygonSymbolizer>
    <CssParameter name="fill">%s</CssParameter>
    <CssParameter name="fill-opacity">%s</CssParameter>
  </PolygonSymbolizer>"""%(color, float(opacity))

def xml_polygonpatternsymbolizer(file=""):
  return """
  <PolygonPatternSymbolizer file="%s%s"/>"""%(icons_path,file)


def xml_linepatternsymbolizer(path=""):
  return """
  <LinePatternSymbolizer file="%s%s"/>"""%(icons_path, path)


def xml_textsymbolizer(text="name",face="DejaVu Sans Book",size="10",color="#000000", halo_color="#ffffff", halo_radius="0", placement="line", offset="0", overlap="false", distance="26", wrap_width=256, align="center", opacity="1", pos="X"):
  color = nicecolor(color)
  halo_color = nicecolor(halo_color)
  pos = pos.replace("exact", "X").replace("any","S, E, X, N, W, NE, SE, NW, SW").split(",")
  pos.extend([str(int(x)) for x in size.split(",")])
  pos = ",".join(pos)
  size = size.split(",")[0]
  
  placement = {"center": "point"}.get(placement.lower(), placement)
  align = {"center": "middle"}.get(align.lower(), align)
  
  return """
  <TextSymbolizer name="%s" fontset_name="%s" size="%s" fill="%s" halo_fill= "%s" halo_radius="%s" placement="%s" dy="%s" max_char_angle_delta="15" allow_overlap="%s" wrap_width="%s" min_distance="%s" vertical_alignment="middle" horizontal_alignment="%s" opacity="%s" placement-type="simple" placements="%s" />
  """%(text,face,int(float(size)),color,halo_color,halo_radius,placement,offset,overlap,wrap_width,distance,align,opacity,pos)

def xml_shieldsymbolizer(path="", width="", height="",text="name",face="DejaVu Sans Book",size="10",color="#000000", halo_color="#ffffff", halo_radius="0", placement="line", offset="0", overlap="false", distance="26", wrap_width=256, align="center", opacity="1"):
  color = nicecolor(color)
  halo_color = nicecolor(halo_color)
  placement = {"center": "point"}.get(placement.lower(), placement)
  align = {"center": "middle"}.get(align.lower(), align)
  size = size.split(",")[0]
  if width:
    width =' width="%s" '%width
  if height:
    height =' height="%s" '%height
  return """
    <ShieldSymbolizer file="%s%s" %s %s name="%s" fontset_name="%s" size="%s" fill="%s" halo_fill= "%s" halo_radius="%s" placement="%s" dy="%s" allow_overlap="%s" wrap_width="%s" min_distance="%s" horizontal_alignment="%s" opacity="%s" />
  """%(icons_path, \
    path, width, height,text,face,int(float(size)),color,halo_color,halo_radius,placement,offset,overlap,wrap_width,distance,align,opacity)

def xml_filter(string):
  return """
  <Filter>%s</Filter>"""%string

def xml_scaledenominator(z1, z2=False):
  zz1, zz2 = zoom_to_scaledenom(z1,z2)
  return """
  <MaxScaleDenominator>%s</MaxScaleDenominator>
  <MinScaleDenominator>%s</MinScaleDenominator><!-- z%s-%s -->"""%(zz1,zz2,z1,z2)

def xml_start(bgcolor="transparent"):
  if bgcolor != "transparent":
    bgcolor = nicecolor(bgcolor)
  return """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE Map>
<Map bgcolor="%s" srs="%s" minimum_version="0.7.1" buffer_size="512" maximum-extent="-20037508.342789244,-20037508.342780735,20037508.342789244,20037508.342780709" >
"""%(bgcolor, map_proj)

def xml_end():
  return """
</Map>"""


def xml_style_start():
  global substyles
  layer_id = get_id(1)
  substyles.append(layer_id)
  return """
  <Style name="s%s">"""%(layer_id)

def xml_style_end():

  return """
  </Style>"""

def xml_rule_start():
  return """
  <Rule>"""

def xml_rule_end():
  return """
  </Rule>"""

def xml_hardcoded_arrows():
  return """
  <LineSymbolizer>
    <CssParameter name="stroke">#6c70d5</CssParameter>
    <CssParameter name="stroke-width">1</CssParameter>
    <CssParameter name="stroke-linejoin">bevel</CssParameter>
    <CssParameter name="stroke-dasharray">0,12,10,152</CssParameter>
  </LineSymbolizer>
  <LineSymbolizer>
    <CssParameter name="stroke">#6c70d5</CssParameter>
    <CssParameter name="stroke-width">2</CssParameter>
    <CssParameter name="stroke-linejoin">bevel</CssParameter>
    <CssParameter name="stroke-dasharray">0,12,9,153</CssParameter>
  </LineSymbolizer>
  <LineSymbolizer>
    <CssParameter name="stroke">#6c70d5</CssParameter>
    <CssParameter name="stroke-width">3</CssParameter>
    <CssParameter name="stroke-linejoin">bevel</CssParameter>
    <CssParameter name="stroke-dasharray">0,18,2,154</CssParameter>
  </LineSymbolizer>
  <LineSymbolizer>
    <CssParameter name="stroke">#6c70d5</CssParameter>
    <CssParameter name="stroke-width">4</CssParameter>
    <CssParameter name="stroke-linejoin">bevel</CssParameter>
    <CssParameter name="stroke-dasharray">0,18,1,155</CssParameter>
  </LineSymbolizer>"""

def xml_layer(type="postgis", geom="point", interesting_tags = "*", sql = "true", zoom=0 ):
  layer_id = get_id(1)
  global substyles
  subs = "\n".join(["<StyleName>s%s</StyleName>"%i for i in substyles])
  substyles = []
  if type == "postgis":
    interesting_tags = list(interesting_tags)
    if '"' not in "".join(interesting_tags):
      interesting_tags = "\", \"".join(interesting_tags)
      interesting_tags = "\""+ interesting_tags+"\""
    else:
      interesting_tags = ", ".join(interesting_tags)
    
    
    return """
    <Layer name="l%s" status="on" srs="%s">
      %s
      <Datasource>
        <Parameter name="table">
        (select %s, way
        from %s%s
        where %s
        ) as text
        </Parameter>
        <Parameter name="type">postgis</Parameter>
        <Parameter name="user">%s</Parameter>
        <Parameter name="dbname">%s</Parameter>
        <Parameter name="srid">%s</Parameter>
        <Parameter name="geometry_field">way</Parameter>
        <Parameter name="geometry_table">%s%s</Parameter>
        <Parameter name="estimate_extent">false</Parameter>
        <Parameter name="extent">-20037508.342789244, -20037508.342780735, 20037508.342789244, 20037508.342780709</Parameter>
      </Datasource>
    </Layer>"""%(layer_id, db_proj, subs, interesting_tags, table_prefix, geom, sql, db_user, db_name, db_srid,  table_prefix, geom)
  elif type == "postgis-process":
    return """
    <Layer name="l%s" status="on" srs="%s">
      %s
      <Datasource>
        <Parameter name="table">
        (%s
        ) as text
        </Parameter>
        <Parameter name="type">postgis</Parameter>
        <Parameter name="user">%s</Parameter>
        <Parameter name="dbname">%s</Parameter>
        <Parameter name="srid">%s</Parameter>
        <Parameter name="geometry_field">way</Parameter>
        <Parameter name="geometry_table">%s%s</Parameter>
        <Parameter name="estimate_extent">false</Parameter>
        <Parameter name="extent">-20037508.342789244, -20037508.342780735, 20037508.342789244, 20037508.342780709</Parameter>
      </Datasource>
    </Layer>"""%(layer_id, db_proj, subs, sql, db_user, db_name, db_srid,  table_prefix, geom)
  elif type == "coast":
    if zoom < 9:
      return """
      <Layer name="l%s" status="on" srs="%s">
        %s
        <Datasource>
        <Parameter name="type">shape</Parameter>
        <Parameter name="file">%sshoreline_300</Parameter>
        </Datasource>
      </Layer>"""%(layer_id, db_proj, subs, world_bnd_path)
    else:
      return """
      <Layer name="l%s" status="on" srs="%s">
        %s
        <Datasource>
        <Parameter name="type">shape</Parameter>
        <Parameter name="file">%sprocessed_p</Parameter>
        </Datasource>
      </Layer>"""%(layer_id, db_proj, subs, world_bnd_path)
def xml_nolayer():
  global substyles
  substyles = []
def xml_nosubstyle():
  global substyles
  substyles = substyles[:-1]