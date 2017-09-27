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
import string
import sys

from jinja2 import Environment

import yaml

from renderspec.distloader import RenderspecLoader
from renderspec import versions
from renderspec import contextfuncs


def generate_spec(spec_style, epochs, requirements, skip_pyversion,
                  input_template_format, input_template_path, output_path):
    """generate a spec file with the given style and input template"""
    if input_template_format == 'spec.j2':
        return _renderer_input_template_format_spec(
            spec_style, epochs, requirements, skip_pyversion,
            input_template_path, output_path)
    else:
        raise Exception('Unknown input-template-format "%s"' %
                        input_template_format)


def _renderer_input_template_format_spec(spec_style, epochs, requirements,
                                         skip_pyversion,
                                         input_template_path, output_path):
    """render a 'traditional' .spec.j2 template into a .spec file"""
    env = Environment(loader=RenderspecLoader(
        template_fn=input_template_path),
        trim_blocks=True)

    contextfuncs.env_register_filters_and_globals(env)

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
                           skip_pyversion=skip_pyversion,
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
    distname, _, _ = platform.linux_distribution()

    # newer distros only have /etc/os-release and then platform doesn't work
    # anymore and upstream does not want to fix it:
    # https://bugs.python.org/issue1322
    if not distname and 'Linux' in platform.system():
        try:
            with open('/etc/os-release', 'r') as lsb_release:
                for l in lsb_release:
                    if l.startswith('ID_LIKE='):
                        distname = l.partition('=')[2].strip(
                            string.punctuation + string.whitespace)
                        break
        except OSError:
            print('WARN: Unable to determine Linux distribution')

    if "suse" in distname.lower():
        return "suse"
    elif _is_fedora(distname):
        return "fedora"
    else:
        return "unknown"


def _get_default_pyskips(distro):
    # py3 building is all complicated on CentOS 7.x
    if distro == 'fedora':
        distname, distver, _ = platform.linux_distribution()
        if 'CentOS' in distname and distver.startswith('7'):
            return 'py3'
    return None


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
    parser.add_argument("--skip-pyversion",
                        help='Skip requirements for this pyversion',
                        default=_get_default_pyskips(distro),
                        choices=['py2', 'py3'])
    parser.add_argument("--epochs", help="yaml file with epochs listed.")
    parser.add_argument("input-template", nargs='?',
                        help="specfile jinja2 template to render. "
                        "default: *.spec.j2")
    parser.add_argument("-f", "--input-template-format", help="Format of the "
                        "input-template file. default: %(default)s",
                        default="spec.j2", choices=["spec.j2"])
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
    output_filename = args['output']
    if not output_filename:
        if not input_template.endswith('.spec.j2'):
            print("Failed to autodetect output file name. "
                  "Please specify using `-o/--output`.")
            return 2
        output_filename, _, _ = input_template.rpartition('.')

    try:
        epochs = _get_epochs(args['epochs'])
        requirements = _get_requirements(args['requirements'])
    except IOError as e:
        print(e)
        return 3

    if output_filename and output_filename != '-':
        output_path = os.path.abspath(output_filename)
    else:
        output_path = None

    spec = generate_spec(args['spec_style'], epochs, requirements,
                         args['skip_pyversion'],
                         args['input_template_format'],
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
