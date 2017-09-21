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

from PyQt4.QtCore import Qt, QDate, QDateTime
from PyQt4.QtGui import QDateEdit, QLineEdit


class MtyDe(QDateEdit):
    """
    A custom date edit that displays empty string when backspace or delete
    button is pressed.
    When empty string is displayed date is set to minimum date.
    """

    def __init__(self, par):
        """
        Constructor.

        :param par: A parent widget.
        :type par: QWidget
        """

        super(MtyDe, self).__init__(par)

        self.setDate(self.minimumDateTime().date())

        self.setCalendarPopup(True)

    def textFromDateTime(self, dttm):
        """
        Returns a text from the given date time.
        Returns empty string if the given date time equals minimum date time.

        :param dttm: A date time.
        :type dttm: QDateTime
        """

        if dttm == self.minimumDateTime():
            return u''
        else:
            return dttm.toString(self.displayFormat())

    def keyPressEvent(self, event):
        """
        Returns key press event.
        Sets date to minimum if backspace or delete button is an event key.

        :param event: An Event.
        :type event: QEvent
        """

        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            self.setDate(self.minimumDateTime().date())

        return QDateEdit.keyPressEvent(self, event)

    def mousePressEvent(self, event):
        """
        Returns mouse press event.
        Sets date to current date if text in line edit is an empty string.

        :param event: An Event.
        :type event: QEvent
        """

        if self.findChild(QLineEdit).text() == u'':
            self.setDate(QDate.currentDate())

        return QDateEdit.mousePressEvent(self, event)
