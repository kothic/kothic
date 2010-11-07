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



class Rule():
  def __init__(self, s=''):
    self.conditions = []
    self.isAnd = True
    self.minZoom = 0   
    self.maxZoom = 19
    self.subject = s    # "", "way", "node" or "relation"
  def __repr__(self):
    return "%s|z%s-%s %s"%(self.subject,self.minZoom,self.maxZoom, self.conditions)

  #public function test(obj:Entity,tags:Object):Boolean {


  
  def test(self, obj, tags, zoom):
    if (self.subject!='') and not _test_feature_compatibility(obj, self.subject, tags):
      return False
    #print _test_feature_compatibility(obj, self.subject, tags), obj, self.subject
    if not self.test_zoom(zoom):
      return False
    v="a"
    for condition in self.conditions:
      r = condition.test(tags)
      if v=="a":
        v = r
      elif self.isAnd:
        v = v & r
      else:
        v = v | r
    return v

  def test_zoom(self, zoom):
    return (zoom >= self.minZoom) and (zoom <= self.maxZoom)

  def get_interesting_tags(self, obj, zoom):
    if obj:
      if (self.subject!='') and not _test_feature_compatibility(obj, self.subject, {}):
        return set()
    if zoom:
      if (zoom < self.minZoom) or (zoom > self.maxZoom):
        return set()
    a = set()
    for condition in self.conditions:
      a.update(condition.get_interesting_tags())
    return a

  def get_sql_hints(self, obj, zoom):
    if obj:
      if (self.subject!='') and not _test_feature_compatibility(obj, self.subject, {":area":"yes"}):
        return set()
    if zoom:
      if (zoom < self.minZoom) or (zoom > self.maxZoom):
        return set()
    a = set()
    b = set()
    for condition in self.conditions:
      q = condition.get_sql()
      a.add(q[0])
      b.add(q[1])
    b = " AND ".join(b)
    return a,b



def _test_feature_compatibility (f1, f2, tags={}):
    """
    Checks if feature of type f1 is compatible with f2.
    """
    
    if f2 == f1:
      return True
    elif f2 == "area" and f1 in ("way", "area", "POLYGON"):
      if ":area" in tags:
        pass
      else:
        return False
    elif f2 == "line" and f1 in ("way", "line", "LINESTRING"):
      pass
    elif f2 == "point" and f1 in ("node", "POINT"):
      pass
    else:
      return False
    #print f1, f2, True
    return True