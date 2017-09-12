# -*- coding: utf-8 -*-
"""
/***************************************************************************
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


class MandNotFldExc(Exception):
    """
    A custom exception when a mandatory widget is not filled.
    """

    def __init__(self, wdg):
        """
        Constructor.

        :param nf_nvl: A widget that is not filled/selected.
        :type nf_nvl: QWidget
        """

        self.wdg = wdg
