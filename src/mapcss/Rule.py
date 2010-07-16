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
    if (self.subject!='') & (obj!=self.subject):
      return False
    if (zoom < self.minZoom) or (zoom > self.maxZoom):
      return False
    v=True
    i=0
    for condition in self.conditions:
      r = condition.test(tags)
      if i==0:
        v=r
      elif self.isAnd:
        v = v & r
      else:
        v = v | r
      i += 1
      
    return v
  def get_interesting_tags(self, obj, zoom):
    if obj:
      if (self.subject!='') & (obj!=self.subject):
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
      if (self.subject!='') & (obj!=self.subject):
        return set()
    if zoom:
      if (zoom < self.minZoom) or (zoom > self.maxZoom):
        return set()
    a = set()
    for condition in self.conditions:
      a.add(condition.get_sql())
    return a