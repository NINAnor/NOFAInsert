# -*- coding: utf-8 -*-
"""
/***************************************************************************
 NOFAInsert
                                 A QGIS plugin
 Insert fish occurrence data to NOFA DB
                             -------------------
        begin                : 2017-01-09
        copyright            : (C) 2017 by NINA
        email                : matteo.destefano@nina.no
        git sha              : $Format:%H$
 ***************************************************************************/

/***************************************************************************
 *                                                                         *
 *   This program is free software; you can redistribute it and/or modify  *
 *   it under the terms of the GNU General Public License as published by  *
 *   the Free Software Foundation; either version 2 of the License, or     *
 *   (at your option) any later version.                                   *
 *                                                                         *
 ***************************************************************************/
 This script initializes the plugin, making it known to QGIS.
"""


def classFactory(iface):
    """Load NOFAInsert class from file NOFAInsert.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """

    from nofa_insert import NOFAInsert
    return NOFAInsert(iface)
