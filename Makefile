#/***************************************************************************
# NOFAInsert
#
# Insert fish occurrence data to NOFA DB
#                               -------------------
#         begin                : 2017-01-09
#         git sha              : $Format:%H$
#         copyright            : (C) 2017 by NINA
#         contributors         : stefan.blumentrath@nina.no
#                                matteo.destefano@nina.no
#                                jakob.miksch@nina.no
#                                ondrej.svoboda@nina.no
# ***************************************************************************/
#
#/***************************************************************************
# *																		 *
# *   This program is free software; you can redistribute it and/or modify  *
# *   it under the terms of the GNU General Public License as published by  *
# *   the Free Software Foundation; either version 2 of the License, or	 *
# *   (at your option) any later version.								   *
# *																		 *
# ***************************************************************************/

#################################################
# Edit the following to match your sources lists
#################################################


#Add iso code for any locales you want to support here (space separated)
# default is no locales
# LOCALES = af
LOCALES =

# If locales are enabled, set the name of the lrelease binary on your system. If
# you have trouble compiling the translations, you may have to specify the full path to
# lrelease
#LRELEASE = lrelease
#LRELEASE = lrelease-qt4


# translation
SOURCES = \
	__init__.py \
	test_plugin.py test_plugin_dialog.py

PLUGINNAME = NOFAInsert-master

PY_FILES = \
	__init__.py \
	test_plugin.py test_plugin_dialog.py

UI_FILES = test_plugin_dialog_base.ui

EXTRA_DIRS =

PEP8EXCLUDE=pydev,conf.py,third_party,ui,create_log_tbls.py,autoimage.py,numfig.py


#################################################
# Normally you would not need to edit below here
#################################################

HELP = help/build/html

QGISDIR=.qgis2

default: compile

compile: $(COMPILED_RESOURCE_FILES)

test: compile
	@echo
	@echo "----------------------"
	@echo "Regression Test Suite"
	@echo "----------------------"

	@# Preceding dash means that make will continue in case of errors
	@-export PYTHONPATH=`pwd`:$(PYTHONPATH); \
		export QGIS_DEBUG=0; \
		export QGIS_LOG_FILE=/dev/null; \
		nosetests -v --with-id --with-coverage --cover-package=. \
		3>&1 1>&2 2>&3 3>&- || true
	@echo "----------------------"
	@echo "If you get a 'no module named qgis.core error, try sourcing"
	@echo "the helper script we have provided first then run make test."
	@echo "e.g. source run-env-linux.sh <path to qgis install>; make test"
	@echo "----------------------"

# The dclean target removes compiled python files from plugin directory
# also deletes any .git entry
clean_pyc:
	@echo
	@echo "-----------------------------------"
	@echo "Removing any compiled python files."
	@echo "-----------------------------------"
	find $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME) -iname "*.pyc" -delete

clean_test:
	@echo
	@echo "------------------------"
	@echo "Removing any test files."
	@echo "------------------------"
	find $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME) -iname ".coverage" -delete
	find $(HOME)/$(QGISDIR)/python/plugins/$(PLUGINNAME) -iname ".noseids" -delete

clean:
	@echo
	@echo "------------------------------------"
	@echo "Removing uic and rcc generated files"
	@echo "------------------------------------"
	rm $(COMPILED_UI_FILES)

doc:
	@echo
	@echo "------------------------------------"
	@echo "Building documentation using sphinx."
	@echo "------------------------------------"
	cd docs; make html


# Run pep8 style checking
#http://pypi.python.org/pypi/pep8
pep8:
	@echo
	@echo "-----------"
	@echo "PEP8 issues"
	@echo "-----------"
	@pep8 --repeat --ignore=E203,E121,E122,E123,E124,E125,E126,E127,E128 --exclude $(PEP8EXCLUDE) . || true
	@echo "-----------"
	@echo "Ignored in PEP8 check:"
	@echo $(PEP8EXCLUDE)
