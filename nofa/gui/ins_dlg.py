# -*- coding: utf-8 -*-
"""
/***************************************************************************
 InsDlg
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

from PyQt4 import QtGui, uic
from PyQt4.QtCore import (
    QSettings, QCoreApplication, Qt, QObject, QDate, QObject, QSignalMapper)
from PyQt4.QtGui import (
    QMessageBox, QTreeWidgetItem, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QDialog, QDoubleValidator, QIntValidator, QComboBox,
    QLineEdit, QDateEdit, QAbstractItemView, QValidator, QBrush, QColor,
    QPlainTextEdit, QTextCursor)

from qgis.core import (
    QgsApplication, QgsMessageLog, QgsCoordinateReferenceSystem,
    QgsCoordinateTransform, QgsPoint, QgsRasterLayer, QgsMapLayerRegistry,
    QgsVectorLayer, QgsDataSourceURI, QgsProject)
from qgis.gui import QgsMapToolEmitPoint

from collections import defaultdict, OrderedDict
import os
import psycopg2, psycopg2.extras
import datetime
import uuid
import sys

import de
import dtst_dlg, prj_dlg, ref_dlg, vald
from .. import db


class ActLyrExc(Exception):
    """
    A custom exception when there is no active layer.
    """

    pass


class LocLyrSrcExc(Exception):
    """
    A custom exception when a layer source is not "nofa.location".
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
        :type nf_nvl: QWidget.
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


class NvlLocTextExc(Exception):
    """
    A custom exception when there is a problem
    with format of 'Norwegian VatLnr' location text.
    """

    pass


class UtmLocTextExc(Exception):
    """
    A custom exception when there is a problem
    with format of 'UTM' location text.
    """

    pass


class NvlLocTblExc(Exception):
    """
    A custom exception when there is a problem
    with data format in 'Norwegian VatLnr' location table.
    """

    pass


class UtmLocTblNeExc(Exception):
    """
    A custom exception when easting or northing is missing
    in 'Norwegian VatLnr' location table.
    """

    pass


class UtmLocTblExc(Exception):
    """
    A custom exception when there is a problem
    with data format in 'UTM' location table.
    """

    pass


class NvlNfExc(Exception):
    """
    A custom exception when not all 'Norwegian VatLnr' were found.
    """

    def __init__(self, nf_nvl):
        """
        Constructor.

        :param nf_nvl: Not found 'Norwegian VatLnr'.
        :type nf_nvl: tuple.
        """

        self.nf_nvl = nf_nvl


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'ins_dlg.ui'))


