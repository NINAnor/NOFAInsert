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

from PyQt4.QtCore import Qt

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
    """Test for plugin GUI initialization."""

    def setUp(self):
        """Runs before each test."""

        self.mc = TestGuiInit.mc

    def tearDown(self):
        """Runs after each test."""

        self.mc = None

    @classmethod
    def setUpClass(cls):
        """Runs before an individual class run."""

        cls.mc = NOFAInsert(IFACE)
        cls.mc.initGui()
        cls.mc.run()

    @classmethod
    def tearDownClass(cls):
        """Runs after an individual class run."""

        cls.mc = None

    def test_gui_init(self):
        """Tests that plugin initializes properly."""

        self.assertIsNotNone(
            self.mc, 'Plugin not initialized properly.')

    def test_loc_tbl_row_count(self):
        """Tests that location table row count equals expected value."""

        self.chck_tbl_row_count(self.mc.ins_mw.loc_tbl, 1)

    def test_occ_tbl_row_count(self):
        """Tests that occurrence table row count equals expected value."""

        self.chck_tbl_row_count(self.mc.ins_mw.occ_tbl, 1)

    def chck_tbl_row_count(self, tbl, exp_row_count):
        """
        Checks that table row count equals the given expected value.

        :param tbl: A table.
        :type tbl: QTableWidget
        :param exp_row_count: An expected row count.
        :type exp_row_count: int
        """

        row_count = tbl.rowCount()
        self.assertEqual(
            row_count, exp_row_count,
            'Table "{}" row count "{}" is not as expected "{}".'
            .format(tbl.objectName(), row_count, exp_row_count))

    def test_cb_cur_txt(self):
        """Tests for all combo boxes that current text equals default value."""

        for cb, cb_list in self.mc.ins_mw._nofa_cb_dict.items():
            txt = cb.currentText()
            exp_txt = cb_list[2]

            self.assertEqual(
                cb.currentText(), exp_txt,
                'Combo box "{}" current text "{}" is not as expected "{}".'
                .format(cb.objectName(), txt, exp_txt))

    def test_occ_tbl_wdgs(self):
        """
        Tests for all occurrence widgets that data corresponds with table data.
        """

        tbl = self.mc.ins_mw.occ_tbl
        tbl_wdgs = self.mc.ins_mw.occ_tbl_wdg_hdr_dict.keys()
        m = tbl.currentRow()

        for wdg in tbl_wdgs:
            wdg_data = self.mc.ins_mw.get_wdg_list([wdg], False, True)[0]
            tbl_data = tbl.item(m, tbl_wdgs.index(wdg)).data(Qt.EditRole)

            self.assertEqual(
                wdg_data, tbl_data,
                'Widget "{}" data "{}" does not correspond '
                'with table data "{}".'
                .format(wdg.objectName(), wdg_data, tbl_data))

    def test_loc_tbl_wdgs(self):
        """
        Tests for all current location widgets that data corresponds
        with table data.
        """

        tbl = self.mc.ins_mw.loc_tbl
        all_tbl_wdgs = self.mc.ins_mw.loc_tbl_wdg_hdr_dict.keys()
        cur_tbl_wdgs = (
            [self.mc.ins_mw.loc_edit_met_cb]
            + self.mc.ins_mw._cur_loc_edit_tbl_wdgs)
        m = tbl.currentRow()

        for wdg in all_tbl_wdgs:
            if wdg in cur_tbl_wdgs:
                wdg_data = self.mc.ins_mw.get_wdg_list([wdg], False, True)[0]
            else:
                wdg_data = None

            tbl_data = tbl.item(m, all_tbl_wdgs.index(wdg)).data(Qt.EditRole)

            self.assertEqual(
                wdg_data, tbl_data,
                'Widget "{}" data "{}" does not correspond '
                'with table data "{}".'
                .format(wdg.objectName(), wdg_data, tbl_data))

    def test_txncvg_tw(self):
        """
        Tests that there are no checked items
        in taxonomic coverage tree widget.
        """

        ckd_txns = self.mc.ins_mw._ckd_txns

        self.assertEqual(
            len(ckd_txns), 0,
            'There are checked items in taxonomic coverage tree widget: {}'
            .format(ckd_txns))


class TestGuiInteract(unittest.TestCase):
    """Test for plugin GUI interaction."""

    def setUp(self):
        """Runs before each test."""

        self.mc = TestGuiInteract.mc

    def tearDown(self):
        """Runs after each test."""

        self.mc = None

    @classmethod
    def setUpClass(cls):
        """Runs before an individual class run."""

        cls.mc = NOFAInsert(IFACE)
        cls.mc.initGui()
        cls.mc.run()

    @classmethod
    def tearDownClass(cls):
        """Runs after an individual class run."""

        cls.mc = None

    def test_loc_srch_wb(self):
        """
        Tests that searching for location by water body works.
        """

        wb_str = u'drop'
        self.mc.ins_mw.wb_le.setText(wb_str)

        self.mc.ins_mw.loc_srch_btn.click()

        txt = self.mc.ins_mw.lake_name_statlbl.text()
        exp_txt = u'Found 4 location(s).'
        self.assertEqual(
            txt, exp_txt,
            u'Searching for location by water body "{}" did not end '
            u'as expected. Status text is "{}" but should be "{}".'
            .format(wb_str, txt, exp_txt))

        btn = self.mc.ins_mw.loc_load_btn
        self.assertTrue(
            btn.isEnabled(),
            u'Searching for location by water body "{}" '
            u'button "{}" is not enabled'
            .format(wb_str, btn.objectName()))

if __name__ == "__main__":
    unittest.main()
