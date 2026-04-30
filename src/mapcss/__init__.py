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
import os
import logging
from .StyleChooser import StyleChooser
from .Condition import Condition
from .Rule import type_matches


def _test_feature_compatibility(feature_type, selector_type):
    """Compatibility export for kothic MVT/Mapbox helpers."""
    return feature_type in type_matches.get(selector_type, (selector_type,))


NEEDED_KEYS = set(["width", "casing-width", "casing-width-add", "fill-color", "fill-image", "icon-image", "text", "extrude",
                   "background-image", "background-color", "pattern-image", "shield-color", "symbol-shape"])

# TODO: Unused constant
WHITESPACE = re.compile(r'\s+ ', re.S | re.X)

COMMENT = re.compile(r'\/\* .*? \*\/ \s* ', re.S | re.X)
CLASS = re.compile(r'([\.:]:?[*\w]+) \s* ', re.S | re.X)
#NOT_CLASS = re.compile(r'!([\.:]\w+) \s* ', re.S | re.X)
ZOOM = re.compile(r'\| \s* z([\d\-]+) \s* ', re.I | re.S | re.X)
GROUP = re.compile(r', \s* ', re.I | re.S | re.X)
CONDITION = re.compile(r'\[(.+?)\] \s* ', re.S | re.X)
OBJECT = re.compile(r'(\*|[\w]+) \s* ', re.S | re.X)
DECLARATION = re.compile(r'\{(.*?)\} \s* ', re.S | re.X)
IMPORT = re.compile(r'@import\("(.+?)"\); \s* ', re.S | re.X)
VARIABLE_SET = re.compile(r'@([a-z][\w\d]*) \s* : \s* (.+?) \s* ; \s* ', re.S | re.X | re.I)
UNKNOWN = re.compile(r'(\S+) \s* ', re.S | re.X)

ZOOM_MINMAX = re.compile(r'(\d+)\-(\d+) $', re.S | re.X)
ZOOM_MIN    = re.compile(r'(\d+)\-      $', re.S | re.X)
ZOOM_MAX    = re.compile(r'     \-(\d+) $', re.S | re.X)
ZOOM_SINGLE = re.compile(r'       (\d+) $', re.S | re.X)

# TODO: move to Condition.py
CONDITION_TRUE    = re.compile(r'\s* ([:\w]+) \s* [?] \s*  $', re.I | re.S | re.X)
CONDITION_invTRUE = re.compile(r'\s* [!] \s* ([:\w]+) \s* [?] \s*  $', re.I | re.S | re.X)
CONDITION_FALSE   = re.compile(r'\s* ([:\w]+) \s* = \s* no  \s*  $', re.I | re.S | re.X)
CONDITION_SET     = re.compile(r'\s* ([-:\w]+) \s* $', re.S | re.X)
CONDITION_UNSET   = re.compile(r'\s* !([:\w]+) \s* $', re.S | re.X)
CONDITION_EQ      = re.compile(r'\s* ([:\w]+) \s* =  \s* (.+) \s* $', re.S | re.X)
CONDITION_NE      = re.compile(r'\s* ([:\w]+) \s* != \s* (.+) \s* $', re.S | re.X)
CONDITION_GT      = re.compile(r'\s* ([:\w]+) \s* >  \s* (.+) \s* $', re.S | re.X)
CONDITION_GE      = re.compile(r'\s* ([:\w]+) \s* >= \s* (.+) \s* $', re.S | re.X)
CONDITION_LT      = re.compile(r'\s* ([:\w]+) \s* <  \s* (.+) \s* $', re.S | re.X)
CONDITION_LE      = re.compile(r'\s* ([:\w]+) \s* <= \s* (.+) \s* $', re.S | re.X)
CONDITION_REGEX   = re.compile(r'\s* ([:\w]+) \s* =~\/ \s* (.+) \/ \s* $', re.S | re.X)

ASSIGNMENT_EVAL = re.compile(r"\s* (\S+) \s* \:      \s* eval \s* \( \s* ' (.+?) ' \s* \) \s* $", re.I | re.S | re.X)
ASSIGNMENT      = re.compile(r'\s* (\S+) \s* \:      \s*          (.+?) \s*                   $', re.S | re.X)
SET_TAG_EVAL    = re.compile(r"\s* set \s+(\S+)\s* = \s* eval \s* \( \s* ' (.+?) ' \s* \) \s* $", re.I | re.S | re.X)
SET_TAG         = re.compile(r'\s* set \s+(\S+)\s* = \s*          (.+?) \s*                   $', re.I | re.S | re.X)
SET_TAG_TRUE    = re.compile(r'\s* set \s+(\S+)\s* $', re.I | re.S | re.X)
EXIT            = re.compile(r'\s* exit \s* $', re.I | re.S | re.X)

