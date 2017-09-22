# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NOFAInsert
                                 A QGIS plugin
 Insert fish occurrence data to NOFA DB
                              -------------------
        begin                : 2017-01-09
        git sha              : $Format:%H$
        copyright            : (C) 2017 by NINA
        contributors         : stefan.blumentrath@nina.no
                               matteo.destefano@nina.no
                               jakob.miksch@nina.no
                               ondrej.svoboda@nina.no
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
"""

import sys
import logging


LOGGER = logging.getLogger('QGIS')
QGIS_APP = None
CANVAS = None
PARENT = None
IFACE = None


def get_qgis_app():
    """
    Start one QGIS application to test against.

    If QGIS is already running the handle to that app is returned.

    :returns:
     | A tuple containing:
     |    - *QgsApplication* -- QGIS application
     |    - *QgisInterface* -- QGIS interface
     |    - *QgsMapCanvas* -- QGIS map canvas
     |    - *QWidget* -- parent
    :rtype: tuple
    """

    try:
        from PyQt4 import QtGui, QtCore
        from qgis.core import QgsApplication
        from qgis.gui import QgsMapCanvas
        from qgis_interface import QgisInterface
    except ImportError:
        return None, None, None, None

    global QGIS_APP

    if QGIS_APP is None:
        # All test will run qgis in gui mode
        gui_flag = True
        QGIS_APP = QgsApplication(sys.argv, gui_flag)
        # make sure QGIS_PREFIX_PATH is set in your env if needed
        QGIS_APP.initQgis()
        s = QGIS_APP.showSettings()
        LOGGER.debug(s)

    global PARENT
    if PARENT is None:
        PARENT = QtGui.QWidget()

    global CANVAS
    if CANVAS is None:
        CANVAS = QgsMapCanvas(PARENT)
        CANVAS.resize(QtCore.QSize(400, 400))

    global IFACE
    if IFACE is None:
        # QgisInterface is a stub implementation of the QGIS plugin interface
        IFACE = QgisInterface(CANVAS)

    return QGIS_APP, IFACE, CANVAS, PARENT
