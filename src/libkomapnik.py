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
db_user = "mapz"
db_name = "gis"



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
  z1 = s/(2**z1-1)+100
  z2 = s/(2**z2-1)-100
  return z1, z2


def xml_linesymbolizer(color="#000000", width="1", opacity="1", linecap="butt", linejoin="round"):
  color = nicecolor(color)
  linecap  = {"none":"butt",}.get(linecap.lower(),  linecap)
  return """
  <LineSymbolizer>
    <CssParameter name="stroke">%s</CssParameter>
    <CssParameter name="stroke-width">%f</CssParameter>
    <CssParameter name="stroke-linejoin">%s</CssParameter>
    <CssParameter name="stroke-linecap">%s</CssParameter>
  </LineSymbolizer>"""(color, float(width), float(opacity), linejoin, linecap)


def xml_polygonsymbolizer(color="#000000", opacity="1"):
  color = nicecolor(color)
  linecap  = {"none":"butt",}.get(linecap.lower(),  linecap)
  return """
  <LineSymbolizer>
  <CssParameter name="stroke">%s</CssParameter>
  <CssParameter name="stroke-width">%f</CssParameter>

  </LineSymbolizer>"""(color, float(width), float(opacity), linejoin, linecap)



def xml_scaledenominator(z1, z2=False):
  z1, z2 = zoom_to_scaledenom(z1,z2)
  return """
  <MaxScaleDenominator>%f</MaxScaleDenominator>
  <MinScaleDenominator>%f</MinScaleDenominator>"""%(z1,z2)

def xml_start(bgcolor="#ffffff"):
  bgcolor = nicecolor(bgcolor)
  return """<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE Map>
<Map bgcolor="%s" srs="%s" minimum_version="0.7.1">
"""%(bgcolor, map_proj)

def xml_end():
  return """
</Map>"""


def xml_style_start():
  layer_id = get_id(1)
  return """
  <Style name="s%s">"""%(layer_id)

def xml_style_end():

  return """
  </Style>"""


def xml_layer(type="postgis", geom="point", interesting_tags = "*", sql = ["true","d"] ):
  layer_id = get_id() ## increment by 0 - was incremented in style
  interesting_tags = "\", \"".join(interesting_tags)
  interesting_tags = "\""+ interesting_tags+"\""
  sql = " OR ".join(sql)
  return """
  <Layer name="l%s" status="on" srs="%s">
    <StyleName>s%s</StyleName>
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
    </Datasource>
  </Layer>"""%(layer_id, db_proj, layer_id, interesting_tags, table_prefix, geom, sql, db_user, db_name)