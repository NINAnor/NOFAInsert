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

    def shortDescription(self):
        """
        Method that overrides default behaviour
        and allows printing multiline test description.
        """

        return self._testMethodDoc

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
            self.mc, u'Plugin not initialized properly.')

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
            u'Table "{}" row count "{}" is not as expected "{}".'
            .format(tbl.objectName(), row_count, exp_row_count))

    def test_cb_cur_txt(self):
        """Tests for all combo boxes that current text equals default value."""

        for cb, cb_list in self.mc.ins_mw._nofa_cb_dict.items():
            txt = cb.currentText()
            exp_txt = cb_list[2]

            self.assertEqual(
                cb.currentText(), exp_txt,
                u'Combo box "{}" current text "{}" is not as expected "{}".'
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
                u'Widget "{}" data "{}" does not correspond '
                u'with table data "{}".'
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
                u'Widget "{}" data "{}" does not correspond '
                u'with table data "{}".'
                .format(wdg.objectName(), wdg_data, tbl_data))

    def test_txncvg_tw(self):
        """
        Tests that there are no checked items
        in taxonomic coverage tree widget.
        """

        ckd_txns = self.mc.ins_mw._ckd_txns

        self.assertEqual(
            len(ckd_txns), 0,
            u'There are checked items in taxonomic coverage tree widget: {}'
            .format(ckd_txns))


class TestGuiInteract(unittest.TestCase):
    """Test for plugin GUI interaction."""

    def shortDescription(self):
        """
        Method that overrides default behaviour
        and allows printing multiline test description.
        """

        return self._testMethodDoc

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

        self.srch_wb(wb_str)

        txt = self.mc.ins_mw.lake_name_statlbl.text()
        exp_txt = u'Found 4 location(s).'
        self.assertEqual(
            txt, exp_txt,
            u'Search for location by water body "{}" did not end '
            u'as expected. Status text is "{}" but it is expected to be "{}".'
            .format(wb_str, txt, exp_txt))

        btn = self.mc.ins_mw.loc_load_btn
        self.assertTrue(
            btn.isEnabled(),
            u'Search for location by water body "{}" '
            u'did not enable button "{}".'
            .format(wb_str, btn.objectName()))

    def srch_wb(self, wb_str):
        """
        Searches for water body by the given name.

        :param wb_str: Water body string.
        :type wb_str: str
        """

        self.mc.ins_mw.cntry_code_cb.setCurrentIndex(0)
        self.mc.ins_mw.cnty_cb.setCurrentIndex(0)
        self.mc.ins_mw.muni_cb.setCurrentIndex(0)

        self.mc.ins_mw.wb_le.setText(wb_str)

        self.mc.ins_mw.loc_srch_btn.click()

    def test_loc_srch_fltrs(self):
        """Tests that location search filters work as expected."""

        self.cntry_code_cb = self.mc.ins_mw.cntry_code_cb
        self.cnty_cb = self.mc.ins_mw.cnty_cb
        self.muni_cb = self.mc.ins_mw.muni_cb

        # reset all location search filters and check current text
        idx = 0
        exp_txt = u'<all>'
        for cb in (self.cntry_code_cb, self.cnty_cb, self.muni_cb):
            cb.setCurrentIndex(idx)
            txt = cb.currentText()
            self.assertEqual(
                txt, exp_txt,
                u'Text on index "{}" of "{}" '
                u'is "{}" but it is expected to be "{}".'
                .format(
                    idx, cb.objectName(),
                    txt, exp_txt))

        # check item count
        cntry_str = u'NO'
        self.cntry_code_cb.setCurrentIndex(
            self.cntry_code_cb.findText(cntry_str))

        self.chck_cb_cnt(self.cntry_code_cb, cntry_str, self.cnty_cb, 20)
        self.chck_cb_cnt(self.cntry_code_cb, cntry_str, self.muni_cb, 423)

        cnty_str = u'Troms'
        self.cnty_cb.setCurrentIndex(self.cnty_cb.findText(cnty_str))

        self.chck_cb_cnt(self.cnty_cb, cnty_str, self.muni_cb, 25)

        self.cntry_code_cb.setCurrentIndex(idx)
        for cb in (self.cnty_cb, self.muni_cb):
            self.assertEqual(
                cb.currentIndex(), idx,
                u'Changing index of "{}" to "{}" '
                u'did not change index of "{}" to "{}".'
                .format(
                    self.cntry_code_cb.objectName(), idx,
                    cb.objectName(), idx))

    def chck_cb_cnt(self, sig_cb, sig_cb_str, slt_cb, exp_slt_cb_cnt):
        """
        Checks that item count of `slot` combo box is as expected.

        :param sig_cb: `Signal` combo box.
        :type sig_cb: QComboBox
        :param sig_cb_str: `Signal` combo box string.
        :type sig_cb_str: str
        :param slt_cb: `Slot` combo box.
        :type slt_cb: QComboBox
        :param exp_slt_cb_cnt: Expected `signal` combo box count.
        :type exp_slt_cb_cnt: int
        """

        slt_cb_cnt = slt_cb.count()
        self.assertEqual(
            slt_cb_cnt, exp_slt_cb_cnt,
            u'Changing current item of "{}" to "{}" did not change '
            u'item count of "{}" as expected. '
            u'Item count is "{}" but it is expected to be "{}".'
            .format(
                sig_cb.objectName(), sig_cb_str,
                slt_cb.objectName(),
                slt_cb_cnt, exp_slt_cb_cnt))

    def test_load_loc_lyr(self):
        """
        Tests that location layer is added to interface
        and set as active layer.
        """

        IFACE.removeAllLayers()

        wb_str = u'drop'

        self.srch_wb(wb_str)
        self.mc.ins_mw.loc_load_btn.click()

        self.assertIsNotNone(
            IFACE.activeLayer(), u'Location layer was not added.')

if __name__ == "__main__":
    unittest.main()
