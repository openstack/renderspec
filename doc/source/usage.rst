Handling templates
==================

.. program:: renderspec
.. highlight:: bash

Templates are based on `Jinja2`_ and usually end with .spec.j2 .

.. note:: There are a lot of examples available in the `openstack/rpm-packaging`_ project.

Rendering a template called `example.spec.j2` can be done with::

  renderspec example.spec.j2

This will output the rendered spec to stdout.

Different styles
****************
Different distributions have different spec file styles (i.e. different naming
policies and different epoch handling policies). :program:`renderspec` automatically
detects which distibution is used and uses that style. Forcing a specific style can
be done with::

  renderspec --spec-style suse example.spec.j2


Handling epochs
***************

Different distributions may have different epochs for different packages. This
is handled with an extra epoch file which must be in yaml format. Here's an example
of a epoch file called `epochs.yaml`::

  ---
  epochs:
      python-dateutil: 3
      oslo.config: 2

Rendering the `example.spec.j2` file and also use the epochs can be done with::

  renderspec --epochs epochs.yaml example.spec.j2

The ```Epoch:``` field in the spec.j2 file itself can be handled with the ```epoch()```
context function like this::

  Epoch: {{  epoch('oslo.config') }}

This will add the epoch number from the yaml file or `0` in case there is no epoch file
or the given name in not available in the yaml file.

.. note:: if no epoch file is available, no epochs are added to the version numbers.
          The epoch file is optional. If a package name is not in the epochs file,
          epoch for that package is not used.

Handling requirements
*********************

Updating versions for `Requires` and `BuildRequires` takes a lot of time.
:program:`renderspec` has the ability to insert versions from a given
`global-requirements.txt` file. The file must contain lines following `PEP0508`_

.. note:: For OpenStack, the `global-requirements.txt`_ can be used.

To render a `example.spec.j2` file with a given requirements file, do::

  renderspec --requirements global-requirements.txt example.spec.j2

It's also possible to use multiple requirements file. The last mentioned file
has the highest priority in case both files contain requirements for the same
package name. Using multiple files looks like this::

  renderspec --requirements global-requirements.txt \
      --requirements custom-requirements.txt \
      example.spec.j2

.. _PEP0508: https://www.python.org/dev/peps/pep-0508/
.. _global-requirements.txt: https://git.openstack.org/cgit/openstack/requirements/tree/global-requirements.txt

Handling the package version
****************************

Distributions handle versions, especially pre-release versions differently.
SUSE for example allows using RPM's tilde ('~) while Fedora doesn't allow that
and uses a combination of RPM `Version` and `Release` tag to express pre-releases.
To support both styles with renderspec, the upstream version and a release
must be available in the context::

  {% set upstream_version = upstream_version('1.2.3.0rc1') %}
  {% set rpm_release = '1' %}

This should be done on the first lines in the spec.j2 template. The `rpm_release` is
only used in the fedora style.
Then for the RPM version and release, use::

  Version: {{ py2rpmversion() }}
  Release: {{ py2rpmrelease() }}

For suse-style, this renders to::

  Version: 1.2.3.0~rc1
  Release: 0

For fedora-style, this renders to::

  Version: 1.2.3
  Release: 0.1.0rc1%{?dist}

Note that in case of pre-releases you may need to adjust the version that is used
in the `Source` tag and the `%prep` sections `%setup`. So use e.g. ::

  {% set upstream_version = upstream_version('1.2.3.0rc1') %}
  {% set rpm_release = '1' %}
  %name oslo.config
  Version: {{ py2rpmversion() }}
  Release: {{ py2rpmrelease() }}
  Source0: https://pypi.io/packages/source/o/%{sname}/%{sname}-{{ upstream_version }}.tar.gz
  %prep
  %setup -q -n %{sname}-{{upstream_version}}

which would render (with suse-style) to::

  %name oslo.config
  Version: 1.2.3.0~rc1
  Release: 0
  Source0: https://pypi.io/packages/source/o/%{sname}/%{sname}-1.2.3rc1.tar.gz
  %prep
  %setup -q -n %{sname}-1.2.3.0rc1

