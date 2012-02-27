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
import logging
from hashlib import md5



from StyleChooser import StyleChooser
from Condition import Condition


WHITESPACE = re.compile(r'^ \s+ ', re.S | re.X)

COMMENT = re.compile(r'^ \/\* .+? \*\/ \s* ', re.S | re.X)
CLASS = re.compile(r'^ ([\.:]:?\w+) \s* ', re.S | re.X)
NOT_CLASS = re.compile(r'^ !([\.:]\w+) \s* ', re.S | re.X)
ZOOM = re.compile(r'^ \| \s* z([\d\-]+) \s* ', re.I | re.S | re.X)
GROUP = re.compile(r'^ , \s* ', re.I | re.S | re.X)
CONDITION = re.compile(r'^ \[(.+?)\] \s* ', re.S | re.X)
OBJECT = re.compile(r'^ (\w+) \s* ', re.S | re.X)
DECLARATION = re.compile(r'^ \{(.+?)\} \s* ', re.S | re.X)
UNKNOWN = re.compile(r'^ (\S+) \s* ', re.S | re.X)

ZOOM_MINMAX = re.compile(r'^ (\d+)\-(\d+) $', re.S | re.X)
ZOOM_MIN = re.compile(r'^ (\d+)\-      $', re.S | re.X)
ZOOM_MAX = re.compile(r'^      \-(\d+) $', re.S | re.X)
ZOOM_SINGLE = re.compile(r'^        (\d+) $', re.S | re.X)

CONDITION_TRUE = re.compile(r'^ \s* ([:\w]+) \s* [?] \s*  $', re.I | re.S | re.X)
CONDITION_invTRUE = re.compile(r'^ \s* [!] \s* ([:\w]+) \s* [?] \s*  $', re.I | re.S | re.X)
CONDITION_FALSE = re.compile(r'^ \s* ([:\w]+) \s* = \s* no  \s*  $', re.I | re.S | re.X)
CONDITION_SET = re.compile(r'^ \s* ([:\w]+) \s* $', re.S | re.X)
CONDITION_UNSET = re.compile(r'^ \s* !([:\w]+) \s* $', re.S | re.X)
CONDITION_EQ = re.compile(r'^ \s* ([:\w]+) \s* =  \s* (.+) \s* $', re.S | re.X)
CONDITION_NE = re.compile(r'^ \s* ([:\w]+) \s* != \s* (.+) \s* $', re.S | re.X)
CONDITION_GT = re.compile(r'^ \s* ([:\w]+) \s* >  \s* (.+) \s* $', re.S | re.X)
CONDITION_GE = re.compile(r'^ \s* ([:\w]+) \s* >= \s* (.+) \s* $', re.S | re.X)
CONDITION_LT = re.compile(r'^ \s* ([:\w]+) \s* <  \s* (.+) \s* $', re.S | re.X)
CONDITION_LE = re.compile(r'^ \s* ([:\w]+) \s* <= \s* (.+) \s* $', re.S | re.X)
CONDITION_REGEX = re.compile(r'^ \s* ([:\w]+) \s* =~\/ \s* (.+) \/ \s* $', re.S | re.X)

ASSIGNMENT_EVAL = re.compile(r"^ \s* (\S+) \s* \:      \s* eval \s* \( \s* ' (.+?) ' \s* \) \s* $", re.I | re.S | re.X)
ASSIGNMENT = re.compile(r'^ \s* (\S+) \s* \:      \s*          (.+?) \s*                   $', re.S | re.X)
SET_TAG_EVAL = re.compile(r"^ \s* set \s+(\S+)\s* = \s* eval \s* \( \s* ' (.+?) ' \s* \) \s* $", re.I | re.S | re.X)
SET_TAG = re.compile(r'^ \s* set \s+(\S+)\s* = \s*          (.+?) \s*                   $', re.I | re.S | re.X)
SET_TAG_TRUE = re.compile(r'^ \s* set \s+(\S+)\s* $', re.I | re.S | re.X)
EXIT = re.compile(r'^ \s* exit \s* $', re.I | re.S | re.X)

oZOOM=2
oGROUP=3
oCONDITION=4
oOBJECT=5
oDECLARATION=6
oSUBPART=7

DASH = re.compile(r'\-/g')
COLOR = re.compile(r'color$/')
BOLD = re.compile(r'^bold$/i')
ITALIC = re.compile(r'^italic|oblique$/i')
UNDERLINE = re.compile(r'^underline$/i')
CAPS = re.compile(r'^uppercase$/i')
CENTER = re.compile(r'^center$/i')

