#!/usr/bin/python
# Copyright (c) 2016 SUSE Linux GmbH
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import print_function

from packaging.requirements import Requirement


def get_requirements(lines):
    """parse the given lines and return a dict with pkg_name->version.
    lines must follow PEP0508"""
    requires = {}
    for l in lines:
        # skip comments and empty lines
        if l.startswith('#') or len(l.strip()) == 0:
            continue
        # remove trailing comments
        l = l.split('#')[0].rstrip(' ')
        r = Requirement(l)
        # check if we need the requirement
        if r.marker:
            # TODO (toabctl): currently we hardcode python 2.7 and linux2
            # see https://www.python.org/dev/peps/pep-0508/#environment-markers
            marker_env = {'python_version': '2.7', 'sys_platform': 'linux'}
            if not r.marker.evaluate(environment=marker_env):
                continue
        if r.specifier:
            # we want the lowest possible version
            # NOTE(toabctl): "min(r.specifier)" doesn't work.
            # see https://github.com/pypa/packaging/issues/69
            lowest = None
            for s in r.specifier:
                # we don't want a lowest version which is not allowed
                if s.operator == '!=':
                    continue
                if not lowest or s.version < lowest.version:
                    lowest = s

            if lowest:
                requires[r.name] = lowest.version
    return requires
