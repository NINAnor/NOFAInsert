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

import uuid


class RefDlg(QDialog):
    """
    A dialog for adding new reference.
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
        self.ttl_lbl.setText(u'title*')
        self.grid_lyt.addWidget(self.ttl_lbl, 0, 0, 1, 1)

        self.ttl_le = QLineEdit(self)
        self.ttl_le.setObjectName(u'ttl_le')
        self.grid_lyt.addWidget(self.ttl_le, 0, 1, 1, 1)

        self.au_lbl = QLabel(self)
        self.au_lbl.setObjectName(u'au_lbl')
        self.au_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.au_lbl.setText(u'author(s)*')
        self.grid_lyt.addWidget(self.au_lbl, 1, 0, 1, 1)

        self.au_le = QLineEdit(self)
        self.au_le.setObjectName(u'au_le')
        self.grid_lyt.addWidget(self.au_le, 1, 1, 1, 1)

        self.yr_lbl = QLabel(self)
        self.yr_lbl.setObjectName(u'yr_lbl')
        self.yr_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.yr_lbl.setText(u'year*')
        self.grid_lyt.addWidget(self.yr_lbl, 2, 0, 1, 1)

        today_date = QDate.currentDate()

        self.yr_de = QDateEdit(self)
        self.yr_de.setObjectName(u'yr_de')
        self.yr_de.setDisplayFormat('yyyy')
        self.yr_de.setDate(today_date)
        self.grid_lyt.addWidget(self.yr_de, 2, 1, 1, 1)

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
        self._pop_tp_cb()
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
        self.vol_le.setValidator(QIntValidator(1, 32767, None))
        self.grid_lyt.addWidget(self.vol_le, 7, 1, 1, 1)

        self.pg_lbl = QLabel(self)
        self.pg_lbl.setObjectName(u'pg_lbl')
        self.pg_lbl.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        self.pg_lbl.setText(u'page')
        self.grid_lyt.addWidget(self.pg_lbl, 8, 0, 1, 1)

        self.pg_le = QLineEdit(self)
        self.pg_le.setObjectName(u'pg_le')
        self.grid_lyt.addWidget(self.pg_le, 8, 1, 1, 1)

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

        self.stat_bar = QStatusBar(self)
        self.stat_bar.setObjectName(u'stat_bar')
        self.grid_lyt.addWidget(self.stat_bar, 10, 0, 1, 2)

    def _pop_tp_cb(self):
        """
        Populates the type combo box.
        """

        cur = self.mw._get_db_cur()
        cur.execute(
            '''
            SELECT      "referenceType" tp
            FROM        nofa."l_referenceType"
            ORDER BY    tp;
            ''')
        tps = cur.fetchall()

        tp_list = [t[0] for t in tps]

        self.tp_cb.clear()
        self.tp_cb.addItems(tp_list)

    def _save_ref(self):
        """
        Saves a reference into the database.
        """

        if len(self.ttl_le.text()) != 0:
            ttl = self.ttl_le.text()
        else:
            self.stat_bar.showMessage(u'Enter a reference title.', 10000)
            return
        if len(self.au_le.text()) != 0:
            au = self.au_le.text()
        else:
            self.stat_bar.showMessage(u'Enter a reference author(s).', 10000)
            return
        yr = self.yr_de.date().year()
        isbn = self.isbn_le.text() \
            if len(self.isbn_le.text()) != 0 else None
        issn = self.issn_le.text() \
            if len(self.issn_le.text()) != 0 else None
        tp = self.tp_cb.currentText()
        jrn = self.jrn_le.text() \
            if len(self.jrn_le.text()) != 0 else None
        vol = self.vol_le.text() \
            if len(self.vol_le.text()) != 0 else None
        pg = self.pg_le.text() \
            if len(self.pg_le.text()) != 0 else None

        cur = self.mw._get_db_cur()
        cur.execute(
            '''
            INSERT INTO     nofa.m_reference (
                                "titel",
                                "author",
                                "year",
                                "isbn",
                                "issn",
                                "referenceType",
                                "journalName",
                                "volume",
                                "page")
            VALUES          (   %(title)s,
                                %(author)s,
                                %(year)s,
                                %(isbn)s,
                                %(issn)s,
                                %(referenceType)s,
                                %(journalName)s,
                                %(volume)s,
                                %(page)s)
            RETURNING           "referenceID"
            ''',
            {'title': ttl,
             'author': au,
             'year': yr,
             'isbn': isbn,
             'issn': issn,
             'referenceType': tp,
             'journalName': jrn,
             'volume': vol,
             'page': pg})
        id = cur.fetchone()[0]

        self.stat_bar.showMessage(u'Reference saved.', 10000)

        self.mw.pop_ref_cb()
        self.mw.upd_ref(self.mw.get_ref_str(au, ttl, id))
