# -*- coding: utf-8 -*-
"""
/***************************************************************************
 PrjDlg
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

from PyQt4.QtCore import Qt, QDate
from PyQt4.QtGui import (
    QDialog, QGridLayout, QSizePolicy, QLabel, QLineEdit, QComboBox,
    QPlainTextEdit, QHBoxLayout, QPushButton, QStatusBar, QDateEdit,
    QIntValidator)


class PrjDlg(QDialog):
    """
    A dialog for adding new project.
    """

    def __init__(self, mw):
        """
        Constructor.

        :param mw: A reference to the main window.
        :type mw: QWidget.
        """

        super(QDialog, self).__init__()

        self.mw = mw

        self._setup_self()

    def _setup_self(self):
        """
        Sets up self.
        """

        self.setObjectName(u'PrjDlg')

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setWindowTitle(u'Add Project')

        self.grid_lyt = QGridLayout(self)
        self.grid_lyt.setObjectName(u'grid_lyt')
        self.grid_lyt.setColumnMinimumWidth(1, 300)

        self._build_wdgs()

    def _build_wdgs(self):
        """
        Builds own widgets.
        """

        self.org_lbl = QLabel(self)
        self.org_lbl.setObjectName(u'org_lbl')
        self.org_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.org_lbl.setText(u'organization*')
        self.grid_lyt.addWidget(self.org_lbl, 0, 0, 1, 1)

        self.org_cb = QComboBox(self)
        self.org_cb.setObjectName(u'org_cb')
        self._pop_org_cb()
        self.grid_lyt.addWidget(self.org_cb, 0, 1, 1, 1)

        self.no_lbl = QLabel(self)
        self.no_lbl.setObjectName(u'no_lbl')
        self.no_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.no_lbl.setText(u'projectNumber*')
        self.grid_lyt.addWidget(self.no_lbl, 1, 0, 1, 1)

        self.no_le = QLineEdit(self)
        self.no_le.setObjectName(u'no_le')
        self.no_le.setValidator(QIntValidator(None))
        self.grid_lyt.addWidget(self.no_le, 1, 1, 1, 1)

        self.name_lbl = QLabel(self)
        self.name_lbl.setObjectName(u'name_lbl')
        self.name_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.name_lbl.setText(u'projectName*')
        self.grid_lyt.addWidget(self.name_lbl, 2, 0, 1, 1)

        self.name_le = QLineEdit(self)
        self.name_le.setObjectName(u'name_le')
        self.grid_lyt.addWidget(self.name_le, 2, 1, 1, 1)

        self.styr_lbl = QLabel(self)
        self.styr_lbl.setObjectName(u'styr_lbl')
        self.styr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.styr_lbl.setText(u'startYear')
        self.grid_lyt.addWidget(self.styr_lbl, 3, 0, 1, 1)

        today_date = QDate.currentDate()

        self.styr_de = QDateEdit(self)
        self.styr_de.setObjectName(u'styr_de')
        self.styr_de.setDisplayFormat('yyyy')
        self.styr_de.setDate(today_date)
        self.grid_lyt.addWidget(self.styr_de, 3, 1, 1, 1)

        self.endyr_lbl = QLabel(self)
        self.endyr_lbl.setObjectName(u'endyr_lbl')
        self.endyr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.endyr_lbl.setText(u'endYear')
        self.grid_lyt.addWidget(self.endyr_lbl, 4, 0, 1, 1)

        self.endyr_de = QDateEdit(self)
        self.endyr_de.setObjectName(u'endyr_de')
        self.endyr_de.setDisplayFormat('yyyy')
        self.endyr_de.setDate(today_date)
        self.grid_lyt.addWidget(self.endyr_de, 4, 1, 1, 1)

        self.ldr_lbl = QLabel(self)
        self.ldr_lbl.setObjectName(u'ldr_lbl')
        self.ldr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.ldr_lbl.setText(u'projectLeader')
        self.grid_lyt.addWidget(self.ldr_lbl, 5, 0, 1, 1)

        self.ldr_le = QLineEdit(self)
        self.ldr_le.setObjectName(u'ldr_le')
        self.grid_lyt.addWidget(self.ldr_le, 5, 1, 1, 1)

        self.mbr_lbl = QLabel(self)
        self.mbr_lbl.setObjectName(u'mbr_lbl')
        self.mbr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.mbr_lbl.setText(u'projectMembers')
        self.grid_lyt.addWidget(self.mbr_lbl, 6, 0, 1, 1)

        self.mbr_pte = QPlainTextEdit(self)
        self.mbr_pte.setObjectName(u'mbr_pte')
        self.grid_lyt.addWidget(self.mbr_pte, 6, 1, 1, 1)

        self.fncr_lbl = QLabel(self)
        self.fncr_lbl.setObjectName(u'fncr_lbl')
        self.fncr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.fncr_lbl.setText(u'financer')
        self.grid_lyt.addWidget(self.fncr_lbl, 7, 0, 1, 1)

        self.fncr_le = QLineEdit(self)
        self.fncr_le.setObjectName(u'fncr_le')
        self.grid_lyt.addWidget(self.fncr_le, 7, 1, 1, 1)

        self.rmk_lbl = QLabel(self)
        self.rmk_lbl.setObjectName(u'rmk_lbl')
        self.rmk_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.rmk_lbl.setText(u'remarks')
        self.grid_lyt.addWidget(self.rmk_lbl, 8, 0, 1, 1)

        self.rmk_pte = QPlainTextEdit(self)
        self.rmk_pte.setObjectName(u'rmk_pte')
        self.grid_lyt.addWidget(self.rmk_pte, 8, 1, 1, 1)

        self.btn_lyt = QHBoxLayout(self)
        self.grid_lyt.addLayout(self.btn_lyt, 9, 1, 1, 1)

        self.sv_btn = QPushButton(self)
        self.sv_btn.setObjectName(u'sv_btn')
        self.sv_btn.setText(u'Save')
        self.sv_btn.clicked.connect(self._save_prj)
        self.btn_lyt.addWidget(self.sv_btn)

        self.cl_btn = QPushButton(self)
        self.cl_btn.setObjectName(u'ok_btn')
        self.cl_btn.setText(u'Close')
        self.cl_btn.clicked.connect(self.close)
        self.btn_lyt.addWidget(self.cl_btn)

        self.stat_bar = QStatusBar(self)
        self.stat_bar.setObjectName(u'stat_bar')
        self.grid_lyt.addWidget(self.stat_bar, 10, 0, 1, 2)

    def _pop_org_cb(self):
        """
        Populates the organization combo box.
        """

        cur = self.mw._get_db_cur()
        cur.execute(
            '''
            SELECT      distinct "institutionCode" i
            FROM        nofa."m_dataset"
            ORDER BY    i;
            ''')
        orgs = cur.fetchall()

        org_list = [i[0] for i in orgs]

        self.org_cb.clear()
        self.org_cb.addItems(org_list)

    def _save_prj(self):
        """
        Saves a project into the database.
        """

        org = self.org_cb.currentText() \
            if len(self.org_cb.currentText()) != 0 else None
        if len(self.no_le.text()) != 0:
            no = self.no_le.text()
        else:
            self.stat_bar.showMessage(u'Enter a project number.', 10000)
            return
        if len(self.name_le.text()) != 0:
            name = self.name_le.text()
        else:
            self.stat_bar.showMessage(u'Enter a project name.', 10000)
            return
        styr = self.styr_de.date().year()
        endyr = self.endyr_de.date().year()
        ldr = self.ldr_le.text() \
            if len(self.ldr_le.text()) != 0 else None
        mbr = self.mbr_pte.toPlainText() \
            if len(self.mbr_pte.toPlainText()) != 0 else None
        fncr = self.fncr_le.text() \
            if len(self.fncr_le.text()) != 0 else None
        rmk = self.rmk_pte.toPlainText() \
            if len(self.rmk_pte.toPlainText()) != 0 else None

        cur = self.mw._get_db_cur()
        cur.execute(
            '''
            INSERT INTO     nofa.m_project (
                                "organisation",
                                "projectNumber",
                                "projectName",
                                "startYear",
                                "endYear",
                                "projectLeader",
                                "projectMembers",
                                "financer",
                                "remarks")
            VALUES          (   %(organisation)s,
                                %(projectNumber)s,
                                %(projectName)s,
                                %(startYear)s,
                                %(endYear)s,
                                %(projectLeader)s,
                                %(projectMembers)s,
                                %(financer)s,
                                %(remarks)s);
            ''',
            {'organisation': org,
             'projectNumber': no,
             'projectName': name,
             'startYear': styr,
             'endYear': endyr,
             'projectLeader': ldr,
             'projectMembers': mbr,
             'financer': fncr,
             'remarks': rmk})

        self.stat_bar.showMessage(u'Project saved.', 10000)

        self.mw.pop_prj_cb()
        self.mw.upd_prj(self.mw.get_prj_str(org, no, name))