oNONE = 0
oZOOM = 2
oGROUP = 3
oCONDITION = 4
oOBJECT = 5
oDECLARATION = 6
oSUBPART = 7
oVARIABLE_SET = 8

# TODO: Following block of variables is never used
DASH = re.compile(r'\-/g')
COLOR = re.compile(r'color$/')
BOLD = re.compile(r'^bold$/i')
ITALIC = re.compile(r'^italic|oblique$/i')
UNDERLINE = re.compile(r'^underline$/i')
CAPS = re.compile(r'^uppercase$/i')
CENTER = re.compile(r'^center$/i')

# TODO: Remove unused HEX variable
HEX = re.compile(r'^#([0-9a-f]+)$/i')
VARIABLE = re.compile(r'@([a-z][\w\d]*)')


class MapCSS():
    def __init__(self, minscale=0, maxscale=19):
        """
        """
        self.cache = {}
        self.cache["style"] = {}
        self.minscale = minscale
        self.maxscale = maxscale
        self.scalepair = (minscale, maxscale)
        self.choosers = []
        self.choosers_by_type = {}
        self.choosers_by_type_zoom_tag = {}
        self.variables = {}
        self.unused_variables = set()
        self.style_loaded = False

    def parseZoom(self, s):
        if ZOOM_MINMAX.match(s):
            return tuple([float(i) for i in ZOOM_MINMAX.match(s).groups()])
        elif ZOOM_MIN.match(s):
            return float(ZOOM_MIN.match(s).groups()[0]), self.maxscale
        elif ZOOM_MAX.match(s):
            return float(self.minscale), float(ZOOM_MAX.match(s).groups()[0])
        elif ZOOM_SINGLE.match(s):
            return float(ZOOM_SINGLE.match(s).groups()[0]), float(ZOOM_SINGLE.match(s).groups()[0])
        else:
            # TODO: Should we raise an exception here?
            logging.error("unparsed zoom: %s" % s)

    def build_choosers_tree(self, clname, type, cltag):
        if type not in self.choosers_by_type_zoom_tag:
            self.choosers_by_type_zoom_tag[type] = {}
        for zoom in range(self.minscale, self.maxscale + 1):
            if zoom not in self.choosers_by_type_zoom_tag[type]:
                self.choosers_by_type_zoom_tag[type][zoom] = {}
            if clname not in self.choosers_by_type_zoom_tag[type][zoom]:
                self.choosers_by_type_zoom_tag[type][zoom][clname] = {'arr': [], 'set': set()}
        if type in self.choosers_by_type:
            cltags = cltag if isinstance(cltag, (dict, set, list, tuple)) else {cltag}
            for chooser in self.choosers_by_type[type]:
                chooser_tags = chooser.extract_tags()
                if '*' in chooser_tags or any(tag in cltags for tag in chooser_tags):
                    for zoom in range(int(chooser.selzooms[0]), int(chooser.selzooms[1]) + 1):
                        if chooser not in self.choosers_by_type_zoom_tag[type][zoom][clname]['set']:
                            self.choosers_by_type_zoom_tag[type][zoom][clname]['arr'].append(chooser)
                            self.choosers_by_type_zoom_tag[type][zoom][clname]['set'].add(chooser)

    def finalize_choosers_tree(self):
        for ftype in self.choosers_by_type_zoom_tag.keys():
            for zoom in self.choosers_by_type_zoom_tag[ftype].keys():
                for clname in self.choosers_by_type_zoom_tag[ftype][zoom].keys():
                    # Discard unneeded unique set of choosers.
                    self.choosers_by_type_zoom_tag[ftype][zoom][clname] = self.choosers_by_type_zoom_tag[ftype][zoom][clname]['arr']
                    for i in range(0, len(self.choosers_by_type_zoom_tag[ftype][zoom][clname])):
                        chooser = self.choosers_by_type_zoom_tag[ftype][zoom][clname][i]
                        optimized = StyleChooser(chooser.scalepair)
                        optimized.styles = chooser.styles
                        optimized.eval_type = chooser.eval_type
                        optimized.has_evals = chooser.has_evals
                        optimized.has_runtime_conditions = chooser.has_runtime_conditions
                        optimized.selzooms = [zoom, zoom]
                        optimized.ruleChains = []
                        for rule in chooser.ruleChains:
                            # Discard chooser's rules that don't match type or zoom.
                            if ftype in rule.type_matches and zoom >= rule.minZoom and zoom <= rule.maxZoom:
                                optimized.ruleChains.append(rule)
                        self.choosers_by_type_zoom_tag[ftype][zoom][clname][i] = optimized


    def get_runtime_rules(self, clname, type, tags, zoom):
        """
        Returns array of runtime_conditions which are used for clname/type/tags/zoom
        """
        runtime_rules = []
        if type in self.choosers_by_type_zoom_tag:
            for chooser in self.choosers_by_type_zoom_tag[type][zoom][clname]:
                runtime_conditions = chooser.get_runtime_conditions(tags)
                if runtime_conditions:
                    runtime_rules.append(runtime_conditions)
        return runtime_rules

    # TODO: Renamed to `get_styles` because it returns a list of styles for each class `::XXX`
    # Refactoring idea: Maybe return dict with `object-id` as a key
    def get_style(self, clname, type, tags, zoom, xscale, zscale, filter_by_runtime_conditions,
                  strict_runtime_filtering=False, subset_runtime_filtering=False):
        style = []
        if type in self.choosers_by_type_zoom_tag:
            for chooser in self.choosers_by_type_zoom_tag[type][zoom][clname]:
                style = chooser.updateStyles(style, tags, xscale, zscale, filter_by_runtime_conditions,
                                             strict_runtime_filtering, subset_runtime_filtering)
        style = [x for x in style if x["object-id"] != "::*"]
        for x in style:
            for k, v in [('width', 0), ('casing-width', 0)]:
                if k in x:
                    if x[k] == v:
                        del x[k]
        st = []
        for x in style:
            if not NEEDED_KEYS.isdisjoint(x):
                st.append(x)
        style = st
        return style

    def get_colors(self):
        colors = self.choosers_by_type.get("colors")
        if colors is not None:
            return colors[0].styles[0]
        return None

    def get_style_dict(self, clname, type, tags={}, zoom=0, xscale=1, zscale=.5, olddict={},
                       filter_by_runtime_conditions=None, strict_runtime_filtering=False,
                       subset_runtime_filtering=False):
        """
        Kothic styling API
        """
        r = self.get_style(clname, type, tags, zoom, xscale, zscale, filter_by_runtime_conditions,
                           strict_runtime_filtering, subset_runtime_filtering)
        d = olddict
        for x in r:
            if x.get('object-id', '') not in d:
                d[x.get('object-id', '')] = {}
            d[x.get('object-id', '')].update(x)
        return d

    def subst_variables(self, t):
        """ Expects an array from parseDeclaration. """
        for k in t[0]:
            t[0][k] = VARIABLE.sub(self.get_variable, t[0][k])
        return t

    def get_variable(self, m):
        name = m.group()[1:]
        if name in self.unused_variables:
            self.unused_variables.remove(name)
        if name not in self.variables:
            raise Exception("Variable not found: " + str(format(name)))
        return self.variables[name] if name in self.variables else m.group()

    def parse(self, css=None, clamp=True, stretch=1000, filename=None, static_tags={},
              dynamic_tags=set(), legacy_zindex=False):
        """
        Parses MapCSS given as string
        """
        basepath = os.curdir
        if filename:
            basepath = os.path.dirname(filename)
        if not css:
            with open(filename) as css_file:
                css = css_file.read()
        if not self.style_loaded:
            self.choosers = []

        log = logging.getLogger('mapcss.parser')
        previous = oNONE  # what was the previous CSS word?
        sc = StyleChooser(self.scalepair)  # currently being assembled

        stck = [] # filename, original, remained
        stck.append([filename, css, css])
        try:
            while (len(stck) > 0):
                css = stck[-1][1].lstrip() # remained

                wasBroken = False
                while (css):
                    # Class - :motorway, :builtup, :hover
                    if CLASS.match(css):
                        if previous == oDECLARATION:
                            self.choosers.append(sc)
                            sc = StyleChooser(self.scalepair)
                        cond = CLASS.match(css).groups()[0]
                        log.debug("class found: %s" % (cond))
                        css = CLASS.sub("", css, 1)
                        sc.addCondition(Condition('eq', ("::class", cond)))
                        previous = oCONDITION

                    ## Not class - !.motorway, !.builtup, !:hover
                    #elif NOT_CLASS.match(css):
                        #if (previous == oDECLARATION):
                            #self.choosers.append(sc)
                            #sc = StyleChooser(self.scalepair)
                        #cond = NOT_CLASS.match(css).groups()[0]
                        #log.debug("not_class found: %s" % (cond))
                        #css = NOT_CLASS.sub("", css, 1)
                        #sc.addCondition(Condition('ne', ("::class", cond)))
                        #previous = oCONDITION

                    # Zoom
                    elif ZOOM.match(css):
                        if (previous != oOBJECT & previous != oCONDITION):
                            sc.newObject()
                        cond = ZOOM.match(css).groups()[0]
                        log.debug("zoom found: %s" % (cond))
                        css = ZOOM.sub("", css, 1)
                        sc.addZoom(self.parseZoom(cond))
                        previous = oZOOM

                    # Grouping - just a comma
                    elif GROUP.match(css):
                        css = GROUP.sub("", css, 1)
                        sc.newGroup()
                        had_main_tag = False
                        previous = oGROUP

                    # Condition - [highway=primary] or [population>1000]
                    elif CONDITION.match(css):
                        if (previous == oDECLARATION):
                            self.choosers.append(sc)
                            sc = StyleChooser(self.scalepair)
                            had_main_tag = False
                        if (previous != oOBJECT) and (previous != oZOOM) and (previous != oCONDITION):
                            sc.newObject()
                            had_main_tag = False
                        cond = CONDITION.match(css).groups()[0]
                        c = parseCondition(cond)
                        tag = c.extract_tag()
                        tag_type = static_tags.get(tag, None)
                        if tag == "*" or tag_type is not None:
                            if tag_type and had_main_tag:
                                if '!' in cond:
                                    condType = 'ne'
                                    cond = cond.replace('!', '')
                                else:
                                    condType = 'eq'
                                sc.addRuntimeCondition(Condition(condType, ('extra_tag', cond)))
                            else:
                                sc.addCondition(c)
                                if tag_type:
                                    had_main_tag = True
                        elif tag in dynamic_tags:
                            sc.addRuntimeCondition(c)
                        else:
                            raise Exception("Unknown tag '" + tag + "' in condition " + cond)
                        css = CONDITION.sub("", css, 1)
                        previous = oCONDITION

                    # Object - way, node, relation
                    elif OBJECT.match(css):
                        if (previous == oDECLARATION):
                            self.choosers.append(sc)
                            sc = StyleChooser(self.scalepair)
                        obj = OBJECT.match(css).groups()[0]
                        log.debug("object found: %s" % (obj))
                        css = OBJECT.sub("", css, 1)
                        sc.newObject(obj)
                        had_main_tag = False
                        previous = oOBJECT

                    # Declaration - {...}
                    elif DECLARATION.match(css):
                        if previous == oDECLARATION or previous == oNONE:
                            raise Exception("Declaration without conditions")
                        decl = DECLARATION.match(css).groups()[0]
                        log.debug("declaration found: %s" % (decl))
                        sc.addStyles(self.subst_variables(parseDeclaration(decl)))
                        css = DECLARATION.sub("", css, 1)
                        previous = oDECLARATION

                    # CSS comment
                    elif COMMENT.match(css):
                        log.debug("comment found")
                        css = COMMENT.sub("", css, 1)

                    # @import("filename.css");
                    elif IMPORT.match(css):
                        log.debug("import found")
                        import_filename = os.path.join(basepath, IMPORT.match(css).groups()[0])
                        try:
                            css = IMPORT.sub("", css, 1)
                            with open(import_filename, "r") as import_file:
                                import_text = import_file.read()
                            stck[-1][1] = css # store remained part
                            stck.append([import_filename, import_text, import_text])
                            wasBroken = True
                            break
                        except IOError as e:
                            raise Exception("Cannot import file " + import_filename + "\n" + str(e))

                    # Variables
                    elif VARIABLE_SET.match(css):
                        name = VARIABLE_SET.match(css).groups()[0]
                        log.debug("variable set found: %s" % name)
                        self.variables[name] = VARIABLE_SET.match(css).groups()[1]
                        self.unused_variables.add( name )
                        css = VARIABLE_SET.sub("", css, 1)
                        previous = oVARIABLE_SET

                    # Unknown pattern
                    elif UNKNOWN.match(css):
                        raise Exception("Unknown construction: " + UNKNOWN.match(css).group())

                    # Must be unreachable
                    else:
                        raise Exception("Unexpected construction: " + css)

                    stck[-1][1] = css # store remained part

                if not wasBroken:
                    stck.pop()

            if (previous == oDECLARATION):
                self.choosers.append(sc)
                sc = StyleChooser(self.scalepair)

        except Exception as e:
            filename = stck[-1][0] # filename
            css_orig = stck[-1][2] # original
            css = stck[-1][1] # remained
            line = css_orig[:-len(css)].count("\n") + 1
            # TODO: Handle filename is None
            msg = str(e) + "\nFile: " + filename + "\nLine: " + str(line)
            # TODO: Print stack trace of original exception `e`
            raise Exception(msg)

        try:
            # TODO: Drop support of z-index because `clamp` is always False and z-index properties unused in Organic Maps)
            if clamp:
                "clamp z-indexes, so they're tightly following integers"
                zindex = set()
                for chooser in self.choosers:
                    for stylez in chooser.styles:
                        zindex.add(float(stylez.get('z-index', 0)))
                zindex = list(zindex)
                zindex.sort()
                zoffset = len([x for x in zindex if x < 0]) if legacy_zindex else 0
                for chooser in self.choosers:
                    for stylez in chooser.styles:
                        if 'z-index' in stylez:
                            res = zindex.index(float(stylez.get('z-index', 0))) - zoffset
                            if stretch:
                                stylez['z-index'] = stretch * res / len(zindex)
                            else:
                                stylez['z-index'] = res
        except TypeError:
            # TODO: Better error handling here
            pass

        # Group MapCSS styles by object type: 'area', 'line', 'way', 'node'
        for chooser in self.choosers:
            for t in chooser.compatible_types:
                if t not in self.choosers_by_type:
                    self.choosers_by_type[t] = [chooser]
                else:
                    self.choosers_by_type[t].append(chooser)

        if self.unused_variables:
            # TODO: Do not print warning here. Instead let libkomwn.komap_mapswithme(...) analyze unused_variables
            print(f"Warning: Unused variables: {', '.join(self.unused_variables)}")

