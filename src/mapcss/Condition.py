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

import re

class Condition:
  def __init__(self, typez, params):
    self.type=typez         # eq, regex, lt, gt etc.
    if type(params) == type(str()):
      params = (params,)
    self.params=params       # e.g. ('highway','primary')
    if typez == "regex":
      self.regex = re.compile(self.params[0], re.I)

    self.compiled_regex = ""
    
  def get_interesting_tags(self):

     return set([self.params[0]])
    
  def test(self, tags):
    """
    Test a hash against this condition
    """
    

    t = self.type
    params = self.params
    try:
      if t == 'eq':
        return tags[params[0]]==params[1]
      if t == 'ne':
        return tags.get(params[0], "")!=params[1]
      if t == 'regex':
        return bool(self.regex.match(tags[params[0]]))
      if t == 'true':
        return (tags[params[0]]=='true') | (tags[params[0]]=='yes') | (tags[params[0]]=='1')
      if t == 'false':
        return (tags.get(params[0], "")=='false') | (tags.get(params[0], "")=='no') | (tags.get(params[0], "")=='')
      if t == 'set':
        if params[0] in tags:
          return tags[params[0]]!=''
        return False
      if t == 'unset':
        if params[0] in tags:
          return tags[params[0]]==''
        return True

      if t == '<':
        return (Number(tags[params[0]])< Number(params[1]))
      if t == '<=':
        return (Number(tags[params[0]])<=Number(params[1]))
      if t == '>':
        return (Number(tags[params[0]])> Number(params[1]))
      if t == '>=':
        return (Number(tags[params[0]])>=Number(params[1]))
    except KeyError:
      pass
    return False;

  def get_sql(self):
    #params = [re.escape(x) for x in self.params]
    params = self.params
    t = self.type
    try:
      if t == 'eq':
        return params[0], '"%s" = \'%s\''%(params[0], params[1])
      if t == 'ne':
        return params[0], 'not("%s" = \'%s\')'%(params[0], params[1])
      if t == 'regex':
        return params[0], '"%s" IS NOT NULL'%(params[0])
      if t == 'true':
        return params[0], '"%s" IN (\'true\', \'yes\', \'1\')'%(params[0])
      if t == 'untrue':
        return params[0], '"%s" NOT IN (\'true\', \'yes\', \'1\')'%(params[0])
      if t == 'set':
        return params[0], '"%s" IS NOT NULL'%(params[0])
      if t == 'unset':
        return params[0], '"%s" IS NULL'%(params[0])
        
      if t == '<':
        return params[0], '"%s" IS NOT NULL'%(params[0])
      if t == '<=':
        return params[0], '"%s" IS NOT NULL'%(params[0])
      if t == '>':
        return params[0], '"%s" IS NOT NULL'%(params[0])
      if t == '>=':
        return params[0], '"%s" IS NOT NULL'%(params[0])
    except KeyError:
      pass
  def get_mapnik_filter(self):
    #params = [re.escape(x) for x in self.params]
    params = self.params
    t = self.type
    try:
      if t == 'eq':
        return '[%s] = \'%s\''%(params[0], params[1])
      if t == 'ne':
        return 'not([%s] = \'%s\')'%(params[0], params[1])
      if t == 'regex':
        return '[%s].match(%s)'%(params[0], params[1])
      if t == 'true':
        return '[%s] = \'yes\''%(params[0])
      if t == 'untrue':
        return '[%s] = \'no\''%(params[0])
      if t == 'set':
        return 'not([%s] = \'\')'%(params[0])
      if t == 'unset':
        return '[%s] = \'\''%(params[0])

      if t == '<':
        return '"%s" &lt; %s'%(params[0], float(params[1]))
      if t == '<=':
        return '"%s" &lt;= %s'%(params[0], float(params[1]))
      if t == '>':
        return '"%s" &gt; %s'%(params[0], float(params[1]))
      if t == '>=':
        return '"%s" &gt;= %s'%(params[0], float(params[1]))
    except KeyError:
      pass
  def __repr__(self):
    return "%s %s "%(self.type, repr(self.params))
def Number(tt):
  """
  Wrap float() not to produce exceptions
  """
  
  try:
    return float(tt)
  except ValueError:
    return 0