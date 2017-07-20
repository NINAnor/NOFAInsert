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
    QDoubleValidator, QIntValidator)

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

        self.host_str = u'host'
        self.port_str = u'port'
        self.db_str = u'database'
        self.usr_str = u'user'
        self.pwd_str = u'password'

        self.con_str_tpl = (
            self.host_str,
            self.port_str,
            self.db_str,
            self.usr_str,
            self.pwd_str)

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
        self.nextWeek = self.today + datetime.timedelta(days=7)

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

        # 16 event values, placeholders
        self.event_values = u'(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'

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

        self.insert_dataset = \
            """
            INSERT INTO     nofa.m_dataset (
                                "rightsHolder",
                                "ownerInstitutionCode",
                                "datasetName",
                                "accessRights",
                                "license",
                                "bibliographicCitation",
                                "datasetComment",
                                "informationWithheld",
                                "dataGeneralization")
            VALUES\n
            """



        self.insert_dataset_columns = u""" "datasetID", "rightsHolder", "ownerInstitutionCode",
        "datasetName", "accessRights", "license", "bibliographicCitation", "datasetComment",
        "informationWithheld", "dataGeneralizations" """

        self.insert_project_columns = u""" "projectID", "projectName", "projectNumber", "startYear", "endYear", "projectLeader",
        "projectMembers", "organisation", "financer", "remarks"
        """

        self.insert_reference_columns = u""" "referenceID", "doi", "author", "referenceType", "year", "titel",
        "journalName", "volume", "date", "issn", "isbn", "page" """

        self.insert_log_dataset_columns = u""" "dataset_id", "test", "username" """

        self.insert_log_project_columns = u""" "project_id", "test", "username" """

        self.insert_log_reference_columns = u""" "reference_id", "test", "username" """

        self.insert_log_location_columns = u""" "location_id", "test", "username", "location_name" """

        self.dataset_values = u'(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'

        self.project_values = u'(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'

        self.reference_values = u'(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'

        self.log_occurrence_values = u'(%s,%s,%s,%s,%s,%s,%s,%s)'

        self.log_dataset_values = u'(%s,%s,%s)'

        self.log_project_values = u'(%s,%s,%s)'

        self.log_reference_values = u'(%s,%s,%s)'

        self.log_location_values = u'(%s,%s,%s,%s)'



        self.preview_conditions = {
            'dataset_selected': False,
            'project_selected': False,
            'taxon_selected': False,
            'est_means_selected': False,
            'quantity': False}

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
        self.locIDType_dict = {
            'Norwegian VatnLnr': 'no_vatn_lnr',
            'coordinates UTM32': 25832,
            'coordinates UTM33': 25833,}

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
            'verified_date': self.today,
            'yearprecision_remarks': 'None'}

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
            'verified_date': [self.today, ],
            'yearprecision_remarks': ['None', ]}

        self.taxonomicc = []

        self.event = {
            'protocol': 'unknown',
            'size_value': None,
            'size_unit': 'None',
            'effort': 'unknown',
            'protocol_remarks': 'None',
            'date_start': self.today,
            'date_end': self.today,
            'recorded_by': 'unknown',
            'event_remarks': 'None',
            'reliability': 'Select'}

        self.dataset = {
            'dataset_id': 'None',
            'rightsholder': 'None',
            'dataset_name': 'None',
            'owner_institution': 'None',
            'access_rights': 'None',
            'license': 'None',
            'citation': 'None',
            'comment': 'None',
            'information': 'None',
            'generalizations': 'None'}

        self.project = {
            'project_id': 'None',
            'project_name': 'None',
            'project_number': 'None',
            'start_year': 'None',
            'end_year': 'None',
            'leader': 'None',
            'members': 'None',
            'organisation': 'None',
            'financer': 'None',
            'project_remarks': 'None'}

        self.reference = {
            'reference_id': 'None',
            'authors': 'None',
            'reference_type': 'None',
            'year': 'None',
            'title': 'None',
            'journal': 'None',
            'volume': 'None',
            'issn': 'None',
            'isbn': 'None',
            'page': 'None'}

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

        # temporary list, to replace the currently empty table l_occurrenceStatus. Will be used in the occurrence status dropdown
        self.occurrence_status = [
            'unknown', 'absent', 'common', 'doubtful',
            'excluded', 'irregular','present', 'rare']

        self.population_trend = [
            'unknown', 'increasing', 'decrasing', 'stable',
            'extinction', 'introduction', 're-introduction']

        self.insert_button.setStyleSheet("background-color: #F6CECE")

        self.editDatasetButton.clicked.connect(self._open_dtst_dlg)
        self.editProjectButton.clicked.connect(self._open_prj_dlg)
        self.edit_reference_button.clicked.connect(self._open_ref_dlg)


        self.dtst_cb.activated.connect(self._upd_dtst_lw)
        self.prj_cb.activated.connect(self._upd_prj_lw)
        self.ref_cb.activated.connect(self._upd_ref_lw)

        self.insert_button.clicked.connect(self.preview)

        self.addOccurrence.clicked.connect(self.add_occurrence)

        # Up and Down buttons to move selection of the occurrence table
        self.upButton.clicked.connect(self.row_up)
        self.downButton.clicked.connect(self.row_down)

        self.deleteOccurrence.clicked.connect(self.delete_occurrence_row)

        # Table clicked events
        self.tableWidget.itemClicked.connect(self.update_row)
        self.tableWidget.verticalHeader().sectionClicked.connect(self.update_header)
        # set the occurrenceStatus checkbox to True, as a default initial status
        #self.occurrenceStatus.setChecked(True)

        #connect the occurrence input widgets to table content
        self.update_row_button.clicked.connect(self.update_occurrence_row)

        # trigger action when history tabs are clicked
        self.tabWidget.currentChanged.connect(self.history_tab_clicked)
        self.tabWidget_history.currentChanged.connect(self.history_tab_clicked)

        # OS.NINA
        # there are not neccessary tables in the new db
        # history tab is disabled
        self.tabWidget.setTabEnabled(1, False)

        self.taxonID.currentIndexChanged.connect(self._pop_ectp_cb)

        # taxonomic coverage treewidget parent item changed
        self.taxonomicCoverage.itemChanged.connect(self.checked_tree)

        # filter occurrences by username and time interval
        self.username_filter_button.clicked.connect(self.filter_occurrences_by_username)
        self.time_filter_button.clicked.connect(self.filter_occurrence_by_time)
        self.combined_filter_button.clicked.connect(self.filter_by_user_and_time)

        self.sampleSizeValue.setValidator(QDoubleValidator(None))
        self.samplingEffort.setValidator(QIntValidator(None))
        self.oq_metric.setValidator(QDoubleValidator(None))

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

    def update_occurrence_row(self):
        """
        Inserts the data from the occurrence form into the occurrence table
        :return: 
        """

        if self.taxonID.currentText():
            self.occurrence['taxon'][self.row_position] = self.taxonID.currentText()

            # update the preview conditions for taxon presence
            if self.taxonID.currentText() != 'Select':
                #QMessageBox.information(None, "DEBUG:", str(self.occurrence['taxon']))
                if 'Select' not in self.occurrence['taxon']:
                    self.preview_conditions['taxon_selected'] = True
                    self.check_preview_conditions()
            elif self.taxonID.currentText() == 'Select':
                self.preview_conditions['taxon_selected'] = False
                self.check_preview_conditions()
        else:
            self.occurrence['taxon'][self.row_position] = 'None'

        if self.establishmentMeans.currentText():
            self.occurrence['est_means'][self.row_position] = self.establishmentMeans.currentText()

            if self.establishmentMeans.currentText() != ' ' or self.establishmentMeans.currentText() != 'Select':
                #QMessageBox.information(None, "DEBUG:", str(self.occurrence['taxon']))
                if 'Select' not in self.occurrence['est_means']:
                    self.preview_conditions['est_means_selected'] = True
                    self.check_preview_conditions()
            elif self.establishmentMeans.currentText() == 'Select' or self.establishmentMeans.currentText() == ' ':
                self.preview_conditions['est_means_selected'] = False
                self.check_preview_conditions()


        if self.organismQuantityID.currentText():
            self.occurrence['quantity'][self.row_position] = self.organismQuantityID.currentText()

            if self.organismQuantityID.currentText() != ' ' or self.organismQuantityID.currentText() != 'Select':
                #QMessageBox.information(None, "DEBUG:", str(self.occurrence['taxon']))
                if 'Select' not in self.occurrence['quantity']:
                    self.preview_conditions['quantity'] = True
                    self.check_preview_conditions()
            elif self.organismQuantityID.currentText() == 'Select' or self.organismQuantityID.currentText() == ' ':
                self.preview_conditions['quantity'] = False
                self.check_preview_conditions()

        self.occurrence['ecotype'][self.row_position] = self.ecotypeID.currentText()
        #QMessageBox.information(None, "DEBUG:", str(self.occurrence['ecotype'][self.row_position]))


        #self.occurrence['quantity'][self.row_position] = self.organismQuantityID.currentText()
        self.occurrence['metric'][self.row_position] = self.oq_metric.text()
        self.occurrence['status'][self.row_position] = self.status.currentText()
        self.occurrence['trend'][self.row_position] = self.trend.currentText()
        self.occurrence['oc_remarks'][self.row_position] = self.occurrenceRemarks.text()

        self.occurrence['est_remarks'][self.row_position] = self.establishmentRemarks.text()
        self.occurrence['spawn_con'][self.row_position] = self.spawningCondition.currentText()
        self.occurrence['spawn_loc'][self.row_position] = self.spawningLocation.currentText()
        self.occurrence['verified_by'][self.row_position] = self.verifiedBy.text()
        self.occurrence['verified_date'][self.row_position] = self.verifiedDate.date()
        self.occurrence['yearprecision_remarks'][self.row_position] = self.yearPrecisionRemarks.text()


        for m, key in enumerate(sorted(self.occurrence.keys())):
            item = self.occurrence[key][self.row_position]
            try:
                newitem = QTableWidgetItem(item)
            except:
                newitem = QTableWidgetItem(unicode(item))
            # setItem(row, column, QTableWidgetItem)
            self.tableWidget.setItem(self.row_position, m, newitem)

    def delete_occurrence_row(self):
        """Delete a row from occurrence table on button click."""

        # checks if table contains occurrences
        if self.tableWidget.rowCount()==0:
            return

        for i, key in enumerate(self.occurrence.keys()):
            del self.occurrence[key][self.row_position]

        self.tableWidget.removeRow(self.row_position)

        self.row_position = 0
        self.tableWidget.selectRow(self.row_position)
        self.occurrence_number.setText(unicode(self.row_position + 1))

        # Check if some row with taxon remains:
        if 'Select' in self.occurrence['taxon']:
            self.preview_conditions['taxon_selected'] = False
            self.check_preview_conditions()
        elif 'Select' not in self.occurrence['taxon']:
            self.preview_conditions['taxon_selected'] = True
            self.check_preview_conditions()

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



            self.row_position = 0

            self.tableWidget_occurrences.setSelectionBehavior(QTableWidget.SelectRows)

            #  populate tableWidget

            cur = self._get_db_cur()
            try:
                cur.execute(u'SELECT  "occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_occurrence_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. occurrences not fetched from db"))

            fetched_occ = cur.fetchall()

            lim = len(fetched_occ)

            self.tableWidget_occurrences.setRowCount(lim)
            self.tableWidget_occurrences.setColumnCount(9)

            self.tableWidget_occurrences.setHorizontalHeaderLabels(
                self.occ_hdrs)

            for l in range(lim):
                occurrence = fetched_occ[l]
                for n, item in enumerate(occurrence):


                    newitem = QTableWidgetItem(unicode(occurrence[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.tableWidget_occurrences.setItem(l, n, newitem)

        elif self.tabWidget_history.currentIndex() == 1:
            # add locations log entries to history -> locations
            self.tableWidget_locations.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "location_id", "username", "location_name", "insert_timestamp", "update_timestamp" FROM nofa.plugin_location_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. location logs not fetched from db"))

            fetched_location_logs = cur.fetchall()

            lim = len(fetched_location_logs)

            self.tableWidget_locations.setRowCount(lim)
            self.tableWidget_locations.setColumnCount(5)

            self.tableWidget_locations.setHorizontalHeaderLabels(
                self.loc_hdrs)

            for l in range(lim):
                locations = fetched_location_logs[l]
                for n, item in enumerate(locations):

                    newitem = QTableWidgetItem(unicode(locations[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.tableWidget_locations.setItem(l, n, newitem)

        elif self.tabWidget_history.currentIndex() == 2:
            self.tableWidget_datasets.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "dataset_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_dataset_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. datasets not fetched from db"))

            fetched_datasets = cur.fetchall()

            lim = len(fetched_datasets)

            self.tableWidget_datasets.setRowCount(lim)
            self.tableWidget_datasets.setColumnCount(4)

            self.tableWidget_datasets.setHorizontalHeaderLabels(
                self.dtst_hdrs)

            for l in range(lim):
                dataset = fetched_datasets[l]
                for n, item in enumerate(dataset):

                    newitem = QTableWidgetItem(unicode(dataset[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.tableWidget_datasets.setItem(l, n, newitem)

        elif self.tabWidget_history.currentIndex() == 3:

            self.tableWidget_projects.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "project_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_project_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. projects not fetched from db"))

            fetched_projects = cur.fetchall()

            lim = len(fetched_projects)

            self.tableWidget_projects.setRowCount(lim)
            self.tableWidget_projects.setColumnCount(4)

            self.tableWidget_projects.setHorizontalHeaderLabels(
                self.prj_hdrs)

            for l in range(lim):
                projects = fetched_projects[l]
                for n, item in enumerate(projects):
                    newitem = QTableWidgetItem(unicode(projects[n]))

                    # setItem(row, column, QTableWidgetItem)
                    self.tableWidget_projects.setItem(l, n, newitem)

        elif self.tabWidget_history.currentIndex() == 4:

            self.tableWidget_references.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "reference_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_reference_log')
            except:
                pass

            fetched_references = cur.fetchall()

            lim = len(fetched_references)

            self.tableWidget_references.setRowCount(lim)
            self.tableWidget_references.setColumnCount(4)

            self.tableWidget_references.setHorizontalHeaderLabels(
                self.ref_hdrs)

            for l in range(lim):
                references = fetched_references[l]
                for n, item in enumerate(references):
                    newitem = QTableWidgetItem(unicode(references[n]))

                    # setItem(row, column, QTableWidgetItem)
                    self.tableWidget_references.setItem(l, n, newitem)

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

        self.tableWidget_occurrences.setRowCount(lim)
        self.tableWidget_occurrences.setColumnCount(9)

        self.tableWidget_occurrences.setHorizontalHeaderLabels(
            self.occ_hdrs)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.tableWidget_occurrences.setItem(l, n, newitem)

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

        self.tableWidget_occurrences.setRowCount(lim)
        self.tableWidget_occurrences.setColumnCount(9)

        self.tableWidget_occurrences.setHorizontalHeaderLabels(
            self.occ_hdrs)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.tableWidget_occurrences.setItem(l, n, newitem)

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

        self.tableWidget_occurrences.setRowCount(lim)
        self.tableWidget_occurrences.setColumnCount(9)

        self.tableWidget_occurrences.setHorizontalHeaderLabels(
            self.occ_hdrs)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.tableWidget_occurrences.setItem(l, n, newitem)

    def checked_tree(self, item):
        """Checking/Unchecking taxa based on hierarchical groups.
        Triggered by items checked/unchecked in TaxonomicCoverage QWidgetTree"""
        counted = item.childCount()
        if counted != 0:

            if item.checkState(0) == Qt.Checked:
                for i in range(counted):
                    child = item.child(i)
                    child.setCheckState(0, Qt.Checked)

                    newcounted = child.childCount()
                    if newcounted != 0:
                        for n in range(newcounted):
                            newchild = child.child(n)
                            newchild.setCheckState(0, Qt.Checked)

                    #QMessageBox.information(None, "DEBUG:", str(item.childCount()))
            elif item.checkState(0) == Qt.Unchecked:
                #QMessageBox.information(None, "DEBUG:", "item unchecked")
                for i in range(counted):
                    child = item.child(i)
                    child.setCheckState(0, Qt.Unchecked)

                    newcounted = child.childCount()
                    if newcounted != 0:
                        for n in range(newcounted):
                            newchild = child.child(n)
                            newchild.setCheckState(0, Qt.Unchecked)

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


        locs = self.locations.text()
        location_type = self.locIDType.currentText()
        #QMessageBox.information(None, "DEBUG:", locations)
        #QMessageBox.information(None, "DEBUG:", location_type)

        #Manage the case of Norwegian VatLnr coordinates input
        if location_type == 'Norwegian VatnLnr':
            locations = locs.split(',')
            col = self.locIDType_dict[location_type]

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
            type = self.locIDType_dict[location_type]
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

                        #QMessageBox.information(None, "DEBUG:", str(loc[4]))
                        #QMessageBox.information(None, "DEBUG:", str("loc not found"))

            self.locations['location'] = coords


    def check_preview_conditions(self):

        if False not in self.preview_conditions.values():
            self.insert_button.setStyleSheet("background-color: #E0F8EC")
        elif False in self.preview_conditions.values():
            self.insert_button.setStyleSheet("background-color: #F6CECE")


    def preview(self):

        #QMessageBox.information(None, "DEBUG:", str(self.occurrence))

        # Check if all required info is available before going to preview
        if False in self.preview_conditions.values():
            QMessageBox.information(None, "DEBUG:", "Please check if all required information is provided")
            return


        # Get the locations:
        self.get_location()
        #self.locations['location'] =


        #Get Event Data

        self.event['protocol'] = self.samplingProtocol.currentText()
        self.event['size_value'] = self.sampleSizeValue.text()
        self.event['size_unit'] = self.sampleSizeUnit.currentText()
        self.event['effort'] = self.samplingEffort.text()
        #self.event['date_start'] = self.dateStart.date().toString()
        self.event['date_start'] = self.dateStart.date()
        #self.event['date_end'] = self.dateEnd.date().toString()
        self.event['date_end'] = self.dateEnd.date()
        self.event['recorded_by'] = self.recordedBy_e.text()
        self.event['event_remarks'] = self.eventRemarks.text()
        self.event['reliability'] = self.reliability.currentText()

        #QMessageBox.information(None, "DEBUG:", str(self.event))
        self.prwdlg = PreviewDialog()
        self.prwdlg.show()

        self.container = [
            self.event,
            self.dataset,
            self.project,
            self.reference]

        listWidget_list = [
            self.prwdlg.listWidget_4,
            self.prwdlg.listWidget_5,
            self.prwdlg.listWidget_6,
            self.prwdlg.listWidget_7]

        # Set the locations
        for elem in self.locations['location']:
            self.prwdlg.listWidget_1.addItem(QListWidgetItem(elem))

        # Get taxonomic coverage items
        root = self.taxonomicCoverage.invisibleRootItem()
        counted = root.childCount()
        #QMessageBox.information(None, "DEBUG:", str(counted))

        taxon_list = []

        for index in range(counted):
            base = root.child(index)
            new_counted = base.childCount()
            #QMessageBox.information(None, "DEBUG:", str(new_counted))
            for t in range(new_counted):
                family = base.child(t)

                very_new_count = family.childCount()
                for n in range(very_new_count):
                    taxon = family.child(n)
                    taxon_list.append(taxon.text(0))

                    if taxon.checkState(0) == Qt.Checked:
                        self.prwdlg.listWidget_3.addItem(QListWidgetItem(taxon.text(0)))

        #QMessageBox.information(None, "DEBUG:", str(taxon_list))
        # 5616, 5627, 10688


        # populate the preview list widgets with info from previous forms
        for i in range(4):

            for key, value in self.container[i].iteritems():
                if value == u'' or value == u'unknown' or value == u'None':
                    prwitem = QListWidgetItem(key + ':    None')
                    prwitem.setTextColor(QColor("red"))
                else:
                    prwitem = QListWidgetItem(key + ':    ' + unicode(value))
                    prwitem.setTextColor(QColor("green"))

                listWidget_list[i].addItem(prwitem)

        ## Create the preview occurrence table


        self.prwdlg.table.setColumnCount(12)

        m = len(self.occurrence['taxon'])
        self.prwdlg.table.setRowCount(m)


        self.prwdlg.table.setSelectionBehavior(QTableWidget.SelectRows);
        #QMessageBox.information(None, "DEBUG:", str(self.occurrence))
        #  populate tableWidget
        headers = []
        for n, key in enumerate(self.occurrence.keys()):
            if key != 'yearprecision_remarks':
                self.prwdlg.table.setColumnWidth(n, 88)
            else:
                self.prwdlg.table.setColumnWidth(n, 94)
            headers.append(key)
            #QMessageBox.information(None, "DEBUG:", str(headers))
            for m, item in enumerate(self.occurrence[key]):

                if key == 'verified_date':
                    newitem = QTableWidgetItem(item.toString())
                else:
                    newitem = QTableWidgetItem(unicode(item))
                # setItem(row, column, QTableWidgetItem)
                self.prwdlg.table.setItem(m, n, newitem)
        self.prwdlg.table.setHorizontalHeaderLabels(headers)
        self.prwdlg.confirmButton.clicked.connect(self.confirmed)


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

            if self.event['size_unit'] is None:
                self.event['size_unit'] = 'metre'
            elif self.event['size_unit'] == 'None':
                self.event['size_unit'] = 'metre'

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

                ectp = self.ecotypeID.currentText()

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
                                       %(organismQuantityID)s,
                                       %(occurrenceRemarks)s,
                                       %(modified)s,
                                       %(establishmentRemarks)s,
                                       %(eventID)s,
                                       %(organismQuantityMetric)s,
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
                     'yearPrecisionRemarks': self.occurrence['yearprecision_remarks'][m],
                     'organismQuantityID': self.occurrence['quantity'][m],
                     'occurrenceRemarks': self.occurrence['oc_remarks'][m],
                     'modified': self.today,
                     'establishmentRemarks': self.occurrence['est_remarks'][m],
                     'eventID': event_id,
                     'organismQuantityMetric': organismquantity_metric,
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

    def open_reference_dialog(self):
        """On button click opens the Project Metadata Editing Dialog"""
        self.rfrdlg = ReferenceDialog()
        self.rfrdlg.show()

        ###########################################################################


        # Get referenceType from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "referenceType" FROM nofa."l_referenceType";')
        refType = cur.fetchall()

        # Create a python-list from query result
        refType_list = [r[0] for r in refType]

        # Inject sorted python-list for referenceType into UI
        refType_list.sort()
        self.rfrdlg.referenceType.clear()
        self.rfrdlg.referenceType.addItems(refType_list)
        self.rfrdlg.referenceType.setCurrentIndex(refType_list.index("Unknown"))

        ###########################################################################


        self.rfrdlg.date.setDate(self.today)

        self.rfrdlg.year.setDate(self.today)
        # self.o_modified.setDate(nextWeek)

        self.rfrdlg.reference_dialog_button.clicked.connect(self.reference_button)

    def reference_button(self):
        """
                method inserting new reference entries to m_reference table
                and log entries in plugin_project_log
                """

        doi = self.rfrdlg.doi.text()
        author = self.rfrdlg.author.text()
        reference_type = self.rfrdlg.referenceType.currentText()
        year = self.rfrdlg.year.date()
        title = self.rfrdlg.title.toPlainText()
        journal_name = self.rfrdlg.journalName.text()
        volume = self.rfrdlg.volume.text()
        date = self.rfrdlg.date.date()
        issn = self.rfrdlg.issn.text()
        isbn = self.rfrdlg.isbn.text()
        page = self.rfrdlg.page.text()

        cur = self._get_db_cur()
        cur.execute(u'SELECT max("referenceID") FROM nofa.m_reference;')
        max_rfr_id = cur.fetchone()[0]
        #QMessageBox.information(None, "DEBUG:", str(max_rfr_id))
        new_r_id = max_rfr_id + 1

        cur = self._get_db_cur()

        insert_reference = cur.mogrify(
            """
            INSERT INTO    nofa.m_reference({})
            VALUES         {}
            RETURNING      "referenceID"
            """.format(
                self.insert_reference_columns,
                self.reference_values), (
                    new_r_id, doi, author, reference_type, int(year.year()),
                    title, journal_name, volume, date.toPyDate(),
                    issn, isbn, page,))

        #QMessageBox.information(None, "DEBUG:", insert_reference)

        cur.execute(insert_reference)

        returned = cur.fetchone()[0]
        #QMessageBox.information(None, "DEBUG:", str(returned))

        ##################
        # Insert a reference log entry

        cur = self._get_db_cur()

        insert_reference_log = cur.mogrify("INSERT INTO nofa.plugin_reference_log({}) VALUES {}".format(
            self.insert_log_reference_columns,
            self.log_reference_values,
        ), (returned, True, self.username,))

        #QMessageBox.information(None, "DEBUG:", insert_reference_log)

        cur.execute(insert_reference_log)

        self.get_existing_references()

    def upd_dtst(self, dtst_id_name=None):
        """
        Updates a dataset according to the last selected.
        
        :param dtst_id_name: A dataset ID and name "<datasetID> - <name>".
        :type dtst_id_name: str.
        """

        if not dtst_id_name:
            dtst_id_name = self.settings.value('dataset_id_name', self.sel_str)

        dtst_cb_index = self.dtst_cb.findText(dtst_id_name)

        self.dtst_cb.setCurrentIndex(dtst_cb_index)

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

        if dtst_id != self.sel_str:
            self.preview_conditions['dataset_selected'] = True

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

            self.dataset['dataset_id'] = dtst[0]
            self.dataset['dataset_name'] = dtst[1]
            self.dataset['rightsholder'] = dtst[2]
            self.dataset['owner_institution'] = dtst[3]
            self.dataset['license'] = dtst[4]
            self.dataset['citation'] = dtst[5]
            self.dataset['comment'] = dtst[6]
            self.dataset['information'] = dtst[7]
            self.dataset['generalizations'] = dtst[8]

            for key, value in self.dataset.iteritems():
                dtst_item = QListWidgetItem(key + ':    ' + unicode(value))
                self.listview_dataset.addItem(dtst_item)

            self._set_mtdt_item_text(
                2,
                u'{}{}{}'.format(
                    self.dtst_str,
                    self.dash_split_str,
                    self.dataset['dataset_name']))
        else:
            self.preview_conditions['dataset_selected'] = False

            for key, value in self.dataset.iteritems():
                dtst_item = QListWidgetItem(key + ':    ' + self.none_str)
                self.listview_dataset.addItem(dtst_item)

            self._set_mtdt_item_text(
                2,
                u'{}{}{}'.format(
                    self.dtst_str,
                    self.dash_split_str,
                    self.none_str))

        self.settings.setValue('dataset_id_name', dtst_id_name)

        self.check_preview_conditions()

    def _set_mtdt_item_text(self, item_index, text):
        """
        Sets metadata item text.

        :param item_index: An Item index.
        :type item_index: int.
        :param text: A text.
        :type text: str.
        """

        self.metadata.setItemText(item_index, text)

    def upd_prj(self, prj_org_no_name=None):
        """
        Updates a project according to the last selected.
        
        :param prj_org_no_name: A project ID number and name
            "<organisation> - <number> - <name>".
        :type prj_org_no_name: str.
        """

        if not prj_org_no_name:
            prj_org_no_name = self.settings.value(
                'project_org_no_name', self.sel_str)

        proj_cb_index = self.prj_cb.findText(prj_org_no_name)

        self.prj_cb.setCurrentIndex(proj_cb_index)

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

        split_prj_org_no_name = prj_org_no_name.split(self.dash_split_str)
        prj_org = split_prj_org_no_name[0]

        self.listview_project.clear()

        if prj_org != self.sel_str:
            prj_no = split_prj_org_no_name[1]
            prj_name = split_prj_org_no_name[2]

            self.preview_conditions['project_selected'] = True

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

            self.project['project_number'] = unicode(prj[0])
            self.project['project_name'] = prj[1]
            self.project['start_year'] = unicode(prj[2])
            self.project['end_year'] = unicode(prj[3])
            self.project['project_leader'] = prj[4]
            self.project['members'] = prj[5]
            self.project['organisation'] = prj[6]
            self.project['financer'] = prj[7]
            self.project['project_remarks'] = prj[8]
            self.project['project_id'] = prj[9]

            for key, value in self.project.iteritems():
                prj_item = QListWidgetItem(key + ':    ' + unicode(value))
                self.listview_project.addItem(prj_item)

            self._set_mtdt_item_text(
                3,
                u'{}{}{}'.format(
                    self.prj_str,
                    self.dash_split_str,
                    prj_org_no_name))
        else:
            self.preview_conditions['project_selected'] = False

            for key, value in self.dataset.iteritems():
                prj_item = QListWidgetItem(key + ':    ' + self.none_str)
                self.listview_project.addItem(prj_item)

            self._set_mtdt_item_text(
                3,
                u'{}{}{}'.format(
                    self.prj_str,
                    self.dash_split_str,
                    self.none_str))

        self.settings.setValue('project_org_no_name', prj_org_no_name)

        self.check_preview_conditions()

    def upd_ref(self, ref_au_til_id=None):
        """
        Updates a reference according to the last selected.
        """

        if not ref_au_til_id:
            ref_au_til_id = self.settings.value(
                'reference_au_til_id', self.sel_str)

        ref_cb_index = self.ref_cb.findText(ref_au_til_id)

        self.ref_cb.setCurrentIndex(ref_cb_index)

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
        if ref_au_til_id == self.sel_str:
            ref_id = self.sel_str
        else:
            ref_id = ref_au_til_id.split(self.at_split_str)[1]

        self.listview_reference.clear()

        if ref_id != self.sel_str:
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

            self.reference['reference_id'] = ref[0]
            self.reference['authors'] = unicode(ref[1])
            self.reference['reference_type'] = unicode(ref[2])
            self.reference['year'] = unicode(ref[3])
            self.reference['title'] = unicode(ref[4])
            self.reference['journal'] = unicode(ref[5])
            self.reference['volume'] = unicode(ref[6])
            self.reference['issn'] = unicode(ref[7])
            self.reference['isbn'] = unicode(ref[8])
            self.reference['page'] = unicode(ref[9])

            for key, value in self.reference.iteritems():
                ref_item = QListWidgetItem(key + ':    ' + unicode(value))
                self.listview_reference.addItem(ref_item)

            self._set_mtdt_item_text(
                4,
                u'{}{}{}'.format(
                    self.ref_str,
                    self.dash_split_str,
                    self.reference['title']))
        else:
            for key, value in self.dataset.iteritems():
                ref_item = QListWidgetItem(key + ':    ' + self.none_str)
                self.listview_reference.addItem(ref_item)

            self._set_mtdt_item_text(
                4,
                u'{}{}{}'.format(
                    self.ref_str,
                    self.dash_split_str,
                    self.none_str))

        self.settings.setValue('reference_au_til_id', ref_au_til_id)

        self.check_preview_conditions()

    def _get_db_cur(self):
        """
        Returns a database cursor.
        
        :returns: A database cursor.
        :rtype: psycopg2.cursor.
        """

        return self.mc.con.cursor()

    def fetch_db(self):

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

        #################################
        '''
        # Get ecotypes from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "vernacularName_NO" FROM nofa."l_ecotype" GROUP BY "vernacularName_NO";')
        ecotypes = cur.fetchall()

        # Create a python-list from query result
        ecotypes_list = [e[0] for e in ecotypes]
        #QMessageBox.information(None, "DEBUG:", unicode(ecotypes_list))
        # Inject sorted python-list for ecotypes into UI
        ecotypes_list.sort()
        self.ecotypeID.clear()
        self.ecotypeID.addItems(ecotypes_list)
        '''
        ##########################################

        # Get organismQuantity from database
        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT    "organismQuantityType" oqt
            FROM      nofa."l_organismQuantityType"
            ORDER BY  oqt
            ''')
        orgQuantID  = cur.fetchall()
        orgQuantID_list = [o[0] for o in orgQuantID]
        orgQuantID_list.insert(0, 'Select')

        self.organismQuantityID.clear()
        self.organismQuantityID.addItems(orgQuantID_list)

        #############################################

        # Get occurrence status
        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT    "occurrenceStatus" os
            FROM      nofa."l_occurrenceStatus"
            ORDER BY  os
            ''')
        occStat  = cur.fetchall()
        occStat_list = [o[0] for o in occStat]
        occStat_list.insert(0, 'Select')

        self.status.clear()
        self.status.addItems(occStat_list)

        #############################################

        # Get population trend
        self.trend.clear()
        self.trend.addItems(self.population_trend)
        self.trend.setCurrentIndex(self.population_trend.index("unknown"))
        

        #############################################

        # Get establishmentMeans from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "establishmentMeans" FROM nofa."l_establishmentMeans";')
        establishment = cur.fetchall()

        # Create a python-list from query result
        establishment_list = [e[0] for e in establishment]

        # Inject sorted python-list for establishmentMeans into UI
        establishment_list.sort()
        establishment_list.insert(0, 'Select')
        self.establishmentMeans.clear()
        self.establishmentMeans.addItems(establishment_list)
        self.establishmentMeans.setCurrentIndex(establishment_list.index("unknown"))

        ###################################################

        # Get samplingProtocols from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "samplingProtocol" FROM nofa."l_samplingProtocol";')
        samplingProt = cur.fetchall()

        # Create a python-list from query result
        samplingProt_list = [s[0] for s in samplingProt]

        # Inject sorted python-list for samplingProtocol into UI
        samplingProt_list.sort()
        self.samplingProtocol.clear()
        self.samplingProtocol.addItems(samplingProt_list)
        self.samplingProtocol.setCurrentIndex(samplingProt_list.index("unknown"))

        ######################################################

        # Get reliability from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "reliability" FROM nofa."l_reliability";')
        reliab = cur.fetchall()

        # Create a python-list from query result
        reliab_list = [r[0] for r in reliab]

        # Inject sorted python-list for reliability into UI
        reliab_list.sort()
        self.reliability.clear()
        self.reliability.addItems(reliab_list)

        #########################################################

        # Get sampleSizeUnit from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "sampleSizeUnit" FROM nofa."l_sampleSizeUnit";')
        sampUnit = cur.fetchall()

        # Create a python-list from query result
        sampUnit_list = [s[0] for s in sampUnit]

        # Inject sorted python-list for establishmentMeans into UI
        sampUnit_list.sort()
        sampUnit_list.insert(0, 'None')
        self.sampleSizeUnit.clear()
        self.sampleSizeUnit.addItems(sampUnit_list)
        self.sampleSizeUnit.setCurrentIndex(sampUnit_list.index("None"))

        ############################################################

        # Get spawningCondition from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "spawningCondition" FROM nofa."l_spawningCondition";')
        spawnCon = cur.fetchall()

        # Create a python-list from query result
        spawnCon_list = [s[0] for s in spawnCon]

        # Inject sorted python-list for spawningCondition into UI
        spawnCon_list.sort()
        self.spawningCondition.clear()
        self.spawningCondition.addItems(spawnCon_list)
        self.spawningCondition.setCurrentIndex(spawnCon_list.index("unknown"))

        ###############################################################

        # Get spawningLocation from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "spawningLocation" FROM nofa."l_spawningLocation";')
        spawnLoc = cur.fetchall()

        # Create a python-list from query result
        spawnLoc_list = [s[0] for s in spawnLoc]

        # Inject sorted python-list for spawningLocation into UI
        spawnLoc_list.sort()
        self.spawningLocation.clear()
        self.spawningLocation.addItems(spawnLoc_list)
        self.spawningLocation.setCurrentIndex(spawnLoc_list.index("unknown"))

        ##################################################################


        # Get institutions from database
        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT    "institutionCode"
            FROM      nofa."m_dataset"
            ''')
        institutions = cur.fetchall()

        # Create a python-list from query result
        self.institution_list = [i[0] for i in institutions]

        # Inject sorted python-list for existingProjects into UI
        self.institution_list.sort()

        ##################################################################

        self.dateStart.setDate(self.today)
        self.dateEnd.setDate(self.today)
        self.verifiedDate.setDate(self.nextWeek)

        """
        locIDType_dict = {'coordinates lon/lat': 4326,
                          'Norwegian VatnLnr': 'no_vatn_lnr',
                          'Swedish SjoID': 'se_sjoid',
                          'Finish nro': 'fi_nro',
                          'coordinates UTM32': 25832,
                          'coordinates UTM33': 25833,
                          'coordinates UTM35': 25835,
                          'waterBody register name': '"waterBody"'
                          }
        """


        # Add more location match options (e.g. coordinates)

        locIDType_list = self.locIDType_dict.keys()
        locIDType_list.sort()

        self.locIDType.clear()
        self.locIDType.addItems(locIDType_list)
        self.locIDType.setCurrentIndex(locIDType_list.index("Norwegian VatnLnr"))

        ###################################################################
        # Create the Taxonomic Coverage list of taxa

        cur = self._get_db_cur()

        cur.execute(u'SELECT "{0}", "{1}" FROM nofa.l_taxon GROUP BY "{0}", "{1}";'.format(self.species_names[self.language], "family"))
        species = cur.fetchall()

        taxa = defaultdict(list)

        for s in species:
            if s[1] is not None:
                taxa[s[1]].append(s[0])

        #QMessageBox.information(None, "DEBUG:", str(taxa))

        self.taxonomicCoverage.clear()

        families = []
        root = QTreeWidgetItem(self.taxonomicCoverage, ["All"])
        root.setCheckState(0, Qt.Unchecked)
        root.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

        for family in taxa.keys():
            #families.append(family)

            if family not in (""):
                item = QTreeWidgetItem(root, [family])

                item.setCheckState(0, Qt.Unchecked)
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

                families.append(item)

                taxa_list = []
                for taxon in taxa[family]:
                    if taxon is not None:
                        child = QTreeWidgetItem(item, [taxon])

                        child.setCheckState(0, Qt.Unchecked)
                        child.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

                        taxa_list.append(child)

        self.taxonomicCoverage.expandToDepth(0)

        #QMessageBox.information(None, "DEBUG:", str(type(families)))

        #self.taxonomicCoverage.topLevelItem(root)

        '''
        taxa = []
        self.taxonomicCoverage.clear()
        for species in species_list:
            if species is not None:
                item = QTreeWidgetItem([species])
                item.setCheckState(0, Qt.Unchecked)
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

                taxa.append(item)

        #QMessageBox.information(None, "DEBUG:", unicode(type(taxa)))
        self.taxonomicCoverage.addTopLevelItems(taxa)

            #QMessageBox.information(None, "DEBUG:", unicode(species))

        '''

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
            ORDER BY    dsn;
            ''')
        dtsts = cur.fetchall()

        dtst_list = [
            self.get_dtst_str(d[0], d[1]) for d in dtsts]
        dtst_list.insert(0, self.sel_str)

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

    def pop_prj_cb(self):
        """
        Populates the project combo box.
        """

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      "organisation" o,
                        "projectNumber" pno,
                        "projectName" pn
            FROM        nofa."m_project"
            ORDER BY    o, pno, pn;
            ''')
        prjs = cur.fetchall()

        proj_list = [
            self.get_prj_str(p[0], p[1], p[2]) for p in prjs]
        proj_list.insert(0, self.sel_str)

        self.prj_cb.clear()
        self.prj_cb.addItems(proj_list)

    def get_prj_str(self, org, no, name):
        """
        Returns a project string "<organisation> - <number> - <name>"

        :param org: A project organization.
        :type org: str.
        :param no: A project number.
        :type no: str.
        :param name: A project name.
        :type name: str.
        """

        prj_str = u'{}{}{}{}{}'.format(
            org, self.dash_split_str, no, self.dash_split_str, name)

        return prj_str

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
        ref_list.insert(0, self.sel_str)

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
            FROM        nofa.l_taxon
            WHERE       "taxonRank" IN ('species', 'hybrid', 'genus')
            ORDER BY    sn
            ''')
        txns = cur.fetchall()

        txn_list = [t[0] for t in txns]
        txn_list.insert(0, self.sel_str)

        self.taxonID.clear()
        self.taxonID.addItems(txn_list)

    def _pop_ectp_cb(self):
        """
        Populates the ecotype combo box.
        """

        txn_name = self.taxonID.currentText()

        cur = self._get_db_cur()
        cur.execute(
            '''
            SELECT      e."vernacularName" vn
            FROM        nofa.l_ecotype e
                        JOIN
                        nofa.l_taxon t ON e."taxonID" = t."taxonID"
            WHERE       t."scientificName" = %s
            ORDER BY    vn;
            ''',
            (txn_name,))
        ectps = cur.fetchall()

        ectp_list = [e[0] for e in ectps]
        ectp_list.insert(0, self.sel_str)

        self.ecotypeID.clear()
        self.ecotypeID.addItems(ectp_list)

    def update_occurrence(self):
        """syncs the occurrence form with the chosen row of the occurrence table"""

        # set current taxon value
        taxon_index = self.taxonID.findText(self.occurrence['taxon'][self.row_position], Qt.MatchFixedString)
        self.taxonID.setCurrentIndex(taxon_index)

        ecotype_index = self.ecotypeID.findText(self.occurrence['ecotype'][self.row_position], Qt.MatchFixedString)
        self.ecotypeID.setCurrentIndex(ecotype_index)

        quantity_index = self.organismQuantityID.findText(self.occurrence['quantity'][self.row_position], Qt.MatchFixedString)
        self.organismQuantityID.setCurrentIndex(quantity_index)

        self.oq_metric.setText(str(self.occurrence['metric'][self.row_position]))

        status_index = self.status.findText(self.occurrence['status'][self.row_position], Qt.MatchFixedString)
        self.status.setCurrentIndex(status_index)

        trend_index = self.trend.findText(self.occurrence['trend'][self.row_position], Qt.MatchFixedString)
        self.trend.setCurrentIndex(trend_index)
        '''if self.occurrence['status'][self.row_position] == 'True':
            self.occurrenceStatus.setChecked(True)
        else:
            self.occurrenceStatus.setChecked(False)
        '''
        self.occurrenceRemarks.setText(self.occurrence['oc_remarks'][self.row_position])

        est_means_index = self.establishmentMeans.findText(self.occurrence['est_means'][self.row_position], Qt.MatchFixedString)
        self.establishmentMeans.setCurrentIndex(est_means_index)

        spawn_con_index = self.spawningCondition.findText(self.occurrence['spawn_con'][self.row_position], Qt.MatchFixedString)
        self.spawningCondition.setCurrentIndex(spawn_con_index)

        spawn_loc_index = self.spawningLocation.findText(self.occurrence['spawn_loc'][self.row_position], Qt.MatchFixedString)
        self.spawningLocation.setCurrentIndex(spawn_loc_index)

        self.establishmentRemarks.setText(self.occurrence['est_remarks'][self.row_position])

        self.verifiedBy.setText(self.occurrence['verified_by'][self.row_position])

        self.yearPrecisionRemarks.setText(self.occurrence['yearprecision_remarks'][self.row_position])

        self.occurrence_number.setText(str(self.row_position + 1))
        self.occurrence_number.setStyleSheet('color: black')
        # self.frame.setStyleSheet('color: white')

    def create_occurrence_table(self):
        """creates occurrence table and populates it one row of default values"""

        #currentrow = self.tableWidget.rowCount()
        #self.tableWidget.insertRow(currentrow)

        #set rows and columns for tableWidget
        self.tableWidget.setRowCount(len(self.occurrence['taxon']))
        self.tableWidget.setColumnCount(12)
        self.row_position = 0

        self.tableWidget.setSelectionBehavior(QTableWidget.SelectRows);

        #  populate tableWidget
        headers = []
        for n, key in enumerate(sorted(self.occurrence.keys())):
            headers.append(key)
            for m, item in enumerate(self.occurrence[key]):
                try:
                    newitem = QTableWidgetItem(item)
                except:
                    newitem = QTableWidgetItem(str(item))
                # setItem(row, column, QTableWidgetItem)
                self.tableWidget.setItem(m, n, newitem)
            self.tableWidget.setHorizontalHeaderLabels(headers)

        self.update_occurrence_form()
        #QMessageBox.information(None, "DEBUG:", str(headers))

    def add_occurrence(self):
        """ adds a new occurrence row in occurrence table """

        # check if Table has some entries
        # check if last row is empty

        if (self.tableWidget.rowCount() > 0 and self.is_last_row_empty()):
            # do not add an occurrence
            QMessageBox.information(None, "Information",
                                    "The last occurrence is empty. " +
                                    "You have to finish it before you can enter a new occurrence.")
            return


        # adds a new occurrence row in occurrence table
        self.row_position = self.tableWidget.rowCount()
        self.tableWidget.insertRow(self.row_position)

        # add a new occurrence record in self.occurrence dictionary and table
        for n, key in enumerate(sorted(self.occurrence.keys())):
            item = self.occurrence_base[key]
            self.occurrence[key].append(item)
            # add it to table
            if isinstance(item, datetime.date):
                item = unicode(item)
            new_item = QTableWidgetItem(item)
            self.tableWidget.setItem(self.row_position, n, new_item)

        self.tableWidget.selectRow(self.row_position)
        self.update_occurrence_form()

        self.preview_conditions['taxon_selected'] = False
        self.preview_conditions['est_means_selected'] = False
        self.check_preview_conditions()

       #QMessageBox.information(None, "DEBUG:", str(self.row_position))

    def is_last_row_empty(self):
        """Checks if last row is empty"""

        # use last row number in case not the last occurrence is clicked
        last_row_number = self.tableWidget.rowCount() - 1

        # iterate trough values of last row
        for key, value in self.occurrence.iteritems():

            value_last_row = value[last_row_number]
            value_default = self.occurrence_base[key]

            # compare with default values
            if value_last_row != value_default:
                # if any of the occurrence's values differs from default
                return False

        return True

    def update_occurrence_form(self):
        """Adds occurrence title and syncs form with table"""

        #QMessageBox.information(None, "DEBUG:", str("Occurrence - " + str(self.row_position)))
        # update values in occurrence form based on current row selection in table widget
        self.reference_4.setTitle("Occurrence - " + unicode(self.row_position + 1))
        self.update_occurrence()

    def update_row(self, widget_object):
        self.row_position = widget_object.row()
        self.update_occurrence_form()
        #QMessageBox.information(None, "DEBUG:", str(widget_object.row()))

    def update_header(self, header_index):

        #QMessageBox.information(None, "DEBUG:", str(header_index))
        self.row_position = header_index
        self.update_occurrence_form()

    def row_up(self):
        # moving selection one row up in occurrence table
        if self.row_position > 0:
            self.row_position = self.row_position - 1
        self.tableWidget.selectRow(self.row_position)
        self.update_occurrence_form()

    def row_down(self):
        # moving selection one row down in occurrence table
        if self.row_position < (self.tableWidget.rowCount() - 1):
            self.row_position = self.row_position + 1
        self.tableWidget.selectRow(self.row_position)
        self.update_occurrence_form()

