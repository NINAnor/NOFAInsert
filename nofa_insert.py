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
    QTableWidgetItem, QColor, QFont, QCompleter, QLineEdit, QDialog)

from qgis.core import *

import resources

from nofa import con_dlg

from nofa_insert_dialog import NOFAInsertDialog
from dataset_dialog import DatasetDialog
from project_dialog import ProjectDialog
from reference_dialog import ReferenceDialog
from preview_dialog import PreviewDialog

from collections import defaultdict
import os.path
import psycopg2, psycopg2.extras
import logging
import datetime
import uuid
import sys


class NOFAInsert:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
        psycopg2.extras.register_uuid()

        # Save reference to the QGIS interface
        self.iface = iface
        # initialize plugin directory
        self.plugin_dir = os.path.dirname(__file__)
        # initialize locale
        locale = QSettings().value('locale/userLocale')[0:2]
        locale_path = os.path.join(
            self.plugin_dir,
            'i18n',
            'NOFAInsert_{}.qm'.format(locale))

        if os.path.exists(locale_path):
            self.translator = QTranslator()
            self.translator.load(locale_path)

            if qVersion() > '4.3.3':
                QCoreApplication.installTranslator(self.translator)
        
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

        self.insert_location = """INSERT INTO nofa.location (locationID, "locationType", geom, "waterBody", "locationRemarks") VALUES (%s, %s, %s, %s, %s);"""

        self.insert_taxonomic_coverage = """INSERT INTO nofa.taxonomicCoverage("taxonID_l_taxon", "eventID_observationEvent") VALUES (%s,%s);"""
        # creating the string for event data insertion to nofa.event table. fieldNotes is used just for testing purposes
        self.insert_event = u"""INSERT INTO nofa.event ("locationID", "eventID",
                            "sampleSizeValue", "samplingProtocolRemarks", "recordedBy",
                            "samplingProtocol", "reliability", "dateStart", "dateEnd", "eventRemarks",
                            "sampleSizeUnit", "samplingEffort", "datasetID", "associatedReferences", "projectID", "fieldNotes")
                            VALUES\n"""


        # 16 event values, placeholders
        self.event_values = u'(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'
        # 16 occurrence values, placeholders
        self.occurrence_values = u'(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'

        # TODO - remove "fieldNumber" column, used for testing purposes
        self.insert_occurrence = u"""INSERT INTO nofa.occurrence ("occurrenceID",
                                    "ecotypeID", "establishmentMeans", "verifiedBy", "verifiedDate", "taxonID",
                                    "spawningLocation", "spawningCondition", "occurrenceStatus", "populationTrend",
                                    "yearPrecisionRemarks", "organismQuantityID",
                                    "occurrenceRemarks", "modified", "establishmentRemarks", "eventID", "organismQuantityMetric", "fieldNumber")
                                    VALUES\n"""

        self.insert_log_occurrence = u"""INSERT INTO nofa.plugin_occurrence_log ("occurrence_id",
                                    "event_id", "dataset_id", "project_id", "reference_id", "location_id",
                                    "test", "username")
                                    VALUES\n"""

        self.insert_dataset = u"""INSERT INTO nofa.m_dataset ("rightsHolder", "ownerInstitutionCode",
                                    "datasetName", "accessRights", "license", "bibliographicCitation", "datasetComment",
                                    "informationWithheld", "dataGeneralization")
                                    VALUES\n"""



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



        self.preview_conditions = {"dataset_selected": False,
                                   'project_selected': False,
                                   'taxon_selected': False,
                                   'est_means_selected': False,
                                   'quantity': False
                                  }

        self.language = 'Latin'

        self.species_names = {'Latin': 'scientificName',
                              'English': 'vernacularName',
                              'Norwegian': 'vernacularName_NO',
                              'Swedish': 'vernacularName_SE',
                              'Finish': 'vernacularName_FI'}

        ## Country codes not used for the moment
        '''countryCodes = {'Latin': None,
                        'English': None,
                        'Norwegian': 'NO',
                        'Swedish': 'SE',
                        'Finish': 'FI'}'''

        #TODO the remaining location types should be added here
        self.locIDType_dict = {'Norwegian VatnLnr': 'no_vatn_lnr',
                          'coordinates UTM32': 25832,
                          'coordinates UTM33': 25833,
                          }


        self.ecotypes = {26164: ['Salmon', 'Landlocked Salmon', 'Relict Salmon'],
                         26165: ['Brown trout', 'Anadromous Brown Trout', 'Big Piscivorous Brown Trout', 'Fine-spotted Brown Trout', 'Danish River Trout'],
                         26167: ['Arctic Charr', 'Anadromous Arctic Charr', 'Arctic Charr Dwarf', 'Saimaa Arctic Charr'],
                         26175: ['Vendace', 'Spring Spawning Vendace'],
                         26176: ['Whitefish', 'Plankton Whitefish']
                        }



        self.occurrence_base = {'taxon': 'Select',
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
                           'yearprecision_remarks': 'None'
                            }

        self.occurrence = {'taxon': ['Select', ],
                           'ecotype': ['Select', ],
                           'quantity': ['Select', ],
                           'metric': [0, ],
                           'status': ['unknown', ],
                           'trend': ['unknown', ],
                           'oc_remarks': ['None', ],
                           'est_means': ['Select', ],
                           'est_remarks': ['None', ],
                           'spawn_con': ['unknown', ],
                           'spawn_loc': ['unknown', ],
                           'verified_by': ['Nobody', ],
                           'verified_date': [self.today, ],
                           'yearprecision_remarks': ['None', ]
                           }

        self.taxonomicc = []

        self.event = {'protocol': 'unknown',
                      'size_value': None,
                      'size_unit': 'None',
                      'effort': 'unknown',
                      'protocol_remarks': 'None',
                      'date_start': self.today,
                      'date_end': self.today,
                      'recorded_by': 'unknown',
                      'event_remarks': 'None',
                      'reliability': 'Select'
                      }

        self.dataset = {'dataset_id': 'None',
                        'rightsholder': 'None',
                        'dataset_name': 'None',
                        'owner_institution': 'None',
                        'access_rights': 'None',
                        'license': 'None',
                        'citation': 'None',
                        'comment': 'None',
                        'information': 'None',
                        'generalizations': 'None'
                        }

        self.project = {'project_id': 'None',
                        'project_name': 'None',
                        'project_number': 'None',
                        'start_year': unicode(self.year),
                        'end_year': unicode(self.year),
                        'leader': 'None',
                        'members': 'None',
                        'organisation': 'None',
                        'financer': 'None',
                        'project_remarks': 'None'
                        }

        self.reference = {'reference_id': 'None',
                          'doi': 'None',
                          'authors': 'None',
                          'reference_type': 'None',
                          'year': unicode(self.year),
                          'title': 'None',
                          'journal': 'None',
                          'volume': 'None',
                          'date': unicode(self.today),
                          'issn': 'None',
                          'isbn': 'None',
                          'page': 'None'
                          }

        # temporary list, to replace the currently empty table l_occurrenceStatus. Will be used in the occurrence status dropdown
        self.occurrence_status = ['unknown', 'absent', 'common', 'doubtful', 'excluded', 'irregular', 'present', 'rare']

        self.population_trend = ['unknown', 'increasing', 'decrasing', 'stable', 'extinction', 'introduction', 're-introduction']

        '''
        # collect the multiple data and metadata containers into a single object, a dictionary of dictionaries/lists.
        self.container = {'locations': self.locations,
                          'occurrence': self.occurrence,
                          'taxonomicc': self.taxonomicc,
                          'event': self.event,
                          'dataset': self.dataset,
                          'project': self.project,
                          'reference': self.reference}
        '''
        # noinspection PyMethodMayBeStatic

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


    def add_action(
        self,
        icon_path,
        text,
        callback,
        enabled_flag=True,
        add_to_menu=True,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None):
        """Add a toolbar icon to the toolbar.

        :param icon_path: Path to the icon for this action. Can be a resource
            path (e.g. ':/plugins/foo/bar.png') or a normal file system path.
        :type icon_path: str

        :param text: Text that should be shown in menu items for this action.
        :type text: str

        :param callback: Function to be called when the action is triggered.
        :type callback: function

        :param enabled_flag: A flag indicating if the action should be enabled
            by default. Defaults to True.
        :type enabled_flag: bool

        :param add_to_menu: Flag indicating whether the action should also
            be added to the menu. Defaults to True.
        :type add_to_menu: bool

        :param add_to_toolbar: Flag indicating whether the action should also
            be added to the toolbar. Defaults to True.
        :type add_to_toolbar: bool

        :param status_tip: Optional text to show in a popup when mouse pointer
            hovers over the action.
        :type status_tip: str

        :param parent: Parent widget for the new action. Defaults None.
        :type parent: QWidget

        :param whats_this: Optional text to show in the status bar when the
            mouse pointer hovers over the action.

        :returns: The action that was created. Note that the action is also
            added to self.actions list.
        :rtype: QAction
        """

        self.row_position = 0

        # Create the dialog (after translation) and keep reference
        self.dlg = NOFAInsertDialog()

        self.dlg.insert_button.setStyleSheet("background-color: #F6CECE")

        self.dlg.editDatasetButton.clicked.connect(self._open_dataset_dialog)
        self.dlg.editProjectButton.clicked.connect(self.open_project_dialog)
        self.dlg.edit_reference_button.clicked.connect(self.open_reference_dialog)


        self.dlg.existingDataset.currentIndexChanged.connect(self.update_dataset)
        self.dlg.existingProject.currentIndexChanged.connect(self.update_project)
        self.dlg.existingReference.currentIndexChanged.connect(self.update_reference)

        self.dlg.insert_button.clicked.connect(self.preview)

        self.dlg.addOccurrence.clicked.connect(self.add_occurrence)

        # Up and Down buttons to move selection of the occurrence table
        self.dlg.upButton.clicked.connect(self.row_up)
        self.dlg.downButton.clicked.connect(self.row_down)

        self.dlg.deleteOccurrence.clicked.connect(self.delete_occurrence_row)

        # Table clicked events
        self.dlg.tableWidget.itemClicked.connect(self.update_row)
        self.dlg.tableWidget.verticalHeader().sectionClicked.connect(self.update_header)
        # set the occurrenceStatus checkbox to True, as a default initial status
        #self.dlg.occurrenceStatus.setChecked(True)

        #connect the occurrence input widgets to table content
        self.dlg.update_row_button.clicked.connect(self.update_occurrence_row)

        # trigger action when history tabs are clicked
        self.dlg.tabWidget.currentChanged.connect(self.history_tab_clicked)
        self.dlg.tabWidget_history.currentChanged.connect(self.history_tab_clicked)

        self.dlg.taxonID.currentIndexChanged.connect(self.look_for_ecotype)

        # taxonomic coverage treewidget parent item changed
        self.dlg.taxonomicCoverage.itemChanged.connect(self.checked_tree)

        # filter occurrences by username and time interval
        self.dlg.username_filter_button.clicked.connect(self.filter_occurrences_by_username)
        self.dlg.time_filter_button.clicked.connect(self.filter_occurrence_by_time)
        self.dlg.combined_filter_button.clicked.connect(self.filter_by_user_and_time)





        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)

        self.actions.append(action)

        return action

    def update_occurrence_row(self):
        """
        Inserts the data from the occurrence form into the occurrence table
        :return: 
        """

        if self.dlg.taxonID.currentText():
            self.occurrence['taxon'][self.row_position] = self.dlg.taxonID.currentText()

            # update the preview conditions for taxon presence
            if self.dlg.taxonID.currentText() != 'Select':
                #QMessageBox.information(None, "DEBUG:", str(self.occurrence['taxon']))
                if 'Select' not in self.occurrence['taxon']:
                    self.preview_conditions['taxon_selected'] = True
                    self.check_preview_conditions()
            elif self.dlg.taxonID.currentText() == 'Select':
                self.preview_conditions['taxon_selected'] = False
                self.check_preview_conditions()
        else:
            self.occurrence['taxon'][self.row_position] = 'None'

        if self.dlg.establishmentMeans.currentText():
            self.occurrence['est_means'][self.row_position] = self.dlg.establishmentMeans.currentText()

            if self.dlg.establishmentMeans.currentText() != ' ' or self.dlg.establishmentMeans.currentText() != 'Select':
                #QMessageBox.information(None, "DEBUG:", str(self.occurrence['taxon']))
                if 'Select' not in self.occurrence['est_means']:
                    self.preview_conditions['est_means_selected'] = True
                    self.check_preview_conditions()
            elif self.dlg.establishmentMeans.currentText() == 'Select' or self.dlg.establishmentMeans.currentText() == ' ':
                self.preview_conditions['est_means_selected'] = False
                self.check_preview_conditions()


        if self.dlg.organismQuantityID.currentText():
            self.occurrence['quantity'][self.row_position] = self.dlg.organismQuantityID.currentText()

            if self.dlg.organismQuantityID.currentText() != ' ' or self.dlg.organismQuantityID.currentText() != 'Select':
                #QMessageBox.information(None, "DEBUG:", str(self.occurrence['taxon']))
                if 'Select' not in self.occurrence['quantity']:
                    self.preview_conditions['quantity'] = True
                    self.check_preview_conditions()
            elif self.dlg.organismQuantityID.currentText() == 'Select' or self.dlg.organismQuantityID.currentText() == ' ':
                self.preview_conditions['quantity'] = False
                self.check_preview_conditions()

        self.occurrence['ecotype'][self.row_position] = self.dlg.ecotypeID.currentText()
        #QMessageBox.information(None, "DEBUG:", str(self.occurrence['ecotype'][self.row_position]))


        #self.occurrence['quantity'][self.row_position] = self.dlg.organismQuantityID.currentText()
        self.occurrence['metric'][self.row_position] = self.dlg.oq_metric.text()
        self.occurrence['status'][self.row_position] = self.dlg.status.currentText()
        self.occurrence['trend'][self.row_position] = self.dlg.trend.currentText()
        self.occurrence['oc_remarks'][self.row_position] = self.dlg.occurrenceRemarks.text()

        self.occurrence['est_remarks'][self.row_position] = self.dlg.establishmentRemarks.text()
        self.occurrence['spawn_con'][self.row_position] = self.dlg.spawningCondition.currentText()
        self.occurrence['spawn_loc'][self.row_position] = self.dlg.spawningLocation.currentText()
        self.occurrence['verified_by'][self.row_position] = self.dlg.verifiedBy.text()
        self.occurrence['verified_date'][self.row_position] = self.dlg.verifiedDate.date()
        self.occurrence['yearprecision_remarks'][self.row_position] = self.dlg.yearPrecisionRemarks.text()


        for m, key in enumerate(sorted(self.occurrence.keys())):
            item = self.occurrence[key][self.row_position]
            try:
                newitem = QTableWidgetItem(item)
            except:
                newitem = QTableWidgetItem(unicode(item))
            # setItem(row, column, QTableWidgetItem)
            self.dlg.tableWidget.setItem(self.row_position, m, newitem)

    def delete_occurrence_row(self):
        """Delete a row from occurrence table on button click."""

        # checks if table contains occurrences
        if self.dlg.tableWidget.rowCount()==0:
            return

        for i, key in enumerate(self.occurrence.keys()):
            del self.occurrence[key][self.row_position]

        self.dlg.tableWidget.removeRow(self.row_position)

        self.row_position = 0
        self.dlg.tableWidget.selectRow(self.row_position)
        self.dlg.occurrence_number.setText(unicode(self.row_position + 1))

        # Check if some row with taxon remains:
        if 'Select' in self.occurrence['taxon']:
            self.preview_conditions['taxon_selected'] = False
            self.check_preview_conditions()
        elif 'Select' not in self.occurrence['taxon']:
            self.preview_conditions['taxon_selected'] = True
            self.check_preview_conditions()

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/NOFAInsert/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'NOFAInsert'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def history_tab_clicked(self):
        #QMessageBox.information(None, "DEBUG:",  str(self.dlg.tabWidget.currentIndex()))

        if self.dlg.tabWidget_history.currentIndex() == 0:
            #QMessageBox.information(None, "DEBUG:", str(self.dlg.tabWidget.currentIndex()))

            self.dlg.date_from.setDate(self.today)
            self.dlg.date_to.setDate(self.today)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  DISTINCT "username" FROM nofa.plugin_occurrence_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. occurrences not fetched from db"))

            usernames_fetched = cur.fetchall()

            username_list = [s[0] for s in usernames_fetched]

            # Inject sorted python-list for spawningCondition into UI
            username_list.sort()
            self.dlg.usernames.clear()
            self.dlg.usernames.addItems(username_list)



            self.row_position = 0

            self.dlg.tableWidget_occurrences.setSelectionBehavior(QTableWidget.SelectRows)

            #  populate tableWidget

            cur = self._get_db_cur()
            try:
                cur.execute(u'SELECT  "occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_occurrence_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. occurrences not fetched from db"))

            fetched_occ = cur.fetchall()

            lim = len(fetched_occ)

            self.dlg.tableWidget_occurrences.setRowCount(lim)
            self.dlg.tableWidget_occurrences.setColumnCount(9)

            headers = ["occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id",
                       "username", "insert_time", "update_time"]
            self.dlg.tableWidget_occurrences.setHorizontalHeaderLabels(headers)

            for l in range(lim):
                occurrence = fetched_occ[l]
                for n, item in enumerate(occurrence):


                    newitem = QTableWidgetItem(unicode(occurrence[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.dlg.tableWidget_occurrences.setItem(l, n, newitem)

        elif self.dlg.tabWidget_history.currentIndex() == 1:
            # add locations log entries to history -> locations
            self.dlg.tableWidget_locations.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "location_id", "username", "location_name", "insert_timestamp", "update_timestamp" FROM nofa.plugin_location_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. location logs not fetched from db"))

            fetched_location_logs = cur.fetchall()

            lim = len(fetched_location_logs)

            self.dlg.tableWidget_locations.setRowCount(lim)
            self.dlg.tableWidget_locations.setColumnCount(5)

            headers = ["dataset_id", "username", "location_name", "insert_time", "update_time"]
            self.dlg.tableWidget_locations.setHorizontalHeaderLabels(headers)

            for l in range(lim):
                locations = fetched_location_logs[l]
                for n, item in enumerate(locations):

                    newitem = QTableWidgetItem(unicode(locations[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.dlg.tableWidget_locations.setItem(l, n, newitem)

        elif self.dlg.tabWidget_history.currentIndex() == 2:
            self.dlg.tableWidget_datasets.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "dataset_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_dataset_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. datasets not fetched from db"))

            fetched_datasets = cur.fetchall()

            lim = len(fetched_datasets)

            self.dlg.tableWidget_datasets.setRowCount(lim)
            self.dlg.tableWidget_datasets.setColumnCount(4)

            headers = ["dataset_id", "username", "insert_time", "update_time"]
            self.dlg.tableWidget_datasets.setHorizontalHeaderLabels(headers)

            for l in range(lim):
                dataset = fetched_datasets[l]
                for n, item in enumerate(dataset):

                    newitem = QTableWidgetItem(unicode(dataset[n]))

                        # setItem(row, column, QTableWidgetItem)
                    self.dlg.tableWidget_datasets.setItem(l, n, newitem)

        elif self.dlg.tabWidget_history.currentIndex() == 3:

            self.dlg.tableWidget_projects.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "project_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_project_log')
            except:
                QMessageBox.information(None, "DEBUG:", unicode(
                    "WARNING - DB ERROR. projects not fetched from db"))

            fetched_projects = cur.fetchall()

            lim = len(fetched_projects)

            self.dlg.tableWidget_projects.setRowCount(lim)
            self.dlg.tableWidget_projects.setColumnCount(4)

            headers = ["project_id", "username", "insert_time", "update_time"]
            self.dlg.tableWidget_projects.setHorizontalHeaderLabels(headers)

            for l in range(lim):
                projects = fetched_projects[l]
                for n, item in enumerate(projects):
                    newitem = QTableWidgetItem(unicode(projects[n]))

                    # setItem(row, column, QTableWidgetItem)
                    self.dlg.tableWidget_projects.setItem(l, n, newitem)

        elif self.dlg.tabWidget_history.currentIndex() == 4:

            self.dlg.tableWidget_references.setSelectionBehavior(QTableWidget.SelectRows)

            cur = self._get_db_cur()
            try:
                cur.execute(
                    u'SELECT  "reference_id", "username", "insert_timestamp", "update_timestamp" FROM nofa.plugin_reference_log')
            except:
                pass

            fetched_references = cur.fetchall()

            lim = len(fetched_references)

            self.dlg.tableWidget_references.setRowCount(lim)
            self.dlg.tableWidget_references.setColumnCount(4)

            headers = ["reference_id", "username", "insert_time", "update_time"]
            self.dlg.tableWidget_references.setHorizontalHeaderLabels(headers)

            for l in range(lim):
                references = fetched_references[l]
                for n, item in enumerate(references):
                    newitem = QTableWidgetItem(unicode(references[n]))

                    # setItem(row, column, QTableWidgetItem)
                    self.dlg.tableWidget_references.setItem(l, n, newitem)

    def filter_occurrences_by_username(self):

        username = self.dlg.usernames.currentText()

        cur = self._get_db_cur()

        try:
            cur.execute(
                u'SELECT  "occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id", "username", "insert_timestamp", "update_timestamp" '
                u'FROM nofa.plugin_occurrence_log WHERE "username" = %s', (username,))
        except:
            QMessageBox.information(None, "DEBUG:", unicode(
                "WARNING - DB ERROR. occurrences not fetched from db"))

        fetched_occ = cur.fetchall()

        lim = len(fetched_occ)

        self.dlg.tableWidget_occurrences.setRowCount(lim)
        self.dlg.tableWidget_occurrences.setColumnCount(9)

        headers = ["occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id",
                   "username", "insert_time", "update_time"]
        self.dlg.tableWidget_occurrences.setHorizontalHeaderLabels(headers)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.dlg.tableWidget_occurrences.setItem(l, n, newitem)

    def filter_occurrence_by_time(self):

        time_from = self.dlg.date_from.date()
        time_to = self.dlg.date_to.date()

        cur = self._get_db_cur()

        try:
            cur.execute(
                u'SELECT  "occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id", "username", "insert_timestamp", "update_timestamp" '
                u'FROM nofa.plugin_occurrence_log WHERE "insert_timestamp" BETWEEN %s AND %s', (time_from.toPyDate(), time_to.toPyDate(),))
        except:
            QMessageBox.information(None, "DEBUG:", unicode(
                "WARNING - DB ERROR. occurrences not fetched from db"))

        fetched_occ = cur.fetchall()

        lim = len(fetched_occ)

        self.dlg.tableWidget_occurrences.setRowCount(lim)
        self.dlg.tableWidget_occurrences.setColumnCount(9)

        headers = ["occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id",
                   "username", "insert_time", "update_time"]
        self.dlg.tableWidget_occurrences.setHorizontalHeaderLabels(headers)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.dlg.tableWidget_occurrences.setItem(l, n, newitem)

    def filter_by_user_and_time(self):

        username = self.dlg.usernames.currentText()

        time_from = self.dlg.date_from.date()
        time_to = self.dlg.date_to.date()

        cur = self._get_db_cur()

        try:
            cur.execute(
                u'SELECT  "occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id", "username", "insert_timestamp", "update_timestamp" '
                u'FROM nofa.plugin_occurrence_log WHERE "username" = %s AND "insert_timestamp" BETWEEN %s AND %s',
                (username, time_from.toPyDate(), time_to.toPyDate(),))
        except:
            QMessageBox.information(None, "DEBUG:", unicode(
                "WARNING - DB ERROR. occurrences not fetched from db"))

        fetched_occ = cur.fetchall()

        lim = len(fetched_occ)

        self.dlg.tableWidget_occurrences.setRowCount(lim)
        self.dlg.tableWidget_occurrences.setColumnCount(9)

        headers = ["occurrence_id", "event_id", "dataset_id", "project_id", "reference_id", "location_id",
                   "username", "insert_time", "update_time"]
        self.dlg.tableWidget_occurrences.setHorizontalHeaderLabels(headers)

        for l in range(lim):
            occurrence = fetched_occ[l]
            for n, item in enumerate(occurrence):
                newitem = QTableWidgetItem(unicode(occurrence[n]))

                # setItem(row, column, QTableWidgetItem)
                self.dlg.tableWidget_occurrences.setItem(l, n, newitem)

    def look_for_ecotype(self):
        taxon_name = self.dlg.taxonID.currentText()
        #QMessageBox.information(None, "DEBUG:", taxon_name)

        if taxon_name is not None and taxon_name not in ("Select"):

            cur = self._get_db_cur()


            string = u"""SELECT "taxonID" FROM nofa."l_taxon" WHERE "{0}" = '{1}';""".format(self.species_names[self.language], taxon_name)
            cur.execute(string)
            taxon = cur.fetchone()[0]

            if taxon in self.ecotypes:
                ecotypes_list = [e for e in self.ecotypes[taxon]]

            # QMessageBox.information(None, "DEBUG:", str(ecotypes_list))
            # Inject sorted python-list for ecotypes into UI
                ecotypes_list.sort()
                ecotypes_list.insert(0, 'None')
                self.dlg.ecotypeID.clear()
                self.dlg.ecotypeID.addItems(ecotypes_list)
            else:
                self.dlg.ecotypeID.clear()
                self.dlg.ecotypeID.addItems(['None',])

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

    def _open_dataset_dialog(self):
        """On button click opens the Dataset Metadata Editing Dialog"""
        self.datadlg = DatasetDialog()
        self.datadlg.show()

        '''
        # Get existingDatasets from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "datasetID", "datasetName" FROM nofa."m_dataset";')
        datasets = cur.fetchall()

        # Create a python-list from query result
        datasetID_list = [d[0] for d in datasets]
        dataset_list = [d[1] for d in datasets]

        # Inject sorted python-list for existingDatasets into UI
        dataset_list.sort()
        dataset_list.insert(0, 'None')
        self.datadlg.existingDataset.clear()
        self.datadlg.existingDataset.addItems(dataset_list)
        self.datadlg.existingDataset.setCurrentIndex(dataset_list.index("None"))
        '''
        ##################################################################

        self.datadlg.rightsHolder.clear()
        self.datadlg.rightsHolder.addItems(self.institution_list)
        self.datadlg.ownerInstitutionCode.clear()
        self.datadlg.ownerInstitutionCode.addItems(self.institution_list)


        #################################################################


        # Add licences
        license_list = ['None', 'NLOD', 'CC-0', 'CC-BY 4.0']
        license_list.sort()
        self.datadlg.license.clear()
        self.datadlg.license.addItems(license_list)



        ################################################################
        # connect the Ok button in dataset dialog to the insert dataset function
        self.datadlg.dataset_dialog_button.clicked.connect(self.dataset_button)

    def dataset_button(self):
        #QMessageBox.information(None, "DEBUG:", str("dataset button pressed"))

        rights_holder = self.datadlg.rightsHolder.currentText()
        owner_institution = self.datadlg.ownerInstitutionCode.currentText()
        dataset_name = self.datadlg.datasetName.text()
        access_rights = self.datadlg.accessRights.text()
        license = self.datadlg.license.currentText()
        bibliographic_citation = self.datadlg.bibliographicCitation.toPlainText()
        dataset_comment = self.datadlg.datasetComment.toPlainText()
        information_withheld = self.datadlg.informationWithheld.toPlainText()
        data_generalizations = self.datadlg.dataGeneralizations.toPlainText()

        '''QMessageBox.information(None, "DEBUG:", unicode(rights_holder + ' ' + owner_institution + ' ' +  dataset_name + ' ' +  access_rights + ' ' +
                                                    bibliographic_citation + ' ' +  dataset_comment + ' ' +  information_withheld + ' ' +
                                                    data_generalizations))
        '''

        cur = self._get_db_cur()
        cur.execute(u'SELECT max("datasetID") FROM nofa.m_dataset;')
        max_dataset_id = cur.fetchone()[0]
        #QMessageBox.information(None, "DEBUG:", str(max_dataset_id))
        new_d_id = max_dataset_id + 1


        cur = self._get_db_cur()

        insert_dataset = cur.mogrify("""INSERT INTO nofa.m_dataset({}) VALUES {} RETURNING "datasetID" """.format(
            self.insert_dataset_columns,
            self.dataset_values
        ), (new_d_id, rights_holder, owner_institution, dataset_name, access_rights, license, bibliographic_citation,
            dataset_comment, information_withheld, data_generalizations,))

        """insert_dataset += cur.mogrify(self.dataset_values, (rights_holder, owner_institution, dataset_name, access_rights,
                                           license, bibliographic_citation, dataset_comment, information_withheld,
                                           data_generalizations,))
        """



        #QMessageBox.information(None, "DEBUG:", insert_dataset)

        cur.execute(insert_dataset)

        returned = cur.fetchone()[0]
        #QMessageBox.information(None, "DEBUG:", str(returned))

        ##################
        # Insert a dataset log entry

        cur = self._get_db_cur()

        insert_dataset_log = cur.mogrify("INSERT INTO nofa.plugin_dataset_log({}) VALUES {}".format(
            self.insert_log_dataset_columns,
            self.log_dataset_values,
        ), (returned, True, self.username,))

        #QMessageBox.information(None, "DEBUG:", insert_dataset_log)

        cur.execute(insert_dataset_log)


        '''

        self.insert_dataset = u"""INSERT INTO nofa.m_dataset ("rightsHolder", "ownerInstitutionCode",
                                    "datasetName", "accessRights", "license", "bibliographicCitation", "datasetComment",
                                    "informationWithheld", "dataGeneralization")
                                    VALUES\n"""

        self.insert_log_dataset_columns = u""""dataset_id", "test",
                                    "username", "insert_timestamp", "update_timestamp""""

         query = cursor.mogrify("INSERT INTO {} ({}) VALUES {} RETURNING {}".format(
            table,
            ', '.join(keys),
            ', '.join(['%s'] * len(values)),
            id_column
        ), [tuple(v.values()) for v in values])

        self.insert_log_dataset = u"""INSERT INTO nofa.plugin_dataset_log ("dataset_id", "test",
                                    "username", "insert_timestamp", "update_timestamp")
                                    VALUES\n"""

        cur = self._get_db_cur()
        insert_log_dataset = self.insert_log_dataset
        insert_log_dataset += cur.mogrify(self.log_occurrence_values,
                                             (unicode(occurrence_id), unicode(event_id), self.dataset['dataset_id'],
                                              self.project['project_id'],
                                              self.reference['reference_id'], loc, True, self.username,
                                              ))
        cur.execute(insert_log_occurrence)

        sql_string = "INSERT INTO domes_hundred (name,name_slug,status) VALUES (%s,%s,%s) RETURNING id;"

        '''

    def get_location(self):
        '''
        Norwegian VatLnr: 1241, 3067, 5616, 5627, 10688, 10719, 10732, 22480, 23086, 129180, 129182, 129209, 129219, 129444, 163449, 205354
        'coordinates UTM33':    '196098.1000    6572796.0100    Dam Grønnerød,194572.6100    6575712.0100    Dam Løberg'
                                '194572.6100    6575712.0100    løberg dam, 136210.9600    6497277.7500    Springvannsdamm, 149719.5000    6506063.2800    DamKilsund'


        '''

        # initialise data and metadata containers:
        self.locations = {'location_ID': [],
                          'location': [],
                          'loc_type': 'Select',
                          'loc_names': [],
                          'x': [],
                          'y': []
                          }

        self.new_locs = []


        locs = self.dlg.locations.text()
        location_type = self.dlg.locIDType.currentText()
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

                    '''

                                               Norwegian VatLnr: 1241, 3067, 5616, 5627, 10688, 10719, 10732, 22480, 23086, 129180, 129182, 129209, 129219, 129444, 163449, 205354
                                               'coordinates UTM33':    196098.1000    6572796.0100    Dam Grønnerød,194572.6100    6575712.0100    Dam Løberg
                                                                       194572.6100    6575712.0100    løberg dam, 136210.9600    6497277.7500    Springvannsdamm, 149719.5000    6506063.2800    DamKilsund
                                                                       -43893.189 6620749.358 Vågavatnet, 194572.6100    6575712.0100    Dam Løberg
                                                                       262491.48    6651383.97    Akerselva,272567.61    6651129.3    nuggerudbk,342561.74    6792178.06    Våråna,379904.34    6791377.43    Storbekken,377548.06    6791361.56    Nesvollbekken

                                               'coordinates UTM32':    601404.85    6644928.24    Hovinbk; 580033.012    6633807.99    Drengsrudbk;580322.6    6632959.64    Askerleva;658472.23    6842698.72    Engeråa;652499.37    6802699.72    Bruråsbk;
                                                                       634422.28    6788379.28    Flåtestøbk;633855.79    6792859.46    Rødsbakkbk;630580.08    6785079.49    Ygla;628663.92    6785056.12    Svarttjernbk;629047.03    6785047.57    Vesl Ygla;
                                                                       634687.42    6814177.67    Pottbekken;630348.1    6801364.63    Ullsettbk;
                                                                       627139.64    6803681.51    Grønvollbk;530415.53    6722441.27    Åslielva;549629.28    6642631.88    Overnbek;
                                       '''


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
            self.dlg.insert_button.setStyleSheet("background-color: #E0F8EC")
        elif False in self.preview_conditions.values():
            self.dlg.insert_button.setStyleSheet("background-color: #F6CECE")


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

        self.event['protocol'] = self.dlg.samplingProtocol.currentText()
        self.event['size_value'] = self.dlg.sampleSizeValue.text()
        self.event['size_unit'] = self.dlg.sampleSizeUnit.currentText()
        self.event['effort'] = self.dlg.samplingEffort.text()
        self.event['protocol_remarks'] = self.dlg.samplingProtocolRemarks.text()
        #self.event['date_start'] = self.dlg.dateStart.date().toString()
        self.event['date_start'] = self.dlg.dateStart.date()
        #self.event['date_end'] = self.dlg.dateEnd.date().toString()
        self.event['date_end'] = self.dlg.dateEnd.date()
        self.event['recorded_by'] = self.dlg.recordedBy_e.text()
        self.event['event_remarks'] = self.dlg.eventRemarks.text()
        self.event['reliability'] = self.dlg.reliability.currentText()

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
        root = self.dlg.taxonomicCoverage.invisibleRootItem()
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
                #QMessageBox.information(None, "DEBUG:", geom)


                #QMessageBox.information(None, "DEBUG:", str((self.insert_location, (loc[0], location_type, geom, loc[4], 'test',))))

                # Insert any new location into the DB

                #QMessageBox.information(None, "DEBUG:", "insert_location is: " + self.insert_location)
                #QMessageBox.information(None, "DEBUG:", str(type(loc[0])))

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



                    '''

                            Norwegian VatLnr: 1241, 3067, 5616, 5627, 10688, 10719, 10732, 22480, 23086, 129180, 129182, 129209, 129219, 129444, 163449, 205354
                            'coordinates UTM33':    196098.1000    6572796.0100    Dam Grønnerød,194572.6100    6575712.0100    Dam Løberg
                                                    194572.6100    6575712.0100    løberg dam, 136210.9600    6497277.7500    Springvannsdamm, 149719.5000    6506063.2800    DamKilsund
                                                    -43893.189 6620749.358 Vågavatnet, 194572.6100    6575712.0100    Dam Løberg
                                                    262491.48    6651383.97    Akerselva,272567.61    6651129.3    nuggerudbk,342561.74    6792178.06    Våråna,379904.34    6791377.43    Storbekken,377548.06    6791361.56    Nesvollbekken

                            'coordinates UTM32':    601404.85    6644928.24    Hovinbk; 580033.012    6633807.99    Drengsrudbk;580322.6    6632959.64    Askerleva;658472.23    6842698.72    Engeråa;652499.37    6802699.72    Bruråsbk;
                                                    634422.28    6788379.28    Flåtestøbk;633855.79    6792859.46    Rødsbakkbk;630580.08    6785079.49    Ygla;628663.92    6785056.12    Svarttjernbk;629047.03    6785047.57    Vesl Ygla;
                                                    634687.42    6814177.67    Pottbekken;630348.1    6801364.63    Ullsettbk;
                                                    627139.64    6803681.51    Grønvollbk;530415.53    6722441.27    Åslielva;549629.28    6642631.88    Overnbek;
                    '''

                '''

                 insert_project = cur.mogrify("""INSERT INTO nofa.m_project({}) VALUES {} RETURNING "projectID" """.format(
            self.insert_project_columns,
            self.project_values
        ), (new_id, project_name, project_number, start_year.year(), end_year.year(), project_leader, project_members,
            organisation, financer, remarks,))

                self.insert_location = """INSERT INTO nofa.location ("locationID", "locationType", geom, "waterBody", "locationRemarks") VALUES (%s, %s, %s, %s, %s);"""


                try:
                    QMessageBox.information(None, "DEBUG:", "insert_location is: " + self.insert_location)
                    QMessageBox.information(None, "DEBUG:", loc[0])
                    cur.execute(self.insert_location, (loc[0], location_type, geom, loc[4], 'test'))

                    # Keep track of the insertion in the location log table
                    try:
                        cur = self._get_db_cur()
                        insert_location_log = cur.mogrify("INSERT INTO nofa.plugin_location_log({}) VALUES {}".format(
                            self.insert_log_location_columns,
                            self.log_location_values,
                        ), (loc[0], True, self.username, loc[4]))

                        cur.execute(insert_location_log)

                        QMessageBox.information(None, "DEBUG:", "occurrence correctly stored in NOFA db")
                    except:
                        QMessageBox.information(None, "DEBUG:", unicode('problem inserting the new locations to location log db'))


                except:
                    QMessageBox.information(None, "DEBUG:", unicode('problem inserting the new locations to db'))
                '''

        # add a new event to nofa.events fore each location
        for i, loc in enumerate(self.locations['location_ID']):
            #QMessageBox.information(None, "DEBUG:", str('in the event loop'))
            #QMessageBox.information(None, "DEBUG:", str(self.locations))
            #QMessageBox.information(None, "DEBUG:", str(type(self.locations['location_ID'][i])))
            # generate an UUID for the event
            event_id = uuid.uuid4()


            #QMessageBox.information(None, "DEBUG:", str(self.dataset['dataset_id'] + self.reference['reference_id'] +
                                                        #self.project['project_id']))
            insert_event = self.insert_event

            #loc_uuid = uuid.UUID(loc)
            #event_uuid = uuid.UUID(str(event_id)).urn
            #QMessageBox.information(None, "DEBUG:", str(type(loc_uuid)))

           # QMessageBox.information(None, "DEBUG:", 'before ' + str((loc, event_id, self.event['size_value'], self.event['protocol_remarks'], self.event['recorded_by'], self.event['protocol'], self.event['reliability'], self.event['date_start'], self.event['date_end'], self.event['event_remarks'], self.event['size_unit'], self.event['effort'], self.dataset['dataset_id'], self.reference['reference_id'], self.project['project_id'], 'test')))
            ## NB - last entry, 'test', going to fieldNotes, is just for testing purposes


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

            if isinstance(self.dataset['dataset_id'], unicode):

                try:
                    dataset = int(self.dataset['dataset_id'])
                except:
                    QMessageBox.information(None, "DEBUG:",
                                                'The type of datasetid is wrong. Should be integer')
                    return

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
                    QMessageBox.information(None, "DEBUG:",
                                                'The type of project id is wrong. Should be integer')
                    return

            elif isinstance(self.project['project_id'], unicode):
                try:
                    project = int(self.project['project_id'])
                except:
                    QMessageBox.information(None, "DEBUG:", 'Problem with project id')
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


            cur = self._get_db_cur()
            insert_event += cur.mogrify(self.event_values, (loc, event_id, size_value, self.event['protocol_remarks'],
                                                            self.event['recorded_by'], self.event['protocol'], self.event['reliability'],
                                                            start_date, end_date, self.event['event_remarks'],
                                                            self.event['size_unit'], effort, dataset,
                                                            reference, project, 'test',))

            #QMessageBox.information(None, "DEBUG:", str(insert_event))
            #QMessageBox.information(None, "DEBUG:", str(type(loc)) + str(type(event_id))+ str(type(self.event['size_value']))+ str(type(self.event['protocol_remarks']))+ str(type(self.event['recorded_by']))+ str(type(self.event['protocol']))+ str(type(self.event['reliability'])) + str(type(self.event['date_start']))+ str(type(self.event['date_end']))+str(type( self.event['event_remarks']))+ str(type(self.event['size_unit'])) + str(type(effort)) + str(type(dataset)) + str(type(reference)) + str(type(project)) + str(type('text')))

            # Adding taxonomic coverage for a given event

            for tax in self.taxonomicc:
                cur.execute(u"""SELECT "taxonID" FROM nofa."l_taxon" WHERE "%s" = '%s';""",
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


                if self.occurrence['ecotype'][m] == 'None':
                    ecotype_id = None
                else:
                    cur = self._get_db_cur()
                    query = u"""SELECT "ecotypeID" FROM nofa."l_ecotype" WHERE "vernacularName" = '{}';""".format(
                        self.occurrence['ecotype'][m])
                    #QMessageBox.information(None, "DEBUG:", str(query))
                    cur.execute(query)

                    ecotype_id = cur.fetchone()[0]


                # change type of date in a uitable one for postgres
                #verified_date = self.occurrence['verified_date'][m].toPyDate()


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

                insert_occurrence = self.insert_occurrence
                cur = self._get_db_cur()
                insert_occurrence += cur.mogrify(self.occurrence_values,
                                                 (occurrence_id, ecotype_id, self.occurrence['est_means'][m], self.occurrence['verified_by'][m],
                                                  verified_date, taxon, self.occurrence['spawn_loc'][m], self.occurrence['spawn_con'][m],
                                                  self.occurrence['status'][m], self.occurrence['trend'][m], self.occurrence['yearprecision_remarks'][m], self.occurrence['quantity'][m],
                                                  self.occurrence['oc_remarks'][m], self.today, self.occurrence['est_remarks'][m],
                                                  event_id, organismquantity_metric, 'test'))

                #QMessageBox.information(None, "DEBUG:", str(insert_occurrence))


                # insert the new occurrence record to nofa.occurrence
                cur.execute(insert_occurrence)

                # storing memory of insertion to db to log tables
                cur = self._get_db_cur()
                insert_log_occurrence = self.insert_log_occurrence
                insert_log_occurrence += cur.mogrify(self.log_occurrence_values,
                                                 (unicode(occurrence_id), unicode(event_id), self.dataset['dataset_id'], self.project['project_id'],
                                                  self.reference['reference_id'], loc, True, self.username,
                                                  ))
                cur.execute(insert_log_occurrence)

        QMessageBox.information(None, "DEBUG:", "occurrences correctly stored in NOFA db")

        '''
            self.insert_occurrence = u"""INSERT INTO nofa.occurrence ("occurrenceID",
                                    "ecotypeID", "establishmentMeans", "verifiedBy", "verifiedDate", "taxonID",
                                    "spawningLocation", "spawningCondition", "occurrenceStatus",
                                    "yearPrecisionRemarks", "organismQuantityID",
                                    "occurrenceRemarks", "modified", "establishmentRemarks", "eventID", "fieldNumber")
                                    VALUES\n"""


                        self.insert_event = u"""INSERT INTO nofa.event ("locationID", "eventID", "fieldNotes",
                            "sampleSizeValue", "fieldNumber", "samplingProtocolRemarks", "recordedBy",
                            "samplingProtocol", "reliability", "dateStart", "dateEnd", "eventRemarks",
                            "sampleSizeUnit", "samplingEffort", "datasetID", "referenceID", "projectID")
                            VALUES\n"""

        # 17 event values, placeholders
        self.event_values = u'(%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)'

        self.occurrence = {'taxon': ['Select', ],
                           'ecotype': ['Select', ],
                           'quantity': ['Select', ],
                           'status': ['True', ],
                           'oc_remarks': ['None', ],
                           'est_means': ['Select', ],
                           'est_remarks': ['None', ],
                           'spawn_con': ['unknown', ],
                           'spawn_loc': ['unknown', ],
                           'verified_by': ['Nobody', ],
                           'verified_date': [unicode(self.today), ],
                           'yearprecision_remarks': ['None', ]
                           }

         self.event = {'protocol': 'unknown',
                      'size_value': 'unknown',
                      'size_unit': 'None',
                      'effort': 'unknown',
                      'protocol_remarks': 'None',
                      'date_start': self.today,
                      'date_end': self.today,
                      'recorded_by': 'unknown',
                      'event_remarks': 'None',
                      'reliability': 'Select'
                      }

                                    Norwegian VatLnr: 1241, 3067, 5616, 5627, 10688, 10719, 10732, 22480, 23086, 129180, 129182, 129209, 129219, 129444, 163449, 205354
                                    'coordinates UTM33':    196098.1000    6572796.0100    Dam Grønnerød,194572.6100    6575712.0100    Dam Løberg
                                                            194572.6100    6575712.0100    løberg dam, 136210.9600    6497277.7500    Springvannsdamm, 149719.5000    6506063.2800    DamKilsund
                                                            -43893.189 6620749.358 Vågavatnet, 194572.6100    6575712.0100    Dam Løberg
                                                            262491.48    6651383.97    Akerselva,272567.61    6651129.3    nuggerudbk,342561.74    6792178.06    Våråna,379904.34    6791377.43    Storbekken,377548.06    6791361.56    Nesvollbekken

                                    'coordinates UTM32':    601404.85    6644928.24    Hovinbk;580033.012    6633807.99    Drengsrudbk;580322.6    6632959.64    Askerleva;658472.23    6842698.72    Engeråa;652499.37    6802699.72    Bruråsbk;
                                                            634422.28    6788379.28    Flåtestøbk;633855.79    6792859.46    Rødsbakkbk;630580.08    6785079.49    Ygla;628663.92    6785056.12    Svarttjernbk;629047.03    6785047.57    Vesl Ygla;
                                                            634687.42    6814177.67    Pottbekken;630348.1    6801364.63    Ullsettbk;
                                                            627139.64    6803681.51    Grønvollbk;530415.53    6722441.27    Åslielva;549629.28    6642631.88    Overnbek;
                            '''





    def open_project_dialog(self):
        """On button click opens the Project Metadata Editing Dialog"""

        self.prjdlg = ProjectDialog()
        self.prjdlg.show()

        '''
        # Get existingProjects from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "projectID", "projectNumber", "projectName" FROM nofa."m_project";')
        projects = cur.fetchall()

        # Create a python-list from query result
        project_list = [u'{0}: {1}'.format(p[1], p[2]) for p in projects]

        # Inject sorted python-list for existingProjects into UI
        project_list.sort()
        project_list.insert(0, 'None')
        self.prjdlg.existingProject.clear()
        self.prjdlg.existingProject.addItems(project_list)
        self.prjdlg.existingProject.setCurrentIndex(project_list.index("None"))

        #####################################################################
        '''


        self.prjdlg.organisation.clear()
        self.prjdlg.organisation.addItems(self.institution_list)

        #############################################
        # Connect the Ok button to the project insert function

        self.prjdlg.project_dialog_button.clicked.connect(self.project_button)

    def project_button(self):
        """
        method inserting new project entries to m_project table
        and log entries in plugin_project_log
        """

        project_name = self.prjdlg.projectName.text()
        project_number = self.prjdlg.projectNumber.text()
        start_year = self.prjdlg.p_startYear.date()
        end_year = self.prjdlg.p_endYear.date()
        project_leader = self.prjdlg.projectLeader.text()
        project_members = self.prjdlg.project_members.toPlainText()
        organisation = self.prjdlg.organisation.currentText()
        financer = self.prjdlg.financer.text()
        remarks = self.prjdlg.remarks.text()


        cur = self._get_db_cur()
        cur.execute(u'SELECT max("projectID") FROM nofa.m_project;')
        max_proj_id = cur.fetchone()[0]
        #QMessageBox.information(None, "DEBUG:", str(max_proj_id))
        new_id = max_proj_id + 1


        cur = self._get_db_cur()

        insert_project = cur.mogrify("""INSERT INTO nofa.m_project({}) VALUES {} RETURNING "projectID" """.format(
            self.insert_project_columns,
            self.project_values
        ), (new_id, project_name, project_number, start_year.year(), end_year.year(), project_leader, project_members,
            organisation, financer, remarks,))

        #QMessageBox.information(None, "DEBUG:", insert_project)

        cur.execute(insert_project)

        returned = cur.fetchone()[0]
        #QMessageBox.information(None, "DEBUG:", str(returned))

        ##################
        # Insert a dataset log entry

        cur = self._get_db_cur()

        insert_project_log = cur.mogrify("INSERT INTO nofa.plugin_project_log({}) VALUES {}".format(
            self.insert_log_project_columns,
            self.log_project_values,
        ), (returned, True, self.username,))

        #QMessageBox.information(None, "DEBUG:", insert_project_log)

        cur.execute(insert_project_log)

        self.get_existing_projects()



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
        # self.dlg.o_modified.setDate(nextWeek)

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

        insert_reference = cur.mogrify("""INSERT INTO nofa.m_reference({}) VALUES {} RETURNING "referenceID" """.format(
            self.insert_reference_columns,
            self.reference_values
        ), (new_r_id, doi, author, reference_type, int(year.year()), title, journal_name,
            volume, date.toPyDate(), issn, isbn, page,))

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


    def update_dataset(self):
        currentdataset = self.dlg.existingDataset.currentText()
        if currentdataset != 'None' and  currentdataset !='' and currentdataset!= None:

            self.preview_conditions['dataset_selected'] = True
            self.check_preview_conditions()

            # Get dataset record from NOFA db:
            cur = self._get_db_cur()
            cur.execute(
                u'SELECT "datasetID", "datasetName", "rightsHolder", "institutionCode", "license", '
                u'"bibliographicCitation", "datasetComment", "informationWithheld", "dataGeneralizations" '
                u'FROM nofa."m_dataset" WHERE "datasetName" = (%s);',  (currentdataset,))
            dataset = cur.fetchone()

            # Create a python-list from query result
            dataset_list = dataset
            #referenceID_list = [p[0] for p in projects]

            # Inject sorted python-list for existingProjects into UI
            #dataset_list.sort()
            #dataset_list.insert(0, 'None')


            self.dataset['dataset_id'] = unicode(dataset_list[0])
            self.dataset['dataset_name'] = dataset_list[1]
            self.dataset['rightsholder'] = dataset_list[2]
            self.dataset['owner_institution'] = dataset_list[3]
            self.dataset['license'] = dataset_list[4]
            self.dataset['citation'] = dataset_list[5]
            self.dataset['comment'] = dataset_list[6]
            self.dataset['information'] = dataset_list[7]
            self.dataset['generalizations'] = dataset_list[8]

            #QMessageBox.information(None, "DEBUG:", str(self.dataset))

            self.dlg.listview_dataset.clear()
            for key, value in self.dataset.iteritems():
                if value is not None:
                    dstitem = QListWidgetItem(key + ':    ' + value)
                else:
                    dstitem = QListWidgetItem(key + ':    None')

                self.dlg.listview_dataset.addItem(dstitem)

            self.dlg.metadata.setItemText(1, 'Dataset - ' + self.dataset['dataset_name'])

        elif currentdataset == 'None':
            self.dlg.listview_dataset.clear()
            self.dlg.metadata.setItemText(1, 'Dataset - None')

            '''
            self.dlg.display_dataset_1.setText(self.dataset['dataset_name'])
            self.dlg.display_dataset_1.setWordWrap(True)
            self.dlg.display_dataset_2.setText(self.dataset['dataset_id'])
            self.dlg.display_dataset_3.setText(self.dataset['rightsholder'])
            self.dlg.display_dataset_4.setText(self.dataset['owner_institution'])
            self.dlg.display_dataset_5.setText(self.dataset['license'])
            self.dlg.display_dataset_6.setText(self.dataset['citation'])
            self.dlg.display_dataset_6.setWordWrap(True)
            self.dlg.display_dataset_7.setText(self.dataset['comment'])
            self.dlg.display_dataset_7.setWordWrap(True)
            self.dlg.display_dataset_8.setText(self.dataset['information'])
            self.dlg.display_dataset_8.setWordWrap(True)
            self.dlg.display_dataset_9.setText(self.dataset['generalizations'])
            self.dlg.display_dataset_9.setWordWrap(True)
            '''
            #QMessageBox.information(None, "DEBUG:", str(dataset_list))

    def update_project(self):
        """
        Fetches the project attributes from the database and stores them in the project list. 
        """

        # get the current project number from the dropdown menu
        current_index = self.dlg.existingProject.currentIndex()
        current_project_number = self.project_list[current_index][0]

        if current_project_number != 'None' and current_project_number != '':

            self.preview_conditions['project_selected'] = True
            self.check_preview_conditions()

            cur = self._get_db_cur()
            cur.execute(
                u'SELECT "projectNumber", "projectName", "startYear", "endYear", "projectLeader", '
                u'"projectMembers", "organisation", "financer", "remarks", "projectID" '
                u'FROM nofa."m_project" WHERE "projectNumber" = (%s);', (current_project_number,))
            project = cur.fetchone()

        # Create a python-list from query result

            self.project['project_number'] = unicode(project[0])
            self.project['project_name'] = project[1]
            self.project['start_year'] = unicode(project[2])
            self.project['end_year'] = unicode(project[3])
            self.project['project_leader'] = project[4]
            self.project['members'] = project[5]
            self.project['organisation'] = project[6]
            self.project['financer'] = project[7]
            self.project['project_remarks'] = project[8]
            self.project['project_id'] = project[9]

            self.dlg.listview_project.clear()
            for key, value in self.project.iteritems():
                if value is not None:
                    prjitem = QListWidgetItem(key + ':    ' + unicode(value))
                else:
                    prjitem = QListWidgetItem(key + ':    None')

                self.dlg.listview_project.addItem(prjitem)

            self.dlg.metadata.setItemText(2, 'Project - ' + self.project['project_name'])

        elif self.dlg.existingProject.currentText() == 'None':
            self.dlg.listview_project.clear()
            self.dlg.metadata.setItemText(2, 'Project - None')

    def update_reference(self):

        currentref= self.dlg.existingReference.currentText()
        #QMessageBox.information(None, "DEBUG:", str(currentref))

        #QMessageBox.information(None, "DEBUG:", str(currentproject_number))

        if currentref != 'None' and currentref != '' and currentref != None:
            currentref_number = currentref.split('@')[1]
            cur = self._get_db_cur()
            cur.execute(
                u'SELECT "referenceID", "doi", "author", "referenceType", "year", '
                u'"titel", "journalName", "volume", "date", "issn", "isbn", "page" '
                u'FROM nofa."m_reference" WHERE "referenceID" = (%s);', (currentref_number,))
            ref = cur.fetchone()
            #QMessageBox.information(None, "DEBUG:", str(project))


            # Create a python-list from query result

            self.reference['reference_id'] = unicode(ref[0])
            self.reference['doi'] = unicode(ref[1])
            self.reference['authors'] = unicode(ref[2])
            self.reference['reference_type'] = unicode(ref[3])
            self.reference['year'] = unicode(ref[4])
            self.reference['title'] = unicode(ref[5])
            self.reference['journal'] = unicode(ref[6])
            self.reference['volume'] = unicode(ref[7])
            self.reference['date'] = unicode(ref[8])
            self.reference['issn'] = unicode(ref[9])
            self.reference['isbn'] = unicode(ref[10])
            self.reference['page'] = unicode(ref[11])

            self.dlg.listview_reference.clear()
            for key, value in self.reference.iteritems():
                if value is not None:
                    refitem = QListWidgetItem(key + ':    ' + value)
                else:
                    refitem = QListWidgetItem(key + ':    None')

                self.dlg.listview_reference.addItem(refitem)

            # Title should have constraint UNIQUE. Or, we should choose another option for visualizing
            if self.reference['title'] is not None and self.reference['title'] != 'None':
                self.dlg.metadata.setItemText(3, 'Reference - ' + self.reference['title'])
            else:
                self.dlg.metadata.setItemText(3, 'Reference - title not available')
        elif currentref == 'None':
            self.dlg.listview_reference.clear()
            self.dlg.metadata.setItemText(3, 'Reference - None')

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        for action in self.actions:
            self.iface.removePluginMenu(
                self.tr(u'&NOFAInsert'),
                action)
            self.iface.removeToolBarIcon(action)
        # remove the toolbar
        del self.toolbar

    def _get_con_info(self):
        """Returns a connection information from QSettings.

        :returns: A connection information dictionary.
        :rtype: dict.
        """

        con_info = {}

        for con_str in self.con_str_tpl:
            con_info[con_str] = self.settings.value(con_str, u'')

        self.username = con_info[self.usr_str]

        return con_info

    def get_con(self, con_info):
        """Returns a connection.

        :returns: A connection.
        :rtype: psycopg2.connection.
        """

        con = psycopg2.connect(**con_info)
        con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        return con

    def check_nofa_tbls(self):
        """Checks if the database is NOFA.

        :returns: True when database is NOFA, False otherwise.
        :rtype: bool.
        """

        cur = self._get_db_cur()

        cur.execute(
            '''
            SELECT    table_name
            FROM      information_schema.tables
            WHERE     table_schema = 'nofa'
                      AND
                      table_name IN ('location', 'event', 'occurrence')
            ''')

        if cur.rowcount == 3:
            resp = True
        else:
            resp = False

        return resp

    def _get_db_cur(self):
        """Returns a database cursor.
        
        :returns: A database cursor.
        :rtype: psycopg2.cursor.
        """

        return self.con.cursor()

    def _open_con_dlg(self, con_info):
        """
        Opens a connection dialog.
        
        :param con_info: A connection information dictionary.
        :type con_info: dict.
        """

        self.con_dlg = con_dlg.ConDlg(self, con_info, u'Set up connection.')
        self.con_dlg.exec_()

    def fetch_db(self):


        self.get_existing_datasets()

        #####################################
        # get existing projects from db
        self.get_existing_projects()

        #####################################

        self.get_existing_references()

        #########################################
        # Get taxon list
        cur = self._get_db_cur()

        cur.execute(u"""SELECT "{0}" FROM nofa.l_taxon WHERE "taxonRank" IN ('species', 'hybrid', 'genus')  GROUP BY "{0}" ;""".format(self.species_names[self.language]))
        species = cur.fetchall()

        # Create a python-list from query result
        species_list = [s[0] for s in species]

        # Inject sorted python-list for species into UI
        species_list.sort()
        species_list.insert(0, 'Select')
        self.dlg.taxonID.clear()
        self.dlg.taxonID.addItems(species_list)
        #QMessageBox.information(None, "DEBUG:", str(species_list))

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
        self.dlg.ecotypeID.clear()
        self.dlg.ecotypeID.addItems(ecotypes_list)
        '''
        ##########################################

        # Get organismQuantity from database - including only 'Total mass' entries
        cur = self._get_db_cur()
        cur.execute(u'SELECT "organismQuantityID" FROM nofa."l_organismQuantityType";')
        orgQuantID = cur.fetchall()

        # Create a python-list from query result
        #orgQuantID_list = [o[0] for o in orgQuantID if not o[0].startswith("Total")]
        orgQuantID_list = [o[0] for o in orgQuantID if o[0].startswith('Total')]

        # Inject sorted python-list for organismQuantity into UI
        orgQuantID_list.sort()
        orgQuantID_list.insert(0, 'Select')

        # removing unknown: violates foreign key contraint - not present in table l_organismQuantityType
        #orgQuantID_list.insert(1, 'unknown')

        self.dlg.organismQuantityID.clear()
        self.dlg.organismQuantityID.addItems(orgQuantID_list)
        self.dlg.organismQuantityID.setCurrentIndex(orgQuantID_list.index("Select"))

        #############################################

        # Get occurrence status
        self.dlg.status.clear()
        self.dlg.status.addItems(self.occurrence_status)
        self.dlg.status.setCurrentIndex(self.occurrence_status.index("unknown"))

        #############################################

        # Get population trend
        self.dlg.trend.clear()
        self.dlg.trend.addItems(self.population_trend)
        self.dlg.trend.setCurrentIndex(self.population_trend.index("unknown"))

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
        self.dlg.establishmentMeans.clear()
        self.dlg.establishmentMeans.addItems(establishment_list)
        self.dlg.establishmentMeans.setCurrentIndex(establishment_list.index("unknown"))

        ###################################################

        # Get samplingProtocols from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "samplingProtocol" FROM nofa."l_samplingProtocol";')
        samplingProt = cur.fetchall()

        # Create a python-list from query result
        samplingProt_list = [s[0] for s in samplingProt]

        # Inject sorted python-list for samplingProtocol into UI
        samplingProt_list.sort()
        self.dlg.samplingProtocol.clear()
        self.dlg.samplingProtocol.addItems(samplingProt_list)
        self.dlg.samplingProtocol.setCurrentIndex(samplingProt_list.index("unknown"))

        ######################################################

        # Get reliability from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "reliability" FROM nofa."l_reliability";')
        reliab = cur.fetchall()

        # Create a python-list from query result
        reliab_list = [r[0] for r in reliab]

        # Inject sorted python-list for reliability into UI
        reliab_list.sort()
        self.dlg.reliability.clear()
        self.dlg.reliability.addItems(reliab_list)

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
        self.dlg.sampleSizeUnit.clear()
        self.dlg.sampleSizeUnit.addItems(sampUnit_list)
        self.dlg.sampleSizeUnit.setCurrentIndex(sampUnit_list.index("None"))

        ############################################################

        # Get spawningCondition from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "spawningCondition" FROM nofa."l_spawningCondition";')
        spawnCon = cur.fetchall()

        # Create a python-list from query result
        spawnCon_list = [s[0] for s in spawnCon]

        # Inject sorted python-list for spawningCondition into UI
        spawnCon_list.sort()
        self.dlg.spawningCondition.clear()
        self.dlg.spawningCondition.addItems(spawnCon_list)
        self.dlg.spawningCondition.setCurrentIndex(spawnCon_list.index("unknown"))

        ###############################################################

        # Get spawningLocation from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "spawningLocation" FROM nofa."l_spawningLocation";')
        spawnLoc = cur.fetchall()

        # Create a python-list from query result
        spawnLoc_list = [s[0] for s in spawnLoc]

        # Inject sorted python-list for spawningLocation into UI
        spawnLoc_list.sort()
        self.dlg.spawningLocation.clear()
        self.dlg.spawningLocation.addItems(spawnLoc_list)
        self.dlg.spawningLocation.setCurrentIndex(spawnLoc_list.index("unknown"))

        ##################################################################


        # Get institutions from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "institutionCode" FROM nofa."l_institution";')
        institutions = cur.fetchall()

        # Create a python-list from query result
        self.institution_list = [i[0] for i in institutions]

        # Inject sorted python-list for existingProjects into UI
        self.institution_list.sort()

        ##################################################################

        self.dlg.dateStart.setDate(self.today)
        self.dlg.dateEnd.setDate(self.today)
        self.dlg.verifiedDate.setDate(self.nextWeek)

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

        self.dlg.locIDType.clear()
        self.dlg.locIDType.addItems(locIDType_list)
        self.dlg.locIDType.setCurrentIndex(locIDType_list.index("Norwegian VatnLnr"))

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

        self.dlg.taxonomicCoverage.clear()

        families = []
        root = QTreeWidgetItem(self.dlg.taxonomicCoverage, ["All"])
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

        self.dlg.taxonomicCoverage.expandToDepth(0)

        #QMessageBox.information(None, "DEBUG:", str(type(families)))

        #self.dlg.taxonomicCoverage.topLevelItem(root)

        '''
        taxa = []
        self.dlg.taxonomicCoverage.clear()
        for species in species_list:
            if species is not None:
                item = QTreeWidgetItem([species])
                item.setCheckState(0, Qt.Unchecked)
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

                taxa.append(item)

        #QMessageBox.information(None, "DEBUG:", unicode(type(taxa)))
        self.dlg.taxonomicCoverage.addTopLevelItems(taxa)

            #QMessageBox.information(None, "DEBUG:", unicode(species))

        '''

    def get_existing_datasets(self):

        cur = self._get_db_cur()
        cur.execute(u'SELECT "datasetID", "datasetName" FROM nofa."m_dataset";')
        datasets = cur.fetchall()

        # Create a python-list from query result
        # datasetID_list = [d[0] for d in datasets]
        dataset_list = [d[1] for d in datasets]

        # Inject sorted python-list for existingDatasets into UI
        dataset_list.sort()
        dataset_list.insert(0, 'None')
        self.dlg.existingDataset.clear()
        self.dlg.existingDataset.addItems(dataset_list)
        self.dlg.existingDataset.setCurrentIndex(dataset_list.index(self.dataset['dataset_name']))

    def get_existing_projects(self):

        # Get existingProjects from database
        cur = self._get_db_cur()
        cur.execute(u'SELECT "projectID", "projectNumber", "projectName" FROM nofa."m_project";')
        projects = cur.fetchall()

        # Create a global list from query result (a list of lists)
        self.project_list = [[p[1], p[2]] for p in projects]

        # Inject sorted python-list for existingProjects into UI
        # sort by project_number
        self.project_list = sorted(self.project_list, key= lambda p: p[0])

        self.project_list.insert(0, ['None','None'])

        self.dlg.existingProject.clear()

        # create list that shows project number and name
        project_list_display = [u'{0} {1}'.format(p[0], p[1]) for p in self.project_list]

        # add this list to the UI
        self.dlg.existingProject.addItems(project_list_display)

        try:
            # convert project_number and project_name to a list like it is stored in self.project_list
            current_project_nr_name = [self.project['project_number'] , self.project['project_name']]

            # find index of current project
            current_project_index = self.project_list.index(current_project_nr_name)

            # set drop-down menu to current project
            self.dlg.existingProject.setCurrentIndex(current_project_index)
        except:
            self.dlg.existingProject.setCurrentIndex(0)


    def get_existing_references(self):

        # Get existingReference from database
        cur = self._get_db_cur()

        cur.execute(u'SELECT "referenceID", "author", "titel" FROM nofa."m_reference";')
        references = cur.fetchall()

        # Create a python-list from query result

        reference_list = [u'{0}: {1} @{2}'.format(r[1], r[2], r[0]) for r in references]
        reference_title_list = [r[1] for r in references]
        reference_title_list.insert(0, 'None')

        # Inject sorted python-list for existingProjects into UI
        reference_list.sort()
        reference_list.insert(0, 'None')
        self.dlg.existingReference.clear()
        self.dlg.existingReference.addItems(reference_list)
        self.dlg.existingReference.setEditable(True)
        self.dlg.existingReference.completer().setCompletionMode(QCompleter.PopupCompletion)
        #self.dlg.existingReference.setCurrentIndex(reference_list.index("None"))

        self.dlg.existingReference.setCurrentIndex(reference_title_list.index(self.reference['authors']))

        #QMessageBox.information(None, "DEBUG:", str(reference_title_list.index(self.reference['authors'])))

    def update_occurrence(self):
        """syncs the occurrence form with the chosen row of the occurrence table"""

        # set current taxon value
        taxon_index = self.dlg.taxonID.findText(self.occurrence['taxon'][self.row_position], Qt.MatchFixedString)
        self.dlg.taxonID.setCurrentIndex(taxon_index)

        ecotype_index = self.dlg.ecotypeID.findText(self.occurrence['ecotype'][self.row_position], Qt.MatchFixedString)
        self.dlg.ecotypeID.setCurrentIndex(ecotype_index)

        quantity_index = self.dlg.organismQuantityID.findText(self.occurrence['quantity'][self.row_position], Qt.MatchFixedString)
        self.dlg.organismQuantityID.setCurrentIndex(quantity_index)

        self.dlg.oq_metric.setText(str(self.occurrence['metric'][self.row_position]))

        status_index = self.dlg.status.findText(self.occurrence['status'][self.row_position], Qt.MatchFixedString)
        self.dlg.status.setCurrentIndex(status_index)

        trend_index = self.dlg.trend.findText(self.occurrence['trend'][self.row_position], Qt.MatchFixedString)
        self.dlg.trend.setCurrentIndex(trend_index)
        '''if self.occurrence['status'][self.row_position] == 'True':
            self.dlg.occurrenceStatus.setChecked(True)
        else:
            self.dlg.occurrenceStatus.setChecked(False)
        '''
        self.dlg.occurrenceRemarks.setText(self.occurrence['oc_remarks'][self.row_position])

        est_means_index = self.dlg.establishmentMeans.findText(self.occurrence['est_means'][self.row_position], Qt.MatchFixedString)
        self.dlg.establishmentMeans.setCurrentIndex(est_means_index)

        spawn_con_index = self.dlg.spawningCondition.findText(self.occurrence['spawn_con'][self.row_position], Qt.MatchFixedString)
        self.dlg.spawningCondition.setCurrentIndex(spawn_con_index)

        spawn_loc_index = self.dlg.spawningLocation.findText(self.occurrence['spawn_loc'][self.row_position], Qt.MatchFixedString)
        self.dlg.spawningLocation.setCurrentIndex(spawn_loc_index)

        self.dlg.establishmentRemarks.setText(self.occurrence['est_remarks'][self.row_position])

        self.dlg.verifiedBy.setText(self.occurrence['verified_by'][self.row_position])

        self.dlg.yearPrecisionRemarks.setText(self.occurrence['yearprecision_remarks'][self.row_position])

        self.dlg.occurrence_number.setText(str(self.row_position + 1))
        self.dlg.occurrence_number.setStyleSheet('color: black')
        self.dlg.frame.setStyleSheet('color: white')


        '''
        self.dlg.verifiedDate = self.occurrence['verified_date'][self.row_position]
        '''

    def populate_dataset(self):
        self.dlg.listview_dataset.clear()
        self.dlg.listview_dataset.setWordWrap(True)

        for key, value in self.dataset.iteritems():
            if value is not None:
                dstitem = QListWidgetItem(key + ':    ' + value)

                self.dlg.listview_dataset.addItem(dstitem)


    def populate_project(self):
        """ 
        Display the attributes of the chosen project in the UI
        """

        #self.project['organisation'] = "Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text"
        self.dlg.listview_project.clear()
        self.dlg.listview_project.setWordWrap(True)
        self.dlg.listview_project.setTextElideMode(Qt.ElideNone)
        #self.dlg.listview_project.setStyleSheet("QListWidget::item { border: 0.5px solid black }")

        for key, value in self.project.iteritems():
            if value is not None:
                prjitem = QListWidgetItem(key + ':    ' + unicode(value))

                self.dlg.listview_project.addItem(prjitem)

    def populate_reference(self):

        self.dlg.listview_reference.clear()
        self.dlg.listview_reference.setWordWrap(True)

        for key, value in self.reference.iteritems():
            if value is not None:
                rfritem = QListWidgetItem(key + ':    ' + unicode(value))

                self.dlg.listview_reference.addItem(rfritem)

    def populate_information(self):

        self.populate_dataset()
        self.populate_project()
        self.populate_reference()

    def create_occurrence_table(self):
        """creates occurrence table and populates it one row of default values"""

        #currentrow = self.dlg.tableWidget.rowCount()
        #self.dlg.tableWidget.insertRow(currentrow)

        #set rows and columns for tableWidget
        self.dlg.tableWidget.setRowCount(len(self.occurrence['taxon']))
        self.dlg.tableWidget.setColumnCount(12)
        self.row_position = 0

        self.dlg.tableWidget.setSelectionBehavior(QTableWidget.SelectRows);

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
                self.dlg.tableWidget.setItem(m, n, newitem)
            self.dlg.tableWidget.setHorizontalHeaderLabels(headers)

        self.update_occurrence_form()
        #QMessageBox.information(None, "DEBUG:", str(headers))

    def add_occurrence(self):
        """ adds a new occurrence row in occurrence table """

        # check if Table has some entries
        # check if last row is empty

        if (self.dlg.tableWidget.rowCount() > 0 and self.is_last_row_empty()):
            # do not add an occurrence
            QMessageBox.information(None, "Information",
                                    "The last occurrence is empty. " +
                                    "You have to finish it before you can enter a new occurrence.")
            return


        # adds a new occurrence row in occurrence table
        self.row_position = self.dlg.tableWidget.rowCount()
        self.dlg.tableWidget.insertRow(self.row_position)

        # add a new occurrence record in self.occurrence dictionary and table
        for n, key in enumerate(sorted(self.occurrence.keys())):
            item = self.occurrence_base[key]
            self.occurrence[key].append(item)
            # add it to table
            if isinstance(item, datetime.date):
                item = unicode(item)
            new_item = QTableWidgetItem(item)
            self.dlg.tableWidget.setItem(self.row_position, n, new_item)

        self.dlg.tableWidget.selectRow(self.row_position)
        self.update_occurrence_form()

        self.preview_conditions['taxon_selected'] = False
        self.preview_conditions['est_means_selected'] = False
        self.check_preview_conditions()

       #QMessageBox.information(None, "DEBUG:", str(self.row_position))

    def is_last_row_empty(self):
        """Checks if last row is empty"""

        # use last row number in case not the last occurrence is clicked
        last_row_number = self.dlg.tableWidget.rowCount() - 1

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
        self.dlg.reference_4.setTitle("Occurrence - " + unicode(self.row_position + 1))
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
        self.dlg.tableWidget.selectRow(self.row_position)
        self.update_occurrence_form()

    def row_down(self):
        # moving selection one row down in occurrence table
        if self.row_position < (self.dlg.tableWidget.rowCount() - 1):
            self.row_position = self.row_position + 1
        self.dlg.tableWidget.selectRow(self.row_position)
        self.update_occurrence_form()


    def run(self):
        """Run method that performs all the real work"""

        self.con = None

        try:
            con_info = self._get_con_info()
            self.con = self.get_con(con_info)

            if not self.check_nofa_tbls():
                self._open_con_dlg(con_info)
        except psycopg2.OperationalError:
            self._open_con_dlg(con_info)

        if not self.con:
            return

        self.fetch_db()
        self.populate_information()
        self.create_occurrence_table()
        # show the dialog
        self.dlg.show()
        # Run the dialog event loop
        result = self.dlg.exec_()
        # See if OK was pressed
        if result:
            # Do something useful here - delete the line containing pass and
            # substitute with your code.
            pass

####################################
#***********************************
####################################
