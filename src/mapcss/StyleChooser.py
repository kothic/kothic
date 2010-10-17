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
 

from Rule import Rule
from webcolors.webcolors import whatever_to_cairo as colorparser
from webcolors.webcolors import cairo_to_hex
from Eval import Eval

class StyleChooser:
  """
                      A StyleChooser object is equivalent to one CSS selector+declaration.
                      
                      Its ruleChains property is an array of all the selectors, which would
                      traditionally be comma-separated. For example:
                               h1, h2, h3 em
                      is three ruleChains.

                        Each ruleChain is itself an array of nested selectors. So the above
                        example would roughly be encoded as:
                                [[h1],[h2],[h3,em]]
                                  ^^   ^^   ^^ ^^   each of these is a Rule

                        The styles property is an array of all the style objects to be drawn
                        if any of the ruleChains evaluate to true.
  """
  def __repr__(self):
    return "{(%s) : [%s] }\n"%(self.ruleChains, self.styles)
  def __init__(self, scalepair):
    self.ruleChains = [[],]
    self.styles = []
    self.eval_type = type(Eval())
    self.scalepair = scalepair
    self.rcpos=0
    self.stylepos=0


  def get_interesting_tags(self, type, zoom):
    """
    Returns a set of tags that were used in here.
    """
    ### FIXME
    a = set()
    for c in self.ruleChains:
      for r in c:
        a.update(r.get_interesting_tags(type, zoom))
    if a:   ## FIXME: semi-illegal optimization, may wreck in future on tagless matches
      
      for r in self.styles:
        for c,b in r.iteritems():
          if __builtins__["type"](b) == self.eval_type:
            a.update(b.extract_tags())
    return a

  def get_sql_hints(self, type, zoom):
    """
    Returns a set of tags that were used in here in form of SQL-hints.
    """
    a = set()
    b = ""
    for c in self.ruleChains:
      for r in c:
        p = r.get_sql_hints(type, zoom)
        q = "("+") AND (".join([t[1] for t in p]) + ")"
        if q == "()":
          q = ""
        if b and q:
          b += " OR "+ q
        else:
          b = q
        a.update(p)
    # no need to check for eval's
    return a,b
  # // Update the current StyleList from this StyleChooser

  def updateStyles(self,sl,type, tags, zoom, scale, zscale):
                  # Are any of the ruleChains fulfilled?
                  w = 0
                  for c in self.ruleChains:
                    if (self.testChain(c,type,tags,zoom)):
                      break
                  else:
                    return sl

                  ## Update StyleList
                  object_id = 1

                  for r in self.styles:
                    ra = {}
                    for a,b in r.iteritems():
                      "calculating eval()'s"
                      if __builtins__["type"](b) == self.eval_type:
                        combined_style = {}
                        for t in sl:
                          combined_style.update(t)
                        for p,q in combined_style.iteritems():
                          if "color" in p:
                            combined_style[p] = cairo_to_hex(q)
                        b = b.compute(tags,combined_style, scale, zscale)
                      ra[a] = b
                    r = ra
                    ra = {}
                    for a, b in r.iteritems():
                      "checking and nicifying style table"
                      if "color" in a:
                        "parsing color value to 3-tuple"
                        ra[a] = colorparser(b)
                      elif any(x in a for x in ("width", "z-index", "opacity", "offset", "radius", "extrude")):
                        "these things are float's or not in table at all"
                        try:
                          ra[a] = float(b)
                        except ValueError:
                          pass
                      elif "dashes" in a:
                        "these things are arrays of float's or not in table at all"
                        try:
                          b = b.split(",")
                          b = [float(x) for x in b]
                          ra[a]= b
                        except ValueError:
                          pass
                      else:
                        ra[a]=b
                    
                    ra["layer"] = float(tags.get("layer",0))*100+ra.get("z-index",1) # calculating z-index
                    for k,v in ra.items():  # if a value is empty, we don't need it - renderer will do as default.
                      if not v:
                        del ra[k]
                    if "object-id" not in ra:
                      ra["object-id"] = str(object_id)
                    for x in sl:
                      if x.get("object-id","1") == ra["object-id"]:
                        x.update(ra)
                        break
                    else:
                      sl.append(ra)
                    object_id += 1
                  return sl
                          #a = ""
                          #if (r is ShapeStyle) {
                                  #a=sl.shapeStyles;
                                  #if (ShapeStyle(r).width>sl.maxwidth && !r.evals['width']) { sl.maxwidth=ShapeStyle(r).width; }
                          #} else if (r is ShieldStyle) {
                                  #a=sl.shieldStyles;
                          #} else if (r is TextStyle) {
                                  #a=sl.textStyles;
                          #} else if (r is PointStyle) {
                                  #a=sl.pointStyles;
                                  #w=0;
                                  #if (PointStyle(r).icon_width && !PointStyle(r).evals['icon_width']) {
                                          #w=PointStyle(r).icon_width;
                                  #} else if (PointStyle(r).icon_image && imageWidths[PointStyle(r).icon_image]) {
                                          #w=imageWidths[PointStyle(r).icon_image];
                                  #}
                                  #if (w>sl.maxwidth) { sl.maxwidth=w; }
                          #} else if (r is InstructionStyle) {
                                  #if (InstructionStyle(r).breaker) { return; }
                                  #if (InstructionStyle(r).set_tags) {
                                          #for (var k:String in InstructionStyle(r).set_tags) { tags[k]=InstructionStyle(r).set_tags[k]; }
                                  #}
                                  #continue;
                          #}
                          #if (r.drawn) { tags[':drawn']='yes'; }
                          #tags['_width']=sl.maxwidth;

                          #r.runEvals(tags);
                          #if (a[r.sublayer]) {
                                  ## // If there's already a style on this sublayer, then merge them
                                  ## // (making a deep copy if necessary to avoid altering the root style)
                                  #if (!a[r.sublayer].merged) { a[r.sublayer]=a[r.sublayer].deepCopy(); }
                                  #a[r.sublayer].mergeWith(r);
                          #} else {
                                  ## // Otherwise, just assign it
                                  #a[r.sublayer]=r;
                          #}
                  #}
          #}


          ## // Test a ruleChain
          ## // - run a set of tests in the chain
          ## //              works backwards from at position "pos" in array, or -1  for the last
          ## //              separate tags object is required in case they've been dynamically retagged
          ## // - if they fail, return false
          ## // - if they succeed, and it's the last in the chain, return happily
          ## // - if they succeed, and there's more in the chain, rerun this for each parent until success

          #private function testChain(chain:Array,pos:int,obj:Entity,tags:Object):Boolean {
                  #if (pos==-1) { pos=chain.length-1; }

                  #var r:Rule=chain[pos];
                  #if (!r.test(obj, tags)) { return false; }
                  #if (pos==0) { return true; }

                  #var o:Array=obj.parentObjects;
                  #for each (var p:Entity in o) {
                          #if (testChain(chain, pos-1, p, p.getTagsHash() )) { return true; }
                  #}
                  #return false;
          #}

  def testChain(self,chain, obj, tags, zoom):
    """
    Tests an object against a chain
    """
    ### FIXME: total MapCSS misreading
    for r in chain:
      if r.test(obj,tags,zoom):
        return True
    return False


          ## // ---------------------------------------------------------------------------------------------
          ## // Methods to add properties (used by parsers such as MapCSS)

          
  def newGroup(self):
    """
    starts a new ruleChain in this.ruleChains
    """
    if (len(self.ruleChains[self.rcpos])>0): 
                          self.ruleChains.append([])
                  #}
          #}


  def newObject(self,e=''):
    """
    adds into the current ruleChain (starting a new Rule)
    """
    self.ruleChains[self.rcpos].append(Rule(e))
    self.ruleChains[self.rcpos][len(self.ruleChains[self.rcpos])-1].minZoom=float(self.scalepair[0])
    self.ruleChains[self.rcpos][len(self.ruleChains[self.rcpos])-1].maxZoom=float(self.scalepair[1])


          
  def addZoom(self,z):
    """
    adds into the current ruleChain (existing Rule)
    """
          
    self.ruleChains[self.rcpos][len(self.ruleChains[self.rcpos])-1].minZoom=float(z[0])
    self.ruleChains[self.rcpos][len(self.ruleChains[self.rcpos])-1].maxZoom=float(z[1])
          


  def addCondition(self,c):
    """
    adds into the current ruleChain (existing Rule)
    """
    self.ruleChains[self.rcpos][len(self.ruleChains[self.rcpos])-1].conditions.append(c)


  def addStyles(self, a):
    """
    adds to this.styles
    """
    rb = []
    for r in a:
      ra = {}
      for a,b in r.iteritems():
        if "text" == a[-4:]:
          if b.strip()[:5] != "eval(":
            b = "eval(tag(\""+b+"\"))"

        if b.strip()[:5] == "eval(":
          b = Eval(b)
        ra[a] = b
      rb.append(ra)
   # print rb
    self.styles = self.styles + rb
