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

### TODO: MapCSS loading and parsing


from debug import debug

class Styling():
  """
  Class used to choose the right way of rendering an object.
  """
  def __init__(self, stylefile = None):
    self.Selectors = {}
    self.Selectors["way"] = []
    self.Selectors["node"] = []
    self.Selectors["relation"] = []
    if not stylefile:
      ### using "builtin" styling
      self.Selectors["way"].append(StyleSelector( ( [ ( ("highway",),("residential", "tertiary", "living_street")) ]  ),{"width": 3, "color":"#ffffff", "casing-width": 5, "z-index":100} ))
      self.Selectors["way"].append(StyleSelector( ( [ ( ("building",),(None) ) ] ),{"fill-color":"#ff0000"} ))
    self.stylefile = stylefile
    self.useful_keys = set()
    for objtype in self.Selectors.values():  # getting useful keys
      for selector in objtype:
        debug(selector)
        for tag in selector.tags:
          self.useful_keys.update(set(tag[0]))
    

  def get_style(self, objtype, tags, nodata = False):
    """
    objtype is "node", "way" or "relation"
    tags - object tags
    nodata - we won't render that now, don't need exact styling
    """
    resp = {}
    for selector in self.Selectors[objtype]:
      resp.update(selector.get_style(tags))
      if nodata:
        if resp:
          return True
    if not nodata and resp:
      resp["layer"] = int(tags.get("layer",0))*100+resp.get("z-index",0)+1000
    return resp
  def filter_tags(self, tags):
    """
    Returns only tags that are useful for rendering
    """
    resp = {}
    for k,v in tags.iteritems():
      if k in self.useful_keys:
        resp[k] = v
    return resp

  
  
class StyleSelector():
  def __init__(self, tags, style):
    """
    Selector that decides if that style is right for the object
    tags - list of tags [(("key","key"..), ("value", "value"...)), (("key","key"..), ("value", "value"...))]
    style - MapCSS rules to apply
    """
    self.tags = tags
    self.style = style
  def get_style(self, tags):
    """
    Get actual styling for object.
    """
    styled = False
    #debug(self.tags)
    for k,v in self.tags:
      for j in k:
        if j in tags:
          if v:
            if tags[j] in v:
              styled = True
          else:
            styled = True
        if styled:
          return self.style
    return {}
  
if __name__ == "__main__":
  c = Styling()
  print c.get_style("way", {"building":"yes"})
  print c.get_style("way", {"highway":"residential"})
  print c.get_style("way", {"highway":"road"})
  print c.get_style("way", {"highway":"residential", "building": "yes"})
  print c.get_style("way", {"highwadfgaay":"resifdgsdential", "builafgding": "yedfgs"})
  print c.get_style("way", {"highwadfgaay":"resifdgsdential", "builafgding": "yedfgs"}, True)
  print c.get_style("way", {"highway":"residential", "building": "yes"}, True)
  print c.filter_tags({"highwadfgaay":"resifdgsdential", "builafgding": "yedfgs", "building": "residential"})