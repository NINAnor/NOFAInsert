# -*- coding: utf-8 -*-
"""
/***************************************************************************
 DtstDlg
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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import (
    QDialog, QGridLayout, QSizePolicy, QLabel, QLineEdit, QComboBox,
    QPlainTextEdit, QHBoxLayout, QPushButton, QStatusBar)

import uuid

from .. import db


class DtstDlg(QDialog):
    """
    A dialog for adding new dataset.
    """

    def __init__(self, mc, iw):
        """
        Constructor.

        :param mc: A reference to the main class.
        :type mc: object.
        :param iw: A reference to the insert window.
        :type iw: QDialog.
        """

        super(QDialog, self).__init__()

        self.mc = mc
        self.iw = iw

        self._setup_self()

    def _setup_self(self):
        """
        Sets up self.
        """

        self.setObjectName(u'DtstDlg')

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setWindowTitle(u'Add Dataset')

        self.grid_lyt = QGridLayout(self)
        self.grid_lyt.setObjectName(u'grid_lyt')
        self.grid_lyt.setColumnMinimumWidth(1, 300)

        self._build_wdgs()

    def _build_wdgs(self):
        """
        Builds own widgets.
        """

        self.name_lbl = QLabel(self)
        self.name_lbl.setObjectName(u'name_lbl')
        self.name_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.name_lbl.setText(u'datasetName*')
        self.grid_lyt.addWidget(self.name_lbl, 0, 0, 1, 1)

        self.name_le = QLineEdit(self)
        self.name_le.setObjectName(u'name_le')
        self.grid_lyt.addWidget(self.name_le, 0, 1, 1, 1)

        self.id_lbl = QLabel(self)
        self.id_lbl.setObjectName(u'id_lbl')
        self.id_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.id_lbl.setText(u'datasetId')
        self.grid_lyt.addWidget(self.id_lbl, 1, 0, 1, 1)

        self.id_le = QLineEdit(self)
        self.id_le.setObjectName(u'id_le')
        self.grid_lyt.addWidget(self.id_le, 1, 1, 1, 1)

        self.inst_lbl = QLabel(self)
        self.inst_lbl.setObjectName(u'inst_lbl')
        self.inst_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.inst_lbl.setText(u'ownerInstitutionCode')
        self.grid_lyt.addWidget(self.inst_lbl, 2, 0, 1, 1)

        self.inst_cb = QComboBox(self)
        self.inst_cb.setObjectName(u'inst_cb')
        self._pop_inst_cb()
        self.grid_lyt.addWidget(self.inst_cb, 2, 1, 1, 1)

        self.rght_lbl = QLabel(self)
        self.rght_lbl.setObjectName(u'rght_lbl')
        self.rght_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.rght_lbl.setText(u'rightsHolder')
        self.grid_lyt.addWidget(self.rght_lbl, 3, 0, 1, 1)

        self.rght_cb = QComboBox(self)
        self.rght_cb.setObjectName(u'rght_cb')
        self._pop_rght_cb()
        self.grid_lyt.addWidget(self.rght_cb, 3, 1, 1, 1)

        self.lic_lbl = QLabel(self)
        self.lic_lbl.setObjectName(u'lic_lbl')
        self.lic_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.lic_lbl.setText(u'license')
        self.grid_lyt.addWidget(self.lic_lbl, 4, 0, 1, 1)

        self.lic_cb = QComboBox(self)
        self.lic_cb.setObjectName(u'lic_cb')
        self._pop_lic_cb()
        self.grid_lyt.addWidget(self.lic_cb, 4, 1, 1, 1)

        self.acs_lbl = QLabel(self)
        self.acs_lbl.setObjectName(u'acs_lbl')
        self.acs_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.acs_lbl.setText(u'accessRights')
        self.grid_lyt.addWidget(self.acs_lbl, 5, 0, 1, 1)

        self.acs_cb = QComboBox(self)
        self.acs_cb.setObjectName(u'acs_cb')
        self._pop_acs_cb()
        self.grid_lyt.addWidget(self.acs_cb, 5, 1, 1, 1)

        self.cit_lbl = QLabel(self)
        self.cit_lbl.setObjectName(u'cit_lbl')
        self.cit_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.cit_lbl.setText(u'bibliographicCitation')
        self.grid_lyt.addWidget(self.cit_lbl, 6, 0, 1, 1)

        self.cit_pte = QPlainTextEdit(self)
        self.cit_pte.setObjectName(u'cit_pte')
        self.grid_lyt.addWidget(self.cit_pte, 6, 1, 1, 1)

        self.cmnt_lbl = QLabel(self)
        self.cmnt_lbl.setObjectName(u'cmnt_lbl')
        self.cmnt_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.cmnt_lbl.setText(u'datasetComment')
        self.grid_lyt.addWidget(self.cmnt_lbl, 7, 0, 1, 1)

        self.cmnt_pte = QPlainTextEdit(self)
        self.cmnt_pte.setObjectName(u'cmnt_pte')
        self.grid_lyt.addWidget(self.cmnt_pte, 7, 1, 1, 1)

        self.info_lbl = QLabel(self)
        self.info_lbl.setObjectName(u'info_lbl')
        self.info_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.info_lbl.setText(u'informationWithheld')
        self.grid_lyt.addWidget(self.info_lbl, 8, 0, 1, 1)

        self.info_pte = QPlainTextEdit(self)
        self.info_pte.setObjectName(u'info_pte')
        self.grid_lyt.addWidget(self.info_pte, 8, 1, 1, 1)

        self.dtgen_lbl = QLabel(self)
        self.dtgen_lbl.setObjectName(u'dtgen_lbl')
        self.dtgen_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.dtgen_lbl.setText(u'dataGeneralizations')
        self.grid_lyt.addWidget(self.dtgen_lbl, 9, 0, 1, 1)

        self.dtgen_pte = QPlainTextEdit(self)
        self.dtgen_pte.setObjectName(u'dtgen_pte')
        self.grid_lyt.addWidget(self.dtgen_pte, 9, 1, 1, 1)

        self.btn_lyt = QHBoxLayout(self)
        self.grid_lyt.addLayout(self.btn_lyt, 10, 1, 1, 1)

        self.sv_btn = QPushButton(self)
        self.sv_btn.setObjectName(u'sv_btn')
        self.sv_btn.setText(u'Save')
        self.sv_btn.clicked.connect(self._save_dtst)
        self.btn_lyt.addWidget(self.sv_btn)

        self.cl_btn = QPushButton(self)
        self.cl_btn.setObjectName(u'ok_btn')
        self.cl_btn.setText(u'Close')
        self.cl_btn.clicked.connect(self.close)
        self.btn_lyt.addWidget(self.cl_btn)

        self.stat_bar = QStatusBar(self)
        self.stat_bar.setObjectName(u'stat_bar')
        self.grid_lyt.addWidget(self.stat_bar, 11, 0, 1, 2)

    def _pop_inst_cb(self):
        """
        Populates the institution combo box.
        """

        inst_list = db.get_inst_list(self.mc.con)

        self.inst_cb.clear()
        self.inst_cb.addItems(inst_list)

    def _pop_rght_cb(self):
        """
        Populates the rights combo box.
        """

        inst_list = db.get_inst_list(self.mc.con)

        self.rght_cb.clear()
        self.rght_cb.addItems(inst_list)

    def _pop_lic_cb(self):
        """
        Populates the license combo box.
        """

        # OS.NINA
        # licenses are hard-coded
        lic_tpl = ('NLOD', 'CC-0', 'CC-BY 4.0')

        self.lic_cb.clear()
        self.lic_cb.addItems(sorted(lic_tpl))

    def _pop_acs_cb(self):
        """
        Populates the access rights combo box.
        """

        acs_rght_list = db.get_acs_list(self.mc.con)

        self.acs_cb.clear()
        self.acs_cb.addItems(acs_rght_list)

    def _save_dtst(self):
        """
        Saves a dataset into the database.
        """

        if len(self.name_le.text()) != 0:
            name = self.name_le.text()
        else:
            self.stat_bar.showMessage(u'Enter a dataset name.', 10000)
            return
        id = self.id_le.text()
        inst = self.inst_cb.currentText() \
            if len(self.inst_cb.currentText()) != 0 else None
        rght = self.rght_cb.currentText() \
            if len(self.rght_cb.currentText()) != 0 else None
        lic = self.lic_cb.currentText() \
            if len(self.lic_cb.currentText()) != 0 else None
        acs = self.acs_cb.currentText() \
            if len(self.acs_cb.currentText()) != 0 else None
        cit = self.cit_pte.toPlainText() \
            if len(self.cit_pte.toPlainText()) != 0 else None
        cmnt = self.cmnt_pte.toPlainText() \
            if len(self.cmnt_pte.toPlainText()) != 0 else None
        info = self.info_pte.toPlainText() \
            if len(self.info_pte.toPlainText()) != 0 else None
        dtgen = self.dtgen_pte.toPlainText() \
            if len(self.dtgen_pte.toPlainText()) != 0 else None

        if len(id) == 0:
            id = uuid.uuid4()
        else:
            dtst_cnt = db.get_dtst_cnt(self.mc.con, id)

            if dtst_cnt != 0:
                self.stat_bar.showMessage(
                    u'datasetID "{}" is already in the table. '
                    u'You can leave it empty.'.format(id),
                    10000)
                return

        db.ins_dtst(
            self.mc.con, name, id, inst, rght, lic, acs, cit, cmnt, info, dtgen)

        db.ins_dtst_log(
            self.mc.con, id, self.mc.get_con_info()[self.mc.usr_str])

        self.stat_bar.showMessage(u'Dataset saved.', 10000)

        self.iw.pop_dtst_cb()
        self.iw.upd_dtst(db.get_dtst_str(id, name))
