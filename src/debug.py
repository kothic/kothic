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
import datetime
import sys


def debug(st):
    """
    Debug write to stderr
    """

    sys.stderr.write(str(st) + "\n")
    sys.stderr.flush()


class Timer:
    """
    A small timer for debugging
    """
    def __init__(self, comment):
        self.time = datetime.datetime.now()
        self.comment = comment
        debug("%s started" % comment)

    def stop(self):
        debug("%s finished in %s" % (self.comment, str(datetime.datetime.now() - self.time)))
