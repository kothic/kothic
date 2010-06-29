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

NONE = ""

class Eval():
  def __init__(self, s='eval()'):
    """
    Parse expression and convert it into Python
    """
    s = s.strip()[5:-1].strip()
    s
    self.expr = compile (s, "MapCSS expression", "eval")

  def compute(self, tags={}, props = {}, xscale = 1., zscale = 0.5 ):
    """
    Compute this eval()
    """
    for k,v in tags.iteritems():
      try:
        tag[k] = float(v)
      except:
        pass
    try:
      return str(eval(self.expr, {}, {
      "tag":lambda x: tags.get(x,""),
      "prop":lambda x: props.get(x,""),
      "num": m_num,
      "metric": lambda x: m_metric(x, xscale),
      "zmetric": lambda x: m_metric(x, zscale),
      "str": str,
      "any": m_any,
        }))
    except:
      return ""

    
  def __repr__(self):
    return "eval(%s)"%repr(self.expr)

def m_any(*x):
  """
  any() MapCSS feature
  """
  for t in x:
    if t:
      return t
  else:
    return ""

def m_num(x):
  """
  num() MapCSS feature
  """
  try:
    return float(str(x))
  except ValueError:
    return 0
def m_metric(x, t):
  """
  metric() and zmetric() function.
  """
  x = str(x)
  try:
    return float(x)*float(t)
  except:
    "Heuristics."
    # FIXME: add ft, m and friends
    x = x.strip()
    try:
      if x[-1] == "m":
        return float(x[0:-1])*float(t)
    except:
      return ""
#def str(x):
  #"""
  #str() MapCSS feature
  #"""
  #return __builtins__.str(x)


if __name__ == "__main__":
  a = Eval(""" eval( any( metric(tag("height")), metric ( num(tag("building:levels")) * 3), metric("1m"))) """)
  print repr(a)
  print a.compute({"building:levels":"3"})