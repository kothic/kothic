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
    self.minZoom = 13   #### FIXME: take from MapCSS creation thingz
    self.maxZoom = 19
    self.subject = s    # "", "way", "node" or "relation"
  def __repr__(self):
    return "%s|z%s-%s %s"%(self.subject,self.minZoom,self.maxZoom, self.conditions)

  #public function test(obj:Entity,tags:Object):Boolean {
    #if (subject!='' && obj.getType()!=subject) { return false; }
    
    #var v:Boolean=true; var i:uint=0;
    #for each (var condition:Condition in conditions) {
      #var r:Boolean=condition.test(tags);
      #if (i==0) { v=r; }
      #else if (isAnd) { v=v && r; }
      #else { v = v || r;}
      #i++;
      #}
      #return v;
      #}
      