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
from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication, Qt
from PyQt4.QtGui import QAction, QIcon, QMessageBox, QTreeWidgetItem, QListWidgetItem, QTableWidgetItem, QColor
# Initialize Qt resources from file resources.py
import resources
# Import the code for the dialog
from nofa_insert_dialog import NOFAInsertDialog
from dataset_dialog import DatasetDialog
from project_dialog import ProjectDialog
from reference_dialog import ReferenceDialog
from preview_dialog import PreviewDialog
import os.path
import psycopg2
import logging
import datetime


class NOFAInsert:
    """QGIS Plugin Implementation."""

    def __init__(self, iface):
        """Constructor.

        :param iface: An interface instance that will be passed to this class
            which provides the hook by which you can manipulate the QGIS
            application at run time.
        :type iface: QgsInterface
        """
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


        # Declare instance attributes
        self.actions = []
        self.menu = self.tr(u'&NOFAInsert')
        # TODO: We are going to let the user set this up in a future iteration
        self.toolbar = self.iface.addToolBar(u'NOFAInsert')
        self.toolbar.setObjectName(u'NOFAInsert')

        self.today = datetime.datetime.today().date()
        self.year = datetime.datetime.today().year
        self.nextWeek = self.today + datetime.timedelta(days=7)

        self.dataset_name = "none"



        # initialise data and metadata containers:
        self.locations = {'location': [], 'loc_type': 'Select'}

        self.occurrence = {'taxon': ['Select', ],
                           'ecotype': ['Select', ],
                           'quantity': ['Select', ],
                           'status': ['False', ],
                           'oc_remarks': ['None', ],
                           'est_means': ['Select', ],
                           'est_remarks': ['None', ],
                           'spawn_con': ['unknown', ],
                           'spawn_loc': ['unknown', ],
                           'verified_by': ['Nobody', ],
                           'verified_date': [str(self.today), ],
                           'yearprecision_remarks': ['None', ]
                           }

        self.taxonomicc = []

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
                        'start_year': str(self.year),
                        'end_year': str(self.year),
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
                          'year': str(self.year),
                          'title': 'None',
                          'journal': 'None',
                          'volume': 'None',
                          'date': str(self.today),
                          'issn': 'None',
                          'isbn': 'None',
                          'page': 'None'
                          }
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

        # Create the dialog (after translation) and keep reference
        self.dlg = NOFAInsertDialog()

        self.dlg.editDatasetButton.clicked.connect(self._open_dataset_dialog)
        self.dlg.editProjectButton.clicked.connect(self._open_project_dialog)
        self.dlg.editReferenceButton.clicked.connect(self._open_reference_dialog)

        self.dlg.existingDataset.currentIndexChanged.connect(self.update_dataset)
        self.dlg.existingProject.currentIndexChanged.connect(self.update_project)
        self.dlg.existingReference.currentIndexChanged.connect(self.update_reference)

        self.dlg.insert_button.clicked.connect(self.preview)

        # set the occurrenceStatus checkbox to True, as a default initial status
        self.dlg.occurrenceStatus.setChecked(True)

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

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        icon_path = ':/plugins/NOFAInsert/icon.png'
        self.add_action(
            icon_path,
            text=self.tr(u'NOFAInsert'),
            callback=self.run,
            parent=self.iface.mainWindow())

    def _open_dataset_dialog(self):
        """On button click opens the Dataset Metadata Editing Dialog"""
        self.datadlg = DatasetDialog()
        self.datadlg.show()

        '''
        # Get existingDatasets from database
        cur = self._db_cur()
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
        self.datadlg.dataset_dialog_button.clicked.connect(self._dataset_button)


    def preview(self):

        # Get occurrence information
        self.occurrence['taxon'] = self.dlg.taxonID.currentText()
        self.occurrence['ecotype'] = self.dlg.ecotypeID.currentText()
        self.occurrence['quantity'] = self.dlg.organismQuantityID.currentText()
        if self.dlg.occurrenceStatus.isChecked():
            self.occurrence['status'] = True
        else:
            self.occurrence['status'] = False

        self.occurrence['oc_remarks'] = self.dlg.occurrenceRemarks.text()
        self.occurrence['est_means'] = self.dlg.establishmentMeans.currentText()
        self.occurrence['est_remarks'] = self.dlg.establishmentRemarks.text()
        self.occurrence['spawn_con'] = self.dlg.spawningCondition.currentText()
        self.occurrence['spawn_loc'] = self.dlg.spawningLocation.currentText()
        self.occurrence['verified_by'] = self.dlg.verifiedBy.text()
        self.occurrence['verified_date'] = self.dlg.verifiedDate.date().toString()
        self.occurrence['yearprecision_remarks'] = self.dlg.yearPrecisionRemarks.text()

        #Get Event Data

        self.event['protocol'] = self.dlg.samplingProtocol.currentText()
        self.event['size_value'] = self.dlg.sampleSizeValue.text()
        self.event['size_unit'] = self.dlg.sampleSizeUnit.currentText()
        self.event['effort'] = self.dlg.samplingEffort.text()
        self.event['protocol_remarks'] = self.dlg.samplingProtocolRemarks.text()
        self.event['date_start'] = self.dlg.dateStart.date().toString()
        self.event['date_end'] = self.dlg.dateEnd.date().toString()
        self.event['recorded_by'] = self.dlg.recordedBy_e.text()
        self.event['event_remarks'] = self.dlg.eventRemarks.text()
        self.event['reliability'] = self.dlg.reliability.currentText()


        #QMessageBox.information(None, "DEBUG:", str(self.event))
        self.prwdlg = PreviewDialog()
        self.prwdlg.show()

        self.container = [self.occurrence,
                          self.event,
                          self.dataset,
                          self.project,
                          self.reference]

        listWidget_list = [
                           self.prwdlg.listWidget_2,
                           self.prwdlg.listWidget_4,
                           self.prwdlg.listWidget_5,
                           self.prwdlg.listWidget_6,
                           self.prwdlg.listWidget_7]

        # Get the locations
        for elem in self.locations['location']:
            self.prwdlg.listWidget_1.addItem(QListWidgetItem(elem))

        # Get taxonomic coverage items
        root = self.dlg.taxonomicCoverage.invisibleRootItem()
        get_taxa = root.childCount()
        #QMessageBox.information(None, "DEBUG:", str(get_taxa))
        for index in range(get_taxa):
            taxon = root.child(index)
            if taxon.checkState(0) == Qt.Checked:
                self.prwdlg.listWidget_3.addItem(QListWidgetItem(taxon.text(0)))


        # populate the preview list widgets with info from previous forms
        for i in range(5):

            for key, value in self.container[i].iteritems():
                if value == u'' or value == u'unknown' or value == u'None':
                    prwitem = QListWidgetItem(key + ':    None')
                    prwitem.setTextColor(QColor("red"))
                else:
                    prwitem = QListWidgetItem(key + ':    ' + str(value))
                    prwitem.setTextColor(QColor("green"))

                listWidget_list[i].addItem(prwitem)

    def _dataset_button(self):
        pass


    def _open_project_dialog(self):
        """On button click opens the Project Metadata Editing Dialog"""
        self.prjdlg = ProjectDialog()
        self.prjdlg.show()

        '''
        # Get existingProjects from database
        cur = self._db_cur()
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

    def _open_reference_dialog(self):
        """On button click opens the Project Metadata Editing Dialog"""
        self.rfrdlg = ReferenceDialog()
        self.rfrdlg.show()

        ###########################################################################


        # Get referenceType from database
        cur = self._db_cur()
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

    def update_dataset(self):
        currentdataset = self.dlg.existingDataset.currentText()
        if currentdataset != 'None' and  currentdataset !='' and currentdataset!= None:

            # Get dataset record from NOFA db:
            cur = self._db_cur()
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


            self.dataset['dataset_id'] = str(dataset_list[0])
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
        #QMessageBox.information(None, "DEBUG:", str(self.project_list))

        currentproject = self.dlg.existingProject.currentText()

        currentproject_number = currentproject.split(':')[0]
        if currentproject_number != 'None' and currentproject_number != '':
            #QMessageBox.information(None, "DEBUG:", str(currentproject_number))

            cur = self._db_cur()
            cur.execute(
                u'SELECT "projectNumber", "projectName", "startYear", "endYear", "projectLeader", '
                u'"projectMembers", "organisation", "financer", "remarks" '
                u'FROM nofa."m_project" WHERE "projectNumber" = (%s);', (currentproject_number,))
            project = cur.fetchone()
            #QMessageBox.information(None, "DEBUG:", str(project))

        # Create a python-list from query result

            self.project['project_number'] = str(project[0])
            self.project['project_name'] = project[1]
            self.project['start_year'] = str(project[2])
            self.project['end_year'] = str(project[3])
            self.project['project_leader'] = project[4]
            self.project['members'] = project[5]
            self.project['organisation'] = project[6]
            self.project['financer'] = project[7]
            self.project['project_remarks'] = project[8]

            self.dlg.listview_project.clear()
            for key, value in self.project.iteritems():
                if value is not None:
                    prjitem = QListWidgetItem(key + ':    ' + value)
                else:
                    prjitem = QListWidgetItem(key + ':    None')

                self.dlg.listview_project.addItem(prjitem)

            self.dlg.metadata.setItemText(2, 'Project - ' + self.project['project_name'])

        elif currentproject == 'None':
            self.dlg.listview_project.clear()
            self.dlg.metadata.setItemText(2, 'Project - None')

    def update_reference(self):

        currentref= self.dlg.existingReference.currentText()
        #QMessageBox.information(None, "DEBUG:", str(currentref))

        currentref_number = currentref.split(':')[0]
        #QMessageBox.information(None, "DEBUG:", str(currentproject_number))

        if currentref_number != 'None' and currentref_number != '' and currentref_number != None:
            cur = self._db_cur()
            cur.execute(
                u'SELECT "referenceID", "doi", "author", "referenceType", "year", '
                u'"titel", "journalName", "volume", "date", "issn", "isbn", "page" '
                u'FROM nofa."m_reference" WHERE "referenceID" = (%s);', (currentref_number,))
            ref = cur.fetchone()
            #QMessageBox.information(None, "DEBUG:", str(project))


            # Create a python-list from query result

            self.reference['reference_id'] = str(ref[0])
            self.reference['doi'] = str(ref[1])
            self.reference['authors'] = str(ref[2])
            self.reference['reference_type'] = str(ref[3])
            self.reference['year'] = str(ref[4])
            self.reference['title'] = str(ref[5])
            self.reference['journal'] = str(ref[6])
            self.reference['volume'] = str(ref[7])
            self.reference['date'] = str(ref[8])
            self.reference['issn'] = str(ref[9])
            self.reference['isbn'] = str(ref[10])
            self.reference['page'] = str(ref[11])

            self.dlg.listview_reference.clear()
            for key, value in self.reference.iteritems():
                if value is not None:
                    refitem = QListWidgetItem(key + ':    ' + value)
                else:
                    refitem = QListWidgetItem(key + ':    None')

                self.dlg.listview_reference.addItem(refitem)

            # Title should have constraint NOT NULL. Or, we should choose another option for visualizing
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

    def get_postgres_conn_info(self):
        """ Read PostgreSQL connection details from QSettings stored by QGIS.
        If connection parameters are not yet stored in Qsettings, use the following in python console:

        import qgis
        from PyQt4.QtCore import QSettings

        settings = Qsettings()
        settings.setValue(u"PostgreSQL/connections/NOFA/host", "your_server_address")
        settings.setValue(u"PostgreSQL/connections/NOFA/port", "5432")
        settings.setValue(u"PostgreSQL/connections/NOFA/database", "your_db_name)
        settings.setValue(u"PostgreSQL/connections/NOFA/username", "your_pg_username")
        settings.setValue(u"PostgreSQL/connections/NOFA/password", "pwd")
        """
        settings = QSettings()
        settings.beginGroup(u"/PostgreSQL/connections/NOFA")

        conn_info = {}
        conn_info["host"] = settings.value("host", "", type=str)
        conn_info["port"] = settings.value("port", 432, type=int)
        conn_info["database"] = settings.value("database", "", type=str)
        username = settings.value("username", "", type=str)
        password = settings.value("password", "", type=str)
        if len(username) != 0:
            conn_info["user"] = username
            conn_info["password"] = password

        #QMessageBox.information(None, "DEBUG:", str(conn_info))
        return conn_info

    def get_connection(self, conn_info):
        """ Connect to the database using conn_info dict:
         { 'host': ..., 'port': ..., 'database': ..., 'username': ..., 'password': ... }
        """
        conn = psycopg2.connect(**conn_info)
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)
        return conn

    def _db_cur(self):
        con_info = self.get_postgres_conn_info()
        con = self.get_connection(con_info)
        return con.cursor()

    def fetch_db(self):

        language = 'Norwegian'

        species_names = {'Latin': 'scientificName',
                         'English': 'vernacularName',
                         'Norwegian': 'vernacularName_NO',
                         'Swedish': 'vernacularName_SE',
                         'Finish': 'vernacularName_FI'}

        countryCodes = {'Latin': None,
                        'English': None,
                        'Norwegian': 'NO',
                        'Swedish': 'SE',
                        'Finish': 'FI'}

        cur = self._db_cur()
        cur.execute(u'SELECT "datasetID", "datasetName" FROM nofa."m_dataset";')
        datasets = cur.fetchall()

        # Create a python-list from query result
        datasetID_list = [d[0] for d in datasets]
        dataset_list = [d[1] for d in datasets]

        # Inject sorted python-list for existingDatasets into UI
        dataset_list.sort()
        dataset_list.insert(0, 'None')
        self.dlg.existingDataset.clear()
        self.dlg.existingDataset.addItems(dataset_list)
        self.dlg.existingDataset.setCurrentIndex(dataset_list.index("None"))

        #####################################

        # Get existingProjects from database
        cur = self._db_cur()
        cur.execute(u'SELECT "projectID", "projectNumber", "projectName" FROM nofa."m_project";')
        projects = cur.fetchall()

        # Create a python-list from query result
        self.project_list = [u'{0}: {1}'.format(p[1], p[2]) for p in projects]

        # Inject sorted python-list for existingProjects into UI
        self.project_list.sort()
        self.project_list.insert(0, 'None')
        self.dlg.existingProject.clear()
        self.dlg.existingProject.addItems(self.project_list)
        if self.project['project_name'] == 'None':
            self.dlg.existingProject.setCurrentIndex(self.project_list.index("None"))

        #########################################

        # Get existingReference from database
        cur = self._db_cur()

        cur.execute(u'SELECT "referenceID", "source", "titel" FROM nofa."m_reference";')
        references = cur.fetchall()

        # Create a python-list from query result

        reference_list = [u'{0}: {1}'.format(r[0], r[1]) for r in references]
        referenceID_list = [r[0] for r in references]

        # Inject sorted python-list for existingProjects into UI
        reference_list.sort()
        reference_list.insert(0, 'None')
        self.dlg.existingReference.clear()
        self.dlg.existingReference.addItems(reference_list)
        self.dlg.existingReference.setCurrentIndex(reference_list.index("None"))

        #########################################

        cur = self._db_cur()

        cur.execute(u'SELECT "{0}" FROM nofa.l_taxon GROUP BY "{0}";'.format(species_names[language]))
        species = cur.fetchall()

        # Create a python-list from query result
        species_list = [s[0] for s in species]

        # Inject sorted python-list for species into UI
        species_list.sort()
        self.dlg.taxonID.clear()
        self.dlg.taxonID.addItems(species_list)
        #QMessageBox.information(None, "DEBUG:", str(species_list))

        #################################

        # Get ecotypes from database
        cur = self._db_cur()
        cur.execute(u'SELECT "vernacularName_NO" FROM nofa."l_ecotype" GROUP BY "vernacularName_NO";')
        ecotypes = cur.fetchall()

        # Create a python-list from query result
        ecotypes_list = [e[0] for e in ecotypes]
        #QMessageBox.information(None, "DEBUG:", str(ecotypes_list))
        # Inject sorted python-list for ecotypes into UI
        ecotypes_list.sort()
        self.dlg.ecotypeID.clear()
        self.dlg.ecotypeID.addItems(ecotypes_list)

        ##########################################

        # Get organismQuantity from database - excluding 'Total mass' entries
        cur = self._db_cur()
        cur.execute(u'SELECT "organismQuantityID" FROM nofa."l_organismQuantityType";')
        orgQuantID = cur.fetchall()

        # Create a python-list from query result
        orgQuantID_list = [o[0] for o in orgQuantID if not o[0].startswith("Total")]

        # Inject sorted python-list for organismQuantity into UI
        orgQuantID_list.sort()
        orgQuantID_list.insert(0, 'Unknown')
        self.dlg.organismQuantityID.clear()
        self.dlg.organismQuantityID.addItems(orgQuantID_list)
        self.dlg.organismQuantityID.setCurrentIndex(orgQuantID_list.index("Unknown"))

        #############################################

        # Get establishmentMeans from database
        cur = self._db_cur()
        cur.execute(u'SELECT "establishmentMeans" FROM nofa."l_establishmentMeans";')
        establishment = cur.fetchall()

        # Create a python-list from query result
        establishment_list = [e[0] for e in establishment]

        # Inject sorted python-list for establishmentMeans into UI
        establishment_list.sort()
        self.dlg.establishmentMeans.clear()
        self.dlg.establishmentMeans.addItems(establishment_list)
        self.dlg.establishmentMeans.setCurrentIndex(establishment_list.index("unknown"))

        ###################################################

        # Get samplingProtocols from database
        cur = self._db_cur()
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
        cur = self._db_cur()
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
        cur = self._db_cur()
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
        cur = self._db_cur()
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
        cur = self._db_cur()
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
        cur = self._db_cur()
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

        locIDType_dict = {'Norwegian VatnLnr': 'no_vatn_lnr',
                          'Swedish SjoID': 'se_sjoid',
                          'Finish nro': 'fi_nro',
                          'coordinates UTM32': 25832,
                          'coordinates UTM33': 25833,
                          'coordinates UTM35': 25835,
                          'coordinates lon/lat': 4326,
                          'waterBody register name': '"waterBody"'}

        # Add more location match options (e.g. coordinates)

        locIDType_list = locIDType_dict.keys()
        locIDType_list.sort()
        self.dlg.locIDType.addItems(locIDType_list)
        self.dlg.locIDType.setCurrentIndex(locIDType_list.index("Norwegian VatnLnr"))

        ###################################################################
        # Create the Taxonomic Coverage list of taxa
        taxa = []
        self.dlg.taxonomicCoverage.clear()
        for species in species_list:
            if species is not None:
                item = QTreeWidgetItem([species])
                item.setCheckState(0, Qt.Unchecked)
                item.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)

                taxa.append(item)

            #QMessageBox.information(None, "DEBUG:", str(species))

        self.dlg.taxonomicCoverage.addTopLevelItems(taxa)



    def populate_dataset(self):

        self.dataset['dataset_name'] = "Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text"
        '''
        self.dlg.display_dataset_1.setText(self.dataset['dataset_name'])
        self.dlg.display_dataset_1.setWordWrap(True)
        self.dlg.display_dataset_2.setText(self.dataset['dataset_id'])
        self.dlg.display_dataset_3.setText(self.dataset['rightsholder'])
        self.dlg.display_dataset_4.setText(self.dataset['owner_institution'])
        self.dlg.display_dataset_5.setText(self.dataset['license'])
        self.dlg.display_dataset_6.setText(self.dataset['citation'])
        self.dlg.display_dataset_7.setText(self.dataset['comment'])
        self.dlg.display_dataset_8.setText(self.dataset['information'])
        self.dlg.display_dataset_9.setText(self.dataset['generalizations'])
        '''
        for key, value in self.dataset.iteritems():
            if value is not None:
                dstitem = QListWidgetItem(key + ':    ' + value)

                self.dlg.listview_dataset.addItem(dstitem)


    def populate_project(self):

        #QMessageBox.information(None, "DEBUG:", str(type(self.project)))
        self.project['organisation'] = "Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text Veeeery long text"
        self.dlg.listview_project.clear()
        self.dlg.listview_project.setWordWrap(True)
        self.dlg.listview_project.setTextElideMode(Qt.ElideNone)
        #self.dlg.listview_project.setStyleSheet("QListWidget::item { border: 0.5px solid black }")

        for key, value in self.project.iteritems():
            if value is not None:
                prjitem = QListWidgetItem(key + ':    ' + value)

                self.dlg.listview_project.addItem(prjitem)

    def populate_reference(self):

        for key, value in self.reference.iteritems():
            if value is not None:
                rfritem = QListWidgetItem(key + ':    ' + str(value))

                self.dlg.listview_reference.addItem(rfritem)

    def populate_information(self):

        self.populate_dataset()
        self.populate_project()
        self.populate_reference()

    def create_occurrence_table(self):
        #currentrow = self.dlg.tableWidget.rowCount()
        #self.dlg.tableWidget.insertRow(currentrow)

        #set rows and columns for tableWidget
        self.dlg.tableWidget.setRowCount(1)
        self.dlg.tableWidget.setColumnCount(12)

        #  populate tableWidget
        headers = []
        for n, key in enumerate(sorted(self.occurrence.keys())):
            headers.append(key)
            for m, item in enumerate(self.occurrence[key]):
                newitem = QTableWidgetItem(item)
                # setItem(row, column, QTableWidgetItem)
                self.dlg.tableWidget.setItem(m, n, newitem)
            self.dlg.tableWidget.setHorizontalHeaderLabels(headers)
        #QMessageBox.information(None, "DEBUG:", str(headers))



    def run(self):
        """Run method that performs all the real work"""

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
