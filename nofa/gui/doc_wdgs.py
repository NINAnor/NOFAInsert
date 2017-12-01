# -*- coding: utf-8 -*-
"""
/***************************************************************************
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

from PyQt4.QtCore import QUrl
from PyQt4.QtGui import QLineEdit, QPushButton
from PyQt4.QtWebKit import QWebPage

from abc import ABCMeta, abstractmethod

class UrlLe(QLineEdit):
    """
    A widget for URL input.
    """

    def __init__(self, par, web_view):
        """
        Constructor.

        :param par: A parent widget.
        :type par: QWidget
        :param web_view: A web view.
        :type web_view: QWebView
        """

        super(UrlLe, self).__init__(par)

        self.web_view = web_view

        self.returnPressed.connect(self._load_url)

    def _load_url(self):
        """
        Loads URL into the web view widget.
        """

        txt = self.text()

        if not txt.startswith(('http://', 'https://')):
            txt = 'http://{}'.format(txt)
            self.setText(txt)

        self.web_view.load(QUrl(txt))


class BackBtn(QPushButton):
    """
    A button for going back in history.
    """

    def __init__(self, par, web_view):
        """
        Constructor.

        :param par: A parent widget.
        :type par: QWidget
        :param web_view: A web view.
        :type web_view: QWebView
        """

        super(BackBtn, self).__init__(par)

        self.web_view = web_view

        self.clicked.connect(self._go_back)

        self.setText('<')
        self.setFixedWidth(self.height())

    def _go_back(self):

        self.web_view.page().triggerAction(QWebPage.Back)


class FwdBtn(QPushButton):
    """
    A button for going forward in history.
    """

    def __init__(self, par, web_view):
        """
        Constructor.

        :param par: A parent widget.
        :type par: QWidget
        :param web_view: A web view.
        :type web_view: QWebView
        """

        super(FwdBtn, self).__init__(par)

        self.web_view = web_view

        self.clicked.connect(self._go_fwd)

        self.setText('>')
        self.setFixedWidth(self.height())

    def _go_fwd(self):

        self.web_view.page().triggerAction(QWebPage.Forward)