The `upstream_version` can also be automatically detected from archive files
(like sdist archives available from pypi) which contain a valid `PKG-INFO`_ file.
For automatic version detection, the context need to know the `pypi_name` and a
archive file must be available and the context variable `upstream_version` needs to
be set to the value of the context function `upstream_version()`. The difference
here is that the version in `upstream_version()` is not explicit given. The archive
can be fetched with the `fetch_source()` function::

  {% set source = fetch_source('http://tarballs.openstack.org/oslo.config/oslo.config-master.tar.gz') %}
  {% set pypi_name = 'oslo.config' %}
  {% set upstream_version = upstream_version() %}
  {% set rpm_release = '1' %}

  Version: {{ py2rpmversion() }}
  Release: {{ py2rpmrelease() }}
  Source0: {{ source }}

.. _PKG-INFO: https://www.python.org/dev/peps/pep-0314/

Template features
=================

Templates are just plain `Jinja2`_ templates. So all magic (i.e. filters) from
Jinja can be used in the templates. Beside the Jinja provided features, there are
some extra features renderspec adds to the template context.

context function `py2name`
**************************
`py2name` is used to translate a given pypi name to a package name following the
different distribution specific guidelines.

.. note:: For translating pypi names (the name a python package has on `pypi.python.org`_
          to distro specific names, internally a module called `pymod2pkg`_ is used.

The prefered way to use `py2name` is to set the context variable `pypi_name` and
then call `py2name()` without any parameters. In that case, the context variable
is used::

  {% set pypi_name = 'oslo.config' %}
  Name: {{ py2name() }}

Rendering this template :program:`renderspec` with the `suse` style would result in::

  Name: python-oslo.config

It is also possible to pass the pypi name directly to the `py2name` context function::

  Name: {{ py2name('oslo.config') }}

That would create the same rendering result.
If the context env var `pypi_name` is set **and** `py2name` is called with a parameter,
the parameter is used instead of the context var.


context function `py2pkg`
*************************
`py2pkg` is used to

* translate the given pypi name to a distro specific name
* handle epochs and version

For example, a BuildRequires in a spec.j2 template for the package `oslo.config` in
version `>= 3.4.0` would be defined as::

  BuildRequires:  {{ py2pkg('oslo.config', ('>=', '3.4.0')) }}

Rendering this template with :program:`renderspec` with the `suse` style would result in::

  BuildRequires:  python-oslo.config >= 3.4.0

Rendering it with the `fedora` style would be::

  BuildRequires:  python-oslo-config >= 3.4.0

With an epoch file and an entry for `oslo.config` set to i.e. `2`, this would be
rendered on Fedora to::

  BuildRequires:  python-oslo-config >= 2:3.4.0

It's also possible to skip adding required versions and handle that with a
`global-requirements.txt` file. Given that this file contains `oslo.config>=4.3.0` and
rendering with `--requirements`, the rendered spec would contain::

  BuildRequires:  python-oslo-config >= 4.3.0


context function `epoch`
************************

The epochs are stored in a yaml file. Using the `epoch` context function can be done with::

  Epoch: {{ epoch('oslo.config') }}

Without an yaml file, this would be rendered to::

  Epoch: 0

With an existing yaml (and `oslo.config` epoch set to 2), this would be rendered to::

  Epoch: 2


context function `license`
************************
The templates use `SPDX`_ license names and theses names are translated for different distros.
For example, a project uses the `Apache-2.0` license::

  License: {{ license('Apache-2.0') }}

With the `fedora` spec-style, this would be rendered to::

  License: ASL 2.0

With the `suse` spec-style::

  License: Apache-2.0


context function `upstream_version`
***********************************
This function can be used to assign a static version to the variable `upstream_version`
or to dynamically detect the version from a archive (eg. an sdist tarball).
Static assignment looks like::

  {% set upstream_version = upstream_version('1.1.0a3') %}

which is basically the same as::

  {% set upstream_version = '1.1.0a3' %}

So static assignment is not that useful. Dynamic assignment looks like::

  {% set pypi_name = 'oslo.config' %}
  {% set upstream_version = upstream_version() %}

Note that for dynamic version detection, the variable `pypi_name` needs to be set
before calling `upstream_version()`. `upstream_version()` tries to find an archive
in:

1. the output directory where the rendered .spec file ends
2. the directory where the .spec.j2 template comes from
3. the current working directory


context function `py2rpmversion`
********************************
Python has a semantic version schema (see `PEP0440`_) and converting Python versions
to RPM compatible versions is needed in some cases. For example, in the Python world
the version "1.1.0a3" is lower than "1.1.0" but for RPM the version is higher.
To transform a Python version to a RPM compatible version, use::

  {% set upstream_version = '1.1.0a3' %}
  {% set rpm_release = '1' %}

  Version: {{ py2rpmversion() }}

With the `suse` spec-style it will be translated to::

  Version: 1.1.0~xalpha3

Note that you need to set 2 context variables (`upstream_version` and `rpm_release`)
to be able to use the `py2rpmversion()` function.


context function `py2rpmrelease`
********************************
Fedora doesn't allow the usage of `~` (tilde) in the `Version` tag. So for pre-releases
the `Release` tag is used (see `Fedora Packaging Versioning`_)
For the fedora-style::

  {% set upstream_version = '1.1.0a3' %}
  {% set rpm_release = '1' %}

  Version: {{ py2rpmversion() }}
  Release: {{ py2rpmrelease() }}

this would render to::

  Version: 1.1.0
  Release: 0.1a3%{?dist}

Note that you need to set 2 context variables (`upstream_version` and `rpm_release`)
to be able to use the `py2rpmrelease()` function.


context function `fetch_source`
*******************************
The function `fetch_source` downloads the given url and puts the file into the
`output_dir` (that's the directory where the rendered .spec file will be in).
If `output_dir` is not available (that's the case when `renderspec` writes the
rendered spec to stdout) the download is skipped. But in any case the function
returns the same url that it got as parameter::

  {% set source = fetch_source('http://tarballs.openstack.org/oslo.log/oslo.log-master.tar.gz') %}
  Source0: {{ source }}


context filter `basename`
*************************
This is a filter which just returns ```os.path.basename()```::

  {% set source = fetch_source('http://tarballs.openstack.org/oslo.log/oslo.log-master.tar.gz') %}
  Source0: {{ source|basename }}

which then renders to::

  Source0: oslo.log-master.tar.gz


distribution specific blocks & child templates
**********************************************

To properly handle differences between individual .spec styles, renderspec
contains child templates in `renderspec/dist-templates` which are
automatically used with corresponding `--spec-style`. These allow different
output for each spec style (distro) using jinja `{% block %}` syntax.

For example consider simple `renderspec/dist-templates/fedora.spec.j2`::

  {% extends ".spec" %}
  {% block build_requires %}
  BuildRequires:  {{ py2pkg('setuptools') }}
  {% endblock %}

allows following in a spec template::

  {% block build_requires %}{% endblock %}

to render into::

  BuildRequires:  python-setuptools

with `fedora` spec style, while `renderspec/dist-templates/suse.spec.j2` might
define other result for `suse` spec style.

For more information, see current `renderspec/dist-templates` and usage in
`openstack/rpm-packaging`_ project.

Available context variables
===========================

There are some variables that need to be set in the spec.j2 template. Preferable
at the beginning before any context function is used.

pypi_name
*********

This variable defines the name that is used on pypi. Set with::

  {% set pypi_name = 'oslo.messaging' %}

where 'oslo.messaging' is the name that is set. The variable can later be used::

  Source: {{ pypi_name }}.tar.gz

upstream_version
****************

The variable defines the upstream version that is used::

  {% set upstream_version = '1.2.3.0rc1' %}


rpm_release
***********
The variable defines the rpm release. It is used together with 'upstream_version'
and only needed with the fedora spec style::

  {% set rpm_release = '1' %}




.. _Jinja2: http://jinja.pocoo.org/docs/dev/
.. _openstack/rpm-packaging: https://git.openstack.org/cgit/openstack/rpm-packaging/
.. _pymod2pkg: https://git.openstack.org/cgit/openstack/pymod2pkg
.. _pypi.python.org: https://pypi.python.org/pypi
.. _SPDX: https://spdx.org/licenses/
.. _PEP0440: https://www.python.org/dev/peps/pep-0440/
.. _Fedora Packaging Versioning: https://fedoraproject.org/wiki/Packaging:Versioning#Pre-Release_packages
