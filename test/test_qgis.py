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


import os
import unittest
from qgis.core import (
    QgsProviderRegistry,
    QgsCoordinateReferenceSystem,
    QgsRasterLayer)

from utilities import get_qgis_app
QGIS_APP = get_qgis_app()


class TestQGIS(unittest.TestCase):
    """Test for QGIS."""

    def test_providers(self):
        """Tests that QGIS contains several providers."""

        reg = QgsProviderRegistry.instance()
        providers = reg.providerList()

        self.assertIn('gdal', providers)
        self.assertIn('ogr', providers)
        self.assertIn('postgres', providers)

    def test_projection(self):
        """Tests that QGIS properly parses a WKT string."""

        crs = QgsCoordinateReferenceSystem()
        wkt = (
            'GEOGCS["GCS_WGS_1984",'
            'DATUM["D_WGS_1984",'
            'SPHEROID["WGS_1984",6378137.0,298.257223563]],'
            'PRIMEM["Greenwich",0.0],'
            'UNIT["Degree",0.0174532925199433]]')
        crs.createFromWkt(wkt)
        auth_id = crs.authid()
        exp_auth_id = 'EPSG:4326'

        self.assertEqual(auth_id, exp_auth_id)

        # test for a loaded layer
        path = os.path.join(os.path.dirname(__file__), 'tenbytenraster.asc')
        lyr = QgsRasterLayer(path, 'TestRaster')
        auth_id = lyr.crs().authid()

        self.assertEqual(auth_id, exp_auth_id)

if __name__ == '__main__':
    unittest.main()
