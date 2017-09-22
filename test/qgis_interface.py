# -*- coding: utf-8 -*-
"""
/***************************************************************************
 QgisInterface
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

import logging
from PyQt4.QtCore import QObject, pyqtSlot, pyqtSignal
from qgis.core import QgsMapLayerRegistry
from qgis.gui import QgsMapCanvasLayer

LOGGER = logging.getLogger('QGIS')


class QgisInterface(QObject):
    """
    Class to expose QGIS objects and functions to plugins.

    This class is here for enabling us to run unit tests only,
    so most methods are simply stubs.
    """

    currentLayerChanged = pyqtSignal(QgsMapCanvasLayer)

    def __init__(self, canvas):
        """
        Constructor.

        :param canvas: Map canvas.
        :type canvas: QgsMapCanvas
        """

        QObject.__init__(self)
        self.canvas = canvas

        # set up slots to mimic the behaviour of QGIS
        QgsMapLayerRegistry.instance().layersAdded.connect(self.addLayers)
        QgsMapLayerRegistry.instance().layerWasAdded.connect(self.addLayer)
        QgsMapLayerRegistry.instance().removeAll.connect(self.removeAllLayers)

        # for processing module
        self.destCrs = None

    @pyqtSlot('QStringList')
    def addLayers(self, layers):
        """
        Handles layers being added to the registry so they show up in canvas.

        :param layers: A list of map layers (QgsMapLayer) that were added.
        :type layers: list

        .. note:: The QgsInterface api does not include this method,
            it is added here as a helper to facilitate testing.
        """

        current_layers = self.canvas.layers()
        final_layers = []
        for layer in current_layers:
            final_layers.append(QgsMapCanvasLayer(layer))
        for layer in layers:
            final_layers.append(QgsMapCanvasLayer(layer))

        self.canvas.setLayerSet(final_layers)

    @pyqtSlot('QgsMapLayer')
    def addLayer(self, layer):
        """
        Handles a layer being added to the registry so it shows up in canvas.

        :param layer: A list of map layers (QgsMapLayer) that were added
        :type layer: list

        .. note: The QgsInterface api does not include this method, it is added
                 here as a helper to facilitate testing.

        .. note: The addLayer method was deprecated in QGIS 1.8 so you should
                 not need this method much.
        """

        pass

    @pyqtSlot()
    def removeAllLayers(self):
        """Removes layers from the canvas before they get deleted."""

        self.canvas.setLayerSet([])

    def newProject(self):
        """Creates a new project."""

        QgsMapLayerRegistry.instance().removeAllMapLayers()

    # ---------------- API Mock for QgsInterface follows -------------------

    def zoomFull(self):
        """Zooms to the map full extent."""

        pass

    def zoomToPrevious(self):
        """Zooms to previous view extent."""

        pass

    def zoomToNext(self):
        """Zooms to next view extent."""

        pass

    def zoomToActiveLayer(self):
        """Zoom to extent of active layer."""

        pass

    def addVectorLayer(self, path, base_name, provider_key):
        """Adds a vector layer.

        :param path: Path to layer.
        :type path: str
        :param base_name: Base name for layer.
        :type base_name: str
        :param provider_key: Provider key e.g. 'ogr'
        :type provider_key: str
        """

        pass

    def addRasterLayer(self, path, base_name):
        """Adds a raster layer given a raster layer file name

        :param path: Path to layer.
        :type path: str
        :param base_name: Base name for layer.
        :type base_name: str
        """

        pass

    def activeLayer(self):
        """Returns pointer to the active layer."""

        for item in QgsMapLayerRegistry.instance().mapLayers():
            return layers[item]

    def addToolBarIcon(self, action):
        """Adds an icon to the plugins toolbar.

        :param action: Action to add to the toolbar.
        :type action: QAction
        """

        pass

    def removeToolBarIcon(self, action):
        """Removes an action (icon) from the plugin toolbar.

        :param action: Action to add to the toolbar.
        :type action: QAction
        """

        pass

    def addToolBar(self, name):
        """Adds toolbar with specified name.

        :param name: Name for the toolbar.
        :type name: str
        """

        pass

    def addPluginToMenu(self, name, action):
        """
        Adds an action to the plugins menu.

        :param name: Name of the plugin menu.
        :type name: str
        :param action: Action to add to the plugins menu.
        :type action: QAction
        """

        pass

    def mapCanvas(self):
        """Returns a pointer to the map canvas."""

        return self.canvas

    def mainWindow(self):
        """Returns a pointer to the main window.

        In case of QGIS it returns an instance of QgisApp.
        """

        pass

    def addDockWidget(self, area, dock_widget):
        """Adds a dock widget to the main window.

        :param area: Where in the ui the dock should be placed.
        :type area:
        :param dock_widget: A dock widget to add to the UI.
        :type dock_widget: QDockWidget
        """

        pass

    def legendInterface(self):
        """Returns the legend."""

        return self.canvas