HEX = re.compile(r'^#([0-9a-f]+)$/i')


builtin_style = """
canvas {fill-color: #cccccc}
way {width: 1; casing-width:1; casing-color: white}
"""


  ## ** also needs to support @import rules

class MapCSS():
    def __init__(self,minscale=0,maxscale=19):
      """
      """
      self.cache = {}
      self.cache["style"] = {}
      self.minscale=minscale
      self.maxscale=maxscale
      self.scalepair = (minscale, maxscale)
      self.choosers = []
      self.style_loaded = False
      self.parse(builtin_style)
      self.style_loaded = False #override one after loading

    def parseZoom(self, s):

      if ZOOM_MINMAX.match(s):
        return tuple([float(i) for i in ZOOM_MINMAX.match(s).groups()])
      elif ZOOM_MIN.match(s):
        return float(ZOOM_MIN.match(s).groups()[0]), self.maxscale
      elif ZOOM_MAX.match(s):
        return float(self.minscale),float(ZOOM_MAX.match(s).groups()[0])
      elif ZOOM_SINGLE.match(s):
        return float(ZOOM_SINGLE.match(s).groups()[0]),float(ZOOM_SINGLE.match(s).groups()[0])
      else:
        logging.error("unparsed zoom: %s" %s)

    def get_style (self, type, tags={}, zoom=0, scale=1, zscale=.5):
      """
      Kothic styling API
      """
      shash = md5(repr(tags)+repr(zoom)).digest()
      if shash in self.cache["style"]:
        return self.cache["style"][shash]
      style = []
      
      #return [{"width": 1, "color":(0,0,0), "layer": 1}, {"width": 3, "color":(1,1,1), "layer":0}]
      for chooser in self.choosers:
        style = chooser.updateStyles(style, type, tags, zoom, scale, zscale)
      self.cache["style"][shash] = style
      return style

    def get_interesting_tags(self, type=None, zoom=None):
      """
      Get set of interesting tags.
      """
      tags = set()
      for chooser in self.choosers:
        tags.update(chooser.get_interesting_tags(type, zoom))
      return tags
    def get_sql_hints(self, type=None, zoom=None):
      """
      Get set of interesting tags.
      """
      hints = []
      for chooser in self.choosers:
        
        p = chooser.get_sql_hints(type, zoom)
        if p:
          if p[0] and p[1]:
           # print chooser.get_sql_hints(type, zoom)
          
            hints.append(p)
      #print hints
      return hints


    def parse(self, css):
      """
      Parses MapCSS given as string
      """
      if not self.style_loaded:
        self.choosers = []
      log = logging.getLogger('mapcss.parser')
      previous = 0  # what was the previous CSS word?
      sc=StyleChooser(self.scalepair) #currently being assembled
      #choosers=[]
      #o = []
      while (css): 

              # CSS comment
              if COMMENT.match(css):
                log.debug("comment found")
                css=COMMENT.sub("", css)

              #// Whitespace (probably only at beginning of file)
              elif WHITESPACE.match(css):
                log.debug("whitespace found")
                css=WHITESPACE.sub("",css)

              #// Class - .motorway, .builtup, :hover
              elif CLASS.match(css):
                if previous==oDECLARATION:
                  self.choosers.append(sc)
                  sc = StyleChooser(self.scalepair)
                
                cond = CLASS.match(css).groups()[0]
                log.debug("class found: %s"% (cond))
                css = CLASS.sub("", css)
                

                      
                sc.addCondition(Condition('eq',("::class",cond)))
                previous=oCONDITION;

              #// Not class - !.motorway, !.builtup, !:hover
              elif NOT_CLASS.match(css):
                if (previous==oDECLARATION):
                  self.choosers.append(sc)
                  sc = StyleChooser(self.scalepair)

                cond = NOT_CLASS.match(css).groups()[0]
                log.debug("not_class found: %s"% (cond))
                css = NOT_CLASS.sub("", css)
                sc.addCondition(Condition('ne',("::class",cond)))
                previous=oCONDITION;
                      #css=css.replace(NOT_CLASS,'');
                      #sc.addCondition(new Condition('unset',o[1]));
                      #previous=oCONDITION;

              #// Zoom
              elif ZOOM.match(css):
                if (previous!=oOBJECT & previous!=oCONDITION):
                  sc.newObject()

                cond = ZOOM.match(css).groups()[0]
                log.debug("zoom found: %s"% (cond))
                css=ZOOM.sub("",css)
                sc.addZoom(self.parseZoom(cond))
                previous=oZOOM;

                      #css=css.replace(ZOOM,'');
                      #var z:Array=parseZoom(o[1]);
                      #sc.addZoom(z[0],z[1]);
                      #previous=oZOOM;

              #// Grouping - just a comma
              elif GROUP.match(css):
                css=GROUP.sub("",css)
                sc.newGroup()
                previous=oGROUP

              #// Condition - [highway=primary]
              elif CONDITION.match(css):
                if (previous==oDECLARATION):
                  self.choosers.append(sc)
                  sc = StyleChooser(self.scalepair)
                if (previous!=oOBJECT) and (previous!=oZOOM) and (previous!=oCONDITION):
                  sc.newObject()
                cond = CONDITION.match(css).groups()[0]
                log.debug("condition found: %s"% (cond))
                css=CONDITION.sub("",css)
                sc.addCondition(parseCondition(cond))
                previous=oCONDITION;

              #// Object - way, node, relation
              elif OBJECT.match(css):
                if (previous==oDECLARATION):
                  self.choosers.append(sc)
                  sc = StyleChooser(self.scalepair)
                obj = OBJECT.match(css).groups()[0]
                log.debug("object found: %s"% (obj))
                css=OBJECT.sub("",css)
                sc.newObject(obj)
                previous=oOBJECT

              #// Declaration - {...}
              elif DECLARATION.match(css):
                decl = DECLARATION.match(css).groups()[0]
                log.debug("declaration found: %s"% (decl))
                sc.addStyles(parseDeclaration(decl))
                css=DECLARATION.sub("",css)
                previous=oDECLARATION

              #// Unknown pattern
              elif UNKNOWN.match(css):
                log.warning("unknown thing found: %s"%(UNKNOWN.match(css).group()))
                css=UNKNOWN.sub("",css)

              else:
                log.warning("choked on: %s"%(css))
                return 

      #print sc
      if (previous==oDECLARATION):
        self.choosers.append(sc)
        sc= StyleChooser(self.scalepair)
      #print self.choosers
      return 
