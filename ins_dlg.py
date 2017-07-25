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
        email                : matteo.destefano@nina.no
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

from PyQt4.QtCore import (
    QSettings, QTranslator, qVersion, QCoreApplication, Qt, QObject, QDate)
from PyQt4.QtGui import (
    QAction, QIcon, QMessageBox, QTreeWidgetItem, QListWidgetItem, QTableWidget,
    QTableWidgetItem, QColor, QFont, QCompleter, QLineEdit, QDialog,
    QDoubleValidator, QIntValidator, QComboBox, QLineEdit, QDateEdit)

from qgis.core import *

import resources

from nofa import con_dlg, dtst_dlg, prj_dlg, ref_dlg

from preview_dialog import PreviewDialog

from collections import defaultdict
import os.path
import psycopg2, psycopg2.extras
import logging
import datetime
import uuid
import sys
import os


class NoLocationException(Exception):
    """
    A custom exception when no location is provided.
    """

    pass



from PyQt4 import QtGui, uic

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'nofa_insert_dialog_base.ui'))


class InsDlg(QtGui.QDialog, FORM_CLASS):
    def __init__(self, iface, mc):
        """Constructor."""
        super(InsDlg, self).__init__()
        # Set up the user interface from Designer.
        # After setupUI you can access any designer object by doing
        # self.<objectname>, and you can use autoconnect slots - see
        # http://qt-project.org/doc/qt-4.8/designer-using-a-ui-file.html
        # #widgets-and-dialogs-with-auto-connect
        self.setupUi(self)

        self.iface = iface
        self.mc = mc

        self.org = u'NINA'
        self.app_name = u'NOFAInsert'

        self.settings = QSettings(self.org, self.app_name)

        self.sel_str = u'Select'
        self.none_str = str(None)

        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&NOFAInsert')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(self.app_name)
        self.toolbar.setObjectName(self.app_name)

        self.today = datetime.datetime.today().date()
        self.year = datetime.datetime.today().year
        self.nxt_week = self.today + datetime.timedelta(days=7)

        self.dtstrt_de.setDate(self.today)
        self.dtend_de.setDate(self.today)
        self.verdt_de.setDate(self.nxt_week)

        self.dataset_name = "none"

        self.insert_location = \
            """
            INSERT INTO     nofa.location (
                                locationID,
                                "locationType",
                                geom,
                                "waterBody",
                                "locationRemarks")
            VALUES          (%s, %s, %s, %s, %s);
            """

        self.insert_taxonomic_coverage = \
            """
            INSERT INTO     nofa.taxonomicCoverage(
                                "taxonID_l_taxon",
                                "eventID_observationEvent")
            VALUES          (%s,%s);
            """
        # creating the string for event data insertion to nofa.event table. fieldNotes is used just for testing purposes

        self.insert_log_occurrence = \
            """
            INSERT INTO     nofa.plugin_occurrence_log (
                                "occurrence_id",
                                "event_id",
                                "dataset_id",
                                "project_id",
                                "reference_id",
                                "location_id",
                                "test",
                                "username")
            VALUES\n
            """

        self.insert_log_dataset_columns = u""" "dataset_id", "test", "username" """

        self.insert_log_project_columns = u""" "project_id", "test", "username" """

        self.insert_log_reference_columns = u""" "reference_id", "test", "username" """

        self.insert_log_location_columns = u""" "location_id", "test", "username", "location_name" """

        self.log_occurrence_values = u'(%s,%s,%s,%s,%s,%s,%s,%s)'

        self.log_dataset_values = u'(%s,%s,%s)'

        self.log_project_values = u'(%s,%s,%s)'

        self.log_reference_values = u'(%s,%s,%s)'

        self.log_location_values = u'(%s,%s,%s,%s)'

        self.language = 'Latin'

        self.species_names = {
            'Latin': 'scientificName',
            'English': 'vernacularName',
            'Norwegian': 'vernacularName_NO',
            'Swedish': 'vernacularName_SE',
            'Finish': 'vernacularName_FI'}

        ## Country codes not used for the moment
        '''countryCodes = {
            'Latin': None,
            'English': None,
            'Norwegian': 'NO',
            'Swedish': 'SE',
            'Finish': 'FI'}'''

        #TODO the remaining location types should be added here
        self.loctp_dict = {
            'Norwegian VatnLnr': 'no_vatn_lnr',
            'coordinates UTM32': 25832,
            'coordinates UTM33': 25833,}

        self.loctp_list = [
            'Norwegian VatnLnr',
            'coordinates UTM32',
            'coordinates UTM33']

        self.occurrence_base = {
            'taxon': 'Select',
            'ecotype': 'Select',
            'quantity': 'Select',
            'metric': 0,
            'status': 'unknown',
            'trend': 'unknown',
            'oc_remarks': 'None',
            'est_means': 'Select',
            'est_remarks': 'None',
            'spawn_con': 'unknown',
            'spawn_loc': 'unknown',
            'verified_by': 'Nobody',
            'verified_date': self.today}

        self.occurrence = {
            'taxon': ['Select', ],
            'ecotype': ['Select', ],
            'quantity': ['Select', ],
            'metric': [0, ],
            'status': ['Select', ],
            'trend': ['unknown', ],
            'oc_remarks': ['None', ],
            'est_means': ['Select', ],
            'est_remarks': ['None', ],
            'spawn_con': ['unknown', ],
            'spawn_loc': ['unknown', ],
            'verified_by': ['Nobody', ],
            'verified_date': [self.today, ]}

        self.taxonomicc = []

        self.event = {
            'protocol': 'unknown',
            'size_value': 'None',
            'size_unit': 'metre',
            'effort': 'unknown',
            'protocol_remarks': 'None',
            'date_start': self.today,
            'date_end': self.today,
            'recorded_by': 'unknown',
            'event_remarks': 'None',
            'reliability': 'Select'}

        self.occ_hdrs = [
            "occurrence_id",
            "event_id",
            "dataset_id",
            "project_id",
            "reference_id",
            "location_id",
            "username",
            "insert_time",
            "update_time"]

        self.loc_hdrs = [
            "dataset_id",
            "username",
            "location_name",
            "insert_time",
            "update_time"]

        self.dtst_hdrs = [
            "dataset_id",
            "username",
            "insert_time",
            "update_time"]

        self.prj_hdrs = [
            "project_id",
            "username",
            "insert_time",
            "update_time"]

        self.ref_hdrs = [
            "reference_id",
            "username",
            "insert_time",
            "update_time"]

        self.dash_split_str = u' - '
        self.at_split_str = u'@'
        self.dtst_str = u'Dataset'
        self.prj_str = u'Project'
        self.ref_str = u'Reference'

        self.adddtst_btn.clicked.connect(self._open_dtst_dlg)
        self.addprj_btn.clicked.connect(self._open_prj_dlg)
        self.addref_btn.clicked.connect(self._open_ref_dlg)

        self.dtst_cb.activated.connect(self._upd_dtst_lw)
        self.prj_cb.activated.connect(self._upd_prj_lw)
        self.ref_cb.activated.connect(self._upd_ref_lw)

        self.occ_tbl.currentItemChanged.connect(self._upd_occ_gb_at_selrow)
        self.rowup_btn.clicked.connect(self._sel_row_up)
        self.rowdwn_btn.clicked.connect(self._sel_row_dwn)
        self.addocc_btn.clicked.connect(self._add_occ_row)
        self.delocc_btn.clicked.connect(self._del_occ_row)

        # trigger action when history tabs are clicked
        self.tabWidget.currentChanged.connect(self.history_tab_clicked)
        self.tabWidget_history.currentChanged.connect(self.history_tab_clicked)

        # OS.NINA
        # there are not neccessary tables in the new db
        # history tab is disabled
        self.tabWidget.setTabEnabled(1, False)

        self.txn_cb.currentIndexChanged.connect(self._pop_ectp_cb)

        self.ins_btn.clicked.connect(self._ins)

        # filter occurrences by username and time interval
        self.username_filter_button.clicked.connect(self.filter_occurrences_by_username)
        self.time_filter_button.clicked.connect(self.filter_occurrence_by_time)
        self.combined_filter_button.clicked.connect(self.filter_by_user_and_time)

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
            self.rcdby_le,
            self.eventrmk_le,
            self.relia_cb]

        self.occ_input_wdgs = [
            self.txn_cb,
            self.ectp_cb,
            self.oqt_cb,
            self.oq_le,
            self.occstat_cb,
            self.poptrend_cb,
            self.occrmk_le,
            self.estm_cb,
            self.estrmk_le,
            self.spwnc_cb,
            self.spwnl_cb,
            self.vfdby_le,
            self.verdt_de]

        self.occ_le_wdgs = []
        self.occ_cb_wdgs = []
        self.occ_de_wdgs = []

        for wdg in self.occ_input_wdgs:
            if isinstance(wdg, QLineEdit):
                self.occ_le_wdgs.append(wdg)
            elif isinstance(wdg, QComboBox):
                self.occ_cb_wdgs.append(wdg)
            elif isinstance(wdg, QDateEdit):
                self.occ_de_wdgs.append(wdg)

        for occ_le_wdg in self.occ_le_wdgs:
            occ_le_wdg.textChanged.connect(self._upd_occ_row)

        for occ_cb_wdg in self.occ_cb_wdgs:
            occ_cb_wdg.activated.connect(self._upd_occ_row)

        for occ_de_wdg in self.occ_de_wdgs:
            occ_de_wdg.dateChanged.connect(self._upd_occ_row)

    def tr(self, message):
        """Get the translation for a string using Qt translation API.

        We implement this ourselves since we do not inherit QObject.

        :param message: String for translation.
        :type message: str, QString

        :returns: Translated version of message.
        :rtype: QString
        """
        # noinspection PyTypeChecker,PyArgumentList,PyCallByClass
        return QCoreApplication.translate('NOFAInsert', message)

    def history_tab_clicked(self):
        #QMessageBox.information(None, "DEBUG:",  str(self.tabWidget.currentIndex()))

        if self.tabWidget_history.currentIndex() == 0:
            #QMessageBox.information(None, "DEBUG:", str(self.tabWidget.currentIndex()))

            self.date_from.setDate(self.today)
            self.date_to.setDate(self.today)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  DISTINCT "username" FROM nofa.plugin_occurrence_log')
            except:
                QMessageBox.information(
                    None, "DEBUG:",
                    unicode(
                        "WARNING - DB ERROR. occurrences not fetched from db"))

            usernames_fetched = cur.fetchall()

            username_list = [s[0] for s in usernames_fetched]

            # Inject sorted python-list for spawningCondition into UI
            username_list.sort()
            self.usernames.clear()
            self.usernames.addItems(username_list)



            self.row = 0

            self.occ_tbl_occurrences.setSelectionBehavior(QTableWidget.SelectRows)

            #  populate tableWidget

            cur = self._get_db_cur()
            try:
                cur.execute(u'SELECT  "occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_occurrence_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. occurrences not fetched from db"))

            fetched_occ = cur.fetchall()

            lim = len(fetched_occ)

            self.occ_tbl_occurrences.setRowCount(lim)
            self.occ_tbl_occurrences.setColumnCount(9)

            self.occ_tbl_occurrences.setHorizontalHeaderLabels(
                self.occ_hdrs)

            for l in range(lim):
                occurrence = fetched_occ[l]
                for n, item in enumerate(occurrence):


                    newitem = QTableWidgetItem(unicode(occurrence[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.occ_tbl_occurrences.setItem(l, n, newitem)

        elif self.tabWidget_history.currentIndex() == 1:
            # add locations log entries to history -> locations
            self.occ_tbl_locations.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "location_id", "username", "location_name", "insert_timestamp", "update_timestamp" FROM nofa.plugin_location_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. location logs not fetched from db"))

            fetched_location_logs = cur.fetchall()

            lim = len(fetched_location_logs)

            self.occ_tbl_locations.setRowCount(lim)
            self.occ_tbl_locations.setColumnCount(5)

            self.occ_tbl_locations.setHorizontalHeaderLabels(
                self.loc_hdrs)

            for l in range(lim):
                locations = fetched_location_logs[l]
                for n, item in enumerate(locations):

                    newitem = QTableWidgetItem(unicode(locations[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.occ_tbl_locations.setItem(l, n, newitem)

        elif self.tabWidget_history.currentIndex() == 2:
            self.occ_tbl_datasets.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "dataset_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_dataset_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. datasets not fetched from db"))

            fetched_datasets = cur.fetchall()

            lim = len(fetched_datasets)

            self.occ_tbl_datasets.setRowCount(lim)
            self.occ_tbl_datasets.setColumnCount(4)

            self.occ_tbl_datasets.setHorizontalHeaderLabels(
                self.dtst_hdrs)

            for l in range(lim):
                dataset = fetched_datasets[l]
                for n, item in enumerate(dataset):

                    newitem = QTableWidgetItem(unicode(dataset[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.occ_tbl_datasets.setItem(l, n, newitem)

        elif self.tabWidget_history.currentIndex() == 3:

            self.occ_tbl_projects.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "project_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_project_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. projects not fetched from db"))

            fetched_projects = cur.fetchall()

            lim = len(fetched_projects)

            self.occ_tbl_projects.setRowCount(lim)
            self.occ_tbl_projects.setColumnCount(4)

            self.occ_tbl_projects.setHorizontalHeaderLabels(
                self.prj_hdrs)

            for l in range(lim):
                projects = fetched_projects[l]
                for n, item in enumerate(projects):
                    newitem = QTableWidgetItem(unicode(projects[n]))

                    # setItem(row, column, QTableWidgetItem)
                    self.occ_tbl_projects.setItem(l, n, newitem)

        elif self.tabWidget_history.currentIndex() == 4:

            self.occ_tbl_references.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "reference_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_reference_log')
            except:
                pass

            fetched_references = cur.fetchall()

            lim = len(fetched_references)

            self.occ_tbl_references.setRowCount(lim)
            self.occ_tbl_references.setColumnCount(4)

            self.occ_tbl_references.setHorizontalHeaderLabels(
                self.ref_hdrs)

            for l in range(lim):
                references = fetched_references[l]
                for n, item in enumerate(references):
                    newitem = QTableWidgetItem(unicode(references[n]))

                    # setItem(row, column, QTableWidgetItem)
                    self.occ_tbl_references.setItem(l, n, newitem)

    def filter_occurrences_by_username(self):

        username = self.usernames.currentText()

        cur = self._get_db_cur()

        try:
            cur.execute(
                '''
                SELECT      "occurrence_id",
                            "event_id",
                            "dataset_id",
                            "project_id",
                            "reference_id",
                            "location_id",
                            "username",
                            "insert_timestamp",
                            "update_timestamp"
                FROM         nofa.plugin_occurrence_log
                WHERE        "username" = %s''',
                (username,))
        except:
            QMessageBox.information(
                None, "DEBUG:",
                unicode("WARNING - DB ERROR. occurrences not fetched from db"))

        fetched_occ = cur.fetchall()

        lim = len(fetched_occ)

        self.occ_tbl_occurrences.setRowCount(lim)
        self.occ_tbl_occurrences.setColumnCount(9)

        self.occ_tbl_occurrences.setHorizontalHeaderLabels(
            self.occ_hdrs)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.occ_tbl_occurrences.setItem(l, n, newitem)

    def filter_occurrence_by_time(self):

        time_from = self.date_from.date()
        time_to = self.date_to.date()

        cur = self._get_db_cur()

        try:
            cur.execute(
                '''
                SELECT      "occurrence_id",
                            "event_id",
                            "dataset_id",
                            "project_id",
                            "reference_id",
                            "location_id",
                            "username",
                            "insert_timestamp",
                            "update_timestamp"
                FROM        nofa.plugin_occurrence_log
                WHERE       "insert_timestamp" BETWEEN %s AND %s''',
                (time_from.toPyDate(), time_to.toPyDate(),))
        except:
            QMessageBox.information(
                None, "DEBUG:",
                unicode("WARNING - DB ERROR. occurrences not fetched from db"))

        fetched_occ = cur.fetchall()

        lim = len(fetched_occ)

        self.occ_tbl_occurrences.setRowCount(lim)
        self.occ_tbl_occurrences.setColumnCount(9)

        self.occ_tbl_occurrences.setHorizontalHeaderLabels(
            self.occ_hdrs)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.occ_tbl_occurrences.setItem(l, n, newitem)

    def filter_by_user_and_time(self):

        username = self.usernames.currentText()

        time_from = self.date_from.date()
        time_to = self.date_to.date()

        cur = self._get_db_cur()

        try:
            cur.execute(
                '''
                SELECT      "occurrence_id",
                            "event_id",
                            "dataset_id",
                            "project_id",
                            "reference_id",
                            "location_id",
                            "username",
                            "insert_timestamp",
                            "update_timestamp" '
                FROM        nofa.plugin_occurrence_log
                WHERE       "username" = %s AND "insert_timestamp"
                            BETWEEN %s AND %s
                ''',
                (username, time_from.toPyDate(), time_to.toPyDate(),))
        except:
            QMessageBox.information(
                None, "DEBUG:",
                unicode("WARNING - DB ERROR. occurrences not fetched from db"))

        fetched_occ = cur.fetchall()

        lim = len(fetched_occ)

        self.occ_tbl_occurrences.setRowCount(lim)
        self.occ_tbl_occurrences.setColumnCount(9)

        self.occ_tbl_occurrences.setHorizontalHeaderLabels(
            self.occ_hdrs)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.occ_tbl_occurrences.setItem(l, n, newitem)

    def _open_dtst_dlg(self):
        """
        Opens a dialog for adding a new dataset.
        """

        self.dtst_dlg = dtst_dlg.DtstDlg(self)
        self.dtst_dlg.show()

    def _open_prj_dlg(self):
        """
        Opens a dialog for adding a new project.
        """

        self.prj_dlg = prj_dlg.PrjDlg(self)
        self.prj_dlg.show()

    def _open_ref_dlg(self):
        """
        Opens a dialog for adding a new reference.
        """

        self.ref_dlg = ref_dlg.RefDlg(self)
        self.ref_dlg.show()

    def _ins(self):
        """
        Insert the data into the database.
        """

        try:
            loc_id_list = self._get_loc()
    
            event_list = self._get_event_list()
    
            dtst_id = self._get_dtst_id()
            prj_id = self._get_prj_id()
    
            for loc_id in loc_id_list:
                event_id = uuid.uuid4()
    
                cur = self._get_db_cur()
                cur.execute(
                    '''
                    INSERT INTO    nofa.event (
                                       "locationID",
                                       "eventID",
                                       "samplingProtocol",
                                       "sampleSizeValue",
                                       "sampleSizeUnit",
                                       "samplingEffort",
                                       "dateStart",
                                       "dateEnd",
                                       "recordedBy",
                                       "eventRemarks",
                                       "reliability",
                                       "datasetID",
                                       "projectID")
                    VALUES         (   %(locationID)s,
                                       %(eventID)s,
                                       %(samplingProtocol)s,
                                       %(sampleSizeValue)s,
                                       %(sampleSizeUnit)s,
                                       %(samplingEffort)s,
                                       %(dateStart)s,
                                       %(dateEnd)s,
                                       %(recordedBy)s,
                                       %(eventRemarks)s,
                                       %(reliability)s,
                                       %(datasetID)s,
                                       %(projectID)s)
                    ''',
                    {'locationID': loc_id,
                     'eventID': event_id,
                     'samplingProtocol': event_list[0],
                     'sampleSizeValue': event_list[1],
                     'sampleSizeUnit': event_list[2],
                     'samplingEffort': event_list[3],
                     'dateStart': event_list[4],
                     'dateEnd': event_list[5],
                     'recordedBy': event_list[6],
                     'eventRemarks': event_list[7],
                     'reliability': event_list[8],
                     'datasetID': dtst_id,
                     'projectID': prj_id})
    
                # self._ins_txncvg(event_id)
    
                for m in range(self.occ_tbl.rowCount()):
                    occ_id = uuid.uuid4()
    
                    occ_row_list = []
    
                    # OS.NINA
                    # depends on the order in the table
                    for n in range(self.occ_tbl.columnCount()):
                        text = self.occ_tbl.item(m, n).text()
    
                        occ_row_list.append(text)
    
                    txn =  occ_row_list[0]
    
                    cur = self._get_db_cur()
                    cur.execute(
                        '''
                        SELECT      "taxonID"
                        FROM        nofa."l_taxon"
                        WHERE       "scientificName" = %s
                        ''',
                        (txn,))
    
                    txn_id = cur.fetchone()[0]
    
                    ectp = occ_row_list[1]
    
                    cur = self._get_db_cur()
                    cur.execute(
                        '''
                        SELECT      "ecotypeID"
                        FROM        nofa."l_ecotype"
                        WHERE       "vernacularName" = %s
                        ''',
                        (ectp,))
    
                    ectp_id = cur.fetchone()[0] if cur.rowcount != 0 else None
    
                    QgsMessageLog.logMessage(str(type(occ_row_list[3])), 'test')
    
                    cur = self._get_db_cur()
                    cur.execute(
                        '''
                        INSERT INTO    nofa."occurrence" (
                                           "occurrenceID",
                                           "taxonID",
                                           "ecotypeID",
                                           "organismQuantityType",
                                           "organismQuantity",
                                           "occurrenceStatus",
                                           "populationTrend",
                                           "occurrenceRemarks",
                                           "establishmentMeans",
                                           "establishmentRemarks",
                                           "spawningCondition",
                                           "spawningLocation",
                                           "verifiedBy",
                                           "verifiedDate",
                                           "modified",
                                           "eventID")
                        VALUES         (   %(occurrenceID)s,
                                           %(taxonID)s,
                                           %(ecotypeID)s,
                                           %(organismQuantityType)s,
                                           %(organismQuantity)s,
                                           %(occurrenceStatus)s,
                                           %(populationTrend)s,
                                           %(occurrenceRemarks)s,
                                           %(establishmentMeans)s,
                                           %(establishmentRemarks)s,
                                           %(spawningCondition)s,
                                           %(spawningLocation)s,
                                           %(verifiedBy)s,
                                           %(verifiedDate)s,
                                           %(modified)s,
                                           %(eventID)s)
                        ''',
                        {'occurrenceID': occ_id,
                         'taxonID': txn_id,
                         'ecotypeID': ectp_id,
                         'organismQuantityType': occ_row_list[2],
                         'organismQuantity': float(occ_row_list[3]) \
                            if len(occ_row_list[3]) != 0 else None,
                         'occurrenceStatus': occ_row_list[4],
                         'populationTrend': occ_row_list[5],
                         'occurrenceRemarks': occ_row_list[6],
                         'establishmentMeans': occ_row_list[7],
                         'establishmentRemarks': occ_row_list[8],
                         'spawningCondition': occ_row_list[9],
                         'spawningLocation': occ_row_list[10],
                         'verifiedBy': occ_row_list[11],
                         'verifiedDate': occ_row_list[12],
                         'modified': datetime.datetime.now(),
                         'eventID': event_id})
    
            QMessageBox.information(self, u'Saved', u'Data correctly saved.')
        except NoLocationException:
            QMessageBox.warning(self, u'No Location', u'Enter a location.')

    def _get_event_list(self):
        """
        Returns the data from event input widgets.

        :returns: A list of data from event input widgets.
        :rtype: list.
        """

        event_list = []

        for wdg in self.event_input_wdgs:

            if isinstance(wdg, QLineEdit):
                if isinstance(wdg.validator, QIntValidator):
                    event_data = int(wdg.text()) \
                        if len(wdg.text()) != 0 else None
                else:
                    event_data = wdg.text() if len(wdg.text()) != 0 else None
            elif isinstance(wdg, QComboBox):
                event_data = wdg.currentText()
            elif isinstance(wdg, QDateEdit):
                event_data = wdg.date().toPyDate()

            event_list.append(event_data)

        return event_list

    def _ins_txncvg(self, eventid):
        """
        Inserts all checked taxons into the database.

        :param eventid: An event ID.
        :type eventid: uuid.UUID.
        """

        for txn in self._get_ckd_txns():
            cur = self._get_db_cur()
            cur.execute(
                '''
                SELECT          "taxonID"
                FROM            nofa."l_taxon"
                WHERE           "scientificName" = '%s'
                '''
                (txn,))
            txnid = cur.fetchone()[0]

            # OS.NINA
            # this query does not work
            # TODO - solve PK 
            cur = self._get_db_cur()
            cur.execute(
                '''
                INSERT INTO     nofa.taxonomicCoverage(
                                    "taxonID_l_taxon",
                                    "eventID_observationEvent")
                VALUES          (%s,%s);
                ''',
                (txnid, eventid))

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
        # OS.NINA
        # add string check
        if len(self.loc_le.text()) != 0:
            locs_tpl = tuple(self.loc_le.text().split(u','))
        else:
            raise NoLocationException()

        # OS.NINA
        # add other location types
        if loctp == 'Norwegian VatnLnr':
            cur = self._get_db_cur()
            cur.execute(
                '''
                SELECT      distinct "locationID" lid
                FROM        nofa.location
                WHERE       "no_vatn_lnr" IN %s
                ORDER BY    lid
                ''',
                (locs_tpl,))
            loc_ids = cur.fetchall()

            loc_id_list = [l[0] for l in loc_ids]

        return loc_id_list

    # OS.NINA
    # it is left here because other location types need to be implemented
    def get_location(self):

        # initialise data and metadata containers:
        self.locations = {'location_ID': [],
                          'location': [],
                          'loc_type': 'Select',
                          'loc_names': [],
                          'x': [],
                          'y': []
                          }

        self.new_locs = []


        locs = self.loc_le.text()
        location_type = self.loctp_cb.currentText()
        #QMessageBox.information(None, "DEBUG:", locations)
        #QMessageBox.information(None, "DEBUG:", location_type)

        #Manage the case of Norwegian VatLnr coordinates input
        if location_type == 'Norwegian VatnLnr':
            locations = locs.split(',')
            col = self.loctp_dict[location_type]

            # Fetch locationIDs (From Stefan's code)
            cur = self._get_db_cur()
            try:
                cur.execute(
                u'SELECT DISTINCT ON ({0}) "locationID", {0}, "waterBody", "decimalLongitude", "decimalLatitude" FROM nofa.location WHERE {0} IN ({1}) ORDER BY {0}, "locationType";'.format(
                    col, u','.join(unicode(l) for l in locations)))
            except:
                QMessageBox.information(None, "DEBUG:", unicode("WARNING - DB ERROR. Did you select the correct type of location identifier?"))
            fetched_locs = cur.fetchall()
            # Create a python-list from query result
            loc_list = [l[1] for l in fetched_locs]
            locID_list = [l[0] for l in fetched_locs]
            loc_names = [l[2] for l in fetched_locs]
            longitudes = [l[3] for l in fetched_locs]
            latitudes = [l[4] for l in fetched_locs]
            #QMessageBox.information(None, "DEBUG:", str(loc_list))
            #QMessageBox.information(None, "DEBUG:", str(locID_list))
            #QMessageBox.information(None, "DEBUG:", str(loc_names))

            coords = []
            #QMessageBox.information(None, "DEBUG:", str("this is loc_list: " + str(loc_list)))
            if len(loc_list) == len(locations):
                for i, loc in enumerate(loc_list):
                    if loc_names[i] is None:
                        loc_names[i] = 'None'
                    self.locations['location_ID'].append(locID_list[i])
                    self.locations['loc_names'].append(loc_names[i])
                    self.locations['x'].append(longitudes[i])
                    self.locations['y'].append(latitudes[i])

                    coords.append(loc_names[i] + ' (' + unicode(longitudes[i]) + ', ' + unicode(latitudes[i]) + ')')

                self.locations['location'] = coords

            else:
                QMessageBox.information(None, "DEBUG:", unicode("WARNING, DB FETCHING ISSUE!"))

        # manage the case of UTM33 coordinates
        elif location_type.startswith('coordinates'):
            type = self.loctp_dict[location_type]
            self.locations['loc_type'] = type
            #QMessageBox.information(None, "DEBUG:", str(type))

            if ';' in locs:
                frags = locs.split(';')
                #QMessageBox.information(None, "DEBUG:", 'elem is : ' + str(frags))
            elif ',' in locs:
                frags = locs.split(',')
                #QMessageBox.information(None, "DEBUG:", 'elem is : ' + str(frags))
            else:
                # make list out of single string in order to stick to the data structure
                frags = [locs]

            coords = []
            # storing the ID of the locations which are exact matches of existing ones
            self.places = []


            #QMessageBox.information(None, "DEBUG:", 'frags = ' + str(frags))

            #walk through all the locations
            for i, elem in enumerate(frags):
                if elem not in (None, ""):
                    #QMessageBox.information(None, "DEBUG:", 'elem is : ' + str(elem))
                    elems = elem.split()
                    #all the locations need to be as: "easting northing location_name"
                    try:
                        easting = elems[0]
                        northing = elems[1]

                        self.locations['x'].append(easting)
                        self.locations['y'].append(northing)

                        x = float(easting)
                        y = float(northing)
                    except:
                        QMessageBox.information(None, "DEBUG:", unicode("WARNIG - problem with easting and northing?"))

                    name = elems[2:]
                    loc_name = ' '.join(name)

                    self.locations['loc_names'].append(loc_name)
                    #coords.append(coordinates)

                    coords.append(loc_name + ' (' + easting + ', ' + northing + ')')
                    #QMessageBox.information(None, "DEBUG:", str(self.locations['x'][i]))

                    cur = self._get_db_cur()
                    srid = type

                    point = "ST_Transform(ST_GeomFromText('POINT({0} {1})', {2}), 25833)".format(x, y, srid)

                    # Query to get the location ID of already existing locations, using distance
                    cur.execute("""SELECT x, y, distance, cat, b."locationID" FROM
                    (SELECT {0} AS x,  {1}  AS y,
                    ST_Distance(geom, {2}) AS distance,
                    * FROM temporary.lakes_nosefi
                    WHERE ST_DWithin(geom, {2}, 0)
                    ORDER BY
                    geom <-> {2}
                    LIMIT 1) AS a,
                    nofa.location AS b
                    WHERE cat = b."waterBodyID"
                    ORDER
                    BY
                    b.geom <-> {2};
                    """.format(x, y, point))

                    loc = cur.fetchone()

                    # Check if a location is already registered in the db. If it is, just get the location ID, and append it to ad-hoc variable, and the locations dict.
                    if loc and loc[2] <= 10 and loc[4]:
                        #QMessageBox.information(None, "DEBUG:", str(loc[4]))
                        self.locations['location_ID'].append(loc[4])
                        self.places.append(loc)
                        placesID = loc[4]
                        #QMessageBox.information(None, "DEBUG:", str(placesID))

                    else:

                        locationID = uuid.uuid4()
                        # location ID added to the locations dict
                        self.locations['location_ID'].append(locationID)

                        #geom = 'MULTIPOINT({0} {1})'.format(x, y)
                        #geom = u"""ST_Transform(ST_GeomFromText('MULTIPOINT({0} {1})', {2}), 25833)""".format(x, y, srid)
                        waterbody = loc_name

                        self.new_locs.append([locationID, x, y, srid, waterbody])

            self.locations['location'] = coords

    # OS.NINA
    # it is left here because adding new location needs to be implemented
    def confirmed(self):
        """
        This method sends the occurrences, events and locations information to NOFA DB
        """

        #QMessageBox.information(None, "DEBUG:", str("new_locs = " + self.new_locs))

        #insert the new location points, if any,  to the db in nofa.location
        if self.new_locs:
            for i, loc in enumerate(self.new_locs):
                cur = self._get_db_cur()
                location_type = 'samplingPoint'

                point = "MULTIPOINT({0} {1})".format(loc[1], loc[2])
                geom_orig = "ST_GeometryFromText('{0}', {1})".format(point, unicode(loc[3]))
                geom = "ST_Transform({}, 25833)".format(geom_orig)

                location_columns = u""" "locationID", "locationType", geom, "waterBody", "locationRemarks" """
                #location_values = '%s, %s, %s, %s, %s'

                insert_location = cur.mogrify(u"""INSERT INTO nofa.location ({0}) VALUES ('{1}', '{2}', {3}::geometry, '{4}', '{5}');""".format(
                    location_columns,
                    loc[0],
                    location_type,
                    geom,
                    unicode(loc[4]),
                    'test'))

                #QMessageBox.information(None, "DEBUG:", insert_location)
                cur.execute(insert_location)

                try:
                    cur = self._get_db_cur()
                    insert_location_log = cur.mogrify("INSERT INTO nofa.plugin_location_log({}) VALUES {}".format(
                        self.insert_log_location_columns,
                        self.log_location_values,
                    ), (loc[0], True, self.username, loc[4]))

                    cur.execute(insert_location_log)

                    #QMessageBox.information(None, "DEBUG:", "new location log record correctly stored in NOFA db")
                except:
                    QMessageBox.information(None, "DEBUG:", unicode('problem inserting the new locations to location log db'))

        # add a new event to nofa.events fore each location
        for i, loc in enumerate(self.locations['location_ID']):
            event_id = uuid.uuid4()

            if self.event['protocol_remarks'] is None:
                QMessageBox.information(None, "DEBUG:", "protocol remarks is empty")
                self.event['protocol_remarks'] = 'None'

            if self.event['size_value'] is None:
                self.event['size_value'] = 0
                size_value = 0
            elif isinstance(self.event['size_value'], unicode):
                if self.event['size_value'] == '':
                    self.event['size_value'] = 0
                    size_value = 0
                else:
                    size_value = int(self.event['size_value'])
            else:
                size_value = 0

            if self.event['recorded_by'] is None:
                self.event['recorded_by'] = 'None'

            if self.event['protocol'] is None:
                self.event['protocol'] = 'None'

            if self.event['event_remarks'] is None:
                self.event['event_remarks'] = 'None'

            start_date = self.event['date_start'].toPyDate()
            end_date = self.event['date_end'].toPyDate()
            #QMessageBox.information(None, "DEBUG:", 'effort type is: ' + str(type(self.event['effort'])))

            if self.event['effort'] is None:
                self.event['effort'] = 0
                effort = self.event['effort']
            elif isinstance(self.event['effort'], unicode):
                try:
                    effort = int(self.event['effort'])
                except:
                    self.event['effort'] = 0
                    effort = self.event['effort']
            elif isinstance(self.event['effort'], unicode):
                try:
                    effort = int(self.event['effort'])
                except:
                    self.event['effort'] = 0
                    effort = self.event['effort']
            else:
                self.event['effort'] = 0
                effort = 0

            dataset = self.dataset['dataset_id']

            # reference is optional. If not existing, defaults to zero
            try:
                reference = int(self.reference['reference_id'])
            except:
                reference = 0



            # check project ID type, and convert to int
            if isinstance(self.project['project_id'], int):
                project = self.project['project_id']
            elif isinstance(self.project['project_id'], unicode):

                try:
                    project = int(self.project['project_id'])
                except:
                    QMessageBox.information(
                        None, "DEBUG:",
                        'The type of project id is wrong. Should be integer')
                    return

            elif isinstance(self.project['project_id'], unicode):
                try:
                    project = int(self.project['project_id'])
                except:
                    QMessageBox.information(
                        None, "DEBUG:", 'Problem with project id')
                    # self.project['project_id'] = 0
                    #project = int(self.project['project_id'])
            #elif self.project['project_id'] is None:
            #   QMessageBox.information(None, "DEBUG:", 'Please select a project')
            #   return

            # get the reliability index from reliability text
            # cur = self._get_db_cur()
            # cur.execute(u'SELECT "reliabilityID" FROM nofa."l_reliability" WHERE "reliability" = %s;',  (self.event['reliability'],))
            # rel = cur.fetchone()
            # QMessageBox.information(None, "DEBUG:", 'reliability index is: ' + str(rel))

            # OS.NINA
            # deleted "samplingProtocolRemarks", associatedReferences"
            insert_event_tmpl = (
                '''
                INSERT INTO    nofa.event (
                                   "locationID",
                                   "eventID",
                                   "sampleSizeValue",
                                   "recordedBy",
                                   "samplingProtocol",
                                   "reliability",
                                   "dateStart",
                                   "dateEnd",
                                   "eventRemarks",
                                   "sampleSizeUnit",
                                   "samplingEffort",
                                   "datasetID",
                                   "projectID",
                                   "fieldNotes")
                VALUES         (   %(locationID)s,
                                   %(eventID)s,
                                   %(sampleSizeValue)s,
                                   %(recordedBy)s,
                                   %(samplingProtocol)s,
                                   %(reliability)s,
                                   %(dateStart)s,
                                   %(dateEnd)s,
                                   %(eventRemarks)s,
                                   %(sampleSizeUnit)s,
                                   %(samplingEffort)s,
                                   %(datasetID)s,
                                   %(projectID)s,
                                   %(fieldNotes)s)
                ''')

            cur = self._get_db_cur()
            # OS.NINA
            # unused values are commented
            insert_event = cur.mogrify(
                insert_event_tmpl,
                {'locationID': loc,
                 'eventID': event_id,
                 'sampleSizeValue': size_value,
                 # 'samplingProtocolRemarks': self.event['protocol_remarks'],
                 'recordedBy': self.event['recorded_by'],
                 'samplingProtocol': self.event['protocol'],
                 'reliability': self.event['reliability'],
                 'dateStart': start_date,
                 'dateEnd': end_date,
                 'eventRemarks': self.event['event_remarks'],
                 'sampleSizeUnit': self.event['size_unit'],
                 'samplingEffort': effort,
                 'datasetID': dataset,
                 # 'associatedReferences': reference,
                 'projectID': project,
                 'fieldNotes': 'test'})

            #QMessageBox.information(None, "DEBUG:", str(insert_event))
            #QMessageBox.information(None, "DEBUG:", str(type(loc)) + str(type(event_id))+ str(type(self.event['size_value']))+ str(type(self.event['protocol_remarks']))+ str(type(self.event['recorded_by']))+ str(type(self.event['protocol']))+ str(type(self.event['reliability'])) + str(type(self.event['date_start']))+ str(type(self.event['date_end']))+str(type( self.event['event_remarks']))+ str(type(self.event['size_unit'])) + str(type(effort)) + str(type(dataset)) + str(type(reference)) + str(type(project)) + str(type('text')))

            # Adding taxonomic coverage for a given event

            for tax in self.taxonomicc:
                cur.execute(
                    u"""SELECT "taxonID" FROM nofa."l_taxon" WHERE "%s" = '%s';""",
                    (self.species_names[self.language], tax,))
                taxon = cur.fetchone()
                #QMessageBox.information(None, "DEBUG:", 'taxon is: ' + str(taxon[0]))
                cur = self._get_db_cur()
                cur.execute(self.insert_taxonomic_coverage, (taxon, event_id))


            cur = self._get_db_cur()
            # insert the new event record to nofa.event

            cur.execute(insert_event)

            for m, occ in enumerate(self.occurrence['taxon']):
                #QMessageBox.information(None, "DEBUG:", str(self.occurrence))
                occurrence_id = uuid.uuid4()

                ectp = self.ectp_cb.currentText()

                if ectp == self.sel_str:
                    ecotype_id = None
                else:
                    cur = self._get_db_cur()
                    cur.execute = (
                        """
                        SELECT      "ecotypeID"
                        FROM        nofa."l_ecotype"
                        WHERE       "vernacularName" = %s;
                        """,
                        (ectp,))

                    ecotype_id = cur.fetchone()[0]

                if self.occurrence['taxon'][m] == 'Select':
                    #QMessageBox.information(None, "DEBUG:", 'Please select a a taxon ID for your occurrence entry')
                    return
                else:
                    #QMessageBox.information(None, "DEBUG:", 'occurrence taxon is: ' + str(type(str(self.occurrence['taxon'][m]))))
                    try:
                        #QMessageBox.information(None, "DEBUG:", self.occurrence['taxon'][m])
                        cur = self._get_db_cur()
                        query = u"""SELECT "taxonID" FROM nofa."l_taxon" WHERE "{}" = %s;""".format(
                            self.species_names[self.language])
                        cur.execute(query, (self.occurrence['taxon'][m],))
                    except:
                        e = sys.exc_info()[1]
                        QMessageBox.information(None, "DEBUG:", "<p>Error: %s</p>" % e)


                    taxon = cur.fetchone()[0]
                    #QMessageBox.information(None, "DEBUG:", 'occurrence taxon is: ' + str(taxon))

                verified_date = self.occurrence['verified_date'][m].toPyDate()

                # WARNING - this is a temporary placeholder value. It should be sniffed from the occurrence form (to be developed)
                if self.occurrence['metric'][m] == 'None':
                    organismquantity_metric = None
                else:
                    organismquantity_metric = self.occurrence['metric'][m]
                #QMessageBox.information(None, "DEBUG:", str(self.occurrence['quantity'][m]))

                # OS.NINA
                # deleted "yearPrecisionRemarks"
                insert_occurrence_tmpl = (
                    '''
                    INSERT INTO    nofa.occurrence (
                                       "occurrenceID",
                                       "ecotypeID",
                                       "establishmentMeans",
                                       "verifiedBy",
                                       "verifiedDate",
                                       "taxonID",
                                       "spawningLocation",
                                       "spawningCondition",
                                       "occurrenceStatus",
                                       "populationTrend",
                                       "organismQuantityType",
                                       "occurrenceRemarks",
                                       "modified",
                                       "establishmentRemarks",
                                       "eventID",
                                       "organismQuantity",
                                       "fieldNumber")
                    VALUES         (   %(occurrenceID)s,
                                       %(ecotypeID)s,
                                       %(establishmentMeans)s,
                                       %(verifiedBy)s,
                                       %(verifiedDate)s,
                                       %(taxonID)s,
                                       %(spawningLocation)s,
                                       %(spawningCondition)s,
                                       %(occurrenceStatus)s,
                                       %(populationTrend)s,
                                       %(organismQuantityType)s,
                                       %(occurrenceRemarks)s,
                                       %(modified)s,
                                       %(establishmentRemarks)s,
                                       %(eventID)s,
                                       %(organismQuantity)s,
                                       %(fieldNumber)s)
                    ''')

                cur = self._get_db_cur()
                insert_occurrence = cur.mogrify(
                    insert_occurrence_tmpl,
                    {'occurrenceID': occurrence_id,
                     'ecotypeID': ecotype_id,
                     'establishmentMeans': self.occurrence['est_means'][m],
                     'verifiedBy': self.occurrence['verified_by'][m],
                     'verifiedDate': verified_date,
                     'taxonID': taxon,
                     'spawningLocation': self.occurrence['spawn_loc'][m],
                     'spawningCondition': self.occurrence['spawn_con'][m],
                     'occurrenceStatus': self.occurrence['status'][m],
                     'populationTrend': self.occurrence['trend'][m],
                     'organismQuantityType': self.occurrence['quantity'][m],
                     'occurrenceRemarks': self.occurrence['oc_remarks'][m],
                     'modified': self.today,
                     'establishmentRemarks': self.occurrence['est_remarks'][m],
                     'eventID': event_id,
                     'organismQuantity': organismquantity_metric,
                     'fieldNumber': 'test'})

                #QMessageBox.information(None, "DEBUG:", str(insert_occurrence))


                # insert the new occurrence record to nofa.occurrence
                cur.execute(insert_occurrence)

                # OS.NINA
                # commented inserting to log tables
                # storing memory of insertion to db to log tables
                # cur = self._get_db_cur()
                # insert_log_occurrence = self.insert_log_occurrence
                # insert_log_occurrence += cur.mogrify(self.log_occurrence_values,
                #                                  (unicode(occurrence_id), unicode(event_id), self.dataset['dataset_id'], self.project['project_id'],
                #                                   self.reference['reference_id'], loc, True, self.username,
                #                                   ))
                # cur.execute(insert_log_occurrence)

        QMessageBox.information(None, "DEBUG:", "occurrences correctly stored in NOFA db")

    def upd_dtst(self, dtst_id_name=None):
        """
        Updates a dataset according to the last selected.
        
        :param dtst_id_name: A dataset ID and name "<datasetID> - <name>".
        :type dtst_id_name: str.
        """

        dtst_id_name = self.settings.value('dataset_id_name')

        if not dtst_id_name:
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

        dtst_id = dtst_id_name.split(self.dash_split_str)[0]

        self.listview_dataset.clear()

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "datasetID",
                        "datasetName",
                        "rightsHolder",
                        "institutionCode",
                        "license",
                        "bibliographicCitation",
                        "datasetComment",
                        "informationWithheld",
                        "dataGeneralizations"
            FROM        nofa."m_dataset"
            WHERE       "datasetID" = (%s);
            ''',
            (dtst_id,))
        dtst = cur.fetchone()

        for idx, dtst_data in enumerate(dtst):
            dtst_item = QListWidgetItem(
                u'{}: {}'.format(cur.description[idx][0], dtst_data))
            self.listview_dataset.addItem(dtst_item)

        self._set_mtdt_item_text(
            2,
            u'{}{}{}'.format(self.dtst_str, self.dash_split_str, dtst[1]))

        self.settings.setValue('dataset_id_name', dtst_id_name)

    def _set_mtdt_item_text(self, item_index, text):
        """
        Sets metadata item text.

        :param item_index: An Item index.
        :type item_index: int.
        :param text: A text.
        :type text: str.
        """

        self.main_tb.setItemText(item_index, text)

    def upd_prj(self, prj_org_no_name=None):
        """
        Updates a project according to the last selected.
        
        :param prj_org_no_name: A project ID number and name
            "<organisation> - <number> - <name>".
        :type prj_org_no_name: str.
        """

        prj_org_no_name = self.settings.value('project_org_no_name')

        if not prj_org_no_name:
            prj_org_no_name = self.prj_cb.currentText()

        self._upd_prj_lw(prj_org_no_name)

    def _upd_prj_lw(self, prj_org_no_name):
        """
        Updates the project list widget according to the current or last
        project.
        
        :param prj_org_no_name: A project ID number and name
            "<organisation> - <number> - <name>".
        :type prj_org_no_name: str.
        """

        if isinstance(prj_org_no_name, int):
            prj_org_no_name = self.prj_cb.currentText()

        self.listview_project.clear()

        split_prj_org_no_name = prj_org_no_name.split(self.dash_split_str)

        prj_org = split_prj_org_no_name[0]
        prj_no = split_prj_org_no_name[1]
        prj_name = split_prj_org_no_name[2]

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "projectNumber",
                        "projectName",
                        "startYear",
                        "endYear",
                        "projectLeader",
                        "projectMembers",
                        "organisation",
                        "financer",
                        "remarks",
                        "projectID"
            FROM        nofa."m_project"
            WHERE       "organisation" = %s
                        AND
                        "projectNumber" = %s
                        AND
                        "projectName" = %s;
            ''',
            (prj_org, prj_no, prj_name,))
        prj = cur.fetchone()

        for idx, prj_data in enumerate(prj):
            prj_item = QListWidgetItem(
                u'{}: {}'.format(cur.description[idx][0], prj_data))
            self.listview_project.addItem(prj_item)

        self._set_mtdt_item_text(
            3,
            u'{}{}{}'.format(
                self.prj_str,
                self.dash_split_str,
                prj_org_no_name))

        self.settings.setValue('project_org_no_name', prj_org_no_name)

    def upd_ref(self, ref_au_til_id=None):
        """
        Updates a reference according to the last selected.
        """

        ref_au_til_id = self.settings.value('reference_au_til_id')

        if not ref_au_til_id:
            ref_au_til_id = self.ref_cb.currentText()

        self._upd_ref_lw(ref_au_til_id)

    def _upd_ref_lw(self, ref_au_til_id):
        """
        Updates the reference list widget according to the current or last
        reference.
        
        :param ref_au_til_id: A reference author title and ID
            "<author>: <title> @<ID>".
        :type ref_au_til_id: str.
        """

        if isinstance(ref_au_til_id, int):
            ref_au_til_id = self.ref_cb.currentText()

        ref_id = ref_au_til_id.split(self.at_split_str)[1]

        self.listview_reference.clear()

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "referenceID",
                        "author",
                        "referenceType",
                        "year",
                        "titel",
                        "journalName",
                        "volume",
                        "issn",
                        "isbn",
                        "page"
            FROM        nofa."m_reference"
            WHERE       "referenceID" = (%s);
            ''',
            (ref_id,))
        ref = cur.fetchone()

        for idx, ref_data in enumerate(ref):
            ref_item = QListWidgetItem(
                u'{}: {}'.format(cur.description[idx][0], ref_data))
            self.listview_reference.addItem(ref_item)

        self._set_mtdt_item_text(
            4,
            u'{}{}{}'.format(self.ref_str, self.dash_split_str, ref[4]))

        self.settings.setValue('reference_au_til_id', ref_au_til_id)

    def _get_db_cur(self):
        """
        Returns a database cursor.
        
        :returns: A database cursor.
        :rtype: psycopg2.cursor.
        """

        return self.mc.con.cursor()

    def fetch_db(self):
        """
        Fetches data from the database and populates widgets.
        """

        self.row = 0

        self.pop_dtst_cb()
        QgsApplication.processEvents()
        self.upd_dtst()

        self.pop_prj_cb()
        QgsApplication.processEvents()
        self.upd_prj()

        self.pop_ref_cb()
        QgsApplication.processEvents()
        self.upd_ref()
        
        self._pop_txn_cb()
        self._pop_oqt_cb()
        self._pop_occstat_cb()
        self._pop_poptrend_cb()
        self._pop_estbm_cb()
        self._pop_smpp_cb()
        self._pop_reliab_cb()
        self._pop_smpsu_cb()
        self._pop_spwnc_cb()
        self._pop_spwnl_cb()
        self._pop_loctp_cb()
        self._pop_txncvg_tw()

    def _pop_txncvg_tw(self):
        """
        Populates the taxon coverage tree widget.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "scientificName",
                        "family"
            FROM        nofa.l_taxon
            WHERE       "scientificName" IS NOT NULL
                        AND
                        "family" IS NOT NULL
            GROUP BY    "scientificName", "family"
            ''')
        spp = cur.fetchall()

        fam_dict = defaultdict(list)
        for s in spp:
            fam_dict[s[1]].append(s[0])

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

    def _get_ckd_txn(self):
        root = self.txncvg_tw.invisibleRootItem()
        

    def pop_dtst_cb(self):
        """
        Populates the dataset combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "datasetID" dsid,
                        "datasetName" dsn
            FROM        nofa."m_dataset"
            ORDER BY    dsid, dsn;
            ''')
        dtsts = cur.fetchall()

        dtst_list = [self.get_dtst_str(d[0], d[1]) for d in dtsts]

        self.dtst_cb.clear()
        self.dtst_cb.addItems(dtst_list)

    def get_dtst_str(self, id, name):
        """
        Returns a dataset string "<id> - <name>"

        :param id: A dataset ID.
        :type id: str.
        :param name: A dataset name.
        :type name: str.
        """

        dtst_str = u'{}{}{}'.format(id, self.dash_split_str, name)

        return dtst_str

    def _get_dtst_id(self):
        """
        Returns a dataset id from the dataset combo box.

        :returns: A dataset ID.
        :rtype: str.
        """

        dtst_str = self.dtst_cb.currentText()

        id = dtst_str.split(self.dash_split_str)[0]

        return id

    def pop_prj_cb(self):
        """
        Populates the project combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "organisation" o,
                        "projectNumber" pno,
                        "projectName" pn,
                        "projectID" pid
            FROM        nofa."m_project"
            ORDER BY    o, pno, pn, pid
            ''')
        prjs = cur.fetchall()

        proj_list = [self.get_prj_str(p[0], p[1], p[2], p[3]) for p in prjs]

        self.prj_cb.clear()
        self.prj_cb.addItems(proj_list)

    def get_prj_str(self, org, no, name, id):
        """
        Returns a project string "<organisation> - <number> - <name> - <ID>"

        :param org: A project organization.
        :type org: str.
        :param no: A project number.
        :type no: str.
        :param name: A project name.
        :type name: str.
        :param id: A project ID.
        :type id: int.
        """

        prj_str = u'{}{}{}{}{}{}{}'.format(
            org,
            self.dash_split_str,
            no,
            self.dash_split_str,
            name,
            self.dash_split_str,
            id)

        return prj_str

    def _get_prj_id(self):
        """
        Returns a project ID from the project combo box.
        """

        prj_str = self.prj_cb.currentText()

        split_prj_str = prj_str.split(self.dash_split_str)

        id = split_prj_str[3]

        return id

    def pop_ref_cb(self):
        """
        Populates the reference combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "referenceID",
                        "author",
                        "titel"
            FROM        nofa."m_reference"
            ORDER BY    "author", "titel";
            ''')
        refs = cur.fetchall()

        ref_list = [self.get_ref_str(r[1], r[2], r[0]) for r in refs]

        self.ref_cb.clear()
        self.ref_cb.addItems(ref_list)

    def get_ref_str(self, au, ttl, id):
        """
        Returns a reference string "<author>: <title> @<id>".

        :param au: A reference author.
        :type au: str.
        :param ttl: A reference title.
        :type ttl: str.
        :param id: A reference ID.
        :type id: str.
        """

        ref_str = u'{}: {} @{}'.format(au, ttl, id)
        
        return ref_str

    def _pop_txn_cb(self):
        """
        Populates the taxon combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "scientificName" sn
            FROM        nofa."l_taxon"
            WHERE       "taxonRank" IN ('species', 'hybrid', 'genus')
            ORDER BY    sn
            ''')
        txns = cur.fetchall()

        txn_list = [t[0] for t in txns]

        self.txn_cb.clear()
        self.txn_cb.addItems(txn_list)

    def _pop_ectp_cb(self):
        """
        Populates the ecotype combo box.
        """

        txn_name = self.txn_cb.currentText()

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      e."vernacularName" vn
            FROM        nofa."l_ecotype" e
                        JOIN
                        nofa."l_taxon" t ON e."taxonID" = t."taxonID"
            WHERE       t."scientificName" = %s
            ORDER BY    vn;
            ''',
            (txn_name,))
        ectps = cur.fetchall()

        ectp_list = [e[0] for e in ectps]

        self.ectp_cb.clear()
        self.ectp_cb.addItems(ectp_list)

    def _pop_oqt_cb(self):
        """
        Populates the organism quantity type combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT    "organismQuantityType" oqt
            FROM      nofa."l_organismQuantityType"
            ORDER BY  oqt
            ''')
        oqts  = cur.fetchall()
        oqt_list = [o[0] for o in oqts]

        self.oqt_cb.clear()
        self.oqt_cb.addItems(oqt_list)

    def _pop_occstat_cb(self):
        """
        Populates the organism quantity type combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT    "occurrenceStatus" os
            FROM      nofa."l_occurrenceStatus"
            ORDER BY  os
            ''')
        occstats  = cur.fetchall()
        occstat_list = [o[0] for o in occstats]

        self.occstat_cb.clear()
        self.occstat_cb.addItems(occstat_list)

    def _pop_poptrend_cb(self):
        """
        Populates the population trend combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "populationTrend" pt
            FROM        nofa."l_populationTrend"
            WHERE       "populationTrend" is not null
            ORDER BY    pt
            ''')
        poptrends  = cur.fetchall()
        poptrend_list = [p[0] for p in poptrends]

        self.poptrend_cb.clear()
        self.poptrend_cb.addItems(poptrend_list)

    def _pop_estbm_cb(self):
        """
        Populates the establishment means combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "establishmentMeans" em
            FROM        nofa."l_establishmentMeans"
            ORDER BY    em
            ''')
        estms  = cur.fetchall()
        estm_list = [e[0] for e in estms]

        self.estm_cb.clear()
        self.estm_cb.addItems(estm_list)

    def _pop_smpp_cb(self):
        """
        Populates the sampling protocol combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "samplingProtocol" sp
            FROM        nofa."l_samplingProtocol"
            ORDER BY    sp
            ''')
        smpps  = cur.fetchall()
        smpp_list = [s[0] for s in smpps]

        self.smpp_cb.clear()
        self.smpp_cb.addItems(smpp_list)

    def _pop_reliab_cb(self):
        """
        Populates the reliability combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "reliability" r
            FROM        nofa."l_reliability"
            ORDER BY    r
            ''')
        relias  = cur.fetchall()
        relia_list = [r[0] for r in relias]

        self.relia_cb.clear()
        self.relia_cb.addItems(relia_list)

    def _pop_smpsu_cb(self):
        """
        Populates the sample size unit combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "sampleSizeUnit" s
            FROM        nofa."l_sampleSizeUnit"
            ORDER BY    s
            ''')
        smpsus  = cur.fetchall()
        smpsu_list = [s[0] for s in smpsus]

        self.smpsu_cb.clear()
        self.smpsu_cb.addItems(smpsu_list)

    def _pop_spwnc_cb(self):
        """
        Populates the spawning condition combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "spawningCondition" s
            FROM        nofa."l_spawningCondition"
            ORDER BY    s
            ''')
        spwncs  = cur.fetchall()
        spwnc_list = [s[0] for s in spwncs]

        self.spwnc_cb.clear()
        self.spwnc_cb.addItems(spwnc_list)

    def _pop_spwnl_cb(self):
        """
        Populates the spawning location combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "spawningLocation" s
            FROM        nofa."l_spawningLocation"
            ORDER BY    s
            ''')
        spwnls  = cur.fetchall()
        spwnl_list = [s[0] for s in spwnls]

        self.spwnl_cb.clear()
        self.spwnl_cb.addItems(spwnl_list)

    def _pop_loctp_cb(self):
        """
        Populates the location type combo box.
        """

        # OS.NINA
        # location types are hardcoded
        # could not find a list of location types in db
        loctp_list = self.loctp_list
        loctp_list.sort()

        self.loctp_cb.clear()
        self.loctp_cb.addItems(loctp_list)
        self.loctp_cb.setCurrentIndex(loctp_list.index('Norwegian VatnLnr'))

        # OS.NINA
        # other location types are disabled for now
        self.loctp_cb.model().item(1).setEnabled(False)
        self.loctp_cb.model().item(2).setEnabled(False)

    def create_occ_tbl(self):
        """
        Creates an occurrence table with one row.
        """

        self.occ_tbl_hdrs = (
            'taxon',
            'ecotype',
            'organismQuantityType',
            'organismQuantity',
            'occurrenceStatus',
            'populationTrend',
            'occurrenceRemarks',
            'establishmentMeans',
            'establishmentRemarks',
            'spawningCondition',
            'spawningLocation',
            'verifiedBy',
            'verifiedDate')
  
        self.occ_tbl.setColumnCount(len(self.occ_tbl_hdrs))
        self.occ_tbl.setSelectionBehavior(QTableWidget.SelectRows)
        self.occ_tbl.setSelectionMode(QTableWidget.SingleSelection)
        self.occ_tbl.setHorizontalHeaderLabels(self.occ_tbl_hdrs)
        self.occ_tbl.setRowCount(1)

        m = 0
        self._add_mty_occ_row_items(0)

        self.occ_tbl.blockSignals(True)
        self.occ_tbl.selectRow(0)
        self.occ_tbl.blockSignals(False)

        self._upd_occ_row()

    def _add_mty_occ_row_items(self, m):
        """
        Adds a row at the given position with empty items.
        
        :param m: A row number.
        :type m: int.
        """

        for n, elem in enumerate(self.occ_tbl_hdrs):
            tbl_item = QTableWidgetItem(None)
            self.occ_tbl.setItem(m, n, tbl_item)

    def _upd_occ_row(self):
        """
        Updates an occurrence row according to the values in the occurrence
        widgets.
        """

        m = self.occ_tbl.currentRow()

        occ_list = [
            self.txn_cb.currentText(),
            self.ectp_cb.currentText(),
            self.oqt_cb.currentText(),
            self.oq_le.text() if len(self.oq_le.text()) != 0 else 0,
            self.occstat_cb.currentText(),
            self.poptrend_cb.currentText(),
            self.occrmk_le.text() if len(self.occrmk_le.text()) != 0 else None,
            self.estm_cb.currentText(),
            self.estrmk_le.text() if len(self.estrmk_le.text()) != 0 else None,
            self.spwnc_cb.currentText(),
            self.spwnl_cb.currentText(),
            self.vfdby_le.text() if len(self.vfdby_le.text()) != 0 else None,
            self.verdt_de.date().toPyDate()]

        for n, elem in enumerate(occ_list):
            try:
                tbl_item = QTableWidgetItem(elem)
            except TypeError:
                tbl_item = QTableWidgetItem(str(elem))
            self.occ_tbl.setItem(m, n, tbl_item)

        self.occ_tbl.resizeColumnsToContents()

    def _add_occ_row(self):
        """
        Adds an occurrence row.
        """

        m = self.occ_tbl.currentRow() + 1
        self.occ_tbl.insertRow(m)
        self._add_mty_occ_row_items(m)

        self.occ_tbl.blockSignals(True)
        self.occ_tbl.selectRow(m)
        self.occ_tbl.blockSignals(False)

        self._clear_occ_le_wdgs()
        self._clear_occ_cb_wdgs()

        self._upd_occ_row()        

    def _clear_occ_le_wdgs(self):
        """
        Clears occurrence line edit widgets.
        """

        for occ_le_wdg in self.occ_le_wdgs:
            occ_le_wdg.clear()

    def _clear_occ_cb_wdgs(self):
        """
        Clears occurrence combo box widgets.
        """

        for occ_cb_wdg in self.occ_cb_wdgs:
            occ_cb_wdg.setCurrentIndex(0)

    def _upd_occ_gb_at_selrow(self, wdg_item):
        """
        Updates the occurrence group box according to the selected row.

        :param wdg_item: A current widget item.
        :type wdg_item: QTableWidgetItem.
        """

        m = self.occ_tbl.currentRow()

        for n, wdg in enumerate(self.occ_input_wdgs):
            text = self.occ_tbl.item(m, n).text()

            if isinstance(wdg, QLineEdit):
                wdg.setText(text)
            elif isinstance(wdg, QComboBox):
                idx = wdg.findText(text)
                wdg.setCurrentIndex(idx)
            elif isinstance(wdg, QDateEdit):
                wdg.setDate(QDate.fromString(text, 'yyyy-MM-dd'))

    def _sel_row_up(self):
        """
        Select one row up in the occurrences table.
        """

        m = self.occ_tbl.currentRow()

        if m > 0:
            self.occ_tbl.selectRow(m - 1)

    def _sel_row_dwn(self):
        """
        Select one row down in the occurrences table.
        """

        m = self.occ_tbl.currentRow()

        if m < (self.occ_tbl.rowCount() - 1):
            self.occ_tbl.selectRow(m + 1)

    def _del_occ_row(self):
        """
        Delete a row from the occurrence table.
        """

        m = self.occ_tbl.currentRow()

        if self.occ_tbl.rowCount() > 1:
            self.occ_tbl.removeRow(m)
