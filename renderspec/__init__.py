#!/usr/bin/python
# Copyright (c) 2015 SUSE Linux GmbH
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

import argparse
import os
import platform
import sys

from jinja2 import contextfilter
from jinja2 import contextfunction
from jinja2 import Environment
from jinja2.exceptions import TemplateRuntimeError
from packaging.version import parse
import pymod2pkg

import yaml

from renderspec.distloader import RenderspecLoader
from renderspec import utils
from renderspec import versions


# a variable that needs to be set for some functions in the context
CONTEXT_VAR_PYPI_NAME = "pypi_name"
CONTEXT_VAR_UPSTREAM_VERSION = "upstream_version"
CONTEXT_VAR_RPM_RELEASE = "rpm_release"


def _context_check_variable(context, var_name, needed_by):
    """check that the context has a given variable"""
    if var_name not in context.vars:
        raise TemplateRuntimeError("Variable '%s' not available in context but"
                                   " needed for '%s'" % (var_name, needed_by))


def _context_fetch_source(context, url):
    """fetch the given url into the output_dir and return the url"""
    if context['output_dir']:
        filename = os.path.basename(url)
        utils._download_file(url, context['output_dir'], filename)
    return url


def _context_upstream_version(context, pkg_version=None):
    """return the version which should be set to the 'upstream_version'
    variable in the jinja context"""
    if pkg_version:
        return pkg_version
    else:
        # try to auto-detect the version - for that we need the pypi name
        _context_check_variable(context, CONTEXT_VAR_PYPI_NAME,
                                'upstream_version')
        pypi_name = context.vars[CONTEXT_VAR_PYPI_NAME]

        # look for archives in:
        # 1) the output_dir
        # 2) the dir where the input template (.spec.j2) comes from
        # 3) the current working dir
        archives = utils._find_archives([context['output_dir'],
                                         context['input_template_dir'],
                                         '.'], pypi_name)
        for archive in archives:
            with utils._extract_archive_to_tempdir(archive) as tmpdir:
                pkg_info_file = utils._find_pkg_info(tmpdir)
                if pkg_info_file:
                    return utils._get_version_from_pkg_info(pkg_info_file)
        # unable to autodetect the version
        raise TemplateRuntimeError("Can not autodetect 'upstream_version' from"
                                   " the following archives: '%s'" % (
                                       ', '.join(archives)))


def _context_py2rpmversion(context):
    """get a python PEP0440 compatible version and translate it to an RPM
    version"""
    # the context needs a variable set via {% set upstream_version = 'ver' %}
    _context_check_variable(context, CONTEXT_VAR_UPSTREAM_VERSION,
                            'py2rpmversion')
    version = context.vars[CONTEXT_VAR_UPSTREAM_VERSION]
    v_python = parse(version)
    # fedora does not allow '~' in versions but uses a combination of Version
    # and Release
    # https://fedoraproject.org/wiki/Packaging:Versioning\#Pre-Release_packages
    if context['spec_style'] == 'fedora':
        if len(v_python._version.release) >= 4:
            return "%d.%d.%d" % (v_python._version.release[0:3])
        else:
            return v_python.base_version
    else:
        v_rpm = v_python.public
        if v_python.is_prerelease:
            # we need to add the 'x' in front of alpha/beta releases because
            # in the python world, "1.1a10" > "1.1.dev10"
            # but in the rpm world, "1.1~a10" < "1.1~dev10"
            v_rpm = v_rpm.replace('a', '~xalpha')
            v_rpm = v_rpm.replace('b', '~xbeta')
            v_rpm = v_rpm.replace('rc', '~rc')
            v_rpm = v_rpm.replace('.dev', '~dev')
        return v_rpm


def _context_py2rpmrelease(context):
    if context['spec_style'] == 'fedora':
        # the context needs a var set via {% set upstream_version = 'ver' %}
        _context_check_variable(context, CONTEXT_VAR_UPSTREAM_VERSION,
                                'py2rpmrelease')
        # the context needs a var set via {% set rpm_release = 'ver' %}
        _context_check_variable(context, CONTEXT_VAR_RPM_RELEASE,
                                'py2rpmrelease')
        upstream_version = context.vars[CONTEXT_VAR_UPSTREAM_VERSION]
        rpm_release = context.vars[CONTEXT_VAR_RPM_RELEASE]
        v_python = parse(upstream_version)
        if v_python.is_prerelease:
            _, alphatag = v_python.public.split(v_python.base_version)
            return '0.{}.{}%{{?dist}}'.format(rpm_release,
                                              alphatag.lstrip('.'))
        else:
            return '{}%{{?dist}}'.format(rpm_release)
    else:
        # SUSE uses just '0'. The OpenBuildService handles the Release tag
        return '0'