#}




def parseCondition(s):
            log = logging.getLogger('mapcss.parser.condition')
            if      CONDITION_TRUE.match(s):
              a = CONDITION_TRUE.match(s).groups()
              log.debug("condition true: %s"%(a[0]))
              return  Condition('true'     ,a)
            if      CONDITION_invTRUE.match(s):
              a = CONDITION_invTRUE.match(s).groups()
              log.debug("condition invtrue: %s"%(a[0]))
              return  Condition('ne'     ,(a[0],"yes"))

            if      CONDITION_FALSE.match(s):
              a = CONDITION_FALSE.match(s).groups()
              log.debug("condition false: %s"%(a[0]))
              return  Condition('false'     ,a)


            if      CONDITION_SET.match(s):
              a = CONDITION_SET.match(s).groups()
              log.debug("condition set: %s"%(a))
              return  Condition('set'     ,a)


            if      CONDITION_UNSET.match(s):
              a = CONDITION_UNSET.match(s).groups()
              log.debug("condition unset: %s"%(a))
              return  Condition('unset'     ,a)

            if      CONDITION_NE.match(s):
              a = CONDITION_NE.match(s).groups()
              log.debug("condition NE: %s = %s"%(a[0], a[1]))
              return  Condition('ne'     ,a)
              ## FIXME: convert other conditions to python
            if      CONDITION_LE.match(s):
              a = CONDITION_LE.match(s).groups()
              log.debug("condition LE: %s <= %s"%(a[0], a[1]))
              return  Condition('<='     ,a)
            if      CONDITION_GE.match(s):
              a = CONDITION_GE.match(s).groups()
              log.debug("condition GE: %s >= %s"%(a[0], a[1]))
              return  Condition('>='     ,a)
            if      CONDITION_LT.match(s):
              a = CONDITION_LT.match(s).groups()
              log.debug("condition LT: %s < %s"%(a[0], a[1]))
              return  Condition('<'     ,a)
            if      CONDITION_GT.match(s):
              a = CONDITION_GT.match(s).groups()
              log.debug("condition GT: %s > %s"%(a[0], a[1]))
              return  Condition('>'     ,a)

            if      CONDITION_REGEX.match(s):
              a = CONDITION_REGEX.match(s).groups()
              log.debug("condition REGEX: %s = %s"%(a[0], a[1]))
              return  Condition('regex'     ,a)
              #else if ((o=CONDITION_REGEX.exec(s))) { return new Condition('regex',o[1],o[2]); }

            if      CONDITION_EQ.match(s):
              a = CONDITION_EQ.match(s).groups()
              log.debug("condition EQ: %s = %s"%(a[0], a[1]))
              return  Condition('eq'     ,a)

            else:
              log.warning("condition UNKNOWN: %s"%(s))