# TODO: move to Condition.py
def parseCondition(s):
    log = logging.getLogger('mapcss.parser.condition')

    if CONDITION_TRUE.match(s):
        a = CONDITION_TRUE.match(s).groups()
        log.debug("condition true: %s" % (a[0]))
        return Condition('true', a)

    if CONDITION_invTRUE.match(s):
        a = CONDITION_invTRUE.match(s).groups()
        log.debug("condition invtrue: %s" % (a[0]))
        return Condition('ne', (a[0], "yes"))

    if CONDITION_FALSE.match(s):
        a = CONDITION_FALSE.match(s).groups()
        log.debug("condition false: %s" % (a[0]))
        return Condition('false', a)

    if CONDITION_SET.match(s):
        a = CONDITION_SET.match(s).groups()
        log.debug("condition set: %s" % (a))
        return Condition('set', a)

    if CONDITION_UNSET.match(s):
        a = CONDITION_UNSET.match(s).groups()
        log.debug("condition unset: %s" % (a))
        return Condition('unset', a)

    if CONDITION_NE.match(s):
        a = CONDITION_NE.match(s).groups()
        log.debug("condition NE: %s = %s" % (a[0], a[1]))
        return Condition('ne', a)

    if CONDITION_LE.match(s):
        a = CONDITION_LE.match(s).groups()
        log.debug("condition LE: %s <= %s" % (a[0], a[1]))
        return Condition('<=', a)

    if CONDITION_GE.match(s):
        a = CONDITION_GE.match(s).groups()
        log.debug("condition GE: %s >= %s" % (a[0], a[1]))
        return Condition('>=', a)

    if CONDITION_LT.match(s):
        a = CONDITION_LT.match(s).groups()
        log.debug("condition LT: %s < %s" % (a[0], a[1]))
        return Condition('<', a)

    if CONDITION_GT.match(s):
        a = CONDITION_GT.match(s).groups()
        log.debug("condition GT: %s > %s" % (a[0], a[1]))
        return Condition('>', a)

    if CONDITION_REGEX.match(s):
        a = CONDITION_REGEX.match(s).groups()
        log.debug("condition REGEX: %s = %s" % (a[0], a[1]))
        return Condition('regex', a)

    if CONDITION_EQ.match(s):
        a = CONDITION_EQ.match(s).groups()
        log.debug("condition EQ: %s = %s" % (a[0], a[1]))
        return Condition('eq', a)

    else:
        raise Exception("condition UNKNOWN: " + s)


def parseDeclaration(s):
    """
    Parse declaration string into list of styles
    """
    t = {}
    for a in s.split(';'):
        # if ((o=ASSIGNMENT_EVAL.exec(a)))   { t[o[1].replace(DASH,'_')]=new Eval(o[2]); }
        if ASSIGNMENT.match(a):
            tzz = ASSIGNMENT.match(a).groups()
            t[tzz[0]] = tzz[1].strip().strip('"')
            logging.debug("%s == %s" % (tzz[0], tzz[1]))
        else:
            logging.debug("unknown %s" % (a))
    return [t] # TODO: don't wrap `t` dict into a list. Return `t` instead.


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    mc = MapCSS(0, 19)
