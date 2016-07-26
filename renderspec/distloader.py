#!/usr/bin/python
# Copyright (c) 2016 Red Hat
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

import jinja2
from jinja2.loaders import TemplateNotFound
from jinja2.utils import open_if_exists
import os


def get_dist_templates_path():
    return os.path.join(os.path.dirname(__file__), 'dist-templates')


class RenderspecLoader(jinja2.BaseLoader):
    """A special template loader which allows rendering supplied .spec template
    with distro specific blocks maintained as part of renderspec.

    '.spec' returns the spec template (which you need to supply during init)
    while other strings map to corresponding child templates included
    in renderspec which simply extend the '.spec' template.
    """
    base_ref = '.spec'
    template_postfix = '.spec.j2'

    def __init__(self, template_fn, encoding='utf-8'):
        self.base_fn = template_fn
        self.encoding = encoding
        self.disttemp_path = get_dist_templates_path()

    def get_source(self, environment, template):
        if template == self.base_ref:
            fn = self.base_fn
        else:
            fn = os.path.join(self.disttemp_path,
                              template + self.template_postfix)

        f = open_if_exists(fn)
        if not f:
            return TemplateNotFound(template)
        try:
            contents = f.read().decode(self.encoding)
        finally:
            f.close()

        mtime = os.path.getmtime(self.base_fn)

        def uptodate():
            try:
                return os.path.getmtime(self.base_fn) == mtime
            except OSError:
                return False

        return contents, fn, uptodate

    def list_templates(self):
        found = set([self.base_ref])
        walk_dir = os.walk(self.disttemp_path)
        for _, _, filenames in walk_dir:
            for fn in filenames:
                if fn.endswith(self.template_postfix):
                    template = fn[:-len(self.template_postfix)]
                    found.add(template)
        return sorted(found)