def parseDeclaration(s):
                  """
                  Parse declaration string into list of styles
                  """
                  styles=[]
                  t = {}

                  for a in s.split(';'):
                          #if ((o=ASSIGNMENT_EVAL.exec(a)))   { t[o[1].replace(DASH,'_')]=new Eval(o[2]); }
                          if ASSIGNMENT.match(a):
                            tzz = ASSIGNMENT.match(a).groups()
                            t[tzz[0]]=tzz[1].strip().strip('"')
                            logging.debug("%s == %s" % (tzz[0],tzz[1]) )
                          else:
                            logging.debug("unknown %s" % (a) )
                  return [t]
                          #else if ((o=SET_TAG_EVAL.exec(a))) { xs.addSetTag(o[1],new Eval(o[2])); }
                          #else if ((o=SET_TAG.exec(a)))      { xs.addSetTag(o[1],o[2]); }
                          #else if ((o=SET_TAG_TRUE.exec(a))) { xs.addSetTag(o[1],true); }
                          #else if ((o=EXIT.exec(a))) { xs.setPropertyFromString('breaker',true); }
                  #}

                  #// Find sublayer
                  #var sub:uint=5;
                  #if (t['z_index']) { sub=Number(t['z_index']); delete t['z_index']; }
                  #ss.sublayer=ps.sublayer=ts.sublayer=hs.sublayer=sub;
                  #xs.sublayer=10;

                  #// Munge special values
                  #if (t['font_weight']    ) { t['font_bold'  ]    = t['font_weight'    ].match(BOLD  )    ? true : false; delete t['font_weight']; }
                  #if (t['font_style']     ) { t['font_italic']    = t['font_style'     ].match(ITALIC)    ? true : false; delete t['font_style']; }
                  #if (t['text_decoration']) { t['font_underline'] = t['text_decoration'].match(UNDERLINE) ? true : false; delete t['text_decoration']; }
                  #if (t['text_position']  ) { t['text_center']    = t['text_position'  ].match(CENTER)    ? true : false; delete t['text_position']; }
                  #if (t['text_transform']) {
                          #// ** needs other transformations, e.g. lower-case, sentence-case
                          #if (t['text_transform'].match(CAPS)) { t['font_caps']=true; } else { t['font_caps']=false; }
                          #delete t['text_transform'];
                  #}

                  #// ** Do compound settings (e.g. line: 5px dotted blue;)

                  #// Assign each property to the appropriate style
                  #for (a in t) {
                          #// Parse properties
                          #// ** also do units, e.g. px/pt
                          #if (a.match(COLOR)) {
                                  #t[a] = parseCSSColor(t[a]);
                          #}

                          #// Set in styles
                          #if      (ss.hasOwnProperty(a)) { ss.setPropertyFromString(a,t[a]); }
                          #else if (ps.hasOwnProperty(a)) { ps.setPropertyFromString(a,t[a]); }
                          #else if (ts.hasOwnProperty(a)) { ts.setPropertyFromString(a,t[a]); }
                          #else if (hs.hasOwnProperty(a)) { hs.setPropertyFromString(a,t[a]); }
                  #}

                  #// Add each style to list
                  #if (ss.edited) { styles.push(ss); }
                  #if (ps.edited) { styles.push(ps); }
                  #if (ts.edited) { styles.push(ts); }
                  #if (hs.edited) { styles.push(hs); }
                  #if (xs.edited) { styles.push(xs); }
                  #return styles;
          #}




  #public static function parseCSSColor(colorStr:String):uint {
      #colorStr = colorStr.toLowerCase();
      #if (CSSCOLORS[colorStr])
          #return CSSCOLORS[colorStr];
      #else {
          #var match:Object = HEX.exec(colorStr);
          #if ( match )
              #return Number("0x"+match[1]);
      #}
      #return 0;
  #}
  #}
#}

if __name__ == "__main__":
  logging.basicConfig(level=logging.WARNING)
  mc = MapCSS(0,19)