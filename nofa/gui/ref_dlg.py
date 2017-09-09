# -*- coding: utf-8 -*-
"""
/***************************************************************************
 RefDlg
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
    QPlainTextEdit, QHBoxLayout, QPushButton, QStatusBar, QDateEdit,
    QMessageBox)

import de
import exc
import vald
from .. import db


class RefDlg(QDialog):
    """
    A dialog for adding new reference.
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

        self.setObjectName(u'RefDlg')

        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.setWindowTitle(u'Add Reference')

        self.grid_lyt = QGridLayout(self)
        self.grid_lyt.setObjectName(u'grid_lyt')
        self.grid_lyt.setColumnMinimumWidth(1, 300)

        self._build_wdgs()

    def _build_wdgs(self):
        """
        Builds own widgets.
        """

        self.ttl_lbl = QLabel(self)
        self.ttl_lbl.setObjectName(u'ttl_lbl')
        self.ttl_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.ttl_lbl.setText(u'title')
        self.grid_lyt.addWidget(self.ttl_lbl, 0, 0, 1, 1)

        self.ttl_le = QLineEdit(self)
        self.ttl_le.setObjectName(u'ttl_le')
        self.grid_lyt.addWidget(self.ttl_le, 0, 1, 1, 1)

        self.au_lbl = QLabel(self)
        self.au_lbl.setObjectName(u'au_lbl')
        self.au_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.au_lbl.setText(u'author(s)')
        self.grid_lyt.addWidget(self.au_lbl, 1, 0, 1, 1)

        self.au_le = QLineEdit(self)
        self.au_le.setObjectName(u'au_le')
        self.grid_lyt.addWidget(self.au_le, 1, 1, 1, 1)

        self.yr_lbl = QLabel(self)
        self.yr_lbl.setObjectName(u'yr_lbl')
        self.yr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.yr_lbl.setText(u'year')
        self.grid_lyt.addWidget(self.yr_lbl, 2, 0, 1, 1)

        today_dt = QDate.currentDate()

        self.yr_mde = de.MtyDe(self)
        self.yr_mde.setObjectName(u'yr_mde')
        self.yr_mde.setDisplayFormat('yyyy')
        self.grid_lyt.addWidget(self.yr_mde, 2, 1, 1, 1)

        self.isbn_lbl = QLabel(self)
        self.isbn_lbl.setObjectName(u'isbn_lbl')
        self.isbn_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.isbn_lbl.setText(u'isbn')
        self.grid_lyt.addWidget(self.isbn_lbl, 3, 0, 1, 1)

        self.isbn_le = QLineEdit(self)
        self.isbn_le.setObjectName(u'isbn_le')
        self.grid_lyt.addWidget(self.isbn_le, 3, 1, 1, 1)

        self.issn_lbl = QLabel(self)
        self.issn_lbl.setObjectName(u'issn_lbl')
        self.issn_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.issn_lbl.setText(u'issn')
        self.grid_lyt.addWidget(self.issn_lbl, 4, 0, 1, 1)

        self.issn_le = QLineEdit(self)
        self.issn_le.setObjectName(u'issn_le')
        self.grid_lyt.addWidget(self.issn_le, 4, 1, 1, 1)

        self.tp_lbl = QLabel(self)
        self.tp_lbl.setObjectName(u'tp_lbl')
        self.tp_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.tp_lbl.setText(u'referenceType')
        self.grid_lyt.addWidget(self.tp_lbl, 5, 0, 1, 1)

        self.tp_cb = QComboBox(self)
        self.tp_cb.setObjectName(u'tp_cb')
        self.grid_lyt.addWidget(self.tp_cb, 5, 1, 1, 1)

        self.jrn_lbl = QLabel(self)
        self.jrn_lbl.setObjectName(u'jrn_lbl')
        self.jrn_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.jrn_lbl.setText(u'journalName')
        self.grid_lyt.addWidget(self.jrn_lbl, 6, 0, 1, 1)

        self.jrn_le = QLineEdit(self)
        self.jrn_le.setObjectName(u'jrn_le')
        self.grid_lyt.addWidget(self.jrn_le, 6, 1, 1, 1)

        self.vol_lbl = QLabel(self)
        self.vol_lbl.setObjectName(u'vol_lbl')
        self.vol_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.vol_lbl.setText(u'volume')
        self.grid_lyt.addWidget(self.vol_lbl, 7, 0, 1, 1)

        self.vol_le = QLineEdit(self)
        self.vol_le.setObjectName(u'vol_le')
        self.grid_lyt.addWidget(self.vol_le, 7, 1, 1, 1)

        self.pg_lbl = QLabel(self)
        self.pg_lbl.setObjectName(u'pg_lbl')
        self.pg_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.pg_lbl.setText(u'page')
        self.grid_lyt.addWidget(self.pg_lbl, 8, 0, 1, 1)

        self.pg_le = QLineEdit(self)
        self.pg_le.setObjectName(u'pg_le')
        self.grid_lyt.addWidget(self.pg_le, 8, 1, 1, 1)

        self.mand_wdgs = [
            self.ttl_le,
            self.au_le,
            self.yr_mde,
            self.tp_cb]

        self.iw.set_mand_wdgs(self.mand_wdgs)

        # temporary workaround
        self.vol_le.setValidator(vald.LenIntVald(self.vol_le, 1, 32767))

        self._fetch_ref_data()

        # to keep order
        self.input_wdgs = [
            self.ttl_le,
            self.au_le,
            self.yr_mde,
            self.isbn_le,
            self.issn_le,
            self.tp_cb,
            self.jrn_le,
            self.vol_le,
            self.pg_le]

        self.btn_lyt = QHBoxLayout(self)
        self.grid_lyt.addLayout(self.btn_lyt, 9, 1, 1, 1)

        self.sv_btn = QPushButton(self)
        self.sv_btn.setObjectName(u'sv_btn')
        self.sv_btn.setText(u'Save')
        self.sv_btn.clicked.connect(self._save_ref)
        self.btn_lyt.addWidget(self.sv_btn)

        self.cl_btn = QPushButton(self)
        self.cl_btn.setObjectName(u'ok_btn')
        self.cl_btn.setText(u'Close')
        self.cl_btn.clicked.connect(self.close)
        self.btn_lyt.addWidget(self.cl_btn)

    def _fetch_ref_data(self):
        """
        Fetches data from the NOFA database and populates widgets.
        """

        ref_cb_dict = self._ref_cb_dict

        self.iw.pop_cb(ref_cb_dict)

    @property
    def _ref_cb_dict(self):
        """
        Returns a reference combo box dictionary.

        :returns: A reference combo box dictionary.
            - key - combo_box_name
            - value - [fill_method, [arguments], default_value]
        :rtype: dict.
        """

        ref_cb_dict = {
            self.tp_cb: [
                db.get_reftp_list,
                [self.mc.con],
                self.iw.sel_str]}

        return ref_cb_dict

    def _save_ref(self):
        """
        Saves a reference into the database.
        """

        try:
            self.iw.chck_mand_wdgs(self.mand_wdgs, exc.MandNotFldExc)

            ref_list = self.iw.get_wdg_list(self.input_wdgs)

            # temporary fix
            ref_list[2] = ref_list[2].year

            id = db.ins_ref(self.mc.con, ref_list)

            db.ins_ref_log(
                self.mc.con, id, self.mc.con_info[self.mc.usr_str])

            self.iw.pop_ref_cb()
            self.iw.upd_ref(
                db.get_ref_str(ref_list[1], ref_list[0], ref_list[2], id))

            QMessageBox.information(self, u'Saved', u'Reference saved.')
        except exc.MandNotFldExc as e:
            e.wdg.setFocus()
            QMessageBox.warning(
                self,
                u'Mandatory Fields',
                u'Fill/select all mandatory fields.')
