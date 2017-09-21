# -*- coding: utf-8 -*-
"""
/***************************************************************************
 InsMw
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

from qgis.core import (
    QgsApplication, QgsMessageLog, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsPoint, QgsRasterLayer, QgsMapLayerRegistry,
    QgsVectorLayer, QgsDataSourceURI, QgsProject, QgsFeature, QgsGeometry)
from qgis.gui import QgsMapToolEmitPoint

from PyQt4 import QtGui, uic
from PyQt4.QtCore import (
    QSettings, QCoreApplication, Qt, QObject, QDate, QDateTime, QObject,
    QSignalMapper)
from PyQt4.QtGui import (
    QMessageBox, QTreeWidgetItem, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QMainWindow, QDoubleValidator, QIntValidator, QComboBox,
    QLineEdit, QDateEdit, QAbstractItemView, QValidator, QBrush, QColor,
    QPlainTextEdit, QTextCursor, QWidget)

from collections import defaultdict, OrderedDict
import os
import psycopg2
import psycopg2.extras
import datetime
import uuid
import sys

import de
import dtst_dlg
import prj_dlg
import ref_dlg
import vald
from .. import db, ordered_set


class ActLyrExc(Exception):
    """
    A custom exception when there is no active layer.
    """

    pass


class LocLyrSrcExc(Exception):
    """
    A custom exception when a layer source is not `nofa.location`.
    """

    pass


class SelFeatExc(Exception):
    """
    A custom exception when there are no selected features.
    """

    pass


class MtdtNotFldExc(Exception):
    """
    A custom exception when a metadata mandatory widget is not filled.
    """

    def __init__(self, wdg):
        """
        Constructor.

        :param nf_nvl: A widget that is not filled/selected.
        :type nf_nvl: QWidget
        """

        self.wdg = wdg


class OccNotFldExc(Exception):
    """
    A custom exception when a mandatory field in occurrence row is not filled.
    """

    pass


class NoLocExc(Exception):
    """
    A custom exception when no location is provided.
    """

    pass


class LocidTxtExc(Exception):
    """
    A custom exception when there is a problem
    with format of `locationID` location text.
    """

    pass


class NvlTxtExc(Exception):
    """
    A custom exception when there is a problem
    with format of `Norwegian VatLnr` location text.
    """

    pass


class CoorTxtExc(Exception):
    """
    A custom exception when there is a problem
    with format of `coordinates` location text.
    """

    pass


class LocidMtyExc(Exception):
    """
    A custom exception when location ID is empty.
    """

    def __init__(self, m):
        """
        Constructor.

        :param m: A location table row.
        :type m: int
        """

        self.m = m


class LocidFmtExc(Exception):
    """
    A custom exception when format of location ID is not *uuid.UUID*.
    """

    def __init__(self, m, locid):
        """
        Constructor.

        :param m: A location table row.
        :type m: int
        :param locid: A location ID.
        :type locid: str
        """

        self.m = m
        self.locid = locid


class LocidNfExc(Exception):
    """
    A custom exception when location ID was not found.
    """

    def __init__(self, m, locid):
        """
        Constructor.

        :param m: A location table row.
        :type m: int
        :param locid: A location ID.
        :type locid: str
        """

        self.m = m
        self.locid = locid


class CoorMtyExc(Exception):
    """
    A custom exception when coordinate is empty.
    """

    def __init__(self, m):
        """
        Constructor.

        :param m: A location table row.
        :type m: int
        """

        self.m = m


class NvlMtyExc(Exception):
    """
    A custom exception when Norwegian VatLnr is empty.
    """

    def __init__(self, m):
        """
        Constructor.

        :param m: A location table row.
        :type m: int
        """

        self.m = m


class NvlNfExc(Exception):
    """
    A custom exception when Norwegian VatLnr was not found.
    """

    def __init__(self, m, nvl):
        """
        Constructor.

        :param m: A location table row.
        :type m: int
        :param nvl: Norwegian VatLnr(s) that was/were not found.
        :type nvl: tuple
        """

        self.m = m
        self.nvl = nvl


FORM_CLASS, _ = uic.loadUiType(
    os.path.join(os.path.dirname(__file__), 'ins_mw.ui'))


class InsMw(QMainWindow, FORM_CLASS):
    """
    A main window for inserting data into NOFA database.
    """

    def __init__(self, iface, mc, plugin_dir):
        """
        Constructor.

        :param iface: A reference to the QgisInterface.
        :type iface: QgisInterface
        :param mc: A reference to the main class.
        :type mc: object
        :param plugin_dir: A plugin directory.
        :type plugin_dir: str
        """

        super(InsMw, self).__init__()

        # set up the user interface from Designer.
        self.setupUi(self)

        self.iface = iface
        self.mc = mc
        self.plugin_dir = plugin_dir

        self._setup_self()

    def _setup_self(self):
        """
        Sets up self.
        """

        self.org = u'NINA'
        self.app_name = u'NOFAInsert - {}'.format(
            self.mc.con_info[self.mc.db_str])

        self.settings = QSettings(self.org, self.app_name)

        self.setWindowTitle(self.app_name)

        self.loctp_dict = {
            u'Norwegian VatnLnr': 'no_vatn_lnr',
            u'coordinates UTM32': 25832,
            u'coordinates UTM33': 25833}

        self.crs_dict = OrderedDict([
            (u'UTM32', QgsCoordinateReferenceSystem('EPSG:25832')),
            (u'UTM33', QgsCoordinateReferenceSystem('EPSG:25833'))])

        self.loc_met_list = [
            u'locationID',
            u'coordinates',
            u'Norwegian VatLnr']

        self.opt_list = [
            u'new',
            u'nearest']

        self.dash_split_str = u' - '
        self.at_split_str = u'@'

        self.mty_str = u''
        self.all_str = u'<all>'
        self.sel_str = u'<select>'

        self.forbi_str_list = [
            self.mty_str,
            self.sel_str]

        self.today_dt = datetime.datetime.today().date()
        self.nxt_week_dt = self.today_dt + datetime.timedelta(days=7)
        self.fltr_str_dt = datetime.datetime(2017, 1, 1)

        # self.def_clr = self.ins_btn.palette().background().color()
        self.grn_clr = QColor(177, 234, 177)
        self.red_clr = QColor(234, 177, 177)
        self.yel_clr = QColor(234, 234, 177)

        self._build_wdgs()

    def _build_wdgs(self):
        """
        Builds and sets up own widgets.
        """

        self._build_main_tab_wdgs()
        self._build_hist_tab_wdgs()

        self.main_tabwdg.setCurrentIndex(0)
        self.loc_tabwdg.setCurrentIndex(0)
        self.loc_manual_swdg.setCurrentIndex(0)

        self._create_loc_tbl()
        self._create_occ_tbl()

        self._con_main_tab_wdgs()
        self._con_hist_tab_wdgs()

    def _build_main_tab_wdgs(self):
        """
        Builds and sets up widgets in main tab.
        """

        # event - dateStart
        self.dtstrt_mde = de.MtyDe(self)
        self.dtstrt_mde.setObjectName(u'dtstrt_mde')
        self.dtstrt_mde.setDisplayFormat('yyyy-MM-dd')
        self.event_grid_lyt.addWidget(self.dtstrt_mde, 4, 1, 1, 1)

        # event - dateEnd
        self.dtend_mde = de.MtyDe(self)
        self.dtend_mde.setObjectName(u'dtend_mde')
        self.dtend_mde.setDisplayFormat('yyyy-MM-dd')
        self.event_grid_lyt.addWidget(self.dtend_mde, 5, 1, 1, 1)

        # occurrence - verifiedDate
        self.verdt_mde = de.MtyDe(self)
        self.verdt_mde.setObjectName(u'verdt_mde')
        self.verdt_mde.setDisplayFormat('yyyy-MM-dd')
        self.occ_grid_lyt.addWidget(self.verdt_mde, 8, 3, 1, 1)

        # dictionary - widget: occurrence table header
        self.loc_tbl_wdg_hdr_dict = OrderedDict([
            (self.loc_edit_met_cb, u'method'),
            (self.loc_edit_locid_le, u'locationID'),
            (self.loc_edit_crs_cb, u'CRS'),
            (self.loc_edit_opt_cb, u'option'),
            (self.loc_edit_x_coor_le, u'X'),
            (self.loc_edit_y_coor_le, u'Y'),
            (self.loc_edit_verloc_le, u'verbatimLocality'),
            (self.loc_edit_nvl_le, u'NVL')])

        # validators
        self.smpsv_le.setValidator(QIntValidator(None))
        self.smpe_le.setValidator(QIntValidator(None))
        self.oq_le.setValidator(QDoubleValidator(None))
        self.loc_edit_x_coor_le.setValidator(QDoubleValidator(None))
        self.loc_edit_y_coor_le.setValidator(QDoubleValidator(None))
        self.loc_edit_nvl_le.setValidator(QIntValidator(None))

        self.event_input_wdgs = [
            self.smpp_cb,
            self.smpsu_cb,
            self.smpsv_le,
            self.smpe_le,
            self.dtstrt_mde,
            self.dtend_mde,
            self.fldnum_le,
            self.rcdby_le,
            self.eventrmk_le,
            self.relia_cb]

        # dictionary - widget: occurrence table header
        self.occ_tbl_wdg_hdr_dict = OrderedDict([
            (self.txn_cb, u'taxon'),
            (self.ectp_cb, u'ecotype'),
            (self.oqt_cb, u'organismQuantityType'),
            (self.oq_le, u'organismQuantity'),
            (self.occstat_cb, u'occurrenceStatus'),
            (self.poptrend_cb, u'populationTrend'),
            (self.recnum_le, u'recordNumber'),
            (self.occrmk_le, u'occurrenceRemarks'),
            (self.estm_cb, u'establishmentMeans'),
            (self.estrmk_le, u'establishmentRemarks'),
            (self.spwnc_cb, u'spawningCondition'),
            (self.spwnl_cb, u'spawningLocation'),
            (self.vfdby_le, u'verifiedBy'),
            (self.verdt_mde, u'verifiedDate')])

        # tool for setting coordinates by left mouse click
        self.cnvs = self.iface.mapCanvas()
        self.coord_cnvs_tool = QgsMapToolEmitPoint(self.cnvs)
        self.coord_cnvs_tool.canvasClicked.connect(
            self._set_cnvs_coord_to_loc_tbl)

        self.loc_load_btn.setEnabled(False)

        self.occ_mand_wdgs = [
            self.txn_cb,
            self.occstat_cb,
            self.estm_cb]

        self.mtdt_mand_wdgs = [
            self.smpp_cb,
            self.dtend_mde,
            self.rcdby_le,
            self.dtst_cb,
            self.prj_cb]

        self.all_mand_wdgs = self.occ_mand_wdgs + self.mtdt_mand_wdgs

        self.set_mand_wdgs(self.all_mand_wdgs)

        # self.main_hspltr.setStretchFactor(0, 1)
        # self.main_hspltr.setStretchFactor(1, 2)
        self.occ_hspltr.setStretchFactor(0, 1)
        self.occ_hspltr.setStretchFactor(1, 2)

    def _build_hist_tab_wdgs(self):
        """
        Builds and sets up widgets in history tab.
        """

        # connect date edits min and max dates
        self.hist_ins_dtstrt_de.dateChanged.connect(
            self.hist_ins_dtend_de.setMinimumDate)
        self.hist_ins_dtend_de.dateChanged.connect(
            self.hist_ins_dtstrt_de.setMaximumDate)
        self.hist_upd_dtstrt_de.dateChanged.connect(
            self.hist_upd_dtend_de.setMinimumDate)
        self.hist_upd_dtend_de.dateChanged.connect(
            self.hist_upd_dtstrt_de.setMaximumDate)

        # set date edits' dates
        self.hist_ins_dtstrt_de.setDate(self.fltr_str_dt)
        self.hist_ins_dtend_de.setDate(self.today_dt)
        self.hist_upd_dtstrt_de.setDate(self.fltr_str_dt)
        self.hist_upd_dtend_de.setDate(self.today_dt)

        # dictionary for updating history tables
        self.hist_tbls_fnc_dict = {
            self.hist_occ_tbl: db.get_hist_occ_list,
            self.hist_loc_tbl: db.get_hist_loc_list,
            self.hist_event_tbl: db.get_hist_event_list,
            self.hist_dtst_tbl: db.get_hist_dtst_list,
            self.hist_prj_tbl: db.get_hist_prj_list,
            self.hist_ref_tbl: db.get_hist_ref_list}

        self.hist_input_wdgs = [
            self.usr_cb,
            self.hist_ins_dtstrt_de,
            self.hist_ins_dtend_de,
            self.hist_upd_dtstrt_de,
            self.hist_upd_dtend_de]

    def _create_loc_tbl(self):
        """
        Creates an occurrence table with one row.
        """

        self._create_tbl_main_tab(
            self.loc_tbl,
            self.loc_tbl_wdg_hdr_dict.values(),
            self.loc_tbl_wdg_hdr_dict.keys(),
            self._upd_loc_tbl_item)

    def _create_occ_tbl(self):
        """
        Creates an occurrence table with one row.
        """

        self._create_tbl_main_tab(
            self.occ_tbl,
            self.occ_tbl_wdg_hdr_dict.values(),
            self.occ_tbl_wdg_hdr_dict.keys(),
            self._upd_occ_tbl_item)

    def _con_main_tab_wdgs(self):
        """
        Connects main tab widgets.
        """

        self.main_tabwdg.currentChanged.connect(self._fetch_schema)

        self._con_loc_wdgs()
        self._con_mtdt_wdgs()
        self._con_occ_wdgs()

        self.txncvg_tw.itemChanged.connect(self._upd_txncvg_tw_chldn)

        self.rst_btn.clicked.connect(self._rst)
        self.ins_btn.clicked.connect(self._ins)

    def _con_loc_wdgs(self):
        """
        Connects location widgets.
        """

        self.wb_le.returnPressed.connect(self._srch_loc)

        self.cntry_code_cb.currentIndexChanged.connect(self._pop_cnty_cb)
        self.cnty_cb.currentIndexChanged.connect(self._pop_muni_cb)

        self.loc_srch_btn.clicked.connect(self._srch_loc)
        self.loc_load_btn.clicked.connect(self._load_loc_lyr)
        self.add_seld_feats_btn.clicked.connect(self._add_locid_seld_feats)

        self.osm_basemap_btn.clicked.connect(self._add_osm_wms_lyr)

        self.loc_edit_coord_cnvs_btn.clicked.connect(self._act_coord_cnvs_tool)

        self.loc_manual_met_cb.currentIndexChanged.connect(
            self._upd_loc_manual_swdg)
        self.loc_manual_met_cb.currentIndexChanged.emit(
            self.loc_manual_met_cb.currentIndex())

        self.loc_manual_locid_add_btn.clicked.connect(self._add_manual_locid)
        self.loc_manual_coor_add_btn.clicked.connect(self._add_manual_coor)
        self.loc_manual_nvl_add_btn.clicked.connect(self._add_manual_nvl)

        self.loc_edit_met_cb.currentIndexChanged.connect(self._upd_loc_tbl_row)

        self.loc_tbl.itemSelectionChanged.connect(self._upd_loc_tbl_wdgs)

        self.loc_tabwdg.currentChanged.connect(self._upd_loc_tbl_wdgs)

        # table buttons - connect
        self.loc_rowup_btn.clicked.connect(self._sel_row_up)
        self.loc_rowdwn_btn.clicked.connect(self._sel_row_dwn)
        self.loc_addrow_btn.clicked.connect(self._add_tbl_row)
        self.loc_delrow_btn.clicked.connect(self._del_tbl_row)
        self.loc_rstrow_btn.clicked.connect(self._rst_tbl_row)
        self.loc_rstallrows_btn.clicked.connect(self._rst_all_tbl_rows)
        self.loc_del_btn.clicked.connect(self._del_all_tbl_rows)

        self.preview_btn.clicked.connect(self._preview_loc)

    def _con_mtdt_wdgs(self):
        """
        Connects metadata widgets.
        """

        self.adddtst_btn.clicked.connect(self._open_dtst_dlg)
        self.addprj_btn.clicked.connect(self._open_prj_dlg)
        self.addref_btn.clicked.connect(self._open_ref_dlg)

        self.dtst_cb.activated.connect(self._upd_mtdt_lw)
        self.prj_cb.activated.connect(self._upd_mtdt_lw)
        self.ref_cb.activated.connect(self._upd_mtdt_lw)

    def _con_occ_wdgs(self):
        """
        Connects occurrence widgets.
        """

        self.txn_cb.currentIndexChanged.connect(self._pop_ectp_cb)

        self.occ_tbl.itemSelectionChanged.connect(self._upd_occ_tbl_wdgs)

        # table buttons - connect
        self.occ_rowup_btn.clicked.connect(self._sel_row_up)
        self.occ_rowdwn_btn.clicked.connect(self._sel_row_dwn)
        self.occ_addrow_btn.clicked.connect(self._add_tbl_row)
        self.occ_delrow_btn.clicked.connect(self._del_tbl_row)
        self.occ_rstrow_btn.clicked.connect(self._rst_tbl_row)
        self.occ_rstallrows_btn.clicked.connect(self._rst_all_tbl_rows)
        self.occ_del_btn.clicked.connect(self._del_all_tbl_rows)

    def _con_hist_tab_wdgs(self):
        """
        Connects history tab widgets.
        """

        self._con_wdgs_sgnls_to_met(self.hist_input_wdgs, self._fill_hist_tbls)

    def set_mand_wdgs(self, wdgs):
        """
        Sets mandatory widgets. Mandatory widgets have predefined color
        when they are not filled/selected.

            - *QLineEdit* -- must contain at least one
            - *QComboBox* -- selected value can not be in list of forbidden
              strings
            - *QDateEdit* -- user must edit (click) on it at least once

        :param wdgs: A list of widgets to be set as mandatory.
        :type wdgs: list
        """

        for wdg in wdgs:
            if isinstance(wdg, QLineEdit):
                wdg.setValidator(vald.LenTxtVald(wdg))
                wdg.textChanged.connect(self._chck_state_text)
                wdg.textChanged.emit(wdg.text())
            elif isinstance(wdg, QComboBox):
                wdg.currentIndexChanged.connect(self._chck_state_text)
                wdg.currentIndexChanged.emit(wdg.currentIndex())
            elif isinstance(wdg, QDateEdit):
                wdg.dateChanged.connect(self._chck_state_text)
                wdg.dateChanged.emit(wdg.date())

    def _chck_state_text(self):
        """
        Checks a sender's state or text and sets its background color
        accordingly.
        """

        sndr = self.sender()

        if isinstance(sndr, QLineEdit):
            valr = sndr.validator()
            state = valr.validate(sndr.text(), 0)[0]
        elif isinstance(sndr, QComboBox):
            txt = sndr.currentText()
            if txt == self.sel_str:
                state = QValidator.Invalid
            else:
                state = QValidator.Acceptable
        elif isinstance(sndr, QDateEdit):
            txt = sndr.findChild(QLineEdit).text()

            if txt == self.mty_str:
                state = QValidator.Invalid
            else:
                state = QValidator.Acceptable
        if state == QValidator.Intermediate or state == QValidator.Invalid:
            clr = self.red_clr
            stl = 'background-color: {}'.format(clr.name())
        else:
            stl = ''

        sndr.setStyleSheet(stl)

    def chck_mand_wdgs(self, mand_wdgs, exc):
        """
        Checks if the given mandatory widgets are filled.

        :param mand_wdgs: A list of mandatory widgets.
        :type mand_wdgs: list
        :param exc: An exception that should be raised.
        :type exc: Exception
        """

        for wdg in mand_wdgs:
            if isinstance(wdg, QLineEdit):
                valr = wdg.validator()
                if valr.validate(wdg.text(), 0)[0] != QValidator.Acceptable:
                    raise exc(wdg)
            elif isinstance(wdg, QComboBox):
                if wdg.currentText() == self.sel_str:
                    raise exc(wdg)
            elif isinstance(wdg, QDateEdit):
                if wdg.findChild(QLineEdit).text() == self.mty_str:
                    raise exc(wdg)

    def _upd_loc_manual_swdg(self, idx):
        """
        Sets index of location manual stacked widget.
        Also resets all input widgets.

        :param idx: A current index of location manual method combo box.
        :type idx: int
        """

        self.loc_manual_swdg.setCurrentIndex(idx)

        self._rst_wdgs(self._cur_loc_manual_tbl_wdgs)

    def _add_osm_wms_lyr(self):
        """
        Adds OpenStreetMap WMS layer.
        """

        xml_fp = os.path.join(self.plugin_dir, 'nofa', 'wms', 'osm.xml')

        lyr = QgsRasterLayer(xml_fp, 'OSM')

        if lyr.isValid():
            QgsMapLayerRegistry.instance().addMapLayer(lyr, False)

            lyr_count = QgsMapLayerRegistry.instance().count()

            lyr_root = QgsProject.instance().layerTreeRoot()
            lyr_root.insertLayer(lyr_count, lyr)

    def _srch_loc(self):
        """
        Searches for location.
        Data are filtered based on information in widgets.
        """

        wb, cntry_code, cnty, muni = self._loc_fltrs

        self.loc_load_btn.setEnabled(False)

        locid_list = db.get_loc_by_fltrs(
            self.mc.con, wb, cntry_code, cnty, muni)

        loc_count = len(locid_list)

        if loc_count != 0:
            self.loc_load_btn.setEnabled(True)

            self.locid_list = locid_list
            self.loc_lyr_name = u'location-{}-{}-{}-{}'.format(
                wb, cntry_code, cnty, muni)
        else:
            self.loc_load_btn.setEnabled(False)

        self.lake_name_statlbl.setText(
            u'Found {} location(s).'.format(loc_count))

    def _get_val_txt(self, txt, forbi=False, all=False):
        """
        Returns a validated text.

        :param txt: A text to be validated.
        :type txt: str
        :param forbi: True to allow forbidden text, False otherwise.
        :type forbi: bool
        :param all: True to allow all text, False otherwise.
        :type all: bool

        :returns: A filter, None when text is in list of forbidden strings
            or when length of text is zero.
        :rtype: str
        """

        if forbi is False and txt in self.forbi_str_list:
            val_txt = None
        elif all is False and txt == self.all_str:
            val_txt = None
        elif len(txt) == 0:
            val_txt = None
        else:
            val_txt = txt

        return val_txt

    @property
    def _loc_fltrs(self):
        """
        Returns location filters.
        It is used to filter locations.

        :returns:
         | A tuple containing:
         |    - *str* -- water body
         |    - *str* -- country code
         |    - *str* -- county
         |    - *str* -- municipality
        :rtype: tuple
        """

        wb = self._wb
        cntry_code = self._cntry_code
        cnty = self._cnty
        muni = self._muni

        return (wb, cntry_code, cnty, muni)

    @property
    def _wb(self):
        """
        Returns a water body from water body line edit.
        Returns None when there is no text in the line edit.

        :returns: A water body, None when there is no text in the line edit.
        :rtype: str
        """

        txt = self.wb_le.text()

        wb = self._get_val_txt(txt, all=True)

        return wb

    @property
    def _cntry_code(self):
        """
        Returns a country code from country code combo box.

        :returns: A country code, None when text is equal to `<all>` string
            or when length of text is zero.
        :rtype: str
        """

        txt = self.cntry_code_cb.currentText()

        cntry_code = self._get_val_txt(txt)

        return cntry_code

    @property
    def _cnty(self):
        """
        Returns a county from county combo box.

        :returns: A county, None when text is equal to `<all>` string
            or when length of text is zero.
        :rtype: str
        """

        txt = self.cnty_cb.currentText()

        cnty = self._get_val_txt(txt)

        return cnty

    @property
    def _muni(self):
        """
        Returns a municipality from municipality combo box.

        :returns: A municipality, None when text is equal to `<all>` string
            or when length of text is zero.
        :rtype: str
        """

        txt = self.muni_cb.currentText()

        muni = self._get_val_txt(txt)

        return muni

    @property
    def _txn(self):
        """
        Returns a taxon from taxon combo box.

        :returns: A taxon, None when text is equal to `<all>` string
            or when length of text is zero.
        :rtype: str
        """

        txt = self.txn_cb.currentText()

        txn = self._get_val_txt(txt)

        return txn

    def _load_loc_lyr(self):
        """
        Loads a layer containing found locations.
        """

        wb, cntry_code, cnty, muni = self._loc_fltrs

        loc_lyr = self._get_loc_lyr(
            self.locid_list,
            u'search_location-{}-{}-{}-{}'.format(wb, cntry_code, cnty, muni))

        if loc_lyr.isValid():
            QgsMapLayerRegistry.instance().addMapLayer(loc_lyr)

    def _get_loc_lyr(self, locid_list, loc_lyr_name):
        """
        Returns a location layer containing features with the given
        location IDs.
        The name of the returned location layer is set according to the given
        name.

        :param locid_list: A list of location IDs.
        :type locid_list: list
        :param loc_lyr_name: A location layer name.
        :type loc_lyr_name: str

        :returns: A location layer containing features with the given
            location IDs.
        :rtype: QgsVectorLayer
        """

        uri = QgsDataSourceURI()

        con_info = self.mc.con_info

        uri.setConnection(
            con_info[self.mc.host_str],
            con_info[self.mc.port_str],
            con_info[self.mc.db_str],
            con_info[self.mc.usr_str],
            con_info[self.mc.pwd_str])

        uri.setDataSource(
            'nofa',
            'location',
            'geom',
            '"locationID" IN ({})'.format(
                ', '.join(['\'{}\''.format(str(l)) for l in locid_list])),
            'locationID')

        loc_lyr = QgsVectorLayer(uri.uri(), loc_lyr_name, u'postgres')

        return loc_lyr

    def _add_locid_seld_feats(self):
        """
        Adds location IDs of selected features to the location table.
        """

        try:
            lyr = self.iface.activeLayer()

            self._chck_lyr(lyr)

            if lyr.selectedFeatureCount() == 0:
                raise SelFeatExc()

            sel_feats = lyr.selectedFeaturesIterator()

            for feat in sel_feats:
                id = str(feat.attribute('locationID'))

                self._set_loc_tbl_row(self._get_locid_list(id))
        except ActLyrExc:
            QMessageBox.warning(
                self,
                u'No Active Layer',
                u'There is no active layer.')
        except LocLyrSrcExc:
            QMessageBox.warning(
                self,
                u'Layer Source',
                u'Source of active layer is not "nofa.location".')
        except SelFeatExc:
            QMessageBox.warning(
                self,
                u'Selected Features',
                u'There are no selected features.')

    def _chck_lyr(self, lyr):
        """
        Checks if the given layer is a from `nofa.location` table.

        :param lyr: A layer to be checked.
        :type lyr: QgsVectorLayer
        """

        try:
            uri = QgsDataSourceURI(lyr.source())
        except AttributeError:
            raise ActLyrExc()

        if uri.schema() != 'nofa' or uri.table() != 'location':
            raise LocLyrSrcExc()

    def _get_locid_list(self, id):
        """
        Returns a location ID list that is used to populate location table.

        :param id: A location ID.
        :type id: str

        :returns: A location ID list.
        :rtype: list
        """

        locid_list = [None] * len(self.loc_tbl_wdg_hdr_dict)

        locid_list[0] = self.loc_met_list[0]
        locid_list[1] = id

        return locid_list

    def _extr_locid_list(self, locid_list):
        """
        Extracts data from location ID list.

        :param locid_list: A location ID list.
        :type locid_list: list

        :returns: A location ID.
        :rtype: str
        """

        locid = locid_list[1]

        return locid

    def _get_coor_list(self, crs_desc, opt, x, y, verb_loc=None):
        """
        Returns a coordinates list that is used to populate location table.

        :param crs_desc: A CRS description.
        :type crs_desc: str
        :param opt: An option.
        :type opt: str
        :param x: X coordinate.
        :type x: float
        :param y: Y coordinate.
        :type y: float.
        :param verb_loc: A verbatim locality.
        :type verb_loc: str

        :returns: A coordinates list.
        :rtype: list.
        """

        coor_list = [None] * len(self.loc_tbl_wdg_hdr_dict)

        coor_list[0] = self.loc_met_list[1]
        coor_list[2] = crs_desc
        coor_list[3] = opt
        coor_list[4] = str(x)
        coor_list[5] = str(y)
        coor_list[6] = verb_loc

        return coor_list

    def _extr_coor_list(self, coor_list):
        """
        Extracts data from coordinates list.

        :param coor_list: A coordinates list.
        :type coor_list: list

        :returns:
         | A tuple containing:
         |    - *str* -- CRS description,
         |    - *str* -- option
         |    - *float* -- X coordinate
         |    - *float* -- Y coordinate
         |    - *str* -- verbatim locality
        :rtype: tuple
        """

        crs_desc = coor_list[2]
        opt = coor_list[3]
        x = float(coor_list[4])
        y = float(coor_list[5])
        verb_loc = coor_list[6]

        return (crs_desc, opt, x, y, verb_loc)

    def _get_nvl_list(self, nvl):
        """
        Returns a `Norwegian VatnLnr` list that is used to populate location
        table.

        :param nvl: A `Norwegian VatnLnr`.
        :type nvl: int

        :returns: A `Norwegian VatnLnr` list.
        :rtype: list
        """

        nvl_list = [None] * len(self.loc_tbl_wdg_hdr_dict)

        nvl_list[0] = self.loc_met_list[2]
        nvl_list[7] = str(nvl)

        return nvl_list

    def _extr_nvl_list(self, nvl_list):
        """
        Extracts data from `Norwegian VatnLnr` list.

        :param nvl_list: A `Norwegian VatnLnr` list.
        :type nvl_list: list

        :returns: A `Norwegian VatnLnr`.
        :rtype: int
        """

        nvl = int(nvl_list[7])

        return nvl

    def dsc_from_iface(self):
        """
        Disconnects the plugin from the QGIS interface.
        """

        if self.iface.mapCanvas().mapTool() == self.coord_cnvs_tool:
            self.iface.mapCanvas().unsetMapTool(self.coord_cnvs_tool)
            self.iface.mapCanvas().setMapTool(self.last_map_tool)

    def _act_coord_cnvs_tool(self):
        """
        Activates a tool that allows user to set coordinates by mouse click.
        """

        self.last_map_tool = self.iface.mapCanvas().mapTool()
        self.iface.mapCanvas().setMapTool(self.coord_cnvs_tool)

    def _set_cnvs_coord_to_loc_tbl(self, pnt, btn):
        """
        Sets canvas coordinates to the location table.
        It transforms coordinates to the current CRS.
        Coordinates are set only on left mouse click.

        :param pnt: A point.
        :type pnt: QgsPoint
        :param btn: A mouse button.
        :type btn: QtCore.MouseButton
        """

        row_data = self._get_row_data(self.loc_tbl, self.loc_tbl.currentRow())

        # set coordinates only on left mouse click
        # and when method of current row is 'coordinates'
        if btn == Qt.LeftButton and row_data[0] == self.loc_met_list[1]:
            in_crs = self.cnvs.mapSettings().destinationCrs()

            crs_desc = self._edit_crs_desc
            out_crs = self.crs_dict[crs_desc]

            in_x = pnt.x()
            in_y = pnt.y()

            out_x, out_y = self._trf_coord(in_crs, out_crs, in_x, in_y)

            self.loc_edit_x_coor_le.setText(str(out_x))
            self.loc_edit_y_coor_le.setText(str(out_y))

    @property
    def _edit_crs_desc(self):
        """
        Returns an edit CRS description.

        :returns: An edit CRS description.
        :rtype: str
        """

        crs_desc = self.loc_edit_crs_cb.currentText()

        return crs_desc

    @property
    def _manual_crs_desc(self):
        """
        Returns a manual CRS description.

        :returns: A manual CRS description.
        :rtype: str
        """

        crs_desc = self.loc_manual_coor_crs_cb.currentText()

        return crs_desc

    @property
    def _edit_opt(self):
        """
        Returns an edit option.

        :returns: An edit option.
        :rtype: str
        """

        opt = self.loc_edit_opt_cb.currentText()

        return opt

    @property
    def _manual_opt(self):
        """
        Returns a manual option.

        :returns: A manual option.
        :rtype: str
        """

        opt = self.loc_manual_coor_opt_cb.currentText()

        return opt

    def _trf_coord(self, in_crs, out_crs, in_x, in_y):
        """
        Transforms the given X and Y coordinates from the input CRS
        to the output CRS.

        :param in_crs: An input CRS.
        :type in_crs: QgsCoordinateReferenceSystem
        :param out_crs: An Output CRS.
        :type out_crs: QgsCoordinateReferenceSystem
        :param in_x: An input X coordinate.
        :type in_x: float
        :param in_y: An input Y coordinate.
        :type in_y: float

        :returns: X and Y coordinates in the output CRS.
        :rtype: tuple
        """

        trf = QgsCoordinateTransform(in_crs, out_crs)

        out_x, out_y = trf.transform(QgsPoint(in_x, in_y))

        return (out_x, out_y)

    def _add_manual_locid(self):
        """
        Adds location IDs from text to location table.
        """

        try:
            locid_input_set = self._get_locid_input_set()

            for locid in locid_input_set:
                self._set_loc_tbl_row(self._get_locid_list(*locid))
        except NoLocExc:
            QMessageBox.warning(
                self, u'No Location', u'Enter at least one location.')
        except LocidTxtExc:
            QMessageBox.warning(
                self,
                u'locationID',
                u'Enter valid UUID separated by commas.\n'
                u'For example:\n'
                u'0001b8f3-65fb-4877-8808-ca67094e1cbb, '
                u'0002bdc7-b232-4c5b-bd4d-3d4f21da24b6')

    def _get_locid_input_set(self):
        """
        Returns a location ID input set.

        :returns: A location ID input set.
        :rtype: ordered_set.OrderedSet
        """

        locid_txt = self.loc_manual_locid_pte.toPlainText()

        if len(locid_txt) == 0:
            raise NoLocExc()

        locid_txt = locid_txt.strip(',')

        locid_input_list = [locid.strip() for locid in locid_txt.split(',')]

        for i, locid in enumerate(locid_input_list):
            try:
                uuid.UUID(locid)
                locid_input_list[i] = [locid]
            except ValueError:
                raise LocidTxtExc()

        locid_input_set = ordered_set.OrderedSet(map(tuple, locid_input_list))

        return locid_input_set

    def _add_manual_coor(self):
        """
        Adds coordinates from text to location table.
        """

        try:
            crs_desc = self._manual_crs_desc
            opt = self._manual_opt
            coor_input_set = self._get_coor_input_set()

            for coor in coor_input_set:
                self._set_loc_tbl_row(
                    self._get_coor_list(crs_desc, opt, *coor))
        except NoLocExc:
            QMessageBox.warning(
                self, u'No Location', u'Enter at least one location.')
        except CoorTxtExc:
            QMessageBox.warning(
                self,
                u'Coordinates',
                u'Enter location in this format separated by commas '
                u'(verbatimLocality is optional):\n'
                u'"<X> <Y> <verbatimLocality>"\n'
                u'For example:\n'
                u'601404.85 6644928.24 Hovinbk, '
                u'580033.12 6633807.99 Drengsrudbk')

    def _get_coor_input_set(self):
        """
        Returns a coordinates input set.

        :returns: A coordinates input set.
        :rtype: ordered_set.OrderedSet
        """

        coor_txt = self.loc_manual_coor_pte.toPlainText()

        if len(coor_txt) == 0:
            raise NoLocExc()

        coor_txt = coor_txt.strip(',')

        coor_input_list = \
            [loc.strip().split(' ') for loc in coor_txt.split(',')]

        for m in range(len(coor_input_list)):
            for n in range(2):
                try:
                    coor_input_list[m][n] = float(coor_input_list[m][n])
                except ValueError:
                    raise CoorTxtExc()

        coor_input_set = ordered_set.OrderedSet(map(tuple, coor_input_list))

        return coor_input_set

    def _add_manual_nvl(self):
        """
        Adds `Norwegian VatnLnr` from text to location table.
        """

        try:
            nvl_input_set = self._get_nvl_input_set()

            for nvl in nvl_input_set:
                self._set_loc_tbl_row(self._get_nvl_list(*nvl))
        except NoLocExc:
            QMessageBox.warning(
                self, u'No Location', u'Enter at least one location.')
        except NvlTxtExc:
            QMessageBox.warning(
                self,
                u'Norwegian VatLnr',
                u'Enter integers separated by commas.\n'
                u'For example:\n'
                u'3067, 5616, 5627')

    def _get_nvl_input_set(self):
        """
        Returns a `Norwegian VatnLnr` input set.

        :returns: A `Norwegian VatnLnr` input set.
        :rtype: ordered_set.OrderedSet
        """

        nvl_txt = self.loc_manual_nvl_pte.toPlainText()

        if len(nvl_txt) == 0:
            raise NoLocExc()

        nvl_txt = nvl_txt.strip(',')

        nvl_input_list = [nvl.strip() for nvl in nvl_txt.split(',')]

        for i, nvl in enumerate(nvl_input_list):
            try:
                nvl_input_list[i] = [int(nvl)]
            except ValueError:
                raise NvlTxtExc()

        nvl_input_set = ordered_set.OrderedSet(map(tuple, nvl_input_list))

        return nvl_input_set

    def _preview_loc(self):
        """
        Previews all locations in the location table.
        It adds two layer to map canvas:

            - layer of existing locations
            - layer of new locations.
        """

        try:
            locid_list = []

            tbl = self.loc_tbl

            new_loc_feat_list = []

            for m in range(tbl.rowCount()):
                row_data = self._get_row_data(tbl, m)

                loc_met = row_data[0]

                # locationID
                if loc_met == self.loc_met_list[0]:
                    locid = self._get_locid_locid(m, row_data)
                # coordinates
                elif loc_met == self.loc_met_list[1]:
                    new_loc_feat, locid = self._get_new_loc_feat_locid_coor(
                        m, row_data)

                    if new_loc_feat:
                        new_loc_feat_list.append(new_loc_feat)
                # nvl
                elif loc_met == self.loc_met_list[2]:
                    locid = self._get_locid_nvl(m, row_data)

                if locid:
                    locid_list.append(locid)

            if len(locid_list) != 0:
                exg_loc_lyr = self._get_loc_lyr(
                    locid_list, u'preview_location-existing')

                if exg_loc_lyr.isValid():
                    QgsMapLayerRegistry.instance().addMapLayer(exg_loc_lyr)

            if len(new_loc_feat_list) != 0:
                new_loc_lyr = QgsVectorLayer(
                    u'Point?crs={}'.format(self._utm33_crs.authid()),
                    u'preview_location-new',
                    u'memory')

                dp = new_loc_lyr.dataProvider()
                dp.addFeatures(new_loc_feat_list)
                new_loc_lyr.updateExtents()

                if new_loc_lyr.isValid():
                    QgsMapLayerRegistry.instance().addMapLayer(new_loc_lyr)
        except LocidMtyExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 1)
            QMessageBox.warning(
                self,
                u'locationID',
                u'locationID of selected row is empty.')
        except LocidFmtExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 1)
            QMessageBox.warning(
                self,
                u'locationID',
                u'locationID "{}" is not UUID.'.format(e.locid))
        except LocidNfExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 1)
            QMessageBox.warning(
                self,
                u'locationID',
                u'locationID "{}" was not found.'.format(e.locid))
        except CoorMtyExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 5)
            QMessageBox.warning(
                self,
                u'coordinates',
                u'Both X and Y coordinates must be entered.')
        except NvlMtyExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 7)
            QMessageBox.warning(
                self,
                u'Norwegian VatLnr',
                u'Norwegian VatLnr of selected row is empty.')
        except NvlNfExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 7)
            QMessageBox.warning(
                self,
                u'Norwegian VatLnr',
                u'Norwegian VatLnr code "{}" was not found.'.format(e.nvl))

    def _get_new_loc_feat_locid_coor(self, m, row_data):
        """
        Returns a new location feature or a location ID.
        It is used for 'coordinates' method.
        Checks if both X and Y coordinates are entered.
        Based on option it returns a new location feature
        or returns location ID of the nearest location.

        :param m: A location table row.
        :type m: int
        :param row_data: Data in location table row.
        :type row_data: list

        :returns: A location ID of new location or the nearest location.
        :rtype: str
        """

        try:
            crs_desc, opt, x, y, verb_loc = self._extr_coor_list(row_data)
        except TypeError:
            raise CoorMtyExc(m)

        crs = self.crs_dict[crs_desc]
        srid = crs.authid().split(u':')[1]

        new_loc_feat = None
        locid = None

        # new
        if opt == self.opt_list[0]:
            out_crs = self._utm33_crs
            out_x, out_y = self._trf_coord(crs, out_crs, x, y)
            pnt_geom = QgsGeometry.fromPoint(QgsPoint(out_x, out_y))
            new_loc_feat = QgsFeature()
            new_loc_feat.setGeometry(pnt_geom)
        # nearest
        elif opt == self.opt_list[1]:
            locid = self._get_nrst_locid(x, y, srid)

        return (new_loc_feat, locid)

    @property
    def _utm33_crs(self):
        """
        Return UTM33 CRS.

        :returns: UTM33 CRS.
        :rtype: QgsCoordinateReferenceSystem
        """

        utm33_crs = self.crs_dict[u'UTM33']

        return utm33_crs

    def _fetch_schema(self):
        """
        Fetches a schema based on what tab is active.
        If the main tab is active it fetches data from `NOFA` schema,
        otherwise it fetches data from `plugin` schema.
        """

        idx = self.main_tabwdg.currentIndex()

        if idx == 0:
            self._fetch_nofa_schema()
        elif idx == 1:
            self._fetch_plugin_schema()

    def _fetch_plugin_schema(self):
        """
        Fetches data from the `plugin` schema and populates tables.
        """

        self._pop_usr_cb()

        self._fill_hist_tbls()

        self.hist_tabwdg.setCurrentIndex(0)

    def _pop_usr_cb(self):
        """
        Populates the user combo box.
        """

        usr_list = db.get_usr_list(self.mc.con)
        usr_list.insert(0, self.all_str)

        self.usr_cb.clear()
        self.usr_cb.addItems(usr_list)
        self.usr_cb.setCurrentIndex(
            usr_list.index(self.mc.con_info[self.mc.usr_str]))

    def _fill_hist_tbls(self):
        """
        Fills all history tables.
        """

        hist_fltrs = self._hist_fltrs

        for tbl, fnc in self.hist_tbls_fnc_dict.items():
            tbl_list, tbl_hdrs = fnc(self.mc.con, *hist_fltrs)
            self._create_tbl_hist_tab(tbl, tbl_list, tbl_hdrs)

    @property
    def _hist_fltrs(self):
        """
        Returns history filters.
        It is used to filter entries in history tab.

        :returns:
         | A tuple containing:
         |    - *str* -- user
         |    - *datetime.date* -- insert start date
         |    - *datetime.date* -- insert end date
         |    - *datetime.date* -- update start date
         |    - *datetime.date* -- update end date
        :rtype: tuple
        """

        usr_txt = self.usr_cb.currentText()
        usr = self._get_val_txt(usr_txt)

        ins_dt_strt = self.hist_ins_dtstrt_de.date().toPyDate()
        ins_dt_end = self.hist_ins_dtend_de.date().toPyDate()
        upd_dt_strt = self.hist_upd_dtstrt_de.date().toPyDate()
        upd_dt_end = self.hist_upd_dtend_de.date().toPyDate()

        return (usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end)

    def _open_dtst_dlg(self):
        """
        Opens a dialog for adding a new dataset.
        """

        self.dtst_dlg = dtst_dlg.DtstDlg(self.mc, self)
        self.dtst_dlg.show()

    def _open_prj_dlg(self):
        """
        Opens a dialog for adding a new project.
        """

        self.prj_dlg = prj_dlg.PrjDlg(self.mc, self)
        self.prj_dlg.show()

    def _open_ref_dlg(self):
        """
        Opens a dialog for adding a new reference.
        """

        self.ref_dlg = ref_dlg.RefDlg(self.mc, self)
        self.ref_dlg.show()

    def _upd_txncvg_tw_chldn(self, par):
        """
        Updates children in the taxonomic coverage tree widget
        based on the state of its parent.

        :param par: A changed item.
        :type par: QTableWidgetItem
        """

        chck_state = par.checkState(0)

        for i in range(par.childCount()):
            chld = par.child(i)
            chld.setCheckState(0, chck_state)

            self._upd_txncvg_tw_chldn(chld)

    def _rst(self):
        """
        Resets all widgets in the main tab.
        """

        self._rst_loc_tbl()
        self._rst_loc_wdgs()
        self._rst_event_wdgs()
        self._rst_mtdt_wdgs()
        self._rst_occ_tbl()
        self._rst_txncvg_tw()

    def _rst_loc_tbl(self):
        """
        Resets location table.
        """

        self.loc_del_btn.click()
        self.loc_rstrow_btn.click()

    def _rst_loc_wdgs(self):
        """
        Resets location widgets.
        """

        self._rst_cb_by_cb_dict(self._loc_cb_dict)
        self._rst_cb_by_cb_dict(self._loc_edit_met_cb_dict)
        self._rst_cb_by_cb_dict(self._loc_manual_met_cb_dict)

        self.wb_le.clear()
        self.lake_name_statlbl.setText(u'Search for locations.')

    def _rst_event_wdgs(self):
        """
        Resets all event widgets.
        """

        self._rst_wdgs(self.event_input_wdgs)

        self._rst_cb_by_cb_dict(self._event_cb_dict)

    def _rst_mtdt_wdgs(self):
        """
        Resets all metadata widgets.
        """

        sel_str = self.sel_str

        self.upd_dtst(sel_str)
        self.upd_prj(sel_str)
        self.upd_ref(sel_str)

    def _rst_occ_tbl(self):
        """
        Resets occurrence table.
        Also resets occurrence widgets because it is connected to the table.
        """

        self.occ_del_btn.click()
        self.occ_rstrow_btn.click()

    def _rst_txncvg_tw(self):
        """
        Resets taxonomic coverage tree widget.
        """

        txncvg_root_item = self.txncvg_tw.invisibleRootItem().child(0)

        if txncvg_root_item.checkState(0) == Qt.Unchecked:
            txncvg_root_item.setCheckState(0, Qt.Checked)

        txncvg_root_item.setCheckState(0, Qt.Unchecked)

        self.txncvg_tw.expandToDepth(0)

    def _ins(self):
        """
        Inserts the data into the database.
        """

        try:
            self.chck_mand_wdgs(self.mtdt_mand_wdgs, MtdtNotFldExc)
            self._chck_occ_tbl()

            locid_list = self._get_loc_list()

            event_list = self.get_wdg_list(self.event_input_wdgs)

            dtst_id = self._get_dtst_id()
            prj_id = self._get_prj_id()
            ref_id = self._get_ref_id()

            for loc_id in locid_list:
                event_id = uuid.uuid4()

                db.ins_event(
                    self.mc.con,
                    loc_id, event_id, event_list, dtst_id, prj_id, ref_id)

                db.ins_event_log(
                    self.mc.con,
                    loc_id, event_id, dtst_id, prj_id, ref_id,
                    self.mc.con_info[self.mc.usr_str])

                self._ins_txncvg(event_id)

                for m in range(self.occ_tbl.rowCount()):
                    occ_id = uuid.uuid4()

                    occ_row_list = self._get_occ_row_list(m)

                    txn_id = db.get_txn_id(self.mc.con, occ_row_list[0])

                    ectp = occ_row_list[1]
                    ectp_id = db.get_ectp_id(self.mc.con, ectp)

                    db.ins_occ(
                        self.mc.con,
                        occ_id, txn_id, ectp_id, occ_row_list, event_id)

                    db.ins_occ_log(
                        self.mc.con,
                        occ_id, event_id, dtst_id, prj_id, ref_id, loc_id,
                        self.mc.con_info[self.mc.usr_str])

            QMessageBox.information(self, u'Saved', u'Data correctly saved.')
        except MtdtNotFldExc as e:
            self.main_tb.setCurrentWidget(e.wdg.parent())
            e.wdg.setFocus()
            QMessageBox.warning(
                self,
                u'Mandatory Metadata Fields',
                u'Fill/select all mandatory metadata fields.')
        except OccNotFldExc:
            QMessageBox.warning(
                self, u'Taxon', u'Select taxon.')
        except LocidMtyExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 1)
            QMessageBox.warning(
                self,
                u'locationID',
                u'locationID of selected row is empty.')
        except LocidFmtExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 1)
            QMessageBox.warning(
                self,
                u'locationID',
                u'locationID "{}" is not UUID.'.format(e.locid))
        except LocidNfExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 1)
            QMessageBox.warning(
                self,
                u'locationID',
                u'locationID "{}" was not found.'.format(e.locid))
        except CoorMtyExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 5)
            QMessageBox.warning(
                self,
                u'coordinates',
                u'Both X and Y coordinates must be entered.')
        except NvlMtyExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 7)
            QMessageBox.warning(
                self,
                u'Norwegian VatLnr',
                u'Norwegian VatLnr of selected row is empty.')
        except NvlNfExc as e:
            self.main_tb.setCurrentWidget(self.loc_wdg)
            self.loc_tbl.setCurrentCell(e.m, 7)
            QMessageBox.warning(
                self,
                u'Norwegian VatLnr',
                u'Norwegian VatLnr code "{}" was not found.'.format(e.nvl))

    def _chck_occ_tbl(self):
        """
        Checks if all rows in the occurrence are filled.
        """

        for m in range(self.occ_tbl.rowCount()):
            occ_row_list = self._get_occ_row_list(m)

            if occ_row_list[0] is None:
                self.occ_tbl.selectRow(m)
                raise OccNotFldExc()

    def _get_loc_list(self):
        """
        Returns a location ID list.

        :returns: A location ID list.
        :rtype: list
        """

        locid_list = []

        tbl = self.loc_tbl

        for m in range(tbl.rowCount()):
            row_data = self._get_row_data(tbl, m)

            loc_met = row_data[0]

            # locationID
            if loc_met == self.loc_met_list[0]:
                locid = self._get_locid_locid(m, row_data)
            # coordinates
            elif loc_met == self.loc_met_list[1]:
                locid = self._get_locid_coor(m, row_data)
            # nvl
            elif loc_met == self.loc_met_list[2]:
                locid = self._get_locid_nvl(m, row_data)

            locid_list.append(locid)

        return locid_list

    def _get_locid_locid(self, m, row_data):
        """
        Returns a location ID. It is used for 'locationID' method.
        Checks if location ID is empty, if it a valid *UUID*
        and if it exists in the database.

        :param m: A location table row.
        :type m: int
        :param row_data: Data in location table row.
        :type row_data: list

        :returns: A location ID.
        :rtype: str
        """

        locid = self._extr_locid_list(row_data)

        if not locid:
            raise LocidMtyExc(m)

        try:
            uuid.UUID(locid)
        except ValueError:
            raise LocidFmtExc(m, locid)

        if not db.chck_locid(self.mc.con, locid):
            raise LocidNfExc(m, locid)

        return locid

    def _get_locid_coor(self, m, row_data):
        """
        Returns a location ID. It is used for 'coordinates' method.
        Checks if both X and Y coordinates are entered.
        Based on option it inserts new location or returns location ID
        of the nearest location.

        :param m: A location table row.
        :type m: int
        :param row_data: Data in location table row.
        :type row_data: list

        :returns: A location ID of new location or the nearest location.
        :rtype: str
        """

        try:
            crs_desc, opt, x, y, verb_loc = self._extr_coor_list(row_data)
        except TypeError:
            raise CoorMtyExc(m)

        srid = self.crs_dict[crs_desc].authid().split(u':')[1]

        # new
        if opt == self.opt_list[0]:
            locid = uuid.uuid4()

            mpt_str = db.get_mpt_str(x, y)
            utm33_geom = db.get_utm33_geom(self.mc.con, mpt_str, srid)
            db.ins_new_loc(self.mc.con, locid, utm33_geom, verb_loc)
            db.ins_loc_log(
                self.mc.con,
                locid,
                verb_loc,
                self.mc.con_info[self.mc.usr_str])
        # nearest
        elif opt == self.opt_list[1]:
            locid = self._get_nrst_locid(x, y, srid)

        return locid

    def _get_nrst_locid(self, x, y, srid):
        """
        Returns a location ID of the nearest location.

        :param x: X coordinate.
        :type x: float
        :param y: Y coordinate.
        :type y: float
        :param srid: SRID.
        :type srid: int

        :returns: A location ID of the nearest location.
        :rtype: str
        """

        pt_str = db.get_pt_str(x, y)
        utm33_geom = db.get_utm33_geom(self.mc.con, pt_str, srid)
        locid = db.get_nrst_locid(self.mc.con, utm33_geom)

        locid = str(locid)

        return locid

    def _get_locid_nvl(self, m, row_data):
        """
        Returns a location ID. It is used for 'Norwegian VatLnr' method.
        Checks if Norwegian VatLnr is empty.
        It searches for location ID with the given Norwegian VatLnr.

        :param m: A location table row.
        :type m: int
        :param row_data: Data in location table row.
        :type row_data: list

        :returns: A location ID with the given Norwegian VatLnr.
        :rtype: str
        """

        try:
            nvl = self._extr_nvl_list(row_data)
        except TypeError:
            raise NvlMtyExc(m)

        try:
            locid = db.get_locid_from_nvl(self.mc.con, nvl)
        except TypeError:
            raise NvlNfExc(m, nvl)

        return locid

    def get_wdg_list(self, wdgs, pydate=True, forbi=False):
        """
        Returns the data from the given list of widgets.

        :param wdgs: A list of widgets whose data should be returned.
        :type wdgs: list
        :param pydate: True to convert *QDate* to *datetime.date*,
            False otherwise.
        :type pydate: bool
        :param forbi: True to allow forbidden text, False otherwise.
        :type forbi: bool

        :returns: A list of data from event input widgets.
        :rtype: list
        """

        wdg_list = []

        for wdg in wdgs:
            if isinstance(wdg, QLineEdit):
                txt = wdg.text()

                wdg_vald = wdg.validator()

                if not vald:
                    wdg_data = self._get_val_txt(txt, forbi)
                elif isinstance(wdg_vald, (QIntValidator, vald.LenIntVald)):
                    try:
                        wdg_data = int(txt)
                    except ValueError:
                        wdg_data = None
                elif isinstance(wdg_vald, QDoubleValidator):
                    try:
                        wdg_data = float(txt)
                    except ValueError:
                        wdg_data = None
                else:
                    wdg_data = self._get_val_txt(txt, forbi)
            elif isinstance(wdg, QComboBox):
                txt = wdg.currentText()
                wdg_data = self._get_val_txt(txt, forbi)
            elif isinstance(wdg, QDateEdit):
                if wdg.findChild(QLineEdit).text() == self.mty_str:
                    wdg_data = None
                else:
                    wdg_data = wdg.date()
                    if pydate:
                        wdg_data = wdg_data.toPyDate()
            elif isinstance(wdg, QPlainTextEdit):
                txt = wdg.toPlainText()
                wdg_data = self._get_val_txt(txt, forbi)

            wdg_list.append(wdg_data)

        return wdg_list

    def _rst_wdgs(self, wdgs):
        """
        Resets the given widgets.

            - *QLineEdit* -- clear
            - *QPlainTextEdit* -- clear
            - *QComboBox* -- set current index to 0
            - *QDateEdit* -- set date to minimum

        :param wdgs: Widgets to be cleared.
        :type wdgs: list
        """

        for wdg in wdgs:
            if isinstance(wdg, QLineEdit):
                wdg.clear()
            elif isinstance(wdg, QPlainTextEdit):
                wdg.clear()
            elif isinstance(wdg, QComboBox):
                wdg.setCurrentIndex(0)
            elif isinstance(wdg, QDateEdit):
                wdg.setDate(wdg.minimumDate())

    def _get_occ_row_list(self, m, forbi=False):
        """
        Returns an occurrence row list.

        :param m: A row number.
        :type m: int
        :param forbi: True to allow forbidden text, False otherwise.
        :type forbi: bool

        :returns: A list of data in the given row in the occurrence table.
        :rtype: list
        """

        occ_row_list = []

        # OS.NINA
        # depends on the order in the table
        for n in range(self.occ_tbl.columnCount()):
            wdg_data = self.occ_tbl.item(m, n).data(Qt.EditRole)

            if isinstance(wdg_data, (str, unicode)):
                wdg_data = self._get_val_txt(wdg_data, forbi)

            if isinstance(wdg_data, QDate):
                wdg_data = wdg_data.toPyDate()

            occ_row_list.append(wdg_data)

        return occ_row_list

    def _ins_txncvg(self, event_id):
        """
        Inserts all checked taxons into the database.

        :param event_id: An event ID.
        :type event_id: uuid.UUID
        """

        for txn in self._ckd_txns:
            txn_id = db.get_txn_id(self.mc.con, txn)

            db.ins_txncvg(self.mc.con, txn_id, event_id)

    @property
    def _ckd_txns(self):
        """
        Returns all checked taxons from the taxon coverage tree widget.

        :returns: A list of all checked taxons.
        :rtype: list
        """

        txn_list = []

        all_item = self.txncvg_tw.invisibleRootItem().child(0)

        for i in range(all_item.childCount()):
            fam_item = all_item.child(i)

            for j in range(fam_item.childCount()):
                txn_item = fam_item.child(j)

                if txn_item.checkState(0) == Qt.Checked:
                    txn_list.append(txn_item.text(0))

        return txn_list

    def upd_dtst(self, dtst_str=None):
        """
        Updates a dataset according to the last selected.

        :param dtst_str: A dataset string `<ID> - <name>`.
        :type dtst_str: str
        """

        self._upd_mtdt(self.dtst_cb, dtst_str)

    def upd_prj(self, prj_str=None):
        """
        Updates a project according to the last selected.

        :param prj_str: A project string `<name> - <organisation>`.
        :type prj_str: str
        """

        self._upd_mtdt(self.prj_cb, prj_str)

    def upd_ref(self, ref_str=None):
        """
        Updates a reference according to the last selected.

        :param ref_str: A reference string `<author>: <title> (<year>) @<ID>`.
        :type ref_str: str
        """

        self._upd_mtdt(self.ref_cb, ref_str)

    def _upd_mtdt(self, cb, cb_str=None):
        """
        Updates a metadata according to the last selected.
        """

        if not cb_str:
            cb_str = self.settings.value(cb.objectName())

        if cb_str:
            cb_idx = cb.findText(cb_str)
            cb.setCurrentIndex(cb_idx)
        else:
            cb_str = cb.currentText()

        self._upd_mtdt_lw(cb_str, cb)

    def _upd_mtdt_lw(self, cb_str, cb=None):
        """
        Updates a metadata list widget.

        :param cb_str: A combob box string.
        :type cb_str: str
        :param cb: A combo box.
        :type cb: QComboBox
        """

        if isinstance(cb_str, int):
            cb = self.sender()
            cb_str = cb.currentText()

        idx = self.main_tb.indexOf(cb.parentWidget())
        mdtd_base_txt = self.main_tb.itemText(idx).split(
            self.dash_split_str)[0]

        lw, id_met, info_fnc, mtdt_str_fnc = self._mtdt_lw_cb_dict[cb]

        lw.clear()

        if cb_str in self.forbi_str_list:
            mtdt_txt = cb_str
        else:
            items, hdrs = info_fnc(self.mc.con, id_met())

            self._pop_lw(lw, items, hdrs)

            mtdt_txt = mtdt_str_fnc(cb_str)

        self._set_mtdt_item_txt(
            idx, u'{}{}{}'
            .format(mdtd_base_txt, self.dash_split_str, mtdt_txt))

        self.settings.setValue(cb.objectName(), cb_str)

    def _set_mtdt_item_txt(self, item_index, text):
        """
        Sets metadata item text.

        :param item_index: An item index.
        :type item_index: int
        :param text: A text.
        :type text: str
        """

        self.main_tb.setItemText(item_index, text)

    @property
    def _mtdt_lw_cb_dict(self):
        """
        Returns a metadata list widget combo box dictionary.

        :returns:
         | A metadata combo box dictionary:
         |    - key - <combo box name>
         |    - value - [
         |        <list widget>,
         |        <method that returns ID>,
         |        <function that returns information>,
         |        <function that returns metadata string>]
        :rtype: dict.
        """

        mtdt_cb_dict = {
            self.dtst_cb: [
                self.dtst_lw,
                self._get_dtst_id,
                db.get_dtst_info,
                db.get_dtst_mtdt_str],
            self.prj_cb: [
                self.prj_lw,
                self._get_prj_id,
                db.get_prj_info,
                db.get_prj_mtdt_str],
            self.ref_cb: [
                self.ref_lw,
                self._get_ref_id,
                db.get_ref_info,
                db.get_ref_mtdt_str]}

        return mtdt_cb_dict

    def _pop_lw(self, lw, items, hdrs):
        """
        Populates the given list widget.
        Adds all items with their corresponding headers `<header>: <item>`.

        :param lw: A list widget.
        :type lw: QListWidget
        :param items: Items to be added.
        :type items: list
        :param hdrs: Headers to be added.
        :type hdrs: list
        """

        for hdr, item in zip(hdrs, items):
            lw_item = QListWidgetItem(
                u'{}: {}'.format(hdr, unicode(item) if item else u''))
            lw.addItem(lw_item)

    def prep(self):
        """
        Prepares the whole plugin to be shown.
        """

        self._fetch_nofa_schema()

        self._rst_loc_tbl()
        self._rst_loc_wdgs()
        self._rst_event_wdgs()
        self._rst_occ_tbl()
        self._rst_txncvg_tw()

    def _fetch_nofa_schema(self):
        """
        Fetches data from the `NOFA` schema and populates widgets.
        """

        nofa_cb_dict = self._nofa_cb_dict

        self.pop_cb(nofa_cb_dict)

        self.upd_dtst()
        self.upd_prj()
        self.upd_ref()

        self._pop_txncvg_tw()

    def pop_cb(self, cb_dict):
        """
        Populates combo boxes.

        :param cb_dict:
         | A combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :type cb_dict: dict.
        :param cb: Who knows.
        :type cb: bool
        """

        for cb, cb_list in cb_dict.items():
            fnc = cb_list[0]
            args = cb_list[1]
            def_val = cb_list[2]

            item_list = fnc(*args)

            if def_val not in item_list:
                item_list.insert(0, def_val)

            self._add_cb_items(cb, item_list)

            cb.setCurrentIndex(item_list.index(def_val))

    def _pop_cnty_cb(self):
        """
        Populates the county combo box according to the currently selected
        country.
        """

        self.pop_cb(self._cnty_cb_dict)

    def _pop_muni_cb(self):
        """
        Populates the municipality combo box according to the currently
        selected country and county.
        """

        self.pop_cb(self._muni_cb_dict)

    def _pop_ectp_cb(self):
        """
        Populates the ecotype combo box according to the currently selected
        taxon.
        """

        self.pop_cb(self._ectp_cb_dict)

    def pop_dtst_cb(self):
        """
        Populates the dataset combo box.
        """

        self.pop_cb(self._dtst_cb_dict)

    def pop_prj_cb(self):
        """
        Populates the project combo box.
        """

        self.pop_cb(self._prj_cb_dict)

    def pop_ref_cb(self):
        """
        Populates the reference combo box.
        """

        self.pop_cb(self._ref_cb_dict)

    def _add_cb_items(self, cb, item_list):
        """
        Adds items from the item list to the combo box.

        :param cb: A combob box.
        :type cb: QComboBox
        :param item_list: An item list.
        :type item_list: list
        """

        cb.clear()

        for i, item in enumerate(item_list):
            cb.addItem(item)

            # if item in self.forbi_str_list:
            #     clr = self.red_clr
            #     cb.setItemData(i, QBrush(clr), Qt.BackgroundRole)

    def _rst_cb_by_cb_dict(self, cb_dict):
        """
        Resets combo boxes by the given combo box dictionary.

        :param cb_dict:
         | A combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :type cb_dict: dict
        """

        for cb, cb_list in cb_dict.items():
            def_val = cb_list[2]
            cb.setCurrentIndex(cb.findText(def_val))

            # ensure that signal is emitted
            cb.currentIndexChanged.emit(cb.currentIndex())

    @property
    def _nofa_cb_dict(self):
        """
        Returns a `NOFA` combo box dictionary.

        :returns:
         | A `NOFA` combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        nofa_cb_dict = {
            self.oqt_cb: [
                db.get_oqt_list,
                [self.mc.con],
                self.mty_str],
            self.poptrend_cb: [
                db.get_poptrend_list,
                [self.mc.con],
                self.mty_str],
            self.spwnc_cb: [
                db.get_spwnc_list,
                [self.mc.con],
                self.mty_str],
            self.spwnl_cb: [
                db.get_spwnl_list,
                [self.mc.con],
                self.mty_str]}

        nofa_cb_dict = self._get_mrgd_dict(
            nofa_cb_dict,
            self._loc_cb_dict,
            self._loc_edit_met_cb_dict,
            self._loc_manual_met_cb_dict,
            self._event_cb_dict,
            self._ectp_cb_dict,
            self._mtdt_cb_dict,
            self._occ_mand_cb_dict)

        return nofa_cb_dict

    def _get_mrgd_dict(self, *dicts):
        """
        Returns a merged dictionary of all given dictionaries.
        """

        mrgd_dict = {}

        for dict in dicts:
            for key, val in dict.items():
                mrgd_dict[key] = val

        return mrgd_dict

    @property
    def _loc_cb_dict(self):
        """
        Returns a combo box dictionary for all location combo boxes.

        :returns:
         | A combo box dictionary for all location combo boxes:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        loc_cb_dict = {
            self.cntry_code_cb: [
                db.get_cntry_code_list,
                [self.mc.con],
                self.all_str],
            self.loc_edit_crs_cb: [
                self._get_srs_desc_list,
                [],
                self.crs_dict.items()[0][0]],
            self.loc_edit_opt_cb: [
                self._get_opt_list,
                [],
                self.opt_list[0]],
            self.loc_manual_coor_crs_cb: [
                self._get_srs_desc_list,
                [],
                self.crs_dict.items()[0][0]],
            self.loc_manual_coor_opt_cb: [
                self._get_opt_list,
                [],
                self.opt_list[0]]}

        loc_cb_dict = self._get_mrgd_dict(
            loc_cb_dict,
            self._cnty_cb_dict,
            self._muni_cb_dict)

        return loc_cb_dict

    @property
    def _cnty_cb_dict(self):
        """
        Returns a county combo box dictionary.

        :returns:
         | A county combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        cnty_cb_dict = {
            self.cnty_cb: [
                db.get_cnty_list,
                [self.mc.con, self._cntry_code],
                self.all_str]}

        return cnty_cb_dict

    @property
    def _muni_cb_dict(self):
        """
        Returns a municipality combo box dictionary.

        :returns:
         | A municipality combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        muni_cb_dict = {
            self.muni_cb: [
                db.get_muni_list,
                [self.mc.con, self._cntry_code, self._cnty],
                self.all_str]}

        return muni_cb_dict

    @property
    def _event_cb_dict(self):
        """
        Returns a combo box dictionary for all event combo boxes.

        :returns:
         | A combo box dictionary for all event combo boxes:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        event_cb_dict = {
            self.smpp_cb: [
                db.get_smpp_list,
                [self.mc.con],
                self.sel_str],
            self.smpsu_cb: [
                db.get_smpsu_list,
                [self.mc.con],
                self.mty_str],
            self.relia_cb: [
                db.get_reliab_list,
                [self.mc.con],
                self.mty_str]}

        return event_cb_dict

    @property
    def _ectp_cb_dict(self):
        """
        Returns an ecotype combo box dictionary.

        :returns:
         | An ecotype combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        ectp_cb_dict = {
            self.ectp_cb: [
                db.get_ectp_list,
                [self.mc.con, self._txn],
                self.mty_str]}

        return ectp_cb_dict

    @property
    def _mtdt_cb_dict(self):
        """
        Returns a metadata combo box dictionary.

        :returns: A metadata combo box dictionary.
         | A metadata combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        mtdt_cb_dict = self._get_mrgd_dict(
            self._dtst_cb_dict,
            self._prj_cb_dict,
            self._ref_cb_dict)

        return mtdt_cb_dict

    @property
    def _dtst_cb_dict(self):
        """
        Returns a dataset combo box dictionary.

        :returns:
         | A dataset combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        dtst_cb_dict = {
            self.dtst_cb: [
                db.get_dtst_list,
                [self.mc.con],
                self.sel_str]}

        return dtst_cb_dict

    @property
    def _prj_cb_dict(self):
        """
        Returns a project combo box dictionary.

        :returns:
         | A project combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        prj_cb_dict = {
            self.prj_cb: [
                db.get_prj_list,
                [self.mc.con],
                self.sel_str]}

        return prj_cb_dict

    @property
    def _ref_cb_dict(self):
        """
        Returns a reference combo box dictionary.

        :returns:
         | A reference combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        ref_cb_dict = {
            self.ref_cb: [
                db.get_ref_list,
                [self.mc.con],
                self.sel_str]}

        return ref_cb_dict

    @property
    def _loc_edit_met_cb_dict(self):
        """
        Returns a location edit method combo box dictionary.

        :returns:
         | A location edit method combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        loc_edit_met_cb_dict = {
            self.loc_edit_met_cb: [
                self._get_loc_met_list,
                [],
                self.loc_met_list[2]]}

        return loc_edit_met_cb_dict

    @property
    def _loc_manual_met_cb_dict(self):
        """
        Returns a location manual method combo box dictionary.

        :returns:
         | A location manual method combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        loc_manual_met_cb_dict = {
            self.loc_manual_met_cb: [
                self._get_loc_met_list,
                [],
                self.loc_met_list[2]]}

        return loc_manual_met_cb_dict

    @property
    def _occ_mand_cb_dict(self):
        """
        Returns an occurrence mandatory combo box dictionary.

        :returns:
         | An occurrence mandatory combo box dictionary:
         |    - key - <combo box name>
         |    - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict
        """

        occ_mand_cb_dict = {
            self.txn_cb: [
                db.get_txn_list,
                [self.mc.con],
                self.sel_str],
            self.occstat_cb: [
                db.get_occstat_list,
                [self.mc.con],
                db.get_col_def_val(
                    self.mc.con,
                    'nofa',
                    'occurrence',
                    'occurrenceStatus').split("'")[1]],
            self.estm_cb: [
                db.get_estbms_list,
                [self.mc.con],
                db.get_col_def_val(
                    self.mc.con,
                    'nofa',
                    'occurrence',
                    'establishmentMeans').split("'")[1]]}

        return occ_mand_cb_dict

    def _pop_txncvg_tw(self):
        """
        Populates the taxon coverage tree widget.
        """

        self.txncvg_tw.clear()

        fam_dict = db.get_fam_dict(self.mc.con)

        root_item = QTreeWidgetItem(self.txncvg_tw, ["All"])
        root_item.setCheckState(0, Qt.Unchecked)
        root_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

        for fam in fam_dict.keys():
            family_item = QTreeWidgetItem(root_item, [fam])
            family_item.setCheckState(0, Qt.Unchecked)
            family_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

            for txn in fam_dict[fam]:
                txn_item = QTreeWidgetItem(family_item, [txn])
                txn_item.setCheckState(0, Qt.Unchecked)
                txn_item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

        self.txncvg_tw.sortByColumn(0, Qt.AscendingOrder)
        self.txncvg_tw.expandToDepth(0)

    def _get_dtst_id(self):
        """
        Returns a dataset ID from the dataset combo box.

        :returns: A dataset ID.
        :rtype: str
        """

        dtst_str = self.dtst_cb.currentText()

        id, name = db.split_dtst_str(dtst_str)

        return id

    def _get_prj_id(self):
        """
        Returns a project ID based on name and organization.

        :returns: A project ID.
        :rtype: str
        """

        prj_str = self.prj_cb.currentText()

        prj_name, prj_org = db.split_prj_str(prj_str)

        prj_id = db.get_prj_id(self.mc.con, prj_name, prj_org)

        return prj_id

    def _get_ref_id(self):
        """
        Returns a reference ID from the reference combo box.

        :returns: A reference ID.
        :rtype: str
        """

        ref_str = self.ref_cb.currentText()

        if self._get_val_txt(ref_str):
            au, ttl, yr, id = db.split_ref_str(ref_str)
        else:
            id = None

        return id

    def _get_srs_desc_list(self):
        """
        Returns a list of SRS descriptions.

        :returns: A list of SRS descriptions.
        :rtype: list
        """

        srs_desc_list = self.crs_dict.keys()

        return srs_desc_list

    def _get_loc_met_list(self):
        """
        Returns a list of methods.

        :returns: A list of methods.
        :rtype: list
        """

        met_list = self.loc_met_list

        return met_list

    def _get_opt_list(self):
        """
        Returns a list of options.

        :returns: A list of options.
        :rtype: list
        """

        opt_list = self.opt_list

        return opt_list

    def _create_tbl_main_tab(self, tbl, tbl_hdrs, tbl_wdgs, met):
        """
        Creates a table with one row.
        This method is used for creating tables in the main tab.

        :param tbl: A table.
        :type tbl: QTableWidget
        :param tbl_hdrs: Table headers.
        :type tbl_hdrs: list
        :param tbl_wdgs: Table widgets.
        :type tbl_wdgs: list
        :param met: A method for updating table.
        :type met: function
        """

        tbl.itemChanged.connect(tbl.resizeColumnsToContents)

        tbl.setColumnCount(len(tbl_hdrs))
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setSelectionMode(QTableWidget.SingleSelection)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSortingEnabled(True)
        tbl.setHorizontalHeaderLabels(tbl_hdrs)
        tbl.setRowCount(1)

        m = 0

        tbl.selectRow(m)

        for n, tbl_hdr in enumerate(tbl_hdrs):
            tbl_item = QTableWidgetItem()
            tbl_item.setData(Qt.EditRole, None)
            tbl.setItem(m, n, tbl_item)

        self._con_wdgs_sgnls_to_met(tbl_wdgs, met)

    def _con_wdgs_sgnls_to_met(self, wdgs, met):
        """
        Connects signals of the given widgets to the given method.

            - *QLineEdit* - textChanged
            - *QComboBox* - currentIndexChanged
            - *QDateEdit* - dateChanged

        :param wdgs: Widgets.
        :type wdgs: list
        :param met: A method.
        :type met: function
        """

        for wdg in wdgs:
            if isinstance(wdg, QLineEdit):
                wdg.textChanged.connect(met)
            elif isinstance(wdg, QComboBox):
                wdg.currentIndexChanged.connect(met)
            elif isinstance(wdg, QDateEdit):
                wdg.dateChanged.connect(met)

    def _emit_wdgs_sgnls(self, tbl_wdgs):
        """
        Emits signals of the given widgets.

            - *QLineEdit* - textChanged
            - *QComboBox* - currentIndexChanged
            - *QDateEdit* - dateChanged

        :param tbl_wdgs: Widgets.
        :type tbl_wdgs: list
        """

        for wdg in tbl_wdgs:
            if isinstance(wdg, QLineEdit):
                wdg.textChanged.emit(wdg.text())
            elif isinstance(wdg, QComboBox):
                wdg.currentIndexChanged.emit(wdg.currentIndex())
            elif isinstance(wdg, QDateEdit):
                wdg.dateChanged.emit(wdg.date())

    def _upd_loc_tbl_row(self, idx):
        """
        Adjusts the current location table row according to the current
        location method.
        Also sets index of location method stacked widget.

        :param idx: A current index of location edit method combo box.
        :type idx: int
        """

        self.loc_edit_met_swdg.setCurrentIndex(idx)

        tbl = self.loc_tbl
        m = tbl.currentRow()

        # skip first column
        for n in range(1, tbl.columnCount()):
            tbl.item(m, n).setData(Qt.EditRole, None)

        cur_loc_edit_tbl_wdgs = self._cur_loc_edit_tbl_wdgs

        self._rst_wdgs(cur_loc_edit_tbl_wdgs)
        self._emit_wdgs_sgnls(cur_loc_edit_tbl_wdgs)

    def _create_tbl_hist_tab(self, tbl, tbl_list, tbl_hdrs):
        """
        Creates a table with one row.
        This method is used for creating tables in the history tab.

        :param tbl: A table.
        :type tbl: QTableWidget
        :param tbl_list: Table list.
        :type tbl_list: list
        :param tbl_hdrs: Table headers.
        :type tbl_hdrs: list
        """

        tbl.setColumnCount(len(tbl_hdrs))
        tbl.setSelectionBehavior(QTableWidget.SelectItems)
        tbl.setSelectionMode(QTableWidget.ExtendedSelection)
        tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)
        tbl.setSortingEnabled(True)
        tbl.setHorizontalHeaderLabels(tbl_hdrs)
        tbl.setRowCount(len(tbl_list))

        for m, row in enumerate(tbl_list):
            for n, item in enumerate(row):
                if isinstance(item, datetime.datetime):
                    item = QDateTime(item)
                elif isinstance(item, uuid.UUID):
                    item = str(item)

                tbl_item = QTableWidgetItem()
                tbl_item.setData(Qt.EditRole, item)
                tbl.setItem(m, n, tbl_item)

        tbl.resizeColumnsToContents()

    def _add_tbl_mty_row_items(self, tbl, tbl_hdrs, m):
        """
        Adds a row at the given position of a table with empty items.

        :param tbl: A table.
        :type tbl: QTableWidget
        :param tbl_hdrs: Table headers.
        :type tbl_hdrs: list
        :param m: A row number.
        :type m: int
        """

        for n, tbl_hdr in enumerate(tbl_hdrs):
            tbl_item = QTableWidgetItem()
            tbl_item.setData(Qt.EditRole, None)
            tbl.setItem(m, n, tbl_item)

    def _upd_loc_tbl_item(self):
        """
        Updates the corresponding item in the location table's current row
        with the values in the sender widget.
        """

        self._upd_tbl_item(self.loc_tbl, self.loc_tbl_wdg_hdr_dict.keys())

    def _upd_occ_tbl_item(self):
        """
        Updates the corresponding item in the occurrence table's current row
        with the values in the sender widget.
        """

        self._upd_tbl_item(self.occ_tbl, self.occ_tbl_wdg_hdr_dict.keys())

    def _upd_tbl_item(self, tbl, tbl_wdgs):
        """
        Updates the corresponding item in the table's current row
        with the values in the sender widget.

        :param tbl: A table.
        :type tbl: QTableWidget
        :param tbl_wdgs: A list of table widgets.
        :type tbl_wdgs: list
        """

        sndr = self.sender()

        wdg_data = self.get_wdg_list([sndr], False, True)[0]
        m = tbl.currentRow()
        n = tbl_wdgs.index(sndr)

        tbl_item = tbl.item(m, n)

        tbl_item.setData(Qt.EditRole, wdg_data)

        tbl.blockSignals(True)
        tbl.selectRow(tbl_item.row())
        tbl.blockSignals(False)

        tbl.resizeColumnsToContents()

    def _sel_row_up(self):
        """
        Select one row up in a table.
        """

        tbl = self._get_tbl()
        m = tbl.currentRow()

        if m > 0:
            tbl.selectRow(m - 1)

    def _sel_row_dwn(self):
        """
        Select one row down in a table.
        """

        tbl = self._get_tbl()
        m = tbl.currentRow()

        if m < (tbl.rowCount() - 1):
            tbl.selectRow(m + 1)

    def _upd_loc_tbl_wdgs(self):
        """
        Updates the location table widgets according to the selected location
        table row.
        """

        tbl = self.loc_tbl
        m = tbl.currentRow()

        loc_met = tbl.item(m, 0).data(Qt.EditRole)

        self.loc_edit_met_cb.blockSignals(True)

        idx = self.loc_edit_met_cb.findText(loc_met)
        self.loc_edit_met_cb.setCurrentIndex(idx)
        self.loc_edit_met_swdg.setCurrentIndex(idx)

        self.loc_edit_met_cb.blockSignals(False)

        for wdg in self._cur_loc_edit_tbl_wdgs:
            n = self.loc_tbl_wdg_hdr_dict.keys().index(wdg)
            wdg_data = tbl.item(m, n).data(Qt.EditRole)

            self._set_wdg_data(wdg, wdg_data)

    def _upd_occ_tbl_wdgs(self):
        """
        Updates the occurrence table widgets according to the selected
        occurrence table row.
        """

        tbl = self.occ_tbl
        m = tbl.currentRow()

        occ_row_list = self._get_occ_row_list(m, True)

        for n, wdg in enumerate(self.occ_tbl_wdg_hdr_dict.keys()):
            wdg_data = occ_row_list[n]
            self._set_wdg_data(wdg, wdg_data)

    def _set_wdg_data(self, wdg, wdg_data):
        """
        Sets widget's data.

        :param wdg: A Widget.
        :type wdg: QWidget
        :param wdg_data: A widget data.
        :type wdg_data: QVariant
        """

        if isinstance(wdg, QLineEdit):
            if wdg_data:
                if isinstance(wdg_data, float):
                    if wdg_data.is_integer():
                        wdg_data = int(wdg_data)
                wdg.setText(str(wdg_data))
            else:
                wdg.clear()
        elif isinstance(wdg, QComboBox):
            wdg.setCurrentIndex(wdg.findText(wdg_data))
        elif isinstance(wdg, QDateEdit):
            if wdg_data:
                wdg.setDate(wdg_data)
            else:
                wdg.setDate(wdg.minimumDateTime().date())

    def _add_tbl_row(self):
        """
        Adds a table row.
        """

        tbl = self._get_tbl()
        tbl_hdrs = self._get_tbl_hdrs()

        tbl.setSortingEnabled(False)

        m = tbl.currentRow() + 1
        tbl.insertRow(m)
        tbl.blockSignals(True)
        tbl.selectRow(m)
        tbl.blockSignals(False)
        self._add_tbl_mty_row_items(tbl, tbl_hdrs, m)

        self._rst_tbl_row()

        tbl.setSortingEnabled(True)

    def _del_tbl_row(self):
        """
        Delete a row from a table.
        """

        tbl = self._get_tbl()
        m = tbl.currentRow()

        if tbl.rowCount() > 1:
            tbl.removeRow(m)

    def _rst_tbl_row(self):
        """
        Resets a current table row.
        """

        self._rst_cb_by_cb_dict(self._get_tbl_mand_cb_dict())

        tbl_wdgs = self._get_tbl_wdgs()

        self._rst_wdgs(tbl_wdgs)
        self._emit_wdgs_sgnls(tbl_wdgs)

    def _rst_all_tbl_rows(self):
        """
        Resets all table rows.
        """

        tbl = self._get_tbl()

        curr_item = tbl.currentItem()

        for m in range(tbl.rowCount()):
            tbl.setCurrentCell(m, 0)
            self._rst_tbl_row()

        tbl.selectRow(curr_item.row())

    def _del_all_tbl_rows(self, tbl):
        """
        Deletes all table rows except the currently selected one.

        :param tbl: A table.
        :type tbl: QTableWidget
        """

        tbl = self._get_tbl()
        orig_m = tbl.currentRow()

        for m in range(tbl.rowCount(), -1, -1):
            if m != orig_m:
                tbl.removeRow(m)

    def _get_row_data(self, tbl, m):
        """
        Returns data from the given table in the given row.

        :param tbl: A table.
        :type tbl: QTableWidget
        :param m: A row number.
        :type m: int

        :returns: Data from the given table in the given row.
        :rtype: list
        """

        row_data = []

        for n in range(tbl.columnCount()):
            row_item = tbl.item(m, n).data(Qt.EditRole)

            row_data.append(row_item)

        return row_data

    def _set_loc_tbl_row(self, row_data):
        """
        Sets data to the current row in the location table.
        New row is added if the current row is not empty.

        :param row_data: A data to be written. It has to have the same length
            as number of columns in the table.
        :type row_data: list
        """

        tbl = self.loc_tbl

        curr_row_data = self._get_row_data(tbl, tbl.currentRow())

        if any(item is not None for item in curr_row_data[1:]):
            self.loc_addrow_btn.click()

        m = tbl.currentRow()

        for n in range(tbl.columnCount()):
            tbl.item(m, n).setData(Qt.EditRole, row_data[n])

    def _get_tbl(self):
        """
        Returns a table the sender works with.

        :returns: A table the sender works with.
        :rtype: QTableWidget
        """

        if self.sender().objectName().startswith(u'occ_'):
            return self.occ_tbl
        else:
            return self.loc_tbl

    def _get_tbl_hdrs(self):
        """
        Returns a table headers the sender works with.

        :returns: A table headers the sender works with.
        :rtype: list
        """

        if self.sender().objectName().startswith(u'occ_'):
            return self.occ_tbl_wdg_hdr_dict.values()
        else:
            return self.loc_tbl_wdg_hdr_dict.values()

    def _get_tbl_wdgs(self):
        """
        Returns a table widgets the sender works with.

        :returns: A table widgets the sender works with.
        :rtype: list
        """

        if self.sender().objectName().startswith(u'occ_'):
            return self.occ_tbl_wdg_hdr_dict.keys()
        else:
            return self._cur_loc_edit_tbl_wdgs

    @property
    def _cur_loc_edit_tbl_wdgs(self):
        """
        Returns a list of current location edit table widgets.

        :returns: A list of current location table widgets.
        :rtype: list
        """

        cur_loc_edit_tbl_wdgs = self.loc_edit_met_swdg.currentWidget()\
            .findChildren((QLineEdit, QPlainTextEdit, QComboBox, QDateEdit))

        return cur_loc_edit_tbl_wdgs

    @property
    def _cur_loc_manual_tbl_wdgs(self):
        """
        Returns a list of current location manual table widgets.

        :returns: A list of current location table widgets.
        :rtype: list
        """

        cur_loc_manual_tbl_wdgs = self.loc_manual_swdg.currentWidget()\
            .findChildren((QLineEdit, QPlainTextEdit, QComboBox, QDateEdit))

        return cur_loc_manual_tbl_wdgs

    def _get_tbl_mand_cb_dict(self):
        """
        Returns a table mandatory combo box dictionary the sender works with.

        :returns: A table mandatory combo box dictionary the sender works with.
        :rtype: dict
        """

        if self.sender().objectName().startswith(u'occ_'):
            return self._occ_mand_cb_dict
        else:
            return self._loc_edit_met_cb_dict
