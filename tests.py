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

from ddt import data, ddt, unpack

from jinja2 import Environment

from mock import Mock, patch
import os
import renderspec
import renderspec.versions
import shutil
import tempfile


@ddt
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

    @data(
        # without version
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         'oslo.config', None, 'python-oslo.config'),
        ({'spec_style': 'fedora', 'epochs': {}, 'requirements': {}},
         'oslo.config', None, 'python-oslo-config'),
        # with version
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         'oslo.config', ('>=', '1.2.3'), 'python-oslo.config >= 1.2.3'),
        ({'spec_style': 'fedora', 'epochs': {}, 'requirements': {}},
         'oslo.config', ('==', '1.2.3~a0'), 'python-oslo-config == 1.2.3~a0'),
        # with version, with epoch
        ({'spec_style': 'suse', 'epochs': {'oslo.config': 4},
          'requirements': {}},
         'oslo.config', ('>=', '1.2.3'), 'python-oslo.config >= 4:1.2.3'),
        # without version, with epoch
        ({'spec_style': 'suse', 'epochs': {'oslo.config': 4},
          'requirements': {}},
         'oslo.config', None, 'python-oslo.config'),
        # with version, with requirements
        ({'spec_style': 'suse', 'epochs': {},
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), 'python-oslo.config >= 4.5.6'),
        # without version, with requirements
        ({'spec_style': 'suse', 'epochs': {},
          'requirements': {'oslo.config': '1.2.3'}},
         'oslo.config', None, 'python-oslo.config >= 1.2.3'),
        # without version, with requirements, with epoch
        ({'spec_style': 'suse', 'epochs': {'oslo.config': 4},
          'requirements': {'oslo.config': '1.2.3'}},
         'oslo.config', None, 'python-oslo.config >= 4:1.2.3'),
        # with version, with requirements, with epoch
        ({'spec_style': 'suse', 'epochs': {'oslo.config': 4},
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), 'python-oslo.config >= 4:4.5.6'),
    )
    @unpack
    def test_context_py2pkg(self, context, pkg_name, pkg_version,
                            expected_result):
        self.assertEqual(
            renderspec._context_py2pkg(context, pkg_name, pkg_version),
            expected_result)

    def test_context_epoch_without_epochs(self):
        self.assertEqual(
            renderspec._context_epoch(
                {'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
                'oslo.config'), 0)

    def test_context_epoch_with_epochs(self):
        self.assertEqual(
            renderspec._context_epoch(
                {'spec_style': 'suse', 'epochs': {'oslo.config': 4},
                 'requirements': {}}, 'oslo.config'), 4)


@ddt
class RenderspecTemplateFunctionTests(unittest.TestCase):
    def setUp(self):
        """create a Jinja2 environment and register the standard filters"""
        self.env = Environment()
        renderspec._env_register_filters_and_globals(self.env)

    def test_render_func_license_spdx(self):
        template = self.env.from_string(
            "{{ license('Apache-2.0') }}")
        self.assertEqual(
            template.render(spec_style='fedora', epochs={}, requirements={}),
            'ASL 2.0')

    @data(
        # plain
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         "{{ py2pkg('requests') }}", "python-requests"),
        # with version
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         "{{ py2pkg('requests', ('>=', '2.8.1')) }}",
         "python-requests >= 2.8.1"),
        # with version, with epoch
        ({'spec_style': 'suse', 'epochs': {'requests': 4}, 'requirements': {}},
         "{{ py2pkg('requests', ('>=', '2.8.1')) }}",
         "python-requests >= 4:2.8.1"),
        # with version, with epoch, with requirements
        ({'spec_style': 'suse', 'epochs': {'requests': 4},
          'requirements': {'requests': '1.2.3'}},
         "{{ py2pkg('requests', ('>=', '2.8.1')) }}",
         "python-requests >= 4:2.8.1"),
        # without version, with epoch, with requirements
        ({'spec_style': 'suse', 'epochs': {'requests': 4},
          'requirements': {'requests': '1.2.3'}},
         "{{ py2pkg('requests') }}",
         "python-requests >= 4:1.2.3"),
    )
    @unpack
    def test_render_func_py2pkg(self, context, string, expected_result):
        template = self.env.from_string(string)
        self.assertEqual(
            template.render(**context),
            expected_result)

    def test_render_func_epoch_without_epochs(self):
        template = self.env.from_string(
            "Epoch: {{ epoch('requests') }}")
        self.assertEqual(
            template.render(spec_style='suse', epochs={}, requirements={}),
            'Epoch: 0')

    def test_render_func_epoch_with_epochs(self):
        template = self.env.from_string(
            "Epoch: {{ epoch('requests') }}")
        self.assertEqual(
            template.render(spec_style='suse', epochs={'requests': 1},
                            requirements={}),
            'Epoch: 1')

    @data(
        # plain name
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         "{{ py2name('requests') }}",
         "python-requests"),
        # name with epoch
        ({'spec_style': 'suse', 'epochs': {'requests': 4}, 'requirements': {}},
         "{{ py2name('requests') }}",
         "python-requests"),
        # name with epoch, with requirements
        ({'spec_style': 'suse', 'epochs': {'requests': 4},
          'requirements': {'requests': '1.4.0'}},
         "{{ py2name('requests') }}",
         "python-requests"),
    )
    @unpack
    def test_render_func_py2name(self, context, string, expected_result):
        """test the template context function called 'py2name()'"""
        template = self.env.from_string(string)
        self.assertEqual(
            template.render(**context),
            expected_result)


