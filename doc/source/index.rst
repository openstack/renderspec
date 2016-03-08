renderspec
==========

`renderspec` is a python program to render RPM spec file templates to a
usable spec file. Distribution specifics like different policies for
package naming in openSUSE or Fedora are handled.

Contents:

.. toctree::
   :maxdepth: 2

   installation
   usage

Testing
=======
renderspec has currently a couple of unittests. The preferred way to run tests
is using ``tox``. To run the testsuite for python 2.7, do:

.. code-block:: shell

   tox -epy27


Contributing
============
Code is hosted at `git.openstack.org`_. Submit bugs to the
renderspec project on `Launchpad`_. Submit code to the
openstack/renderspec project using `Gerrit`_.

.. _git.openstack.org: https://git.openstack.org/cgit/openstack/renderspec
.. _Launchpad: https://launchpad.net/renderspec
.. _Gerrit: http://docs.openstack.org/infra/manual/developers.html#development-workflow


Indices and tables
==================

* :ref:`genindex`
* :ref:`search`

