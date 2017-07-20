# -*- coding: utf-8 -*-
"""
/***************************************************************************
 ConDlg
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

from PyQt4.QtGui import (
    QDialog, QGridLayout, QLabel, QLineEdit, QHBoxLayout, QPushButton,
    QStatusBar)

from qgis.core import *

import psycopg2


class ConDlg(QDialog):
    """
    A connection dialog for setting database connection parameters.
    """

    def __init__(self, mw, con_info, stat_bar_msg):
        """
        Constructor.

        :param mw: A reference to the main window.
        :type mw: QWidget.
        :param con_info: A connection information.
        :type con_info: dict.
        :param stat_bar_msg: A status bar message.
        :type stat_bar_msg: str.
        """

        super(QDialog, self).__init__()

        self.mw = mw

        self._setup_self(con_info, stat_bar_msg)

    def _setup_self(self, con_info, stat_bar_msg):
        """
        Sets up self.

        :param con_info: A connection information.
        :type con_info: dict.
        :param stat_bar_msg: A status bar message.
        :type stat_bar_msg: str.
        """

        self.setObjectName(u'ConnDlg')

        self.setWindowTitle(u'Connection Information')

        self.grid_lyt = QGridLayout(self)
        self.grid_lyt.setObjectName(u'grid_lyt')
        self.grid_lyt.setColumnMinimumWidth(1, 300)

        self._build_wdgs(con_info, stat_bar_msg)

    def _build_wdgs(self, con_info, stat_bar_msg):
        """
        Builds own widgets.

        :param con_info: A connection information.
        :type con_info: dict.
        :param stat_bar_msg: A status bar message.
        :type stat_bar_msg: str.
        """
 
        self.host_lbl = QLabel(self)
        self.host_lbl.setObjectName(u'host_lbl')
        self.host_lbl.setText(self.mw.host_str.title())
        self.grid_lyt.addWidget(self.host_lbl, 0, 0, 1, 1)
 
        self.host_le = QLineEdit(self)
        self.host_le.setObjectName(u'host_le')
        self.grid_lyt.addWidget(self.host_le, 0, 1, 1, 1)
 
        self.port_lbl = QLabel(self)
        self.port_lbl.setObjectName(u'port_lbl')
        self.port_lbl.setText(self.mw.port_str.title())
        self.grid_lyt.addWidget(self.port_lbl, 1, 0, 1, 1)
 
        self.port_le = QLineEdit(self)
        self.port_le.setObjectName(u'port_le')
        self.grid_lyt.addWidget(self.port_le, 1, 1, 1, 1)
 
        self.db_lbl = QLabel(self)
        self.db_lbl.setObjectName(u'db_lbl')
        self.db_lbl.setText(self.mw.db_str.title())
        self.grid_lyt.addWidget(self.db_lbl, 2, 0, 1, 1)
 
        self.db_le = QLineEdit(self)
        self.db_le.setObjectName(u'db_le')
        self.grid_lyt.addWidget(self.db_le, 2, 1, 1, 1)
 
        self.usr_lbl = QLabel(self)
        self.usr_lbl.setObjectName(u'usr_lbl')
        self.usr_lbl.setText(self.mw.usr_str.title())
        self.grid_lyt.addWidget(self.usr_lbl, 3, 0, 1, 1)
 
        self.usr_le = QLineEdit(self)
        self.usr_le.setObjectName(u'usr_le')
        self.grid_lyt.addWidget(self.usr_le, 3, 1, 1, 1)
 
        self.pwd_lbl = QLabel(self)
        self.pwd_lbl.setObjectName(u'pwd_lbl')
        self.pwd_lbl.setText(self.mw.pwd_str.title())
        self.grid_lyt.addWidget(self.pwd_lbl, 4, 0, 1, 1)
 
        self.pwd_le = QLineEdit(self)
        self.pwd_le.setObjectName(u'pwd_le')
        self.pwd_le.setEchoMode(QLineEdit.Password)
        self.grid_lyt.addWidget(self.pwd_le, 4, 1, 1, 1)

        self.con_dict = {}
        self.con_dict[self.mw.host_str] = self.host_le
        self.con_dict[self.mw.port_str] = self.port_le
        self.con_dict[self.mw.db_str] = self.db_le
        self.con_dict[self.mw.usr_str] = self.usr_le
        self.con_dict[self.mw.pwd_str] = self.pwd_le

        self._ins_con_info(con_info)
 
        self.btn_lyt = QHBoxLayout(self)
        self.grid_lyt.addLayout(self.btn_lyt, 5, 0, 1, 2)
 
        self.test_btn = QPushButton(self)
        self.test_btn.setObjectName(u'test_btn')
        self.test_btn.setText(u'Test and Save')
        self.test_btn.clicked.connect(self._test_con)
        self.btn_lyt.addWidget(self.test_btn)
 
        self.ok_btn = QPushButton(self)
        self.ok_btn.setObjectName(u'ok_btn')
        self.ok_btn.setText(u'OK')
        self.ok_btn.setDisabled(True)
        self.ok_btn.clicked.connect(self.close)
        self.btn_lyt.addWidget(self.ok_btn)

        self.stat_bar = QStatusBar(self)
        self.stat_bar.setObjectName(u'stat_bar')
        self.stat_bar.showMessage(stat_bar_msg)
        self.grid_lyt.addWidget(self.stat_bar, 6, 0, 1, 2)

    def _ins_con_info(self, con_info):
        """
        Inserts a connection information into line edits.

        :param con_info: A connection information.
        :type con_info: dict.
        """

        for conn_str, conn_le in self.con_dict.iteritems():
            conn_le.setText(con_info[conn_str])

    def _test_con(self):
        """
        Tests a connection.
        """

        msg_dur = 5000

        try:
            self._enable_wdgs(False)
            if self.ok_btn.isEnabled():
                self.ok_btn.setEnabled(False)

            QgsApplication.processEvents()

            con_info = self._get_con_info_le()
            self._save_con_info(con_info)

            QgsApplication.processEvents()

            self.mw.con = self.mw.get_con(con_info)

            if self.mw.check_nofa_tbls():
                self.stat_bar.showMessage(
                    u'Connection to NOFA database succeeded.',
                    msg_dur)
                self.ok_btn.setEnabled(True)
            else:
                self.stat_bar.showMessage(
                    u'Connection succeeded but the database is not NOFA.',
                    msg_dur)
                self.ok_btn.setEnabled(False)

                self.mw.con.close()
                self.mw.con = None
        except psycopg2.OperationalError:
            self.mw.con = None
            self.ok_btn.setEnabled(False)
            self.stat_bar.showMessage(u'Connection failed.', msg_dur)
        finally:
            self._enable_wdgs(True)

    def _get_con_info_le(self):
        """
        Returns a connection information from line edits.

        :returns: A connection information dictionary.
        :rtype: dict.
        """

        con_info = {}

        for con_str, con_le in self.con_dict.iteritems():
            con_info[con_str] = con_le.text()

        return con_info

    def _save_con_info(self, con_info):
        """
        Saves a connection information to QSettings.

        :param con_info: A connection information.
        :type con_info: dict.
        """

        for con_str, con_val in con_info.iteritems():
            self.mw.settings.setValue(con_str, con_val)

    def _enable_wdgs(self, bl):
        """
        Enables or disables line edits and push buttons.
        
        :param bl: True to enable widgets, False to disable widgets.
        :type bl: bool.
        """

        for con_str, con_le in self.con_dict.iteritems():
            con_le.setEnabled(bl)

        self.test_btn.setEnabled(bl)