class RenderspecVersionsTests(unittest.TestCase):
    def test_without_version(self):
        requires = renderspec.versions.get_requirements(
            ['# a comment', '', '   ', 'pyasn1  # BSD', 'Paste'])
        self.assertEqual(requires, {})

    def test_with_single_version(self):
        requires = renderspec.versions.get_requirements(
            ['paramiko>=1.16.0  # LGPL'])
        self.assertEqual(requires, {'paramiko': '1.16.0'})

    def test_with_multiple_versions(self):
        requires = renderspec.versions.get_requirements(
            ['sphinx>=1.1.2,!=1.2.0,!=1.3b1,<1.3  # BSD'])
        self.assertEqual(requires, {'sphinx': '1.1.2'})

    def test_with_multiple_versions_and_invalid_lowest(self):
        requires = renderspec.versions.get_requirements(
            ['sphinx>=1.1.2,!=1.1.0,!=1.3b1,<1.3  # BSD'])
        self.assertEqual(requires, {'sphinx': '1.1.2'})

    def test_with_single_marker(self):
        requires = renderspec.versions.get_requirements(
            ["pywin32>=1.0;sys_platform=='win32'  # PSF"])
        self.assertEqual(requires, {})

    def test_with_multiple_markers(self):
        requires = renderspec.versions.get_requirements(
            ["""pyinotify>=0.9.6;sys_platform!='win32' and \
            sys_platform!='darwin' and sys_platform!='sunos5' # MIT"""])
        self.assertEqual(requires, {'pyinotify': '0.9.6'})


