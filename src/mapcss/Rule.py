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

type_matches = {
    "": ('area', 'line', 'way', 'node'),
    "area": ("area", "way"),
    "node": ("node",),
    "way": ("line", "area", "way"),
    "line": ("line", "area"),
    }

class Rule():
    def __init__(self, s=''):
        self.runtime_conditions = None
        self.conditions = []
        # self.isAnd = True
        self.minZoom = 0
        self.maxZoom = 19
        if s == "*":
            s = ""
        self.subject = s    # "", "way", "node" or "relation"
        self.type_matches = type_matches[s] if s in type_matches else set()

    def __repr__(self):
        return "%s|z%s-%s %s %s" % (self.subject, self.minZoom, self.maxZoom, self.conditions, self.runtime_conditions)

    def test(self, tags):
        subpart = "::default"
        for condition in self.conditions:
            res = condition.test(tags)
            if not res:
                return False
            if type(res) != bool:
                subpart = res
        return subpart

    def get_compatible_types(self):
        return type_matches.get(self.subject, (self.subject,))

    def extract_tags(self):
        a = set()
        for condition in self.conditions:
            tag = condition.extract_tag()
            if tag != '*':
                a.add(tag)
            elif len(a) == 0:
                return set(["*"])

        return a
