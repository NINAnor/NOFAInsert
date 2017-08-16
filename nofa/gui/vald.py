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

from PyQt4.QtGui import QValidator


class LenTxtVald(QValidator):
    """
    A custom validator that check if text length is zero.
    """

    def __init__(self, par):
        """
        Constructor.

        :param par: A parent widget.
        :type par: QWidget.
        """

        super(LenTxtVald, self).__init__(par)

    def validate(self, txt, pos):
        """
        Validates the given text.

        :param txt: A text.
        :type txt: str.
        :param pos: A position.
        :type pos: int.

        :returns: A tuple that contains validator, text and position.
        :rtype: tuple
        """

        if len(txt) == 0:
            return (QValidator.Intermediate, txt, pos)

        return (QValidator.Acceptable, txt, pos)

    def fixup(self, txt):
        """
        Corrects the given text.

        :param txt: A text.
        :type txt: str.
        """

        pass


class LenIntVald(QValidator):
    """
    A custom validator that check if text length is zero and integer.
    """

    def __init__(self, par):
        """
        Constructor.

        :param par: A parent widget.
        :type par: QWidget.
        """

        super(LenIntVald, self).__init__(par)

    def validate(self, txt, pos):
        """
        Validates the given text.

        :param txt: A text.
        :type txt: str.
        :param pos: A position.
        :type pos: int.

        :returns: A tuple that contains validator, text and position.
        :rtype: tuple
        """

        if len(txt) == 0:
            return (QValidator.Intermediate, txt, pos)
        else:
            try:
                int(txt)
            except ValueError:
                return (QValidator.Invalid, txt, pos)

        return (QValidator.Acceptable, txt, pos)

    def fixup(self, txt):
        """
        Corrects the given text.

        :param txt: A text.
        :type txt: str.
        """

        pass
