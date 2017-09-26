################
Developer Manual
################

.. note::

   All commands listed in this manual are for
   `Debian <https://www.debian.org/>`__
   and `its derivations <https://www.debian.org/misc/children-distros>`__.

************
Technologies
************

NOFAInsert is a `QGIS <https://www.qgis.org/>`__ plugin written in
`Python <https://www.python.org/>`__. Like other
`QGIS <https://www.qgis.org/>`__ `Python <https://www.python.org/>`__ plugins
it uses `QGIS API <https://qgis.org/api/>`__ and
`PyQt <https://riverbankcomputing.com/software/pyqt/>`__ bindings.
Additionally NOFAInsert plugin makes extensive use of
`psycopg <http://initd.org/psycopg/>`__ package.

Documentation
=============

The newest version of plugin
(`0.5 <https://github.com/NINAnor/NOFAInsert/releases/tag/v0.5-beta_candidate>`__)
was developed for `QGIS <https://www.qgis.org/>`__ 2.18.

   * `QGIS 2.18 API <https://qgis.org/api/2.18/>`__
   * `PyQt4 <http://pyqt.sourceforge.net/Docs/PyQt4/>`__
   * `psycopg2 <http://initd.org/psycopg/docs/>`__
   * `unittest <https://docs.python.org/2/library/unittest.html>`__
   * `nose <https://nose.readthedocs.io/>`__
   * `coverage <https://coverage.readthedocs.io/en/coverage-4.4.1/>`__

***********
Development
***********

History
=======

In December 2016 Stefan Blumentrath
(`GitHub profile <https://github.com/ninsbl>`__) started developing the plugin.
At the beggining of 2017 Matteo De Stefano
(`GitHub profile <https://github.com/mdlux>`__) created a separate repository
and released version
`0.3 <https://github.com/NINAnor/NOFAInsert/releases/tag/v0.3-alpha>`__.
Together with intern
Jakob Miksch (`GitHub profile <https://github.com/bufferclip>`__) who worked in
`NINA <http://www.nina.no/english/Home>`__ as part of his
`Erasmus+ Internship <https://erasmusintern.org/>`__ version
`0.4 <https://github.com/NINAnor/NOFAInsert/releases/tag/v.0.4-prebeta>`__
was released. Another Erasmus+ intern Ondřej Svoboda
(`GitHub profile <https://github.com/svoboond>`__) reworked the whole plugin
and released version
`0.5 <https://github.com/NINAnor/NOFAInsert/releases/tag/v0.5-beta_candidate>`__.

Development Tools Setup
=======================

There is nothing a developer must setup in order to start
(except for building :ref:`documentation <online-documentation>`) because all
needed `Python <https://www.python.org/>`__ packages are already present in
`QGIS <https://www.qgis.org/>`__ by default.

However, if you are using an IDE you can set it up to understand the API.

   * `Making Eclipse understand the API <http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/ide_debugging.html#making-eclipse-understand-the-api>`__

.. _api-documentation:

API Documentation
=================

All classes, methods and functions are documented in
`reStructuredText <http://docutils.sourceforge.net/rst.html>`__ format
that can be used by `Sphinx <http://sphinx-doc.org/>`__
to generate documentation.

   * :ref:`API <api>`

Debugging
=========

   * `Debugging using Eclipse and PyDev <http://docs.qgis.org/testing/en/docs/pyqgis_developer_cookbook/ide_debugging.html#debugging-using-eclipse-and-pydev>`__

Branches
========

There are three important branches:

   * **master** – main branch.
   * **gh-pages** – branch with :ref:`documentation <online-documentation>`.
   * **before_rework_2017-07-13** – version `0.5 <https://github.com/NINAnor/NOFAInsert/releases/tag/v0.5-beta_candidate>`__
     came with significant changes. This branch serves as a backup
     of the previous version.

Plugin Structure
================

Structure with short comments is as follows:

::

   /
   ├── data/
   │   └── icons/
   │       └── options.png      # icon for opening connection parameters dialog
   ├── docs/                    # directory with docs
   │   ├── source/              # directory with docs source
   │   ├── make.bat             # batch file for creating docs
   │   ├── Makefile             # makefile for creating docs
   │   └── update-docs.sh       # bash script for publishing updates docs
   ├── nofa/                    # NOFA package
   │   ├── gui/                 # GUI package
   │   │   ├── __init__.py      # module for package initialization
   │   │   ├── con_dlg.py       # module with connection dialog class
   │   │   ├── de.py            # module with custom date edit class
   │   │   ├── dtst_dlg.py      # module with reference dialog class
   │   │   ├── exc.py           # module with custom exceptions
   │   │   ├── ins_mw.py        # module with insert main window class
   │   │   ├── ins_mw.ui        # XML file for creating GUI
   │   │   ├── prj_dlg.py       # module with project dialog class
   │   │   ├── ref_dlg.py       # module with reference dialog class
   │   │   └── vald.py          # module with custom validators
   │   ├── wms/                 # directory with WMS files
   │   │   └── osm.xml          # XML file for loading OSM basemap
   │   ├── __init__.py          # module for package initialization
   │   ├── db.py                # module with database queries
   │   └── ordered_set.py       # module with OrderedSet container
   ├── scripts/                 # directory with scripts
   │   └── create_log_tbls.py   # script for creating log tables
   ├── test/                    # directory with tests
   ├── __init__.py              # module for package initialization
   ├── metadata.txt             # plugin metadata
   ├── nofa_insert.py           # module with main class
   └── README.md                # GitHub readme

