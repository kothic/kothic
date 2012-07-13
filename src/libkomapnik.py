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


import os
from debug import debug, Timer

from mapcss.webcolors.webcolors import whatever_to_hex as nicecolor


map_proj = ""
db_proj = ""
table_prefix = ""
db_user = ""
db_name = ""
db_srid = ""
icons_path = ""
world_bnd_path = ""
cleantopo_dem_path = ""
srtm_dem_path = ""
cleantopo_hs_path = ""
srtm_hs_path = ""
text_scale = 1

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
  <PointSymbolizer file="%s" %s %s opacity="%s" allow_overlap="%s" />"""\
          %(os.path.join(icons_path, path), width, height, opacity, overlap)


def xml_linesymbolizer(color="#000000", width="1", opacity="1", linecap="butt", linejoin="round", dashes="", smooth=0, zoom=200):
  color = nicecolor(color)
  linecap  = {"none":"butt",}.get(linecap.lower(),  linecap)

  if dashes:
    dashes = 'stroke-dasharray="%s"'%(dashes)
  else:
    dashes = ""

  if smooth:
    smooth = 'smooth="%s"'%(smooth)
  else:
    smooth = ""

  rasterizer = ""
#  if float(width) < 4 and not dashes and zoom < 6:
#    rasterizer = ' rasterizer="fast"'

  return """
  <LineSymbolizer %s %s stroke="%s" stroke-width="%s" stroke-opacity="%s" stroke-linejoin="%s" stroke-linecap="%s" %s/>"""%(rasterizer, smooth, color, float(width), float(opacity), linejoin, linecap, dashes)


def xml_polygonsymbolizer(color="#000000", opacity="1", smooth='0'):
  color = nicecolor(color)
  if smooth:
    smooth = 'smooth="%s"'%(smooth)
  else:
    smooth = ""
  return """
  <PolygonSymbolizer fill="%s" fill-opacity="%s" gamma="0.73" %s />"""%(color, float(opacity), smooth)

def xml_polygonpatternsymbolizer(file=""):
  return """
  <PolygonPatternSymbolizer file="%s"/>"""%(os.path.join(icons_path,file))


def xml_linepatternsymbolizer(file=""):
  return """
  <LinePatternSymbolizer file="%s"/>"""%(os.path.join(icons_path,file))


def xml_textsymbolizer(
                      text="name",face="DejaVu Sans Book",size="10",color="#000000", halo_color="#ffffff", halo_radius="0", placement="line", offset="0", overlap="false", distance="26", wrap_width=256, align="center", opacity="1", pos="X", transform = "none", spacing="4096"):
  color = nicecolor(color)
  halo_color = nicecolor(halo_color)
  pos = pos.replace("exact", "X").replace("any","S, E, X, N, W, NE, SE, NW, SW").split(",")
  pos.extend([str(int(float(x)*text_scale)) for x in size.split(",")])
  pos = ",".join(pos)
  size = str(int(float(size.split(",")[0])*text_scale))
  
  
  placement = {"center": "interior"}.get(placement.lower(), placement)
  align = {"center": "middle"}.get(align.lower(), align)
  dy = int(float(offset))
  dx = 0
  if align in ("right",'left'):
    dx = dy
    dy = 0
  
  return """
  <TextSymbolizer name="%s" fontset_name="%s" size="%s" fill="%s" halo_fill= "%s" halo_radius="%s" placement="%s" dx="%s" dy="%s" max_char_angle_delta="17" allow_overlap="%s" wrap_width="%s" min_distance="%s" vertical_alignment="middle" horizontal_alignment="%s" opacity="%s" placement-type="simple" placements="%s" text-transform="%s" minimum-path-length="5" spacing="%s" />
  """%(text,face,int(float(size)),color,halo_color,halo_radius,placement,dx,dy,overlap,wrap_width,distance,align,opacity,pos, transform, spacing)

def xml_shieldsymbolizer(path="", width="", height="",
                        text="name",face="DejaVu Sans Book",size="10",color="#000000", halo_color="#ffffff", halo_radius="0", placement="line", offset="0", overlap="false", distance="26", wrap_width=256, align="center", opacity="1", transform="none", unlock_image='true', spacing='500'):
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
    <ShieldSymbolizer file="%s%s" %s %s name="%s" fontset_name="%s" size="%s" fill="%s" halo_fill= "%s" halo_radius="%s" placement="%s" dy="%s" allow_overlap="%s" wrap_width="%s" min_distance="%s" horizontal_alignment="%s" opacity="%s" text-transform="%s" unlock-image="%s" spacing="%s" />
  """%(icons_path, \
    path, width, height,text,face,int(float(size)*text_scale),color,halo_color,halo_radius,placement,offset,overlap,wrap_width,distance,align,opacity, transform, unlock_image, spacing )

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

