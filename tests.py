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


try:
    import unittest2 as unittest
except ImportError:
    import unittest

from jinja2 import Environment

import renderspec


class RenderspecContextFunctionTests(unittest.TestCase):
    """test functions which do some calculation based on the context"""
    def test_context_license_spdx(self):
        self.assertEqual(
            renderspec._context_license_spdx(
                {'spec_style': 'suse'}, 'Apache-2.0'),
            'Apache-2.0'
        )
        self.assertEqual(
            renderspec._context_license_spdx(
                {'spec_style': 'fedora'}, 'Apache-2.0'),
            'ASL 2.0'
        )

    def test_context_py2pkg_pgkname_only(self):
        self.assertEqual(
            renderspec._context_py2pkg(
                {'spec_style': 'suse', 'epochs': {}}, 'oslo.config'),
            'python-oslo.config'
        )
        self.assertEqual(
            renderspec._context_py2pkg(
                {'spec_style': 'fedora', 'epochs': {}}, 'oslo.config'),
            'python-oslo-config'
        )

    def test_context_py2pkg_pgkname_and_version(self):
        self.assertEqual(
            renderspec._context_py2pkg(
                {'spec_style': 'suse', 'epochs': {}},
                'oslo.config', ('>=', '1.2.3')),
            'python-oslo.config >= 1.2.3'
        )
        self.assertEqual(
            renderspec._context_py2pkg(
                {'spec_style': 'fedora', 'epochs': {}},
                'oslo.config', ('==', '1.2.3~a0')),
            'python-oslo-config == 1.2.3~a0'
        )

    def test_context_py2pkg_pgkname_and_version_and_epoch(self):
        self.assertEqual(
            renderspec._context_py2pkg(
                {'spec_style': 'suse', 'epochs': {'oslo.config': '4'}},
                'oslo.config', ('>=', '1.2.3')),
            'python-oslo.config >= 4:1.2.3'
        )

    def test_context_py2pkg_pgkname_and_epoch_no_version(self):
        self.assertEqual(
            renderspec._context_py2pkg(
                {'spec_style': 'suse', 'epochs': {'oslo.config': '4'}},
                'oslo.config'),
            'python-oslo.config'
        )


class RenderspecTemplateFilterTests(unittest.TestCase):
    def setUp(self):
        """create a Jinja2 environment and register the standard filters"""
        self.env = Environment()
        renderspec._env_register_filters_and_globals(self.env)

    def test_render_filter_py2pkg_oldstyle(self):
        template = self.env.from_string("{{ 'requests' | py2pkg }} >= 2.8.1")
        self.assertEqual(
            template.render(spec_style='suse', epochs={}),
            'python-requests >= 2.8.1')

    def test_render_filter_py2pkg(self):
        template = self.env.from_string(
            "{{ 'requests' | py2pkg }}")
        self.assertEqual(
            template.render(spec_style='suse', epochs={}),
            'python-requests')

    def test_render_filter_py2pkg_with_version(self):
        template = self.env.from_string(
            "{{ 'requests' | py2pkg(('>=', '2.8.1')) }}")
        self.assertEqual(
            template.render(spec_style='suse', epochs={}),
            'python-requests >= 2.8.1')

    def test_render_filter_py2pkg_with_version_and_epoch(self):
        template = self.env.from_string(
            "{{ 'requests' | py2pkg(('>=', '2.8.1')) }}")
        self.assertEqual(
            template.render(spec_style='suse', epochs={'requests': '1'}),
            'python-requests >= 1:2.8.1')


class RenderspecTemplateFunctionTests(unittest.TestCase):
    def setUp(self):
        """create a Jinja2 environment and register the standard filters"""
        self.env = Environment()
        renderspec._env_register_filters_and_globals(self.env)

    def test_render_func_py2pkg(self):
        template = self.env.from_string(
            "{{ py2pkg('requests') }}")
        self.assertEqual(
            template.render(spec_style='suse', epochs={}),
            'python-requests')

    def test_render_func_py2pkg_with_version(self):
        template = self.env.from_string(
            "{{ py2pkg('requests', ('>=', '2.8.1')) }}")
        self.assertEqual(
            template.render(spec_style='suse', epochs={}),
            'python-requests >= 2.8.1')

    def test_render_func_py2pkg_with_version_and_epoch(self):
        template = self.env.from_string(
            "{{ py2pkg('requests', ('>=', '2.8.1')) }}")
        self.assertEqual(
            template.render(spec_style='suse', epochs={'requests': '1'}),
            'python-requests >= 1:2.8.1')


if __name__ == '__main__':
    unittest.main()
