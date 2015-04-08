#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# This file is part of JuliaBase, see http://www.juliabase.org.
# Copyright © 2008–2015 Forschungszentrum Jülich GmbH, Jülich, Germany
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU Affero General Public License as published by the Free
# Software Foundation, either version 3 of the License, or (at your option) any
# later version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU Affero General Public License for more
# details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""Functions and classes for building the main menu.
"""

from __future__ import absolute_import, unicode_literals

import collections


class MenuItem(object):
    def __init__(self, url="", icon_name=None, icon_url=None, icon_description=None, position="left", rule_before=False):
        self.url, self.icon_name, self.icon_url, self.icon_description, self.position, self.rule_before = \
                        url, icon_name, icon_url, icon_description, position, rule_before
        self.sub_items = collections.OrderedDict()
