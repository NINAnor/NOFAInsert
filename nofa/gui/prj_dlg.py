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

from PyQt4.QtCore import Qt, QDate
from PyQt4.QtGui import (
    QDialog, QGridLayout, QSizePolicy, QLabel, QLineEdit, QComboBox,
    QPlainTextEdit, QHBoxLayout, QPushButton, QStatusBar, QMessageBox)

import de
import exc
import vald
from .. import db


class PrjDlg(QDialog):
    """
    A dialog for adding new project.
    """

    def __init__(self, mc, iw):
        """
        Constructor.

        :param mc: A reference to the main class.
        :type mc: object.
        :param iw: A reference to the insert window.
        :type iw: QMainWindow.
        """

        super(QDialog, self).__init__()

        self.mc = mc
        self.iw = iw

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
        self.org_lbl.setText(u'organization')
        self.grid_lyt.addWidget(self.org_lbl, 0, 0, 1, 1)

        self.org_cb = QComboBox(self)
        self.org_cb.setObjectName(u'org_cb')
        self.grid_lyt.addWidget(self.org_cb, 0, 1, 1, 1)

        self.no_lbl = QLabel(self)
        self.no_lbl.setObjectName(u'no_lbl')
        self.no_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.no_lbl.setText(u'projectNumber')
        self.grid_lyt.addWidget(self.no_lbl, 1, 0, 1, 1)

        self.no_le = QLineEdit(self)
        self.no_le.setObjectName(u'no_le')
        self.grid_lyt.addWidget(self.no_le, 1, 1, 1, 1)

        self.name_lbl = QLabel(self)
        self.name_lbl.setObjectName(u'name_lbl')
        self.name_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.name_lbl.setText(u'projectName')
        self.grid_lyt.addWidget(self.name_lbl, 2, 0, 1, 1)

        self.name_le = QLineEdit(self)
        self.name_le.setObjectName(u'name_le')
        self.grid_lyt.addWidget(self.name_le, 2, 1, 1, 1)

        self.styr_lbl = QLabel(self)
        self.styr_lbl.setObjectName(u'styr_lbl')
        self.styr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.styr_lbl.setText(u'startYear')
        self.grid_lyt.addWidget(self.styr_lbl, 3, 0, 1, 1)

        self.styr_mde = de.MtyDe(self)
        self.styr_mde.setObjectName(u'styr_mde')
        self.styr_mde.setDisplayFormat('yyyy')
        self.grid_lyt.addWidget(self.styr_mde, 3, 1, 1, 1)

        self.endyr_lbl = QLabel(self)
        self.endyr_lbl.setObjectName(u'endyr_lbl')
        self.endyr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.endyr_lbl.setText(u'endYear')
        self.grid_lyt.addWidget(self.endyr_lbl, 4, 0, 1, 1)

        self.endyr_mde = de.MtyDe(self)
        self.endyr_mde.setObjectName(u'endyr_mde')
        self.endyr_mde.setDisplayFormat('yyyy')
        self.grid_lyt.addWidget(self.endyr_mde, 4, 1, 1, 1)

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

        self.mand_wdgs = [
            self.org_cb,
            self.no_le,
            self.name_le,
            self.styr_mde,
            self.ldr_le,
            self.fncr_le]

        self.iw.set_mand_wdgs(self.mand_wdgs)

        # temporary workaround
        self.no_le.setValidator(
            vald.LenIntVald(self.no_le, -2147483648, 2147483647))

        self._fetch_prj_data()

        # to keep order
        self.input_wdgs = [
            self.org_cb,
            self.no_le,
            self.name_le,
            self.styr_mde,
            self.endyr_mde,
            self.ldr_le,
            self.mbr_pte,
            self.fncr_le,
            self.rmk_pte]

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

    def _fetch_prj_data(self):
        """
        Fetches data from the NOFA database and populates widgets.
        """

        self.iw.pop_cb(self._prj_cb_dict)

    @property
    def _prj_cb_dict(self):
        """
        Returns a project combo box dictionary.

        :returns: A project combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        dtst_cb_dict = {
            self.org_cb: [
                db.get_inst_list,
                [self.mc.con],
                self.iw.sel_str]}

        return dtst_cb_dict

    def _save_prj(self):
        """
        Saves a project into the database.
        """

        try:
            self.iw.chck_mand_wdgs(self.mand_wdgs, exc.MandNotFldExc)

            prj_list = self.iw.get_wdg_list(self.input_wdgs)

            # temporary fix
            for i in range(3, 5):
                try:
                    prj_list[i] = prj_list[i].year
                except:
                    pass

            id = db.ins_prj(self.mc.con, prj_list)

            db.ins_prj_log(
                self.mc.con, id, self.mc.con_info[self.mc.usr_str])

            self.iw.pop_prj_cb()
            self.iw.upd_prj(db.get_prj_str(prj_list[2], prj_list[0]))

            QMessageBox.information(self, u'Saved', u'Project saved.')
        except exc.MandNotFldExc as e:
            e.wdg.setFocus()
            QMessageBox.warning(
                self,
                u'Mandatory Fields',
                u'Fill/select all mandatory fields.')