@ddt
class RenderspecCommonTests(unittest.TestCase):
    def test__get_requirements_single_file(self):
        tmpdir = tempfile.mkdtemp(prefix='renderspec-test_')
        try:
            f1 = os.path.join(tmpdir, 'f1')
            with open(f1, 'w+') as f:
                f.write('paramiko>=1.16.0\n'
                        'pyinotify>=0.9.6')
            self.assertDictEqual(
                renderspec._get_requirements([f1]),
                {'paramiko': '1.16.0', 'pyinotify': '0.9.6'})
        finally:
            shutil.rmtree(tmpdir)

    def test__get_requirements_multiple_files(self):
        tmpdir = tempfile.mkdtemp(prefix='renderspec-test_')
        try:
            f1 = os.path.join(tmpdir, 'f1')
            f2 = os.path.join(tmpdir, 'f2')
            with open(f1, 'w+') as f:
                f.write('paramiko>=1.17.0  # LGPL')
            with open(f2, 'w+') as f:
                f.write('paramiko>=1.16.0  # LGPL')
            # we expect the second file was used (because mentioned last)
            self.assertEqual(renderspec._get_requirements([f1, f2]),
                             {'paramiko': '1.16.0'})
        finally:
            shutil.rmtree(tmpdir)

    @data(
        ("{{ py2pkg('requests') }}", "suse", {}, {}, "python-requests"),
        ("{{ py2pkg('requests') }}", "fedora", {}, {}, "python-requests"),
        ("{{ py2pkg('requests') }}", "suse", {}, {"requests": '1.1.0'},
         "python-requests >= 1.1.0"),
    )
    @unpack
    def test_generate_spec(self, template, style, epochs, requirements,
                           expected_result):
        tmpdir = tempfile.mkdtemp(prefix='renderspec-test_')
        try:
            f1 = os.path.join(tmpdir, 'test.spec')
            with open(f1, 'w+') as f:
                f.write(template)
            rendered = renderspec.generate_spec(
                style, epochs, requirements, f1)
            self.assertEqual(rendered, expected_result)
        finally:
            shutil.rmtree(tmpdir)


class RenderspecDistroDetection(unittest.TestCase):
    def test_is_fedora(self):
        self.assertTrue(renderspec._is_fedora("CentOS Linux"))
        self.assertTrue(renderspec._is_fedora("Fedora"))
        self.assertTrue(renderspec._is_fedora("Red Hat Enterprise Linux 7.2"))
        self.assertFalse(renderspec._is_fedora("SUSE Linux Enterprise Server"))

    def test_get_default_distro(self):
        import platform
        platform.linux_distribution = Mock(
            return_value=('SUSE Linux Enterprise Server ', '12', 'x86_64'))
        self.assertEqual(renderspec._get_default_distro(),
                         "suse")
        platform.linux_distribution = Mock(
            return_value=('Fedora', '24', 'x86_64'))
        self.assertEqual(renderspec._get_default_distro(), "fedora")
        platform.linux_distribution = Mock(
            return_value=('Red Hat Enterprise Linux Server', '7.3', 'x86_64'))
        self.assertEqual(renderspec._get_default_distro(), "fedora")
        platform.linux_distribution = Mock(
            return_value=('CentOS Linux', '7.3', 'x86_64'))
        self.assertEqual(renderspec._get_default_distro(), "fedora")
        platform.linux_distribution = Mock(
            return_value=('debian', '7.0', 'x86_64'))
        self.assertEqual(renderspec._get_default_distro(), "unknown")


class RenderspecDistTeamplatesTests(unittest.TestCase):
    @patch('renderspec.distloader.get_dist_templates_path')
    def test_dist_templates(self, mock_dt_path):
        base_txt = ('Line before block\n'
                    '{% block footest %}{% endblock %}\n'
                    'Line after block\n')
        dt_txt = ('{% extends ".spec" %}'
                  '{% block footest %}'
                  'foo block\n'
                  'macro: {{ py2pkg("test") }}\n'
                  '{% endblock %}')
        expected_out = ('Line before block\n'
                        'foo block\n'
                        'macro: python-test\n'
                        'Line after block')
        tmpdir = tempfile.mkdtemp(prefix='renderspec-test_')
        try:
            # create .spec template
            base_path = os.path.join(tmpdir, 'foo.spec.j2')
            with open(base_path, 'w+') as f:
                f.write(base_txt)
            # create custom dist template
            dt_dir = os.path.join(tmpdir, 'dist-templates')
            os.mkdir(dt_dir)
            dt_path = os.path.join(dt_dir, 'loldistro.spec.j2')
            with open(dt_path, 'w+') as f:
                f.write(dt_txt)
            # mock this to use testing dist-tempaltes folder
            mock_dt_path.return_value = dt_dir

            out = renderspec.generate_spec('loldistro', {}, {}, base_path)
            self.assertEqual(out, expected_out)
        finally:
            shutil.rmtree(tmpdir)


if __name__ == '__main__':
    unittest.main()
