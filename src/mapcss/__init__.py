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

from StyleChooser import StyleChooser
from Condition import Condition


WHITESPACE = re.compile(r'^ \s+ ', re.S | re.X)

COMMENT = re.compile(r'^ \/\* .+? \*\/ \s* ', re.S | re.X)
CLASS = re.compile(r'^ ([\.:]\w+) \s* ', re.S | re.X)
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

CONDITION_TRUE = re.compile(r'^ \s* ([:\w]+) \s* = \s* yes \s*  $', re.I | re.S | re.X)
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
      self.minscale=minscale
      self.maxscale=maxscale
      self.choosers = []
      self.style_loaded = False
      self.parse(builtin_style)
      self.style_loaded = False #override one after loading

    def parseZoom(self, s):

      if ZOOM_MINMAX.match(s):
        return ZOOM_MINMAX.match(s).groups()
      elif ZOOM_MIN.match(s):
        return ZOOM_MIN.match(s).groups()[0], self.maxscale
      elif ZOOM_MAX.match(s):
        return self.minscale,ZOOM_MAX.match(s).groups()[0]
      elif ZOOM_SINGLE.match(s):
        return ZOOM_SINGLE.match(s).groups()[0],ZOOM_SINGLE.match(s).groups()[0]
      else:
        logging.error("unparsed zoom: %s" %s)

    def get_style (self, type, tags, zoom, scale, zscale):
      """
      Kothic styling API
      """
      style = []
      #return [{"width": 1, "color":(0,0,0), "layer": 1}, {"width": 3, "color":(1,1,1), "layer":0}]
      for chooser in self.choosers:
        style = chooser.updateStyles(style, type, tags, zoom, scale, zscale)
      return style
      
    def parse(self, css):
      """
      Parses MapCSS given as string
      """
      if not self.style_loaded:
        self.choosers = []
      log = logging.getLogger('mapcss.parser')
      previous = 0  # what was the previous CSS word?
      sc=StyleChooser() #currently being assembled
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
                  sc = StyleChooser()
                
                cond = CLASS.match(css).groups()[0]
                log.debug("class found: %s"% (cond))
                css = CLASS.sub("", css)
                

                      
                sc.addCondition(Condition('set',cond));
                previous=oCONDITION;

              #// Not class - !.motorway, !.builtup, !:hover
              elif NOT_CLASS.match(css):
                if (previous==oDECLARATION):
                  self.choosers.append(sc)
                  sc = StyleChooser()

                cond = NOT_CLASS.match(css).groups()[0]
                log.debug("not_class found: %s"% (cond))
                css = NOT_CLASS.sub("", css)
                sc.addCondition(Condition('unset',cond));
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
                  sc = StyleChooser()
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
                  sc = StyleChooser()
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

      print sc
      if (previous==oDECLARATION):
        self.choosers.append(sc)
        sc= StyleChooser()
      print self.choosers
      return 
#}




