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
    QPlainTextEdit)

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

import dtst_dlg, prj_dlg, ref_dlg, vald

from .. import db


class MtdtNotFldExc(Exception):
    """
    A custom exception when a metadata mandatory widget is not filled.
    """

    pass


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
        :type nf_nvl: tuple
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
            self.mc.get_con_info()[self.mc.db_str])

        self.settings = QSettings(self.org, self.app_name)

        # OS.NINA
        # clear setting for development purposes
        self.settings.clear()

        self.setWindowTitle(self.app_name)

        self.language = 'Latin'

        self.species_names = {
            'Latin': 'scientificName',
            'English': 'vernacularName',
            'Norwegian': 'vernacularName_NO',
            'Swedish': 'vernacularName_SE',
            'Finish': 'vernacularName_FI'}

        self.loctp_dict = {
            u'Norwegian VatnLnr': 'no_vatn_lnr',
            u'coordinates UTM32': 25832,
            u'coordinates UTM33': 25833,}

        self.loctp_list = [
            'Norwegian VatnLnr',
            'coordinates UTM32',
            'coordinates UTM33']

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

        self.dtstrt_de.setDate(self.today_dt)
        self.dtend_de.setDate(self.today_dt)
        self.verdt_de.setDate(self.nxt_week_dt)
        self.hist_ins_dtstrt_de.setDate(self.fltr_str_dt)
        self.hist_ins_dtend_de.setDate(self.today_dt)
        self.hist_upd_dtstrt_de.setDate(self.fltr_str_dt)
        self.hist_upd_dtend_de.setDate(self.today_dt)

        self.adddtst_btn.clicked.connect(self._open_dtst_dlg)
        self.addprj_btn.clicked.connect(self._open_prj_dlg)
        self.addref_btn.clicked.connect(self._open_ref_dlg)

        self.dtst_cb.activated.connect(self._upd_dtst_lw)
        self.prj_cb.activated.connect(self._upd_prj_lw)
        self.ref_cb.activated.connect(self._upd_ref_lw)

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
            self.dtstrt_de,
            self.dtend_de,
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
            (u'verifiedDate', self.verdt_de)])

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

        self.lake_name_srch_btn.clicked.connect(self._srch_loc)
        self.wb_le.returnPressed.connect(self._srch_loc)

        self.lake_name_load_btn.setEnabled(False)
        self.lake_name_load_btn.clicked.connect(self._load_loc_layer)

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

        self.ins_btn.clicked.connect(self._ins)

        self.occ_mand_wdgs = [
            self.txn_cb,
            self.occstat_cb,
            self.estm_cb]

        self.mtdt_mand_wdgs = [
            self.rcdby_le,
            self.smpp_cb,
            self.dtend_de,
            self.dtst_cb,
            self.prj_cb,
            self.ref_cb]

        self.all_mand_wdgs = self.occ_mand_wdgs + self.mtdt_mand_wdgs
 
        self.set_mand_wdgs(self.all_mand_wdgs)

        # self.main_hspltr.setStretchFactor(0, 1)
        # self.main_hspltr.setStretchFactor(1, 2)
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
                wdg.setStyleSheet(
                    "background-color: {}".format(self.yel_clr.name()))
                wdg.editingFinished.connect(self._chck_state_text)

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
                    raise exc()
            elif isinstance(wdg, QComboBox):
                if wdg.currentText() == self.sel_str:
                    raise exc()
            elif isinstance(wdg, QDateEdit):
                if wdg.styleSheet() != self.mty_str:
                    raise exc()

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

        wb, cntry_code, cnty, muni = self._get_loc_fltrs()

        self.lake_name_load_btn.setEnabled(False)

        locid_list = db.get_loc_by_fltrs(
            self.mc.con, wb, cntry_code, cnty, muni)

        loc_count = len(locid_list)

        if loc_count != 0:
            self.lake_name_load_btn.setEnabled(True)

            self.locid_list = locid_list
        else:
            self.lake_name_load_btn.setEnabled(False)

        self.lake_name_statlbl.setText(
            u'Found {} location(s).'.format(loc_count))

    def _get_val_txt(self, txt, forbi=False):
        """
        Returns a validated text.

        :param txt: A text.
        :type txt: str.
        :param forbi: True to allow forbidden text, False otherwise.
        :type forbi: bool.

        :returns: A filter, None when text is in list of forbidden strings
            or when length of text is zero.
        :rtype: str.
        """

        if forbi == False and txt in self.forbi_str_list:
            val_txt = None
        elif len(txt) == 0:
            val_txt = None
        else:
            val_txt = txt

        return val_txt

    def _get_loc_fltrs(self):
        """
        Returns location filters.
        It is used to filter locations.

        :returns: A tuple containing water body, country code, county
            and municipality.
        :rtype: tuple.
        """

        wb = self._get_wb()
        cntry_code = self._get_cntry_code()
        cnty = self._get_cnty()
        muni = self._get_muni()

        return (wb, cntry_code, cnty, muni)

    def _get_wb(self):
        """
        Returns a water body from water body line edit.
        Returns None when there is no text in the line edit.

        :returns: A water body, None when there is no text in the line edit.
        :rtype: str.
        """

        txt = self.wb_le.text()

        wb = self._get_val_txt(txt)

        return wb

    def _get_cntry_code(self):
        """
        Returns a country code from country code combo box.

        :returns: A country code, None when text is equal to <all> string
            or when length of text is zero.
        :rtype: str.
        """

        txt = self.cntry_code_cb.currentText()

        cntry_code = self._get_val_txt(txt)

        return cntry_code

    def _get_cnty(self):
        """
        Returns a county from county combo box.

        :returns: A county, None when text is equal to <all> string
            or when length of text is zero.
        :rtype: str.
        """

        txt = self.cnty_cb.currentText()

        cnty = self._get_val_txt(txt)

        return cnty

    def _get_muni(self):
        """
        Returns a municipality from municipality combo box.

        :returns: A municipality, None when text is equal to <all> string
            or when length of text is zero.
        :rtype: str.
        """

        txt = self.muni_cb.currentText()

        muni = self._get_val_txt(txt)

        return muni

    def _get_txn(self):
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

        con_info = self.mc.get_con_info()

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

        wb, cntry_code, cnty, muni = self._get_loc_fltrs()

        lyr = QgsVectorLayer(
            uri.uri(),
            u'location-{}-{}-{}-{}'.format(wb, cntry_code, cnty, muni),
            'postgres')

        if lyr.isValid():
            QgsMapLayerRegistry.instance().addMapLayer(lyr)

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
        else:
            self.loc_tbl_sw.setCurrentIndex(1)
            self.coord_cnvs_btn.setEnabled(True)

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
            usr_list.index(self.mc.get_con_info()[self.mc.usr_str]))

    def _fill_hist_tbls(self):
        """
        Fills all history tables.
        """

        usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end = \
            self._get_hist_fltrs()

        for tbl, fnc in self.hist_tbls_fnc_dict.items():
            tbl_list, tbl_hdrs = fnc(
                self.mc.con,
                usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end)
            self._create_tbl_hist_tab(tbl, tbl_list, tbl_hdrs)

    def _get_hist_fltrs(self):
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
 
        :param item: A changed item.
        :type item: QTableWidgetItem.
        """

        chck_state = par.checkState(0)

        for i in range(par.childCount()):
            chld = par.child(i)
            chld.setCheckState(0, chck_state)

            self._upd_txncvg_tw_chldn(chld)

    def _ins(self):
        """
        Insert the data into the database.
        """

        try:
            loc_id_list = self._get_loc()

            self.chck_mand_wdgs(self.mtdt_mand_wdgs, MtdtNotFldExc)
            self._chck_occ_tbl()

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
                    self.mc.get_con_info()[self.mc.usr_str])

                # OS.NINA
                # does not work now
                # self._ins_txncvg(event_id)

                for m in range(self.occ_tbl.rowCount()):
                    occ_id = uuid.uuid4()

                    occ_row_list = self._get_occ_row_list(m)

                    txn =  occ_row_list[0]

                    if txn == None:
                        self.occ_tbl.selectRow(m)
                        raise OccNotFldExc()

                    txn_id = db.get_txn_id(self.mc.con, txn)

                    ectp = occ_row_list[1]    
                    ectp_id = db.get_ectp_id(self.mc.con, ectp)

                    db.ins_occ(
                        self.mc.con,
                        occ_id, txn_id, ectp_id, occ_row_list, event_id)

                    db.ins_occ_log(
                        self.mc.con,
                        occ_id, event_id, dtst_id, prj_id, ref_id, loc_id,
                        self.mc.get_con_info()[self.mc.usr_str])

            QMessageBox.information(self, u'Saved', u'Data correctly saved.')
        except NoLocExc:
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
        except MtdtNotFldExc:
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
                wdg_data = wdg.date().toPyDate()
            elif isinstance(wdg, QPlainTextEdit):
                txt = wdg.toPlainText()
                wdg_data = self._get_val_txt(txt, forbi)

            wdg_list.append(wdg_data)

        return wdg_list

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

        for txn in self._get_ckd_txns():
            txn_id = db.get_txn_id(self.mc.con, txn)

            db.ins_txncvg(self.mc.con, txn_id, event_id)

    def _get_ckd_txns(self):
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

        loc_input_list = self._get_loc_input_list(loctp)

        if loctp == 'Norwegian VatnLnr':
            locs_tpl = tuple([nvl for loc in loc_input_list for nvl in loc])

            loc_id_nvl_list = db.get_loc_id_nvl_list(self.mc.con, locs_tpl)

            # check if all codes were found
            if len(loc_id_nvl_list) != len(locs_tpl):
                loc_nvl_list = [l[1] for l in loc_id_nvl_list]

                nf_nvl = tuple(set(locs_tpl) - set(loc_nvl_list))

                raise NvlNfExc(nf_nvl)

            loc_id_list = [l[0] for l in loc_id_nvl_list]
        else:
            loc_id_list = []

            for loc in loc_input_list:
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
                        self.mc.get_con_info()[self.mc.usr_str])

                loc_id_list.append(loc_id)

        return loc_id_list

    def _get_loc_input_list(self, loctp):
        """
        Return a list of location inputs.

        :param loctp: A location type.
        :type loctp: str.

        :returns: A list of location inputs.
        :rtype: list.
        """

        loc_input_list = []

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

        return loc_input_list

    def _chck_occ_tbl(self):
        """
        Checks if all rows in the occurrence are filled.
        """

        for m in range(self.occ_tbl.rowCount()):
            occ_row_list = self._get_occ_row_list(m)

            if occ_row_list[0] == None:
                self.occ_tbl.selectRow(m)
                raise OccNotFldExc()

    def upd_dtst(self, dtst_id_name=None):
        """
        Updates a dataset according to the last selected.
        
        :param dtst_id_name: A dataset ID and name "<datasetID> - <name>".
        :type dtst_id_name: str.
        """

        if not dtst_id_name:
            dtst_id_name = self.settings.value('dtst_str')

        if dtst_id_name:
            dtst_cb_index = self.dtst_cb.findText(dtst_id_name)
            self.dtst_cb.setCurrentIndex(dtst_cb_index)
        else:
            dtst_id_name = self.dtst_cb.currentText()

        self._upd_dtst_lw(dtst_id_name)

    def _upd_dtst_lw(self, dtst_id_name):
        """
        Updates the dataset list widget according to the current or last
        dataset.

        :param dtst_id_name: A dataset ID and name "<datasetID> - <name>".
        :type dtst_id_name: str.
        """

        if isinstance(dtst_id_name, int):
            dtst_id_name = self.dtst_cb.currentText()

        self.dtst_lw.clear()

        if dtst_id_name in self.forbi_str_list:
            dtst_txt = dtst_id_name
        else:
            dtst_id = dtst_id_name.split(self.dash_split_str)[0]

            cur, dtst = db.get_dtst_info(self.mc.con, dtst_id)

            for idx, dtst_data in enumerate(dtst):
                dtst_item = QListWidgetItem(
                    u'{}: {}'.format(cur.description[idx][0], dtst_data))
                self.dtst_lw.addItem(dtst_item)

            dtst_txt = dtst[1]
    
        self._set_mtdt_item_text(
            2, u'{}{}{}'.format(self.dtst_str, self.dash_split_str, dtst_txt))

        self.settings.setValue('dtst_str', dtst_id_name)

    def _set_mtdt_item_text(self, item_index, text):
        """
        Sets metadata item text.

        :param item_index: An Item index.
        :type item_index: int.
        :param text: A text.
        :type text: str.
        """

        self.main_tb.setItemText(item_index, text)

    def upd_prj(self, prj_str=None):
        """
        Updates a project according to the last selected.
        
        :param prj_str: A project string "<name> - <organisation>".
        :type prj_str: str.
        """

        if not prj_str:
            prj_str = self.settings.value('prj_str')

        if prj_str:
            proj_cb_index = self.prj_cb.findText(prj_str)
            self.prj_cb.setCurrentIndex(proj_cb_index)
        else:
            prj_str = self.prj_cb.currentText()

        self._upd_prj_lw(prj_str)

    def _upd_prj_lw(self, prj_str):
        """
        Updates the project list widget according to the current or last
        project.
        
        :param prj_str: A project string "<name> - <organisation>".
        :type prj_str: str.
        """

        if isinstance(prj_str, int):
            prj_str = self.prj_cb.currentText()

        self.prj_lw.clear()

        if prj_str in self.forbi_str_list:
            mtdt_txt = prj_str
        else:
            prj_name, prj_org = db.get_prj_name_org_from_str(prj_str)

            cur, prj = db.get_prj_info(self.mc.con, prj_name, prj_org)

            for idx, prj_data in enumerate(prj):
                prj_item = QListWidgetItem(
                    u'{}: {}'.format(cur.description[idx][0], prj_data))
                self.prj_lw.addItem(prj_item)

            mtdt_txt = prj_str

        self._set_mtdt_item_text(
            3, u'{}{}{}'.format(self.prj_str, self.dash_split_str, mtdt_txt))

        self.settings.setValue('prj_str', prj_str)

    def upd_ref(self, ref_str=None):
        """
        Updates a reference according to the last selected.
        """

        if not ref_str:
            ref_str = self.settings.value('ref_str')

        if ref_str:
            ref_cb_index = self.ref_cb.findText(ref_str)
            self.ref_cb.setCurrentIndex(ref_cb_index)
        else:
            ref_str = self.ref_cb.currentText()

        self._upd_ref_lw(ref_str)

    def _upd_ref_lw(self, ref_str):
        """
        Updates the reference list widget according to the current or last
        reference.
        
        :param ref_str: A reference author title and ID
            "<author>: <title> (<year>) @<ID>".
        :type ref_str: str.
        """

        if isinstance(ref_str, int):
            ref_str = self.ref_cb.currentText()

        self.ref_lw.clear()

        if ref_str in self.forbi_str_list:
            mtdt_txt = ref_str
        else:
            ref_au = ref_str.split(u': ')[0]
            ref_yr = ref_str.split(u' (')[1].split(u') ')[0]
            ref_ttl = ref_str.split(u': ')[1].split(u' (')[0]
            ref_id = ref_str.split(self.at_split_str)[1]

            cur, ref = db.get_ref_info(self.mc.con, ref_id)

            for idx, ref_data in enumerate(ref):
                ref_item = QListWidgetItem(
                    u'{}: {}'.format(cur.description[idx][0], ref_data))
                self.ref_lw.addItem(ref_item)

            mtdt_txt = u'{}{}{}{}{}'.format(
                ref_au,
                self.dash_split_str,
                ref_yr,
                self.dash_split_str,
                ref_ttl)

        self._set_mtdt_item_text(
            4, u'{}{}{}'.format(self.ref_str, self.dash_split_str, mtdt_txt))

        self.settings.setValue('ref_str', ref_str)

    def _get_db_cur(self):
        """
        Returns a database cursor.
        
        :returns: A database cursor.
        :rtype: psycopg2.cursor.
        """

        return self.mc.con.cursor()

    def fetch_nofa_schema(self):
        """
        Fetches data from the NOFA schema and populates widgets.
        """

        nofa_cb_dict = self._get_nofa_cb_dict()

        self.pop_cb(nofa_cb_dict)

        self.upd_dtst()
        self.upd_prj()
        self.upd_ref()

        self._pop_txncvg_tw()

    def pop_cb(self, cb_dict):
        """
        Populates combo boxes.

        :param cb_dict: A combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
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

        cnty_cb_dict = self._get_cnty_cb_dict()

        self.pop_cb(cnty_cb_dict)

    def _pop_muni_cb(self):
        """
        Populates the municipality combo box according to the currently
        selected country and county.
        """

        muni_cb_dict = self._get_muni_cb_dict()

        self.pop_cb(muni_cb_dict)

    def _pop_ectp_cb(self):
        """
        Populates the ecotype combo box according to the currently selected
        taxon.
        """

        ectp_cb_dict = self._get_ectp_cb_dict()

        self.pop_cb(ectp_cb_dict)

    def pop_dtst_cb(self):
        """
        Populates the dataset combo box.
        """

        dtst_cb_dict = self._get_dtst_cb_dict()

        self.pop_cb(dtst_cb_dict)

    def pop_prj_cb(self):
        """
        Populates the project combo box.
        """

        prj_cb_dict = self._get_prj_cb_dict()

        self.pop_cb(prj_cb_dict)

    def pop_ref_cb(self):
        """
        Populates the reference combo box.
        """

        ref_cb_dict = self._get_ref_cb_dict()

        self.pop_cb(ref_cb_dict)

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

    def _get_nofa_cb_dict(self):
        """
        Returns a nofa combo box dictionary.

        :returns: A nofa combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        nofa_cb_dict = {
            self.loctp_cb: [
                self._get_loctp_list,
                [],
                'Norwegian VatnLnr'],
            self.cntry_code_cb:[
                db.get_cntry_code_list,
                [self.mc.con],
                self.all_str],
            self.smpp_cb: [
                db.get_smpp_list,
                [self.mc.con],
                self.sel_str],
            self.smpsu_cb: [
                db.get_smpsu_list,
                [self.mc.con],
                self.sel_str],
            self.relia_cb: [
                db.get_reliab_list,
                [self.mc.con],
                self.mty_str],
            self.prj_cb: [
                db.get_prj_list,
                [self.mc.con],
                self.sel_str],
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
            self._get_cnty_cb_dict(),
            self._get_muni_cb_dict(),
            self._get_ectp_cb_dict(),
            self._get_dtst_cb_dict(),
            self._get_prj_cb_dict(),
            self._get_ref_cb_dict(),
            self._get_occ_mand_cb_dict())

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

    def _get_cnty_cb_dict(self):
        """
        Returns a county combo box dictionary.

        :returns: A county combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        cnty_cb_dict = {
            self.cnty_cb: [
                db.get_cnty_list,
                [self.mc.con, self._get_cntry_code()],
                self.all_str]}

        return cnty_cb_dict

    def _get_muni_cb_dict(self):
        """
        Returns a municipality combo box dictionary.

        :returns: A municipality combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        muni_cb_dict = {
            self.muni_cb: [
                db.get_muni_list,
                [self.mc.con, self._get_cntry_code(), self._get_cnty()],
                self.all_str]}

        return muni_cb_dict

    def _get_ectp_cb_dict(self):
        """
        Returns an ecotype combo box dictionary.

        :returns: An ecotype combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        ectp_cb_dict = {
            self.ectp_cb: [
                db.get_ectp_list,
                [self.mc.con, self._get_txn()],
                self.mty_str]}

        return ectp_cb_dict

    def _get_dtst_cb_dict(self):
        """
        Returns a dataset combo box dictionary.

        :returns: An dataset combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        dtst_cb_dict = {
            self.dtst_cb: [
                db.get_dtst_list,
                [self.mc.con],
                self.sel_str]}

        return dtst_cb_dict

    def _get_prj_cb_dict(self):
        """
        Returns a project combo box dictionary.

        :returns: An project combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        prj_cb_dict = {
            self.prj_cb: [
                db.get_prj_list,
                [self.mc.con],
                self.sel_str]}

        return prj_cb_dict

    def _get_ref_cb_dict(self):
        """
        Returns a reference combo box dictionary.

        :returns: An reference combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        ref_cb_dict = {
            self.ref_cb: [
                db.get_ref_list,
                [self.mc.con],
                self.sel_str]}

        return ref_cb_dict

    def _get_occ_mand_cb_dict(self):
        """
        Returns an occurrence mandatory combo box dictionary.

        :returns: An occurrence mandatory combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
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

        id = dtst_str.split(self.dash_split_str)[0]

        return id

    def _get_prj_id(self):
        """
        Returns a project ID based on name and organization.

        :returns: A project ID.
        :rtype: str.
        """

        prj_str = self.prj_cb.currentText()

        prj_name, prj_org = db.get_prj_name_org_from_str(prj_str)

        prj_id = db.get_prj_id(self.mc.con, prj_name, prj_org)

        return prj_id

    def _get_ref_id(self):
        """
        Returns a reference ID from the reference combo box.

        :returns: A reference ID.
        :rtype: str.
        """

        ref_str = self.ref_cb.currentText()

        id = int(ref_str.split(self.at_split_str)[1])

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
        loctp_list = self.loctp_list
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
        :param tbl_hdrs: Table headers.
        :type tbl_hdrs: tuple.
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
        Updates an occurrence row according to the values in the occurrence
        widgets.
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
            self._rst_occ_mand_cb()
            self._upd_occ_row()

    def _rst_occ_row(self):
        """
        Resets a current occurrence row in the occurrence table.
        """

        for wdg in self.occ_tbl_hdrs_wdg_dict.values():
            if isinstance(wdg, QLineEdit):
                wdg.clear()
            elif isinstance(wdg, QComboBox):
                wdg.setCurrentIndex(0)
            elif isinstance(wdg, QDateEdit):
                wdg.setDate(self.nxt_week_dt)

        self._rst_occ_mand_cb()
        self._upd_occ_row()

    def _rst_occ_mand_cb(self):
        """
        Resets occurrence mandatory combo boxes.
        """

        occ_mand_cb_dict = self._get_occ_mand_cb_dict()

        for cb, cb_list in occ_mand_cb_dict.items():
            def_val = cb_list[2]
            cb.setCurrentIndex(cb.findText(def_val))

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

        for n, wdg in enumerate(self.occ_tbl_hdrs_wdg_dict.values()):
            text = self.occ_tbl.item(m, n).text()

            if isinstance(wdg, QLineEdit):
                wdg.setText(text)
            elif isinstance(wdg, QComboBox):
                idx = wdg.findText(text)
                wdg.setCurrentIndex(idx)
            elif isinstance(wdg, QDateEdit):
                wdg.setDate(QDate.fromString(text, 'yyyy-MM-dd'))

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