class InsDlg(QDialog, FORM_CLASS):
    """
    A dialog for inserting data into NOFA database.
    """

    def __init__(self, iface, mc, plugin_dir):
        """
        Constructor.

        :param iface: A reference to the QgisInterface.
        :type iface: QgisInterface.
        :param mc: A reference to the main class.
        :type mc: object.
        :param plugin_dir: A plugin directory.
        :type plugin_dir: str.
        """

        super(InsDlg, self).__init__()

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
            u'coordinates UTM33': 25833,}

        self.utm_tbl_hdrs = [
            u'easting',
            u'northing',
            u'verbatimLocality (optional)']

        self.nvl_tbl_hdrs = [
            u'Norwegian VatnLnr']

        self.dash_split_str = u' - '
        self.at_split_str = u'@'
        self.dtst_str = u'Dataset'
        self.prj_str = u'Project'
        self.ref_str = u'Reference'
        self.psql_str = u'postgres'

        self.mty_str = u''
        self.all_str = u'<all>'
        self.sel_str = u'<select>'

        self.forbi_str_list = [
            self.mty_str,
            self.sel_str]

        self.today_dt = datetime.datetime.today().date()
        self.nxt_week_dt = self.today_dt + datetime.timedelta(days=7)
        self.fltr_str_dt = datetime.datetime(2017, 1, 1)

        self.def_clr = self.ins_btn.palette().background().color()
        self.grn_clr = QColor(177, 234, 177)
        self.red_clr = QColor(234, 177, 177)
        self.yel_clr = QColor(234, 234, 177)

        self._build_wdgs()

    def _build_wdgs(self):
        """
        Builds and sets up own widgets.
        """

        self.dtstrt_mde = de.MtyDe(self)
        self.dtstrt_mde.setObjectName(u'dtstrt_mde')
        self.dtstrt_mde.setDisplayFormat('yyyy-MM-dd')
        self.event_grid_lyt.addWidget(self.dtstrt_mde, 4, 1, 1, 1)

        self.dtend_mde = de.MtyDe(self)
        self.dtend_mde.setObjectName(u'dtend_mde')
        self.dtend_mde.setDisplayFormat('yyyy-MM-dd')
        self.event_grid_lyt.addWidget(self.dtend_mde, 5, 1, 1, 1)

        self.verdt_mde = de.MtyDe(self)
        self.verdt_mde.setObjectName(u'verdt_mde')
        self.verdt_mde.setDisplayFormat('yyyy-MM-dd')
        self.occ_grid_lyt.addWidget(self.verdt_mde, 8, 3, 1, 1)

        self.cntry_code_cb.currentIndexChanged.connect(self._pop_cnty_cb)
        self.cnty_cb.currentIndexChanged.connect(self._pop_muni_cb)

        self.hist_ins_dtstrt_de.dateChanged.connect(
            self.hist_ins_dtend_de.setMinimumDate)
        self.hist_ins_dtend_de.dateChanged.connect(
            self.hist_ins_dtstrt_de.setMaximumDate)
        self.hist_upd_dtstrt_de.dateChanged.connect(
            self.hist_upd_dtend_de.setMinimumDate)
        self.hist_upd_dtend_de.dateChanged.connect(
            self.hist_upd_dtstrt_de.setMaximumDate)

        self.hist_ins_dtstrt_de.setDate(self.fltr_str_dt)
        self.hist_ins_dtend_de.setDate(self.today_dt)
        self.hist_upd_dtstrt_de.setDate(self.fltr_str_dt)
        self.hist_upd_dtend_de.setDate(self.today_dt)

        self.adddtst_btn.clicked.connect(self._open_dtst_dlg)
        self.addprj_btn.clicked.connect(self._open_prj_dlg)
        self.addref_btn.clicked.connect(self._open_ref_dlg)

        self.dtst_cb.activated.connect(self._upd_mtdt_lw)
        self.prj_cb.activated.connect(self._upd_mtdt_lw)
        self.ref_cb.activated.connect(self._upd_mtdt_lw)

        self.occ_tbl.currentItemChanged.connect(self._upd_occ_gb_at_selrow)
        self.occ_rowup_btn.clicked.connect(self._sel_row_up)
        self.occ_rowdwn_btn.clicked.connect(self._sel_row_dwn)
        self.occ_addrow_btn.clicked.connect(self._add_row)
        self.occ_delrow_btn.clicked.connect(self._del_row)
        self.occ_rstrow_btn.clicked.connect(self._rst_occ_row)
        self.occ_rstallrows_btn.clicked.connect(self._rst_all_occ_rows)
        self.occ_del_btn.clicked.connect(self._del_all_occ_rows)

        self.loc_rowup_btn.clicked.connect(self._sel_row_up)
        self.loc_rowdwn_btn.clicked.connect(self._sel_row_dwn)
        self.loc_addrow_btn.clicked.connect(self._add_row)
        self.loc_delrow_btn.clicked.connect(self._del_row)
        self.loc_rstrow_btn.clicked.connect(self._rst_loc_row)
        self.loc_rstallrows_btn.clicked.connect(self._rst_all_loc_rows)
        self.loc_del_btn.clicked.connect(self._del_all_loc_rows)

        self.main_tabwdg.setCurrentIndex(0)
        self.main_tabwdg.currentChanged.connect(self._fetch_schema)

        self.txncvg_tw.itemChanged.connect(self._upd_txncvg_tw_chldn)

        self.txn_cb.currentIndexChanged.connect(self._pop_ectp_cb)

        self.smpsv_le.setValidator(QIntValidator(None))
        self.smpe_le.setValidator(QIntValidator(None))
        self.oq_le.setValidator(QDoubleValidator(None))

        self.event_input_wdgs = [
            self.smpp_cb,
            self.smpsv_le,
            self.smpsu_cb,
            self.smpe_le,
            self.dtstrt_mde,
            self.dtend_mde,
            self.fldnum_le,
            self.rcdby_le,
            self.eventrmk_le,
            self.relia_cb]

        # to keep order
        self.occ_tbl_hdrs_wdg_dict = OrderedDict([
            (u'taxon', self.txn_cb),
            (u'ecotype', self.ectp_cb),
            (u'organismQuantityType', self.oqt_cb),
            (u'organismQuantity', self.oq_le),
            (u'occurrenceStatus', self.occstat_cb),
            (u'populationTrend', self.poptrend_cb),
            (u'recordNumber', self.recnum_le),
            (u'occurrenceRemarks', self.occrmk_le),
            (u'establishmentMeans', self.estm_cb),
            (u'establishmentRemarks', self.estrmk_le),
            (u'spawningCondition', self.spwnc_cb),
            (u'spawningLocation', self.spwnl_cb),
            (u'verifiedBy', self.vfdby_le),
            (u'verifiedDate', self.verdt_mde)])

        for wdg in self.occ_tbl_hdrs_wdg_dict.values():
            if isinstance(wdg, QLineEdit):
                wdg.textChanged.connect(self._upd_occ_row)
            elif isinstance(wdg, QComboBox):
                wdg.activated.connect(self._upd_occ_row)
            elif isinstance(wdg, QDateEdit):
                wdg.dateChanged.connect(self._upd_occ_row)

        self.loctp_cb.currentIndexChanged.connect(self._set_loc_tbl)

        self._create_tbl_main_tab(self.nvl_tbl, self.nvl_tbl_hdrs)
        self._create_tbl_main_tab(self.utm_tbl, self.utm_tbl_hdrs)

        self.occ_tbl.setEditTriggers(QAbstractItemView.NoEditTriggers)

        self.nvl_tbl.itemChanged.connect(self.nvl_tbl.resizeColumnsToContents)
        self.utm_tbl.itemChanged.connect(self.utm_tbl.resizeColumnsToContents)

        self.loc_input_sm = QSignalMapper(self)

        self.loc_tbl_rb.clicked.connect(self.loc_input_sm.map)
        self.loc_input_sm.setMapping(self.loc_tbl_rb, 0)

        self.loc_pte_rb.clicked.connect(self.loc_input_sm.map)
        self.loc_input_sm.setMapping(self.loc_pte_rb, 1)

        self.loc_input_sm.mapped.connect(self.loc_sw.setCurrentIndex)

        self.loc_tbl_rb.click()

        # tool for setting coordinates by left mouse click
        self.cnvs = self.iface.mapCanvas()
        self.coord_cnvs_tool = QgsMapToolEmitPoint(self.cnvs)
        self.coord_cnvs_tool.canvasClicked.connect(
            self._set_coord_cnvs_to_utm_tbl)
        self.coord_cnvs_btn.clicked.connect(self._act_coord_cnvs_tool)

        self.osm_basemap_btn.clicked.connect(self._add_osm_wms_lyr)

        self.loc_srch_btn.clicked.connect(self._srch_loc)
        self.wb_le.returnPressed.connect(self._srch_loc)
        self.loc_load_btn.setEnabled(False)
        self.loc_load_btn.clicked.connect(self._load_loc_layer)
        self.add_nvl_btn.clicked.connect(self._add_nvl_codes)

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

        for wdg in self.hist_input_wdgs:
            if isinstance(wdg, QComboBox):
                wdg.currentIndexChanged.connect(self._fill_hist_tbls)
            elif isinstance(wdg, QDateEdit):
                wdg.dateChanged.connect(self._fill_hist_tbls)

        self.rst_btn.clicked.connect(self._rst)
        self.ins_btn.clicked.connect(self._ins)

        self.occ_mand_wdgs = [
            self.txn_cb,
            self.occstat_cb,
            self.estm_cb]

        self.mtdt_mand_wdgs = [
            self.smpp_cb,
            self.dtend_mde,
            self.rcdby_le,
            self.dtst_cb,
            self.prj_cb,
            self.ref_cb]

        self.all_mand_wdgs = self.occ_mand_wdgs + self.mtdt_mand_wdgs
 
        self.set_mand_wdgs(self.all_mand_wdgs)

        self.main_hspltr.setStretchFactor(0, 1)
        self.main_hspltr.setStretchFactor(1, 2)
        self.occ_hspltr.setStretchFactor(0, 1)
        self.occ_hspltr.setStretchFactor(1, 2)

    def set_mand_wdgs(self, wdgs):
        """
        Sets mandatory widgets. Mandatory widgets have predefined color
        when they are not filled/selected.
            - line edit - must contain at least one
            - combo box - selected value can not be in list of forbidden
                          strings
            - date edit - user must edit (click) on it at least once
        
        :param wdgs: A list of widgets to be set as mandatory.
        :type wdgs: list.
        """

        for wdg in wdgs:
            if isinstance(wdg, QLineEdit):
                wdg.setValidator(vald.LenTxtVald(wdg))
                wdg.textChanged.connect(self._chck_state_text)
                wdg.textChanged.emit(wdg.text())
            elif isinstance(wdg, QComboBox):
                wdg.currentIndexChanged.connect(self._chck_state_text)
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
        Check if the given mandatory widgets are filled.

        :param mand_wdgs: A list of mandatory widgets.
        :type mand_wdgs: list.
        :param exc: An exception that should be raised.
        :type exc: Exception.
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

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString.
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('NOFAInsert', message)

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
        else:
            self.loc_load_btn.setEnabled(False)

        self.lake_name_statlbl.setText(
            u'Found {} location(s).'.format(loc_count))

    def _get_val_txt(self, txt, forbi=False, all=False):
        """
        Returns a validated text.

        :param txt: A text.
        :type txt: str.
        :param forbi: True to allow forbidden text, False otherwise.
        :type forbi: bool.
        :param all: True to allow all text, False otherwise.
        :type all: bool

        :returns: A filter, None when text is in list of forbidden strings
            or when length of text is zero.
        :rtype: str.
        """

        if forbi == False and txt in self.forbi_str_list:
            val_txt = None
        elif all == False and txt == self.all_str:
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

        :returns: A tuple containing water body, country code, county
            and municipality.
        :rtype: tuple.
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
        :rtype: str.
        """

        txt = self.wb_le.text()

        wb = self._get_val_txt(txt, all=True)

        return wb

    @property
    def _cntry_code(self):
        """
        Returns a country code from country code combo box.

        :returns: A country code, None when text is equal to <all> string
            or when length of text is zero.
        :rtype: str.
        """

        txt = self.cntry_code_cb.currentText()

        cntry_code = self._get_val_txt(txt)

        return cntry_code

    @property
    def _cnty(self):
        """
        Returns a county from county combo box.

        :returns: A county, None when text is equal to <all> string
            or when length of text is zero.
        :rtype: str.
        """

        txt = self.cnty_cb.currentText()

        cnty = self._get_val_txt(txt)

        return cnty

    @property
    def _muni(self):
        """
        Returns a municipality from municipality combo box.

        :returns: A municipality, None when text is equal to <all> string
            or when length of text is zero.
        :rtype: str.
        """

        txt = self.muni_cb.currentText()

        muni = self._get_val_txt(txt)

        return muni

    @property
    def _txn(self):
        """
        Returns a taxon from taxon combo box.

        :returns: A taxon, None when text is equal to <all> string
            or when length of text is zero.
        :rtype: str.
        """

        txt = self.txn_cb.currentText()

        txn = self._get_val_txt(txt)

        return txn

    def _load_loc_layer(self):
        """
        Loads a layer of found locations.
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
                ', '.join(['\'{}\''.format(str(l)) for l in self.locid_list])),
            'locationID')

        wb, cntry_code, cnty, muni = self._loc_fltrs

        lyr = QgsVectorLayer(
            uri.uri(),
            u'location-{}-{}-{}-{}'.format(wb, cntry_code, cnty, muni),
            self.psql_str)

        if lyr.isValid():
            QgsMapLayerRegistry.instance().addMapLayer(lyr)

    def _add_nvl_codes(self):
        """
        Adds Norwegian VatLnr codes of selected features
        to table/plain text edit.
        """

        try:
            lyr = self.iface.activeLayer()

            self._chck_lyr(lyr)

            if lyr.selectedFeatureCount() == 0:
                raise SelFeatExc()

            sel_feats = lyr.selectedFeaturesIterator()

            for feat in sel_feats:
                nvl = str(feat.attribute('no_vatn_lnr'))

                if nvl.lower() == 'null':
                    continue

                if self.loc_tbl_rb.isChecked():
                    row_data = self._get_row_data(
                        self.nvl_tbl, self.nvl_tbl.currentRow())[0]

                    if row_data:
                        self.loc_addrow_btn.click()

                    self._set_row_data(
                        self.nvl_tbl, self.nvl_tbl.currentRow(), [nvl])
                else:
                    self.loc_pte.moveCursor(QTextCursor.End)

                    txt = self.loc_pte.toPlainText()

                    if not txt.strip().endswith(u',') and len(txt) != 0:
                        self.loc_pte.insertPlainText(u', ')

                    self.loc_pte.insertPlainText(nvl)
                    self.loc_pte.moveCursor(QTextCursor.End)
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
        Checks if the given layer is a from nofa.location table.
        
        :param lyr: A layer to be checked.
        :type lyr: QgsVectorLayer.
        """

        try:
            uri = QgsDataSourceURI(lyr.source())
        except AttributeError:
            raise ActLyrExc()

        if uri.schema() != 'nofa' or uri.table() != 'location':
            raise LocLyrSrcExc()

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

    def _set_coord_cnvs_to_utm_tbl(self, pnt, btn):
        """
        Sets canvas coordinates to the current row in the UTM table.
        It transforms coordinates to the current UTM system.
        Coordinates are set only on left mouse click.

        :param pnt: A point.
        :type pnt: QgsPoint.
        :param btn: A mouse button.
        :type btn: QtCore.MouseButton.
        """

        if btn == Qt.LeftButton:
            in_authid = self.cnvs.mapSettings().destinationCrs().authid()
    
            loctp = self.loctp_cb.currentText()
            out_authid = 'EPSG:{}'.format(self.loctp_dict[loctp])
    
            in_x = pnt.x()
            in_y = pnt.y()
    
            out_x, out_y = self._trf_coord(in_authid, out_authid, in_x, in_y)
    
            m = self.utm_tbl.currentRow()
    
            self.utm_tbl.item(m, 0).setText(str(out_x))
            self.utm_tbl.item(m, 1).setText(str(out_y))

    def _trf_coord(self, in_authid, out_authid, in_x, in_y):
        """
        Transforms the given X and Y coordinates from the input CRS
        to the output CRS.

        :param in_authid: An input CRS.
        :type in_authid: str.
        :param out_authid: An Output CRS.
        :type out_authid: str.
        :param in_x: An input X coordinate.
        :type in_x: float.
        :param in_y: An input Y coordinate.
        :type in_y: float.

        :returns: X and Y coordinates in the output CRS.
        :rtype: tuple.
        """

        in_proj = QgsCoordinateReferenceSystem(in_authid)
        out_proj = QgsCoordinateReferenceSystem(out_authid)

        trf = QgsCoordinateTransform(in_proj, out_proj)

        out_x, out_y = trf.transform(QgsPoint(in_x, in_y))

        return (out_x, out_y)

    def _set_loc_tbl(self, cb_idx):
        """
        Sets a location table according to the combo box index.
        When location input method is set to text, nothing happens.

        :param cb_idx: A combo box index.
        :type cb_idx: int.
        """

        if cb_idx == 0:
            self.loc_tbl_sw.setCurrentIndex(0)
            self.coord_cnvs_btn.setEnabled(False)
            self.add_nvl_btn.setEnabled(True)
        else:
            self.loc_tbl_sw.setCurrentIndex(1)
            self.coord_cnvs_btn.setEnabled(True)
            self.add_nvl_btn.setEnabled(False)

    def _fetch_schema(self):
        """
        Fetches a schema based on what tab is active.
        If the main tab is active it fetches data from NOFA schema,
        otherwise it fetches data from plugin schema.
        """

        idx = self.main_tabwdg.currentIndex()

        if idx == 0:
            self.fetch_nofa_schema()
        elif idx == 1:
            self._fetch_plugin_schema()

    def _fetch_plugin_schema(self):
        """
        Fetches data from the plugin schema and populates tables.
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

        :returns: A tuple containing user, insert start date, insert end date,
            update start date and update end date.
        :rtype: tuple.
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
        :type par: QTableWidgetItem.
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

        self._rst_loc_wdgs()
        self._rst_event_wdgs()
        self._rst_mtdt_wdgs()
        self._rst_occ_tbl()
        self._rst_txncvg_tw()

    def _rst_loc_wdgs(self):
        """
        Resets all location widgets.
        """

        self._rst_cb_by_cb_dict(self._loc_cb_dict)

        self.wb_le.clear()
        self.lake_name_statlbl.setText(u'Search for locations.')

        self._create_loc_tbls()

        self.loc_pte.clear()

        self.loc_tbl_rb.click()

    def _create_loc_tbls(self):
        """
        Creates location tables.
        """

        self._create_tbl_main_tab(self.nvl_tbl, self.nvl_tbl_hdrs)
        self._create_tbl_main_tab(self.utm_tbl, self.utm_tbl_hdrs)

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

        self._del_all_occ_rows()
        self._rst_occ_row()

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
        Insert the data into the database.
        """

        try:
            self.chck_mand_wdgs(self.mtdt_mand_wdgs, MtdtNotFldExc)
            self._chck_occ_tbl()

            loc_id_list = self._get_loc()

            event_list = self.get_wdg_list(self.event_input_wdgs)

            dtst_id = self._get_dtst_id()
            prj_id = self._get_prj_id()
            ref_id = self._get_ref_id()

            for loc_id in loc_id_list:
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
        except NoLocExc:
            self.main_tb.setCurrentIndex(0)
            QMessageBox.warning(
                self, u'No Location', u'Enter at least one location.')
        except NvlLocTextExc:
            QMessageBox.warning(
                self,
                u'Norwegian VatLnr',
                u'Enter integers separated by commas.\n'
                u'For example:\n'
                u'3067, 5616, 5627')
        except UtmLocTextExc:
            QMessageBox.warning(
                self,
                u'UTM',
                u'Enter location in this format separated by commas '
                u'(location name is optional):\n'
                u'"<easting> <northing> <location_name>"\n'
                u'For example:\n'
                u'601404.85 6644928.24 Hovinbk, '
                u'580033.012 6633807.99 Drengsrudbk')
        except NvlLocTblExc:
            QMessageBox.warning(
                self,
                u'Norwegian VatLnr',
                u'Enter integers.\n'
                u'For example:\n'
                u'3067')
        except UtmLocTblNeExc:
            QMessageBox.warning(
                self,
                u'UTM',
                u'Enter both easting and northing.')
        except UtmLocTblExc:
            QMessageBox.warning(
                self,
                u'UTM',
                u'Both easting and northing must be decimals.')
        except NvlNfExc as e:
            QMessageBox.warning(
                self,
                u'Norwegian VatLnr',
                u'The following Norwegian VatLnr codes were not found:\n'
                u'{}\n'.format(u', '.join(str(n) for n in e.nf_nvl)))
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

    def get_wdg_list(self, wdgs, forbi=False):
        """
        Returns the data from the given list of widgets.

        :param wdgs: A list of widgets whose data should be returned.
        :type wdgs: list.
        :param forbi: True to allow forbidden text, False otherwise.
        :type forbi: bool.

        :returns: A list of data from event input widgets.
        :rtype: list.
        """

        wdg_list = []

        for wdg in wdgs:
            if isinstance(wdg, QLineEdit):
                txt = wdg.text()
                wdg_data = self._get_val_txt(txt, forbi)
            elif isinstance(wdg, QComboBox):
                txt = wdg.currentText()
                wdg_data = self._get_val_txt(txt, forbi)
            elif isinstance(wdg, QDateEdit):
                if wdg.findChild(QLineEdit).text() == self.mty_str:
                    wdg_data = None
                else:
                    wdg_data = wdg.date().toPyDate()
            elif isinstance(wdg, QPlainTextEdit):
                txt = wdg.toPlainText()
                wdg_data = self._get_val_txt(txt, forbi)

            wdg_list.append(wdg_data)

        return wdg_list

    def _rst_wdgs(self, wdgs):
        """
        Resets the given widgets.
            - line edit - clear
            - combo box - set current index to 0
            - date edit - set date to minimum

        :param wdgs: Widgets to be cleared.
        :type wdgs: list.
        """

        for wdg in wdgs:
            if isinstance(wdg, QLineEdit):
                wdg.clear()
            elif isinstance(wdg, QComboBox):
                wdg.setCurrentIndex(0)
            elif isinstance(wdg, QDateEdit):
                wdg.setDate(wdg.minimumDate())

    def _get_occ_row_list(self, m):
        """
        Returns an occurrence row list.

        :param m: A row number.
        :type m: int.

        :returns: A list of data in the given row in the occurrence table.
        :rtype: list.
        """

        occ_row_list = []

        # OS.NINA
        # depends on the order in the table
        for n in range(self.occ_tbl.columnCount()):
            txt = self.occ_tbl.item(m, n).text()
            val_txt = self._get_val_txt(txt)

            occ_row_list.append(val_txt)

        return occ_row_list

    def _ins_txncvg(self, event_id):
        """
        Inserts all checked taxons into the database.

        :param event_id: An event ID.
        :type event_id: uuid.UUID.
        """

        for txn in self._ckd_txns:
            txn_id = db.get_txn_id(self.mc.con, txn)

            db.ins_txncvg(self.mc.con, txn_id, event_id)

    @property
    def _ckd_txns(self):
        """
        Returns all checked taxons from the taxon coverage tree widget.

        :returns: A list of all checked taxons.
        :rtype: list.
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

    def _get_loc(self):
        """
        Returns a list of location IDs.

        :returns: A list of location IDs.
        :rtype: list.
        """

        loctp = self.loctp_cb.currentText()

        loc_input_set = self._get_loc_input_set(loctp)

        if loctp == 'Norwegian VatnLnr':
            locs_tpl = tuple([nvl for loc in loc_input_set for nvl in loc])

            loc_id_nvl_list = db.get_loc_id_nvl_list(self.mc.con, locs_tpl)

            # check if all codes were found
            if len(loc_id_nvl_list) != len(locs_tpl):
                loc_nvl_list = [l[1] for l in loc_id_nvl_list]

                nf_nvl = tuple(set(locs_tpl) - set(loc_nvl_list))

                raise NvlNfExc(nf_nvl)

            loc_id_list = [l[0] for l in loc_id_nvl_list]
        else:
            loc_id_list = []

            for loc in loc_input_set:
                utme = loc[0]
                utmn = loc[1]

                try:
                    loc_name = loc[2]
                except IndexError:
                    loc_name = None

                srid = self.loctp_dict[loctp]

                pt_str = db.get_pt_str(utme, utmn)

                utm33_geom = db.get_utm33_geom(self.mc.con, pt_str, srid)

                # OS.NINA
                # is 10 meters alright?
                loc_id = db.get_nrst_loc_id(self.mc.con, utm33_geom, 10)

                if not loc_id:
                    loc_id = uuid.uuid4()

                    mpt_str = db.get_mpt_str(utme, utmn)
                    utm33_geom = db.get_utm33_geom(self.mc.con, mpt_str, srid)

                    db.ins_new_loc(self.mc.con, loc_id, utm33_geom, loc_name)

                    db.ins_loc_log(
                        self.mc.con,
                        loc_id,
                        loc_name,
                        self.mc.con_info[self.mc.usr_str])

                loc_id_list.append(loc_id)

        return loc_id_list

    def _get_loc_input_set(self, loctp):
        """
        Return a set of location inputs.

        :param loctp: A location type.
        :type loctp: str.

        :returns: A set of location inputs.
        :rtype: set.
        """

        # get data from table
        if self.loc_tbl_rb.isChecked():
            loc_input_list = []

            tbl = self.loc_tbl_sw.currentWidget().findChild(QTableWidget)

            mty_row_idx = []

            for m in range(tbl.rowCount()):
                row_data = self._get_row_data(tbl, m)

                if all(item is None for item in row_data) \
                    and tbl.rowCount() != 1:
                    mty_row_idx.append(m)
                else:
                    loc_input_list.append(row_data)

            mty_row_idx.sort(reverse=True)

            # remove empty rows
            for m in mty_row_idx:
                if tbl.rowCount() != 1:
                    tbl.removeRow(m)

            if all(item is None for row in loc_input_list for item in row):
                raise NoLocExc()

            if loctp == 'Norwegian VatnLnr':
                for m in range(len(loc_input_list)):
                    try:
                        loc_input_list[m][0] = int(loc_input_list[m][0])
                    except ValueError:
                        raise NvlLocTblExc()
            else:
                for m in range(len(loc_input_list)):
                    if None in loc_input_list[m][:2]:
                        raise UtmLocTblNeExc()
                    for n in range(2):
                        try:
                            loc_input_list[m][n] = float(loc_input_list[m][n])
                        except ValueError:
                            raise UtmLocTblExc()
        # get data from plain text edit
        else:
            loc_text = self.loc_pte.toPlainText()

            if len(loc_text) == 0:
                raise NoLocExc()

            if loctp == 'Norwegian VatnLnr':
                loc_input_list = loc_text.split(',')

                for i, nvl in enumerate(loc_input_list):
                    try:
                        loc_input_list[i] = [int(nvl)]
                    except ValueError:
                        raise NvlLocTextExc()
            else:
                loc_input_list = [loc.split(' ') for loc in loc_text.split(',')]

                for m in range(len(loc_input_list)):
                    for n in range(2):
                        try:
                            loc_input_list[m][n] = float(loc_input_list[m][n])
                        except ValueError:
                            raise UtmLocTextExc()

        loc_input_set = set(map(tuple, loc_input_list))

        return loc_input_set

    def _chck_occ_tbl(self):
        """
        Checks if all rows in the occurrence are filled.
        """

        for m in range(self.occ_tbl.rowCount()):
            occ_row_list = self._get_occ_row_list(m)

            if occ_row_list[0] == None:
                self.occ_tbl.selectRow(m)
                raise OccNotFldExc()

    def upd_dtst(self, dtst_str=None):
        """
        Updates a dataset according to the last selected.
        
        :param dtst_str: A dataset string "<ID> - <name>".
        :type dtst_str: str.
        """

        self._upd_mtdt(self.dtst_cb, dtst_str)

    def upd_prj(self, prj_str=None):
        """
        Updates a project according to the last selected.
        
        :param prj_str: A project string "<name> - <organisation>".
        :type prj_str: str.
        """

        self._upd_mtdt(self.prj_cb, prj_str)

    def upd_ref(self, ref_str=None):
        """
        Updates a reference according to the last selected.

        :param ref_str: A reference string "<author>: <title> (<year>) @<ID>".
        :type ref_str: str.
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
        :type cb_str: str.
        :param cb: A combo box.
        :type cb: QComboBox.
        """

        if isinstance(cb_str, int):
            cb = self.sender()
            cb_str = cb.currentText()

        idx = self.main_tb.indexOf(cb.parentWidget())
        mdtd_base_txt = self.main_tb.itemText(idx).split(self.dash_split_str)[0]

        lw, id_met, info_fnc, mtdt_str_fnc = self._mtdt_lw_cb_dict[cb]

        lw.clear()

        if cb_str in self.forbi_str_list:
            mtdt_txt = cb_str
        else:
            items, hdrs = info_fnc(self.mc.con, id_met())

            self._pop_lw(lw, items, hdrs)

            mtdt_txt = mtdt_str_fnc(cb_str)

        self._set_mtdt_item_txt(
            idx, u'{}{}{}'.format(mdtd_base_txt, self.dash_split_str, mtdt_txt))

        self.settings.setValue(cb.objectName(), cb_str)

    def _set_mtdt_item_txt(self, item_index, text):
        """
        Sets metadata item text.

        :param item_index: An Item index.
        :type item_index: int.
        :param text: A text.
        :type text: str.
        """

        self.main_tb.setItemText(item_index, text)

    @property
    def _mtdt_lw_cb_dict(self):
        """
        Returns a metadata list widget combo box dictionary.

        :returns: A metadata combo box dictionary.
            - key - <combo box name>
            - value - [<list widget>,
                       <method that returns ID>,
                       <function that returns information>,
                       <function that returns metadata string>]
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
        Adds all items with their corresponding headers "<header>: <item>".

        :param lw: A list widget.
        :type lw: QListWidget.
        :param items: Items to be added.
        :type items: list.
        :param hdrs: Headers to be added.
        :type hdrs: list.
        """

        for hdr, item in zip(hdrs, items):
            lw_item = QListWidgetItem(u'{}: {}'.format(hdr, item))
            lw.addItem(lw_item)

    def fetch_nofa_schema(self):
        """
        Fetches data from the NOFA schema and populates widgets.
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

        :param cb_dict: A combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :type cb_dict:
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
        Color of items whose text is in the list of forbidden strings
        is set to red.

        :param cb:
        :type cb:
        :param item_list:
        :type item_list:
        """

        cb.clear()

        for i, item in enumerate(item_list):
            cb.addItem(item)

            if item in self.forbi_str_list:
                clr = self.red_clr
                cb.setItemData(i, QBrush(clr), Qt.BackgroundRole)

    def _rst_cb_by_cb_dict(self, cb_dict):
        """
        Resets combo boxes by the given combo box dictionary.

        :param cb_dict: A nofa combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :type cb_dict: dict.
        """

        for cb, cb_list in cb_dict.items():
            def_val = cb_list[2]
            cb.setCurrentIndex(cb.findText(def_val))

    @property
    def _nofa_cb_dict(self):
        """
        Returns a nofa combo box dictionary.

        :returns: A nofa combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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

        :returns: A combo box dictionary for all location combo boxes.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
        """

        loc_cb_dict = {
            self.loctp_cb: [
                self._get_loctp_list,
                [],
                'Norwegian VatnLnr'],
            self.cntry_code_cb:[
                db.get_cntry_code_list,
                [self.mc.con],
                self.all_str]}

        loc_cb_dict = self._get_mrgd_dict(
            loc_cb_dict,
            self._cnty_cb_dict,
            self._muni_cb_dict)

        return loc_cb_dict

    @property
    def _cnty_cb_dict(self):
        """
        Returns a county combo box dictionary.

        :returns: A county combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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

        :returns: A municipality combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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

        :returns: A combo box dictionary for all event combo boxes.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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
                self.mty_str],}

        return event_cb_dict

    @property
    def _ectp_cb_dict(self):
        """
        Returns an ecotype combo box dictionary.

        :returns: An ecotype combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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

        :returns: An metadata combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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

        :returns: An dataset combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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

        :returns: An project combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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

        :returns: An reference combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
        """

        ref_cb_dict = {
            self.ref_cb: [
                db.get_ref_list,
                [self.mc.con],
                self.sel_str]}

        return ref_cb_dict

    @property
    def _occ_mand_cb_dict(self):
        """
        Returns an occurrence mandatory combo box dictionary.

        :returns: An occurrence mandatory combo box dictionary.
            - key - <combo box name>
            - value - [<fill method>, [<arguments>], <default value>]
        :rtype: dict.
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
        root_item.setFlags(Qt.ItemIsUserCheckable|Qt.ItemIsEnabled)

        for fam in fam_dict.keys():
            family_item = QTreeWidgetItem(root_item, [fam])
            family_item.setCheckState(0, Qt.Unchecked)
            family_item.setFlags(Qt.ItemIsUserCheckable|Qt.ItemIsEnabled)

            for txn in fam_dict[fam]:
                txn_item = QTreeWidgetItem(family_item, [txn])
                txn_item.setCheckState(0, Qt.Unchecked)
                txn_item.setFlags(Qt.ItemIsUserCheckable|Qt.ItemIsEnabled)

        self.txncvg_tw.sortByColumn(0, Qt.AscendingOrder)
        self.txncvg_tw.expandToDepth(0)

    def _get_dtst_id(self):
        """
        Returns a dataset ID from the dataset combo box.

        :returns: A dataset ID.
        :rtype: str.
        """

        dtst_str = self.dtst_cb.currentText()

        id, name = db.split_dtst_str(dtst_str)

        return id

    def _get_prj_id(self):
        """
        Returns a project ID based on name and organization.

        :returns: A project ID.
        :rtype: str.
        """

        prj_str = self.prj_cb.currentText()

        prj_name, prj_org = db.split_prj_str(prj_str)

        prj_id = db.get_prj_id(self.mc.con, prj_name, prj_org)

        return prj_id

    def _get_ref_id(self):
        """
        Returns a reference ID from the reference combo box.

        :returns: A reference ID.
        :rtype: str.
        """

        ref_str = self.ref_cb.currentText()

        au, ttl, yr, id = db.split_ref_str(ref_str)

        return id

    def _get_loctp_list(self):
        """
        Returns a list of location types.

        :returns: A list of location types.
        :rtype: list.
        """

        # OS.NINA
        # location types are hardcoded
        # could not find a list of location types in db
        loctp_list = [
            'Norwegian VatnLnr',
            'coordinates UTM32',
            'coordinates UTM33']
        loctp_list.sort()

        return loctp_list

    def create_occ_tbl(self):
        """
        Creates an occurrence table with one row.
        """

        self._create_tbl_main_tab(
            self.occ_tbl, self.occ_tbl_hdrs_wdg_dict.keys())
        self._upd_occ_row()

    def _create_tbl_main_tab(self, tbl, tbl_hdrs):
        """
        Creates a table with one row.
        This method is used for creating tables in the main tab.
        
        :param tbl: A table widget.
        :type tbl: QTableWidget.
        :param tbl_hdrs: Table headers.
        :type tbl_hdrs: tuple.
        """
  
        tbl.setColumnCount(len(tbl_hdrs))
        tbl.setSelectionBehavior(QTableWidget.SelectRows)
        tbl.setSelectionMode(QTableWidget.SingleSelection)
        tbl.setHorizontalHeaderLabels(tbl_hdrs)
        tbl.setRowCount(1)

        m = 0

        self._add_mty_row_items(tbl, tbl_hdrs, m)

        tbl.blockSignals(True)
        tbl.selectRow(m)
        tbl.blockSignals(False)

        tbl.resizeColumnsToContents()

    def _create_tbl_hist_tab(self, tbl, tbl_items, tbl_hdrs):
        """
        Creates a table with one row.
        This method is used for creating tables in the history tab.
        
        :param tbl: A table widget.
        :type tbl: QTableWidget.
        :param tbl_items: Table items.
        :type tbl_items: list.
        :param tbl_hdrs: Table headers.
        :type tbl_hdrs: list.
        """
  
        tbl.setColumnCount(len(tbl_hdrs))
        tbl.setSelectionBehavior(QTableWidget.SelectItems)
        tbl.setSelectionMode(QTableWidget.ExtendedSelection)
        tbl.setHorizontalHeaderLabels(tbl_hdrs)
        tbl.setRowCount(len(tbl_items))

        for m, row in enumerate(tbl_items):
            for n, item in enumerate(row):
                tbl_item = QTableWidgetItem(unicode(item))

                tbl.setItem(m, n, tbl_item)

        tbl.resizeColumnsToContents()

    def _add_mty_row_items(self, tbl, tbl_hdrs, m):
        """
        Adds a row at the given position of a table with empty items.
        
        :param tbl: A table widget.
        :type tbl: QTableWidget.
        :param tbl_hdrs: Table headers.
        :type tbl_hdrs: tuple.
        :param m: A row number.
        :type m: int.
        """

        for n, tbl_hdr in enumerate(tbl_hdrs):
            tbl_item = QTableWidgetItem(None)
            tbl.setItem(m, n, tbl_item)

    def _upd_occ_row(self):
        """
        Updates an occurrence row with the values in the occurrence widgets.
        """

        m = self.occ_tbl.currentRow()

        occ_list = self.get_wdg_list(self.occ_tbl_hdrs_wdg_dict.values(), True)

        self._set_occ_row(m, occ_list)

        self.occ_tbl.resizeColumnsToContents()

    def _set_occ_row(self, m, occ_list):
        """
        Sets data from occurrence list to occurrence row.

        :param m: An occurrence row number.
        :type m: int.
        :param occ_list: A list off occurrence data.
        :type occ_list: list.
        """

        for n, elem in enumerate(occ_list):
            try:
                tbl_item = QTableWidgetItem(elem)
            except TypeError:
                tbl_item = QTableWidgetItem(str(elem))
            self.occ_tbl.setItem(m, n, tbl_item)

    def _add_row(self):
        """
        Adds a table row.
        """

        sndr = self.sender()

        tbl = self._get_tbl(sndr)
        tbl_hdrs = self._get_tbl_hdrs(sndr)

        m = tbl.currentRow() + 1
        tbl.insertRow(m)
        self._add_mty_row_items(tbl, tbl_hdrs, m)

        self.occ_tbl.blockSignals(True)
        tbl.selectRow(m)
        self.occ_tbl.blockSignals(False)

        if self._check_occ_tbl(tbl):
            self._rst_occ_row()

    def _rst_occ_row(self):
        """
        Resets a current occurrence row in the occurrence table.
        """

        self._rst_wdgs(self.occ_tbl_hdrs_wdg_dict.values())

        self._rst_occ_mand_cb()
        self._upd_occ_row()

    def _rst_occ_mand_cb(self):
        """
        Resets occurrence mandatory combo boxes.
        """

        self._rst_cb_by_cb_dict(self._occ_mand_cb_dict)

    def _rst_all_occ_rows(self):
        """
        Resets all occurrence rows.
        """

        self._rst_occ_row()

        for m in range(self.occ_tbl.rowCount()):
            occ_list = self.get_wdg_list(
                self.occ_tbl_hdrs_wdg_dict.values(), True)
            self._set_occ_row(m, occ_list)

        self.occ_tbl.resizeColumnsToContents()

    def _upd_occ_gb_at_selrow(self, wdg_item):
        """
        Updates the occurrence group box according to the selected row.

        :param wdg_item: A current widget item.
        :type wdg_item: QTableWidgetItem.
        """

        m = self.occ_tbl.currentRow()

        QgsApplication.processEvents()

        for wdg in self.occ_tbl_hdrs_wdg_dict.values():
            wdg.blockSignals(True)

        QgsApplication.processEvents()

        for n, wdg in enumerate(self.occ_tbl_hdrs_wdg_dict.values()):
            text = self.occ_tbl.item(m, n).text()

            if isinstance(wdg, QLineEdit):
                wdg.setText(text)
            elif isinstance(wdg, QComboBox):
                idx = wdg.findText(text)
                wdg.setCurrentIndex(idx)
            elif isinstance(wdg, QDateEdit):
                wdg.setDate(QDate.fromString(text, 'yyyy-MM-dd'))

        QgsApplication.processEvents()

        for wdg in self.occ_tbl_hdrs_wdg_dict.values():
            wdg.blockSignals(False)

        QgsApplication.processEvents()

    def _rst_loc_row(self):
        """
        Resets the current row in the current location table.
        """

        tbl = self._get_tbl(self.sender())

        m = tbl.currentRow()

        self._clear_row(tbl, m)

    def _rst_all_loc_rows(self):
        """
        Resets all rows in the current location table.
        """

        tbl = self._get_tbl(self.sender())

        for m in range(tbl.rowCount()):
            self._clear_row(tbl, m)

    def _clear_row(self, tbl, m):
        """
        Clears the given row in the given table.

        :param tbl: A table.
        :type tbl: QTableWidget.
        :param m: A location row number.
        :type m: int.
        """

        for n in range(tbl.columnCount()):
            tbl.item(m, n).setText(None)

    def _sel_row_up(self):
        """
        Select one row up in a table.
        """

        tbl = self._get_tbl(self.sender())

        m = tbl.currentRow()

        if m > 0:
            tbl.selectRow(m - 1)

    def _sel_row_dwn(self):
        """
        Select one row down in a table.
        """

        tbl = self._get_tbl(self.sender())

        m = tbl.currentRow()

        if m < (tbl.rowCount() - 1):
            tbl.selectRow(m + 1)

    def _del_row(self):
        """
        Delete a row from a table.
        """

        tbl = self._get_tbl(self.sender())

        m = tbl.currentRow()

        if tbl.rowCount() > 1:
            tbl.removeRow(m)

    def _del_all_occ_rows(self):
        """
        Deletes all occurrence rows except the currently selected one.
        """

        occ_list = self.get_wdg_list(self.occ_tbl_hdrs_wdg_dict.values(), True)

        self.occ_tbl.blockSignals(True)
        self.occ_tbl.setRowCount(1)
        self.occ_tbl.blockSignals(False)

        self._set_occ_row(0, occ_list)

    def _del_all_loc_rows(self):
        """
        Deletes all location rows except the currently selected one.
        """

        tbl = self._get_tbl(self.sender())

        m = tbl.currentRow()

        row_data = self._get_row_data(tbl, m)

        tbl.setRowCount(1)

        self._set_row_data(tbl, tbl.currentRow(), row_data)

    def _get_row_data(self, tbl, m):
        """
        Returns data from the given table in the given row.

        :param tbl: A table.
        :type tbl: QTableWidget.
        :param m: A row number.
        :type m: int.

        :returns: Data from the given table in the given row.
        :rtype: list.
        """

        row_data = []

        for n in range(tbl.columnCount()):
            row_item = tbl.item(m, n).text() \
                if len(tbl.item(m, n).text()) != 0 else None

            row_data.append(row_item)

        return row_data

    def _set_row_data(self, tbl, m, row_data):
        """
        Sets data to the given row in the given table.

        :param tbl: A table.
        :type tbl: QTableWidget.
        :param m: A row number.
        :type m: int.
        :param row_data: A data to be written. It has to have the same length
            as number of columns in the table.
        :type row_data:
        """

        for n in range(tbl.columnCount()):
            tbl.item(m, n).setText(row_data[n])

    def _get_tbl(self, sndr):
        """
        Returns a table the sender works with.

        :param sndr: A sender push button.
        :type sndr: QPushButton.

        :returns: A table the sender works with.
        :rtype: QTableWidget.
        """

        sndr_name = sndr.objectName()

        if sndr_name.startswith(u'occ_'):
            tbl = self.occ_tbl
        else:
            tbl = self.loc_tbl_sw.currentWidget().findChild(QTableWidget)

        return tbl

    def _get_tbl_hdrs(self, sndr):
        """
        Returns table headers the sender works with.

        :param sndr: A sender push button.
        :type sndr: QPushButton.

        :returns: Table headers the sender works with.
        :rtype: list.
        """

        sndr_name = sndr.objectName()

        if sndr_name.startswith(u'occ_'):
            tbl_hdrs = self.occ_tbl_hdrs_wdg_dict.keys()
        else:
            tbl_name = self.loc_tbl_sw.currentWidget()\
                .findChild(QTableWidget).objectName()

            if tbl_name == u'nvl_tbl':
                tbl_hdrs = self.nvl_tbl_hdrs
            else:
                tbl_hdrs = self.utm_tbl_hdrs

        return tbl_hdrs

    def _check_occ_tbl(self, tbl):
        """
        Checks if the given table is the occurrence table.

        :param tbl: A table.
        :type tbl: QTableWidget.

        :returns: True when the given table is the occurrence table,
            False otherwise.
        :rtype: bool.
        """

        if tbl.objectName() == u'occ_tbl':
            occ_tbl = True
        else:
            occ_tbl = False

        return occ_tbl
