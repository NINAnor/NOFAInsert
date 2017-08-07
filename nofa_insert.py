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

from PyQt4.QtCore import QSettings, QTranslator, qVersion, QCoreApplication
from PyQt4.QtGui import QAction, QIcon

import os
import psycopg2, psycopg2.extras

import resources

from nofa.gui import ins_dlg, con_dlg
from nofa import db


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

        self.sel_str = u'Select'
        self.none_str = str(None)

    def initGui(self):
        """Create the menu entries and toolbar icons inside the QGIS GUI."""

        self.nofa_act = QAction(self.iface.mainWindow())
        self.nofa_act.setText(self.app_name)
        nofa_icon = QIcon(':/plugins/NOFAInsert/icon.png')
        self.nofa_act.setIcon(nofa_icon)
        self.nofa_act.triggered.connect(self.run)
        self.iface.addToolBarIcon(self.nofa_act)
        self.iface.addPluginToMenu(self.app_name, self.nofa_act)

        self.con_act = QAction(self.iface.mainWindow())
        self.con_act.setText(u'Connection Parameters')
        con_icon = QIcon(
            os.path.join(self.plugin_dir, 'data', 'icons', 'options.png'))
        self.con_act.setIcon(con_icon)
        self.con_act.triggered.connect(self._open_con_dlg)
        self.iface.addPluginToMenu(self.app_name, self.con_act)

        self.ins_dlg = ins_dlg.InsDlg(self.iface, self, self.plugin_dir)

    def unload(self):
        """
        Removes the plugin menu and icon.
        """

        self.iface.removePluginMenu(self.app_name, self.nofa_act)
        self.iface.removePluginMenu(self.app_name, self.con_act)
        self.iface.removeToolBarIcon(self.nofa_act)
        self.ins_dlg.dsc_from_iface()

    def _get_con_info(self):
        """
        Returns a connection information from QSettings.

        :returns: A connection information dictionary.
        :rtype: dict.
        """

        con_info = {}

        for con_str in self.con_str_tpl:
            con_info[con_str] = self.settings.value(con_str, u'')

        self.username = con_info[self.usr_str]

        return con_info

    def _open_con_dlg(self, con_info=None):
        """
        Opens a connection dialog.
        
        :param con_info: A connection information dictionary.
        :type con_info: dict.
        """

        if not con_info:
            con_info = self._get_con_info()

        self.con_dlg = con_dlg.ConDlg(self, con_info, u'Set up connection.')
        self.con_dlg.exec_()

    def run(self):
        """Run method that performs all the real work"""

        self.con = None

        try:
            con_info = self._get_con_info()
            self.con = db.get_con(con_info)

            if not db.check_nofa_tbls(self.con):
                self._open_con_dlg(con_info)
        except psycopg2.OperationalError:
            self._open_con_dlg(con_info)

        if not self.con:
            return

        self.ins_dlg.fetch_db()
        self.ins_dlg.create_occ_tbl()
        self.ins_dlg.show()