def parseCondition(s):
            log = logging.getLogger('mapcss.parser.condition')
            if      CONDITION_TRUE.match(s):
              a = CONDITION_TRUE.match(s).groups()
              log.debug("condition true: %s"%(a[0]))
              return  Condition('true'     ,a)

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

              ## FIXME: convert other conditions to python

              #else if ((o=CONDITION_NE.exec(s)))    { return new Condition('ne'       ,o[1],o[2]); }
              #else if ((o=CONDITION_GT.exec(s)))    { return new Condition('>'        ,o[1],o[2]); }
              #else if ((o=CONDITION_GE.exec(s)))    { return new Condition('>='       ,o[1],o[2]); }
              #else if ((o=CONDITION_LT.exec(s)))    { return new Condition('<'        ,o[1],o[2]); }
              #else if ((o=CONDITION_LE.exec(s)))    { return new Condition('<='       ,o[1],o[2]); }
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
                  #var t:Object=new Object();
                  #var o:Object=new Object();
                  #var a:String, k:String;

                  #// Create styles
                  #var ss:ShapeStyle =new ShapeStyle() ;
                  #var ps:PointStyle =new PointStyle() ;
                  #var ts:TextStyle  =new TextStyle()  ;
                  #var hs:ShieldStyle=new ShieldStyle();
                  #var xs:InstructionStyle=new InstructionStyle();

                  for a in s.split(';'):
                          #if ((o=ASSIGNMENT_EVAL.exec(a)))   { t[o[1].replace(DASH,'_')]=new Eval(o[2]); }
                          if ASSIGNMENT.match(a):
                            tzz = ASSIGNMENT.match(a).groups()
                            t[tzz[0]]=tzz[1]
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
  mc.parse("""
     
  /*
  
  Stylesheet that mimicks, to a certain extent, potlatch 1.x
  Andy Allan, November 2009
  
  Based heavily on:
  MapCSS demonstration stylesheet
  Richard Fairhurst, October 2009
  
  */

  canvas   {antialiasing: full;}
  
  /* This rule applies to all areas (closed ways). Note that rules are applied in the order
  they appear in the file, so later rules may replace this one for some ways.
  This is used as a debugger for finding unstyled areas; it's obviously oversimplistic since
  it picks up closed-loop highways. */
  
  way :area { color: red; width: 1; fill-color: red; fill-opacity: 0.5; }
  
  /* A set of fairly standard rules.
  We use z-index to make sure high-priority roads appear above minor ones.
  The default z-index is 5. If an object matches multiple rules with the same
  z-index then the rules are "merged" (but individual properties become one or the other)  */
  
  way[highway=motorway],way[highway=motorway_link],
  way[highway=trunk],way[highway=trunk_link],
  way[highway=primary],way[highway=primary_link],
  way[highway=secondary],way[highway=secondary_link],
  way[highway=tertiary],way[highway=tertiary_link],
  way[highway=residential]                             { text: name; text-color: black; font-size: 7; text-position: line;}
  way[highway=motorway],way[highway=motorway_link]    { z-index: 9; color: #809BC0; width: 7; casing-color: black; casing-width: 8; }
  way[highway=trunk],way[highway=trunk_link]          { z-index: 9; color: #7FC97F; width: 7; casing-color: black; casing-width: 8; }
  way[highway=primary],way[highway=primary_link]      { z-index: 8; color: #E46D71; width: 7; casing-color: black; casing-width: 8; }
  way[highway=secondary],way[highway=secondary_link]  { z-index: 7; color: #FDBF6F; width: 7; casing-width: 8; }
  way[highway=tertiary],way[highway=unclassified]     { z-index: 6; color: #FEFECB; width: 5; casing-width: 7; }
  way[highway=residential]                            { z-index: 5; color: #E8E8E8; width: 5; casing-color: gray; casing-width: 7; }
  way[highway=service]                                { color: white; width: 3; casing-width: 5; }
  
  /* Pedestrian precincts need to be treated carefully. Only closed-loops with an explicit
  area=yes tag should be filled. The below doesn't yet work as intended. */
  way[highway=pedestrian] !:area { color: #ddddee; width: 5; casing-color: #555555; casing-width: 6; }
  way[highway=pedestrian] :area  { color: #555555; width: 1; fill-color: #ddddee; fill-opacity: 0.8; }
  
  way[highway=steps]     { color: #FF6644; width: 2; dashes: 4, 2; }
  way[highway=footway]   { color: #FF6644; width: 2; dashes: 6, 3; }
  way[highway=bridleway] { z-index:9; color: #996644; width: 2; dashes: 4, 2, 2, 2; }
  way[highway=track]     { color: #996644; width: 2; dashes: 4, 2; }
  way[highway=path]      { color: lightgreen; width: 2; dashes: 2, 2; }
  
  way[waterway=river], way[waterway=canal] { color: blue; width: 2; text:name; text-color:blue; font-size:9; text-position: offset; text-offset: 7;}
  
  way[barrier] {color: #000000; width: 1}
  
  /* Fills can be solid colour or bitmap images */
  
  
  way[natural] :area                          { color: #ADD6A5; width: 1; fill-color: #ADD6A5; fill-opacity: 0.2; }
  way[landuse] :area                          { color: #444444; width: 2; fill-color: #444444; fill-opacity: 0.3; }
  way[amenity],way[shop] :area                { color: #ADCEB5; width: 1; fill-color: #ADCEB5; fill-opacity: 0.2; }
  way[leisure],way[sport] :area               { color: #8CD6B5; width: 1; fill-color: #8CD6B5; fill-opacity: 0.2; }
  way[tourism] :area                          { color: #F7CECE; width: 1; fill-color: #F7CECE; fill-opacity: 0.2; }
  way[historic],way[ruins] :area              { color: #F7F7DE; width: 1; fill-color: #F7F7DE; fill-opacity: 0.2; }
  way[military] :area                         { color: #D6D6D6; width: 1; fill-color: #D6D6D6; fill-opacity: 0.2; }
  way[building] :area                         { color: #ff6ec7; width: 1; fill-color: #ff6ec7; fill-opacity: 0.2; }
  way[natural=water],
  way[waterway] :area               { color: blue;    width: 2; fill-color: blue;    fill-opacity: 0.2; }
  way[landuse=forest],way[natural=wood] :area { color: green;   width: 2; fill-color: green;   fill-opacity: 0.2; }
  way[leisure=pitch],way[leisure=park]        { color: #44ff44; width: 1; fill-color: #44ff44; fill-opacity: 0.2; }
  way[amenity=parking] :area                  { color: gray;    width: 1; fill-color: gray;    fill-opacity: 0.2; }
  way[public_transport=pay_scale_area] :area  { color: gray;    width: 1; fill-color: gray;    fill-opacity: 0.1; }
  
  /* Addressing. Nodes with addresses *and* match POIs should have a poi icon, so we put addressing first */
  
  node[addr:housenumber],
  node[addr:housename] { icon-image: circle; icon-width: 4; color: #B0E0E6; casing-color:blue; casing-width: 1; }
  way[addr:interpolation] { color: #B0E0E6; width: 3; dashes: 3,3;}
  
  /* POIs, too, can have bitmap icons - they can even be transparent */
  
  node[amenity=pub] { icon-image: icons/pub.png; text-offset: 15; font-family: DejaVu; text: name; font-size: 9; }
  node[place] { icon-image: icons/place.png; text-offset: 17; font-family: DejaVu; text: name; font-size: 9; font-weight: bold; text-decoration: underline; }
  node[railway=station] { icon-image: icons/station.png; text-offset: 13; font-family: DejaVu; text: name; font-size: 9; font-weight: bold; }
  node[aeroway=aerodrome] { icon-image: icons/airport.png; text-offset: 13; font-family: DejaVu; text: name; font-size: 10; }
  node[amenity=atm] { icon-image: icons/atm.png; }
  node[amenity=bank] { icon-image: icons/bank.png; text-offset: 15; text: name; }
  node[highway=bus_stop] { icon-image: icons/bus_stop.png; }
  node[amenity=cafe] { icon-image: icons/cafe.png; text-offset: 15; text: name; }
  node[shop=convenience] { icon-image: icons/convenience.png; text-offset:15; text:name; }
  node[shop=supermarket] { icon-image: icons/supermarket.png; text-offset:15; text:name; }
  node[amenity=fast_food] { icon-image: icons/fast_food.png; text-offset:15; text: name; }
  node[amenity=fire_station] { icon-image: icons/fire_station.png; }
  node[amenity=hospital] { icon-image: icons/hospital.png; }
  node[tourism=hotel] { icon-image: icons/hotel.png; }
  node[amenity=parking] { icon-image: icons/parking.png; }
  node[amenity=bicycle_parking] { icon-image: icons/parking_cycle.png; text-offset: 15; text: capacity; }
  node[amenity=pharmacy] { icon-image: icons/pharmacy.png; }
  node[amenity=pharmacy][dispensing=yes] { icon-image: icons/pharmacy_dispensing.png; }
  node[amenity=police] { icon-image: icons/police.png; }
  node[amenity=post_box] { icon-image: icons/post_box.png; }
  node[amenity=recycling] { icon-image: icons/recycling.png; }
  node[amenity=restaurant] { icon-image: icons/restaurant.png; }
  node[amenity=school] { icon-image: icons/school.png; }
  node[amenity=taxi] { icon-image: icons/taxi.png; }
  node[amenity=telephone] { icon-image: icons/telephone.png; }
  way node[barrier=gate], way node[highway=gate] { icon-image: icons/gate.png; }
  way node[barrier=bollard] { icon-image: icons/bollard.png; }
  node[barrier=cattle_grid] { icon-image: icons/cattle_grid.png; }
  
  /* We can stack styles at different z-index (depth) */
  
  way[railway=rail]
  { z-index: 6; color: black; width: 5; }
  { z-index: 7; color: white; width: 3; dashes: 12,12; }
  way[railway=platform] { color:black; width: 2; }
  way[railway=subway]
  { z-index: 6; color: #444444; width: 5; }
  { z-index: 7; color: white; width: 3; dashes: 8,8; }
  
  /* Bridge */
  way[bridge=yes], way[bridge=viaduct], way[bridge=suspension]
  { z-index: 4; color: white; width: eval('_width+3'); }
  { z-index: 3; color: black; width: eval('_width+6'); }
  
  /* Tunnel */
  way[tunnel=yes]
  { z-index: 4; color: white; width: eval('_width+2'); }
  { z-index: 3; color: black; width: eval('_width+6'); dashes: 4,4; }
  
  /* Oneway */
  way[oneway=yes] { z-index: 10; color: #444444; width: 3; dashes: 15,25; line-style: arrows; }
  
  
  /* Change the road colour based on dynamically set "highlighted" tag (see earlier) */
  
  way|z1-12 .highlighted { color: pink; }
  
  /* Interactive editors may choose different behaviour when a user mouses-over or selects
  an object. Potlatch 2 supports these but the stand-alone Halcyon viewer does not */
  
  way :hover      { z-index: 2; width: eval('_width+10'); color: #ffff99; }
  way :selected { z-index: 2; width: eval('_width+10'); color: yellow; opacity: 0.7;}
  way !:drawn { z-index:10; width: 0.5; color: gray; }
  
  node :selectedway { z-index: 9; icon-image: square; icon-width: 8; color: red; }
  node :hoverway { z-index: 9; icon-image: square; icon-width: 7; color: blue; }
  node !:drawn :poi { z-index: 2; icon-image: circle; icon-width: 4; color: green; casing-color: black; casing-width: 1; }
  node :selected { z-index: 1; icon-image: square; icon-width: eval('_width+10'); color: yellow; }
  node :junction :selectedway { z-index: 8; icon-image: square; icon-width: 12; casing-color: black; casing-width: 1; }
  
  /* Descendant selectors provide an easy way to style relations: this example means "any way
  which is part of a relation whose type=route". */
  
  relation[type=route] way { z-index: 1; width: 17; color: blue; opacity: 0.3; }
  relation[type=route][route=bicycle][network=ncn] way { z-index: 1; width: 12; color: red; opacity: 0.3; }
  relation[type=route][route=bicycle][network=rcn] way { z-index: 1; width: 12; color: cyan; opacity: 0.3; }
  relation[type=route][route=bicycle][network=lcn] way { z-index: 1; width: 12; color: blue; opacity: 0.3; }
  relation[type=route][route=foot] way { z-index: 1; width: 10; color: #80ff80; opacity: 0.6; }
  
  

  """)