def _context_epoch(context, pkg_name):
    """get the epoch (or 0 if unknown) for the given pkg name"""
    return context['epochs'].get(pkg_name, 0)


def _context_py2name(context, pkg_name=None):
    if not pkg_name:
        # if the name is not given, try to get the name from the context
        _context_check_variable(context, CONTEXT_VAR_PYPI_NAME,
                                'py2name')
        pkg_name = context.vars[CONTEXT_VAR_PYPI_NAME]
    return pymod2pkg.module2package(pkg_name, context['spec_style'])


def _context_py2pkg(context, pkg_name, pkg_version=None):
    """generate a distro specific package name with optional version tuple."""
    # package name handling
    name = pymod2pkg.module2package(pkg_name, context['spec_style'])

    # if no pkg_version is given, look in the requirements and set one
    if not pkg_version:
        if pkg_name in context['requirements']:
            pkg_version = ('>=', context['requirements'][pkg_name])

    # pkg_version is a tuple with comparator and number, i.e. "('>=', '1.2.3')"
    if pkg_version:
        # epoch handling
        if pkg_name in context['epochs'].keys():
            epoch = '%s:' % context['epochs'][pkg_name]
        else:
            epoch = ''
        v_comparator, v_number = pkg_version
        v_str = ' %s %s%s' % (v_comparator, epoch, v_number)
    else:
        v_str = ''

    return '%s%s' % (name, v_str)


def _context_license_spdx(context, value):
    """convert a given known spdx license to another one"""
    # more values can be taken from from https://github.com/hughsie/\
    #    appstream-glib/blob/master/libappstream-builder/asb-package-rpm.c#L76
    mapping = {
        "Apache-1.1": "ASL 1.1",
        "Apache-2.0": "ASL 2.0",
        "BSD-3-Clause": "BSD",
        "GPL-1.0+": "GPL+",
        "GPL-2.0": "GPLv2",
        "GPL-2.0+": "GPLv2+",
        "GPL-3.0": "GPLv3",
        "GPL-3.0+": "GPLv3+",
        "LGPL-2.1": "LGPLv2.1",
        "LGPL-2.1+": "LGPLv2+",
        "LGPL-2.0": "LGPLv2 with exceptions",
        "LGPL-2.0+": "LGPLv2+ with exceptions",
        "LGPL-3.0": "LGPLv3",
        "LGPL-3.0+": "LGPLv3+",
        "MIT": "MIT with advertising",
        "MPL-1.0": "MPLv1.0",
        "MPL-1.1": "MPLv1.1",
        "MPL-2.0": "MPLv2.0",
        "OFL-1.1": "OFL",
        "Python-2.0": "Python",
    }

    if context['spec_style'] == 'fedora':
        return mapping[value]
    else:
        # just use the spdx license name
        return value


###############
# jinja2 filter
###############
@contextfilter
def _filter_epoch(context, value):
    return _context_epoch(context, value)


@contextfilter
def _filter_basename(context, value):
    return os.path.basename(value)


################
# jinja2 globals
################
@contextfunction
def _globals_py2pkg(context, pkg_name, pkg_version=None):
    return _context_py2pkg(context, pkg_name, pkg_version)


@contextfunction
def _globals_fetch_source(context, url):
    return _context_fetch_source(context, url)


@contextfunction
def _globals_upstream_version(context, pkg_version=None):
    return _context_upstream_version(context, pkg_version)


@contextfunction
def _globals_py2rpmversion(context):
    return _context_py2rpmversion(context)


@contextfunction
def _globals_py2rpmrelease(context):
    return _context_py2rpmrelease(context)


@contextfunction
def _globals_epoch(context, value):
    return _context_epoch(context, value)


@contextfunction
def _globals_license_spdx(context, value):
    return _context_license_spdx(context, value)


@contextfunction
def _globals_py2name(context, value=None):
    return _context_py2name(context, value)


def _env_register_filters_and_globals(env):
    """register all the jinja2 filters we want in the environment"""
    env.filters['epoch'] = _filter_epoch
    env.filters['basename'] = _filter_basename
    env.globals['py2rpmversion'] = _globals_py2rpmversion
    env.globals['py2rpmrelease'] = _globals_py2rpmrelease
    env.globals['py2pkg'] = _globals_py2pkg
    env.globals['py2name'] = _globals_py2name
    env.globals['epoch'] = _globals_epoch
    env.globals['license'] = _globals_license_spdx
    env.globals['upstream_version'] = _globals_upstream_version
    env.globals['fetch_source'] = _globals_fetch_source


