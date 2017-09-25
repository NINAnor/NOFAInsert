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

import logging
import os
import sys
import unittest
import warnings

from nofa_insert import NOFAInsert

from utilities import get_qgis_app

sys.path.append(os.path.abspath('..'))

warnings.filterwarnings('ignore', category=RuntimeWarning)

LOGGER = logging.getLogger('QGIS')
QGIS_APP, IFACE, CANVAS, PARENT = get_qgis_app()


class TestGuiInit(unittest.TestCase):
    """Test for plugin initialization."""

    def setUp(self):
        """Runs before each test."""
        pass
 
    def tearDown(self):
        """Runs after each test."""
        pass

    def test_gui_init(self):
        """
        Tests that plugin initializes.
        """

        mc = NOFAInsert(IFACE)
        mc.initGui()
        mc.run()

        self.assertIsNotNone(mc, 'Plugin not initalized properly.')

        self.assertEqual(
            mc.ins_mw.loc_tbl.rowCount(), 1,
            'Location table row count is not 1.')

        self.assertEqual(
            mc.ins_mw.occ_tbl.rowCount(), 1,
            'Occurrence table row count is not 1.')

if __name__ == "__main__":
    unittest.main()