def xml_cleantopo(zoom, x_scale, demramp):
  return """
<Style name="elevation1z%s">
  <Rule>%s
    <RasterSymbolizer>
      <RasterColorizer default-mode="linear" epsilon="0.001">
        %s
      </RasterColorizer>
    </RasterSymbolizer>
  </Rule>
</Style>

<Layer name="ele-raster1z%s">
    <StyleName>elevation1z%s</StyleName>
    <Datasource>
        <Parameter name="file">%s</Parameter>
        <Parameter name="type">gdal</Parameter>
        <Parameter name="band">1</Parameter>
        <Parameter name="srid">3857</Parameter>
    </Datasource>
</Layer>
""" % (zoom, x_scale, demramp, zoom, zoom, cleantopo_dem_path)

def xml_srtm(zoom, x_scale, demramp):
  return """
<Style name="elevationz%s">
  <Rule>%s
    <RasterSymbolizer>
      <RasterColorizer default-mode="linear" epsilon="0.001">
        %s
     </RasterColorizer>
    </RasterSymbolizer>
  </Rule>
</Style>

<Layer name="ele-rasterz%s">
    <StyleName>elevationz%s</StyleName>
    <Datasource>
        <Parameter name="file">%s</Parameter>
        <Parameter name="type">gdal</Parameter>
        <Parameter name="band">1</Parameter>
        <Parameter name="srid">3857</Parameter>
    </Datasource>
</Layer>
      """ % (zoom, x_scale, demramp, zoom, zoom, srtm_dem_path)

      
def xml_hillshade(zoom, x_scale):
  hs_path = cleantopo_hs_path
  if zoom>6:
    hs_path = srtm_hs_path
  return """
<Style name="hillshade%s">
  <Rule>%s
    <RasterSymbolizer opacity="0.3">
      <RasterColorizer  default-mode="linear">
        <stop value="0"   color="rgba(0,0,0,1)" />
        <stop value="128"   color="rgba(128,128,128,0.4)" />
        <stop value="255" color="rgba(255,255,255,1)" />
      </RasterColorizer>
    </RasterSymbolizer>
  </Rule>
</Style>

<Layer name="ele-hsz%s">
    <StyleName>hillshade%s</StyleName>
    <Datasource>
        <Parameter name="file">%s</Parameter>
        <Parameter name="type">gdal</Parameter>
        <Parameter name="band">1</Parameter>
        <Parameter name="srid">3857</Parameter>
    </Datasource>
</Layer>
      """ % (zoom, x_scale, zoom, zoom, hs_path)
      
      
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
  intersection_SQL = ""
  if zoom < 5:
    intersection_SQL = '<Parameter name="intersect_max_scale">1</Parameter>'
  elif zoom > 16:
    intersection_SQL = '<Parameter name="intersect_min_scale">500000000000</Parameter>'
  if type == "postgis":
    interesting_tags = list(interesting_tags)
    if '"' not in "".join(interesting_tags) and "->" not in "".join(interesting_tags):
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
        %s
        <Parameter name="type">postgis</Parameter>
        <Parameter name="st_prefix">true</Parameter>
        <Parameter name="user">%s</Parameter>
        <Parameter name="dbname">%s</Parameter>
        <Parameter name="srid">%s</Parameter>
        <Parameter name="geometry_field">way</Parameter>
        <Parameter name="geometry_table">%s%s</Parameter>
        <Parameter name="estimate_extent">false</Parameter>
        <Parameter name="extent">-20037508.342789244, -20037508.342780735, 20037508.342789244, 20037508.342780709</Parameter>
      </Datasource>
    </Layer>"""%(layer_id, db_proj, subs, interesting_tags, table_prefix, geom, sql, intersection_SQL, db_user, db_name, db_srid,  table_prefix, geom)
  elif type == "postgis-process":
    return """
    <Layer name="l%s" status="on" srs="%s">
      %s
      <Datasource>
        <Parameter name="table">
        (%s
        ) as text
        </Parameter>
        %s
        <Parameter name="type">postgis</Parameter>
        <Parameter name="st_prefix">true</Parameter>
        <Parameter name="user">%s</Parameter>
        <Parameter name="dbname">%s</Parameter>
        <Parameter name="srid">%s</Parameter>
        <Parameter name="geometry_field">way</Parameter>
        <Parameter name="geometry_table">%s%s</Parameter>
        <Parameter name="estimate_extent">false</Parameter>
        <Parameter name="extent">-20037508.342789244, -20037508.342780735, 20037508.342789244, 20037508.342780709</Parameter>
      </Datasource>
    </Layer>"""%(layer_id, db_proj, subs, sql, intersection_SQL, db_user, db_name, db_srid,  table_prefix, geom)
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