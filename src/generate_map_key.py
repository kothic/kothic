#!/usr/bin/env python
# -*- coding: utf-8 -*-
from mapcss import MapCSS
import mapcss.webcolors
whatever_to_hex = mapcss.webcolors.webcolors.whatever_to_hex

import json

import cairo

import sys

reload(sys)
sys.setdefaultencoding("utf-8")

minzoom = 0
maxzoom = 18

sample_width = 80

style = MapCSS(minzoom, maxzoom)
style.parse(open(sys.argv[1],"r").read(), clamp=False)


tags = [json.loads(x) for x in open("data/tags.list", "r")]
print len(tags)
#a = cairo.PDFSurface("legend.pdf",100,100*len(tags))

maxzoom += 1

a = cairo.ImageSurface (cairo.FORMAT_ARGB32, maxzoom*sample_width, 50*len(tags))
cr = cairo.Context(a)
cr.translate(0,0.5)


i = 0
icons = {}
for tag in tags:
  had_lines = False
  for zoom in range (minzoom, maxzoom):
    styles = style.get_style_dict("node", tag, zoom, olddict = {})
    styles = style.get_style_dict("area", tag, zoom, olddict = styles.copy())
    styles = style.get_style_dict("line", tag, zoom, olddict = styles.copy())
    
    styles = styles.values()
    styles.sort(key=lambda x: x.get('z-index',0))
    if len(styles) > 0:
      for st in styles:
        if "fill-color" in st and st.get("fill-opacity", 1) > 0:
            color = st.get('fill-color', (0.,0.,0.))
            cr.set_source_rgba(color[0], color[1], color[2], st.get("fill-opacity", 1))
            cr.move_to(0+sample_width*zoom, 20+50*i)
            cr.line_to(sample_width+sample_width*zoom, 20+50*i)
            cr.line_to(sample_width+sample_width*zoom, 55+50*i)
            cr.line_to(0+sample_width*zoom, 20+50*i)
            had_lines = True
            cr.fill()
      for st in styles:
        if "casing-width" in st and st.get("casing-opacity", 1) > 0:
            color = st.get('casing-color', (0.,0.,0.))
            cr.set_source_rgba(color[0], color[1], color[2], st.get("casing-opacity", 1))
            cr.set_line_width (st.get("width",0)+2*st.get("casing-width", 0))
            cr.set_dash(st.get('casing-dashes', st.get('dashes', []) ))
            cr.move_to(0+sample_width*zoom, 50+50*i)
            cr.line_to(sample_width+sample_width*zoom, 50+50*i)
            had_lines = True
            cr.stroke()
      for st in styles:
        if "width" in st and st.get("opacity", 1) > 0:
            color = st.get('color', (0.,0.,0.))
            cr.set_source_rgba(color[0], color[1], color[2], st.get("opacity", 1))
            cr.set_line_width (st.get("width",0))
            cr.set_dash(st.get('dashes', []))
            cr.move_to(0+sample_width*zoom, 50+50*i)
            cr.line_to(sample_width+sample_width*zoom, 50+50*i)
            had_lines = True
            cr.stroke()
        if "icon-image" in st:
					icons[st["icon-image"]] = icons.get(st["icon-image"], set())
					icons[st["icon-image"]].add('[' + ']['.join([ k+"="+v for k,v in tag.iteritems()])+']')
      

      if had_lines:
            cr.move_to(0+sample_width*zoom, 25+50*i)
            cr.set_source_rgb(0, 0, 0)
            cr.show_text('z'+str(zoom))

  if had_lines:
        text = '[' + ']['.join([ k+"="+v for k,v in tag.iteritems()])+']'
        cr.move_to(10, 20+50*i)
        cr.set_source_rgb(0, 0, 0)
        cr.show_text(text)
        cr.set_line_width (1)
        cr.set_dash([])
        cr.move_to(0, 60+50*i)
        cr.line_to(maxzoom*sample_width, 60+50*i)
        
        cr.stroke()
        i += 1
#a.finish()\
ss = open("icons.html","w")
print >> ss, "<html><body><table border=1>"
for k, v in icons.iteritems():
	print >> ss, "<tr><td><img src='%s' width='24' height='24'></td><td>%s</td><td>%s</td></tr>\n"%(k.lower(), k.lower(), "<br>".join(list(v)))
print >> ss, "</table></body></html>"
a.write_to_png ("legend.png") 