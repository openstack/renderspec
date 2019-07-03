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
from jinja2.exceptions import TemplateRuntimeError

from mock import Mock, patch
import os
import renderspec
import renderspec.contextfuncs
import renderspec.utils
import renderspec.versions
import shutil
import tempfile
import time


@ddt
class RenderspecContextFunctionTests(unittest.TestCase):
    """test functions which do some calculation based on the context"""
    def test_context_license_spdx(self):
        self.assertEqual(
            renderspec.contextfuncs._context_license_spdx(
                {'spec_style': 'suse'}, 'Apache-2.0'),
            'Apache-2.0'
        )
        self.assertEqual(
            renderspec.contextfuncs._context_license_spdx(
                {'spec_style': 'fedora'}, 'Apache-2.0'),
            'ASL 2.0'
        )

    @data(
        # without version
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         'oslo.config', None, None, 'python-oslo.config'),
        ({'spec_style': 'fedora', 'epochs': {}, 'requirements': {}},
         'oslo.config', None, None, 'python-oslo-config'),
        # without version, multiple python versions
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         'oslo.config', None, ('py', 'py3'),
         'python-oslo.config python3-oslo.config'),
        # with version
        ({'epochs': {}, 'requirements': {}},
         'oslo.config', ('>=', '1.2.3'), None, 'python-oslo.config >= 1.2.3'),
        ({'spec_style': 'fedora', 'epochs': {}, 'requirements': {}},
         'oslo.config', ('==', '1.2.3~a0'), None,
         'python-oslo-config == 1.2.3~a0'),
        # with version, with epoch
        ({'epochs': {'oslo.config': 4},
          'requirements': {}},
         'oslo.config', ('>=', '1.2.3'), None,
         'python-oslo.config >= 4:1.2.3'),
        # without version, with epoch
        ({'epochs': {'oslo.config': 4},
          'requirements': {}},
         'oslo.config', None, None, 'python-oslo.config'),
        # with version, with requirements
        ({'epochs': {},
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), None, 'python-oslo.config >= 4.5.6'),
        # without version, with requirements
        ({'epochs': {},
          'requirements': {'oslo.config': '1.2.3'}},
         'oslo.config', None, None, 'python-oslo.config >= 1.2.3'),
        # without version, with requirements, with epoch
        ({'epochs': {'oslo.config': 4},
          'requirements': {'oslo.config': '1.2.3'}},
         'oslo.config', None, None, 'python-oslo.config >= 4:1.2.3'),
        # with version, with requirements, with epoch
        ({'epochs': {'oslo.config': 4},
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), None,
         'python-oslo.config >= 4:4.5.6'),
        # with version, with requirements, with epoch, python2
        ({'epochs': {'oslo.config': 4},
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), 'py2',
         'python2-oslo.config >= 4:4.5.6'),
        # with version, with requirements, with epoch, python3
        ({'epochs': {'oslo.config': 4},
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), 'py3',
         'python3-oslo.config >= 4:4.5.6'),
        # with version, with requirements, python3, skip python3
        ({'epochs': {}, 'skip_pyversion': 'py3',
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), 'py3',
         ''),
        # with version, with requirements, with epoch, python2 and python3
        ({'epochs': {'oslo.config': 4},
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), ['py2', 'py3'],
         'python2-oslo.config >= 4:4.5.6 python3-oslo.config >= 4:4.5.6'),
        # with version, with requirements, python2 and python3, skip python3
        ({'epochs': {'oslo.config': 4}, 'skip_pyversion': 'py3',
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), ['py2', 'py3'],
         'python2-oslo.config >= 4:4.5.6'),
        # with version, with requirements, python2 and python3, skip python2
        ({'epochs': {'oslo.config': 4}, 'skip_pyversion': 'py2',
          'requirements': {'oslo.config' '1.2.3'}},
         'oslo.config', ('>=', '4.5.6'), ['py2', 'py3'],
         'python3-oslo.config >= 4:4.5.6'),
    )
    @unpack
    def test_context_py2pkg(self, context, pkg_name, pkg_version,
                            py_versions, expected_result):
        context.setdefault('skip_pyversion', ())
        context.setdefault('spec_style', 'suse')
        self.assertEqual(
            renderspec.contextfuncs._context_py2pkg(
                context, pkg_name, pkg_version, py_versions),
            expected_result)

    @data(
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         'oslo.config', None, 'python2-oslo.config'),
    )
    @unpack
    def test_context_py2(self, context, pkg_name, pkg_version,
                         expected_result):
        context.setdefault('skip_pyversion', ())
        self.assertEqual(
            renderspec.contextfuncs._context_py2(
                context, pkg_name, pkg_version),
            expected_result)

    @data(
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         'oslo.config', None, 'python3-oslo.config'),
    )
    @unpack
    def test_context_py3(self, context, pkg_name, pkg_version,
                         expected_result):
        context.setdefault('skip_pyversion', ())
        self.assertEqual(
            renderspec.contextfuncs._context_py3(
                context, pkg_name, pkg_version),
            expected_result)

    def test_context_epoch_without_epochs(self):
        self.assertEqual(
            renderspec.contextfuncs._context_epoch(
                {'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
                'oslo.config'), 0)

    def test_context_epoch_with_epochs(self):
        self.assertEqual(
            renderspec.contextfuncs._context_epoch(
                {'spec_style': 'suse', 'epochs': {'oslo.config': 4},
                 'requirements': {}}, 'oslo.config'), 4)

    def test_context_upstream_version(self):
        context = {'spec_style': 'suse', 'epochs': {},
                   'requirements': {}}
        self.assertEqual(renderspec.contextfuncs._context_upstream_version(
                context, '1.2.0'), '1.2.0')

    @data(
        # no output_dir -> download_files should not be called
        (None, 0),
        # output_dir defined -> download_files should be called once
        ('.', 1)
    )
    @unpack
    def test_context_fetch_source_no_output_dir(self, output_dir,
                                                expected_calls):
        context = {'spec_style': 'suse', 'epochs': {},
                   'requirements': {}, 'output_dir': output_dir}
        url = 'http://foo/bar'
        with patch('renderspec.utils._download_file') as m:
            self.assertEqual(renderspec.contextfuncs._context_fetch_source(
                context, url), url)
            self.assertEqual(m.call_count, expected_calls)


@ddt
class RenderspecTemplateFunctionTests(unittest.TestCase):
    def setUp(self):
        """create a Jinja2 environment and register the standard filters"""
        self.env = Environment()
        renderspec.contextfuncs.env_register_filters_and_globals(self.env)

    @data(
        ("{{ 'http://foo/bar'|basename }}", "bar")
    )
    @unpack
    def test_render_func_basename(self, input, expected):
        template = self.env.from_string(input)
        self.assertEqual(
            template.render(spec_style='suse', epochs={}, requirements={}),
            expected)

    def test_render_func_license_spdx(self):
        template = self.env.from_string(
            "{{ license('Apache-2.0') }}")
        self.assertEqual(
            template.render(spec_style='fedora', epochs={}, requirements={}),
            'ASL 2.0')

    @data(
        # plain
        ({'epochs': {}, 'requirements': {}},
         "{{ py2pkg('requests') }}", "python-requests"),
        # plain, with multiple py_versions
        ({'epochs': {}, 'requirements': {}},
         "{{ py2pkg('requests', py_versions=['py2', 'py3']) }}",
         "python2-requests python3-requests"),
        # with version
        ({'epochs': {}, 'requirements': {}},
         "{{ py2pkg('requests', ('>=', '2.8.1')) }}",
         "python-requests >= 2.8.1"),
        # with version, with epoch
        ({'epochs': {'requests': 4}, 'requirements': {}},
         "{{ py2pkg('requests', ('>=', '2.8.1')) }}",
         "python-requests >= 4:2.8.1"),
        # with version, with epoch, with requirements
        ({'epochs': {'requests': 4},
          'requirements': {'requests': '1.2.3'}},
         "{{ py2pkg('requests', ('>=', '2.8.1')) }}",
         "python-requests >= 4:2.8.1"),
        # without version, with epoch, with requirements
        ({'epochs': {'requests': 4},
          'requirements': {'requests': '1.2.3'}},
         "{{ py2pkg('requests') }}",
         "python-requests >= 4:1.2.3"),
        # without version, with epoch, with requirements, with py_versions
        ({'epochs': {'requests': 4},
          'requirements': {'requests': '1.2.3'}},
         "{{ py2pkg('requests', py_versions=['py2']) }}",
         "python2-requests >= 4:1.2.3"),
    )
    @unpack
    def test_render_func_py2pkg(self, context, string, expected_result):
        template = self.env.from_string(string)
        context.setdefault('skip_pyversion', ())
        context.setdefault('spec_style', 'suse')
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
        # with pypi_name context var
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         "{% set pypi_name = 'oslo.messaging' %}{{ py2name() }}",
         "python-oslo.messaging"),
        # with pypi_name context var and explicit parameter
        ({'spec_style': 'suse', 'epochs': {}, 'requirements': {}},
         "{% set pypi_name = 'oslo.messaging' %}{{ py2name('requests') }}",
         "python-requests"),
    )
    @unpack
    def test_render_func_py2name(self, context, string, expected_result):
        """test the template context function called 'py2name()'"""
        template = self.env.from_string(string)
        self.assertEqual(
            template.render(**context),
            expected_result)

    def test_render_func_py2name_raise(self):
        """py2name() called without parameter but no pypi_name context
        variable set"""
        template = self.env.from_string(
            "{{ py2name() }}")
        with self.assertRaises(TemplateRuntimeError):
            template.render(
                **{'spec_style': 'suse', 'epochs': {}, 'requirements': {}}
            )

    @data(
        ('suse', '1.1.0', '1.1.0'),
        ('suse', '1.1.0.post2', '1.1.0.post2'),
        ('suse', '1.1.0dev10', '1.1.0~dev10'),
        ('suse', '1.1.0a10', '1.1.0~xalpha10'),
        ('suse', '1.1.0a10dev5', '1.1.0~xalpha10~dev5'),
        ('suse', '1.1.0b10', '1.1.0~xbeta10'),
        ('suse', '1.1.0rc2', '1.1.0~xrc2'),
        ('suse', '1.1.0rc2dev2', '1.1.0~xrc2~dev2'),
        ('fedora', '1.1.0', '1.1.0'),
        ('fedora', '1.1.0b10', '1.1.0'),
        ('fedora', '1.1.0rc2dev2', '1.1.0'),
        ('fedora', '11.0.0.0b1', '11.0.0'),
    )
    @unpack
    def test_render_func_py2rpmversion(self, style, py_ver, rpm_ver):
        context = {'spec_style': style, 'epochs': {}, 'requirements': {}}
        # need to escape '{' and '}' here
        s = "{{% set upstream_version = '{}' %}}{{{{ py2rpmversion() }}}}"\
            .format(py_ver)
        template = self.env.from_string(s)
        self.assertEqual(
            template.render(**context),
            rpm_ver)

    @data(
        ('suse', '1.1.0', '1', '0'),
        ('suse', '1.1.0.post2', '1', '0'),
        ('suse', '1.1.0dev10', '2', '0'),
        ('fedora', '1.1.0', '1', '1%{?dist}'),
        # ('fedora', '1.1.0.post2', '1', 'FIXME'),
        ('fedora', '1.1.0dev10', '1', '0.1.dev10%{?dist}'),
        ('fedora', '1.1.0a10', '1', '0.1.a10%{?dist}'),
        ('fedora', '1.1.0a10dev5', '1', '0.1.a10.dev5%{?dist}'),
        ('fedora', '1.1.0b10', '1', '0.1.b10%{?dist}'),
        ('fedora', '1.1.0rc2', '5', '0.5.rc2%{?dist}'),
        ('fedora', '1.1.0rc2dev2', '1', '0.1.rc2.dev2%{?dist}'),
        ('fedora', '11.0.0.0b1', '1', '0.1.b1%{?dist}'),
    )
    @unpack
    def test_render_func_py2rpmrelease(self, style, upstream_ver, rpm_release,
                                       rpm_release_expected):
        context = {'spec_style': style, 'epochs': {}, 'requirements': {}}
        # need to escape '{' and '}' here
        s = "{{% set upstream_version = '{}' %}}" \
            "{{% set rpm_release = '{}' %}}" \
            "{{{{ py2rpmrelease() }}}}".format(upstream_ver, rpm_release)
        template = self.env.from_string(s)
        self.assertEqual(
            template.render(**context),
            rpm_release_expected)

    def test_render_func_url_pypi(self):
        context = {'spec_style': 'suse', 'epochs': {}, 'requirements': {}}
        # need to escape '{' and '}' here
        s = "{% set upstream_version = '3.20.0' %}" \
            "{% set pypi_name = 'oslo.concurrency' %}" \
            "{{ url_pypi() }}"
        template = self.env.from_string(s)
        self.assertEqual(
            template.render(**context),
            "https://files.pythonhosted.org/packages/source/o/"
            "oslo.concurrency/oslo.concurrency-3.20.0.tar.gz")


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

    def test_lexical_version(self):
        requires = renderspec.versions.get_requirements(
            ['django>=1.8,<1.10  # FOO BAR'])
        self.assertEqual(requires, {'django': '1.8'})

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
            self.assertEqual(
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
            f1 = os.path.join(tmpdir, 'test.spec.j2')
            with open(f1, 'w+') as f:
                f.write(template)
            rendered = renderspec.generate_spec(
                style, epochs, requirements, (), 'spec.j2', f1, None)
            self.assertTrue(rendered.endswith(expected_result))
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

            out = renderspec.generate_spec('loldistro', {}, {}, (), 'spec.j2',
                                           base_path, None)
            self.assertEqual(out, expected_out)
        finally:
            shutil.rmtree(tmpdir)


@ddt
class RenderspecUtilsTests(unittest.TestCase):
    def _write_pkg_info(self, destdir, version='5.10.0'):
        """write a PKG-INFO file into destdir"""
        f1 = os.path.join(destdir, 'PKG-INFO')
        with open(f1, 'w+') as f:
            f.write('Metadata-Version: 1.1\n'
                    'Name: oslo.messaging\n'
                    'Version: %s' % (version))

    def test__extract_archive_to_tempdir_no_file(self):
        with self.assertRaises(Exception) as e_info:
            with renderspec.utils._extract_archive_to_tempdir("foobar"):
                self.assertIn("foobar", str(e_info))

    def test__find_pkg_info(self):
        tmpdir = tempfile.mkdtemp(prefix='renderspec-test_')
        try:
            self._write_pkg_info(tmpdir)
            # we expect _find_pkg_info() to find the file in the tmpdir
            self.assertEqual(
                renderspec.utils._find_pkg_info(tmpdir),
                os.path.join(tmpdir, 'PKG-INFO')
            )
        finally:
            shutil.rmtree(tmpdir)

    def test__find_pkg_info_not_found(self):
        tmpdir = tempfile.mkdtemp(prefix='renderspec-test_')
        try:
            self.assertEqual(
                renderspec.utils._find_pkg_info(tmpdir),
                None
            )
        finally:
            shutil.rmtree(tmpdir)

    def test__version_from_pkg_info(self):
        tmpdir = tempfile.mkdtemp(prefix='renderspec-test_')
        version = '5.10.0'
        try:
            self._write_pkg_info(tmpdir, version)
            pkg_info_file = renderspec.utils._find_pkg_info(tmpdir)
            self.assertEqual(
                renderspec.utils._get_version_from_pkg_info(pkg_info_file),
                version
            )
        finally:
            shutil.rmtree(tmpdir)

    @data(
        (['foo-1.2.3.tar.gz'], 'foo', ['foo-1.2.3.tar.gz']),
        (['foo-1.2.3.tar.gz', 'bar-1.2.3.xz'], 'foo', ['foo-1.2.3.tar.gz']),
        # now 2 valid archives - latest created one should be first
        (['foo-1.2.3.tar.gz', 'foo-2.3.4.xz'], 'foo',
         ['foo-2.3.4.xz', 'foo-1.2.3.tar.gz']),
        (['foo-1.2.3.tar.gz'], 'bar', []),
    )
    @unpack
    def test__find_archives(self, archives, pypi_name, expected):
        tmpdir = tempfile.mkdtemp(prefix='renderspec-test_')
        expected = [os.path.join(tmpdir, e) for e in expected]
        try:
            for a in archives:
                open(os.path.join(tmpdir, a), 'w').close()
                time.sleep(0.1)
            self.assertEqual(
                renderspec.utils._find_archives(tmpdir, pypi_name),
                expected
            )
        finally:
            shutil.rmtree(tmpdir)

    def test__find_archives_multiple_dirs(self):
        tmpdir1 = tempfile.mkdtemp(prefix='renderspec-test_')
        tmpdir2 = tempfile.mkdtemp(prefix='renderspec-test_')
        try:
            open(os.path.join(tmpdir2, 'foo-1.2.3.tar.xz'), 'w').close()
            self.assertEqual(
                renderspec.utils._find_archives([None, tmpdir1, tmpdir2],
                                                'foo'),
                [os.path.join(tmpdir2, 'foo-1.2.3.tar.xz')]
            )
        finally:
            shutil.rmtree(tmpdir1)
            shutil.rmtree(tmpdir2)

    def test__find_archives_only_no_dir(self):
        self.assertEqual(renderspec.utils._find_archives([None], 'foo'), [])


if __name__ == '__main__':
    unittest.main()