def generate_spec(spec_style, epochs, requirements, input_template_path,
                  output_path):
    """generate a spec file with the given style and the given template"""

    env = Environment(loader=RenderspecLoader(
        template_fn=input_template_path),
        trim_blocks=True)

    _env_register_filters_and_globals(env)

    template_name = '.spec'
    if spec_style in env.loader.list_templates():
        template_name = spec_style
    template = env.get_template(template_name)
    input_template_dir = os.path.dirname(os.path.abspath(input_template_path))
    if output_path:
        output_dir = os.path.dirname(
            os.path.abspath(output_path))
    else:
        output_dir = None
    return template.render(spec_style=spec_style, epochs=epochs,
                           requirements=requirements,
                           input_template_dir=input_template_dir,
                           output_dir=output_dir)


def _is_fedora(distname):
    """detect Fedora-based distro (e.g Fedora, CentOS, RHEL)"""
    distname = distname.lower()
    for x in ["fedora", "centos", "red hat"]:
        if x in distname:
            return True
    return False


def _get_default_distro():
    distname, version, id_ = platform.linux_distribution()
    if "suse" in distname.lower():
        return "suse"
    elif _is_fedora(distname):
        return "fedora"
    else:
        return "unknown"


def _get_default_template():
    fns = [f for f in os.listdir('.')
           if os.path.isfile(f) and f.endswith('.spec.j2')]
    if not fns:
        return None, ("No *.spec.j2 templates found. "
                      "See `renderspec -h` for usage.")
    elif len(fns) > 1:
        return None, ("Multiple *.spec.j2 templates found, "
                      "please specify one.\n"
                      "See `renderspec -h` for usage.")
    else:
        return fns[0], None


def _get_epochs(filename):
    """get a dictionary with pkg-name->epoch mapping"""
    epochs = {}
    if filename is not None:
        with open(filename, 'r') as f:
            data = yaml.safe_load(f.read())
            epochs.update(data['epochs'])
    return epochs


def _get_requirements(filenames):
    """get a dictionary with pkg-name->min-version mapping"""
    reqs = {}
    for filename in filenames:
        with open(filename, 'r') as f:
            reqs.update(versions.get_requirements(f.readlines()))
    return reqs


def process_args():
    distro = _get_default_distro()
    parser = argparse.ArgumentParser(
        description="Convert a .spec.j2 template into a .spec")
    parser.add_argument("-o", "--output",
                        help="output filename or '-' for stdout. "
                        "default: autodetect")
    parser.add_argument("--spec-style", help="distro style you want to use. "
                        "default: %s" % (distro), default=distro,
                        choices=['suse', 'fedora'])
    parser.add_argument("--epochs", help="yaml file with epochs listed.")
    parser.add_argument("input-template", nargs='?',
                        help="specfile jinja2 template to render. "
                        "default: *.spec.j2")
    parser.add_argument("--requirements", help="file(s) which contain "
                        "PEP0508 compatible requirement lines. Last mentioned "
                        "file has highest priority. default: %(default)s",
                        action='append', default=[])

    return vars(parser.parse_args())


def main():
    args = process_args()

    # autodetect input/output fns if possible
    input_template = args['input-template']
    if not input_template:
        input_template, errmsg = _get_default_template()
        if not input_template:
            print(errmsg)
            return 1
    output_fn = args['output']
    if not output_fn:
        if not input_template.endswith('.spec.j2'):
            print("Failed to autodetect output file name. "
                  "Please specify using `-o/--output`.")
            return 2
        output_fn, _, _ = input_template.rpartition('.')

    try:
        epochs = _get_epochs(args['epochs'])
        requirements = _get_requirements(args['requirements'])
    except IOError as e:
        print(e)
        return 3

    if output_fn and output_fn != '-':
        output_path = os.path.abspath(output_fn)
    else:
        output_path = None

    spec = generate_spec(args['spec_style'], epochs, requirements,
                         input_template, output_path)
    if output_path:
        print("Rendering: %s -> %s" % (input_template, output_path))
        with open(output_path, "w") as o:
            o.write(spec)
    else:
        print(spec)
    return 0


if __name__ == '__main__':
    sys.exit(main())