NINA QGIS Plugin Repository
===========================

Users install NOFAInsert plugin from NINA QGIS Plugin Repository.
It is a simple `XML <https://en.wikipedia.org/wiki/XML>`__ file:

   * http://vm-srv-finstad.vm.ntnu.no/NOFA_plugins/plugins.xml

When new version of plugin is released it is necessary to edit the file so that
users get a notification.

.. note::

   How soon a user gets notified depends on his/her settings in
   :guilabel:`Plugins` :menuselection:`-->`
   :guilabel:`Manage and Install Plugins...` :menuselection:`-->`
   :guilabel:`Settings`.

To adjust the file log in to server and edit ``version="0.5"`` to the new
version. In order to be able to do that you need to have superuser rights.

.. code-block:: bash

   ssh <username>@vm-srv-finstad.vm.ntnu.no
   cd /var/www/html/NOFA_plugins
   sudo nano plugins.xml

.. note::

   Version listed in http://vm-srv-finstad.vm.ntnu.no/NOFA_plugins/plugins.xml
   should match version in :file:`metadata.txt`.

.. _online-documentation:

Online Documentation
====================

Plugin documentation is available on its own
`webpage <https://ninanor.github.io/NOFAInsert/>`__. This webpage is connected
to `gh-pages <https://github.com/NINAnor/NOFAInsert/tree/gh-pages>`__ branch.
The documentation itself is written in
`reStructuredText <http://docutils.sourceforge.net/rst.html>`__
and built with `Sphinx <http://sphinx-doc.org/>`__.

First install `Sphinx <http://sphinx-doc.org/>`__ and
`Read the Docs Theme <http://docs.readthedocs.io/en/latest/theme.html>`__:

.. code-block:: bash

   sudo pip install sphinx
   sudo pip install sphinx_rtd_theme

.. note::

   To run commands mentioned above you need to have ``pip`` installed.

   .. code-block:: bash

      sudo apt install python-pip

Then you can build the documentation:

.. code-block:: bash

   cd docs/
   make html

.. warning::

   If you run across a problem building the documentation
   (especially :ref:`API documentation <api-documentation>`) make sure you run
   `Sphinx <http://sphinx-doc.org/>`__
   for `Python <https://www.python.org/>`__ 2.

To view created pages in `Firefox <https://www.mozilla.org/>`__:

.. code-block:: bash

   firefox build/html/index.html &

When you are satisfied with your changes publish updated documentation to
`gh-pages <https://github.com/NINAnor/NOFAInsert/tree/gh-pages>`__ branch
by calling a script.

.. code-block:: bash

   ./docs/update-docs.sh

.. hint::

   Call the script from plugin main directory.

Testing
=======

Unfortunately NOFAInsert plugin was not developed by using
`test-driven development <https://en.wikipedia.org/wiki/Test-driven_development>`__
so test were written later. That means there are not as many test as there
should be.

.. todo::

   Write tests for:

      * :guilabel:`Location Table`
      * :guilabel:`Occurrence Table`
      * :guilabel:`Dataset` :guilabel:`Project` and :guilabel:`Reference`
        windows
      * inserting new :guilabel:`Dataset` :guilabel:`Project`
        and :guilabel:`Reference`
      * :guilabel:`Reset` button
      * :guilabel:`Insert to NOFA` button
      * :guilabel:`History` tab

After trying to make
`QGIS Tester Plugin <https://github.com/boundlessgeo/qgis-tester-plugin>`__
work and considering
`QGIS Desktop for Docker <https://github.com/kartoza/docker-qgis-desktop>`__
it was decided to use
`unittest <https://docs.python.org/2/library/unittest.html>`__ framework
and `nose <https://nose.readthedocs.io/>`__ extension.
On top of that
`coverage <https://coverage.readthedocs.io/en/coverage-4.4.1/>`__ tool is used
for an overview of how much code is tested.

First install all required packages:

.. code-block:: bash

   sudo pip install nose
   sudo pip install coverage

To run tests execute this command from plugin main directory:

.. code-block:: bash

   make test

GitHub Repository
=================

   * `GitHub repository – Code <https://github.com/NINAnor/NOFAInsert>`__
   * `GitHub repository – Issues <https://github.com/NINAnor/NOFAInsert/issues>`__
