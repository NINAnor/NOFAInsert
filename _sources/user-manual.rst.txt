###########
User Manual
###########

************
Installation
************

NOFAInsert plugin is not a part of the
`official QGIS repository <https://plugins.qgis.org/>`__.
However, it still can be installed the same way as other plugins.
All you need to do is to add a `NINA <http://www.nina.no/english/Home>`__
repository.

.. note::

   Your `QGIS <https://www.qgis.org/>`__ and plugin might look different from
   the screenshots in this manual. All screenshots presented here were taken
   in `QGIS <https://www.qgis.org/>`__ with ``Cleanlooks`` style.
   You can change your `QGIS <https://www.qgis.org/>`__ style
   in :guilabel:`Settings` :menuselection:`-->` :guilabel:`Options...`
   :menuselection:`-->` :guilabel:`General`.

First open :guilabel:`Plugins` :menuselection:`-->`
:guilabel:`Manage and Install Plugins...`.

.. figure:: images/installation-open_plugin_manager.png

   Open plugin manager.

In :guilabel:`Settings` tab activate option
:guilabel:`Show also experimental plugins`.

By clicking on :guilabel:`Add...` button add a
`NINA <http://www.nina.no/english/Home>`__ repository:

.. code-block:: none

   Name:	NINA
   URL:		http://vm-srv-finstad.vm.ntnu.no/NOFA_plugins/plugins.xml

.. figure:: images/installation-add_repository.png

   Add repository.

.. figure:: images/installation-add_nina_repository.png

   Add NINA repository.

In :guilabel:`All` or :guilabel:`Not installed` tab search for ``NOFAInsert``.
Select NOFAInsert plugin and click on :guilabel:`Install plugin`.

.. figure:: images/installation-plugin_installation.png

   Plugin installation.

After a successful installation plugin's icon will appear in
:guilabel:`Plugins Toolbar`.
You can start NOFAInsert plugin by clicking on its icon or by selecting
:guilabel:`Plugins` :menuselection:`-->` :guilabel:`NOFAInsert`
:menuselection:`-->` :guilabel:`NOFAInsert`.

.. figure:: images/installation-plugins_toolbar_icon.png

   Plugin icon in Plugins Toolbar.

****************
Connection Setup
****************

Before inserting data into `NOFA <https://github.com/NINAnor/NOFA/wiki>`__
database it is necessary to set up connection parameters.

.. figure:: images/connection-gui.png

   Connection Dialog – Graphical User Interface.

Element 1:
   Line edits for connection parameters.

Element 2:
   Button that tests and saves connection parameters.

Element 3:
   Button that closes the dialog.

First enter all connection parameters (element 1) and then test the connection
(element 2). After successful connection test close the dialog (element 3).

Connection parameters can be later accessed by :guilabel:`Plugins`
:menuselection:`-->` :guilabel:`NOFAInsert` :menuselection:`-->`
:guilabel:`Connection Parameters`.

************************
Graphical User Interface
************************

Graphical user interface of the main window contains two tabs - :guilabel:`Main`
and :guilabel:`History`.
In :guilabel:`Main` tab you can insert data and :guilabel:`History` tab serves
as an overview of data insertion.

.. figure:: images/gui.png

   Graphical User Interface.

Element 1:
   You can switch between two tabs:

      * :guilabel:`Main` – to insert data.
        :ref:`More information <main>`.
      * :guilabel:`History` – to view history of data insertion.
        :ref:`More information <history>`.

Element 2:
   :guilabel:`Database Name` – displays name of a database the plugin is
   connected to.

The whole graphical user interface is customizable meaning that you can resize
sections or hide it completely.
Widgets that are mandatory and have not been filled or selected yet are
displayed with reddish background.

.. _main:

****
Main
****

:guilabel:`Main` tab is used for inserting data.

.. figure:: images/main-gui.png

   Main tab – Graphical User Interface.

Element 1:
   :guilabel:`Metadata Tool Box` – to set metadata.
   :ref:`More information <metadata-tool-box>`.

Element 2:
   :guilabel:`Occurrence Table` is an overview of all entered occurrences.
   Data can not be edited directly in the table.
   To edit data select a row you want to adjust
   and set data in :guilabel:`Occurrence Widgets` (element 4).
   There are several buttons that let you work with the table rows:

      * |select-row-up| Select row up.
      * |select-row-down| Select row down.
      * |add-row| Add row.
      * |delete-row| Delete selected row.
      * |reset-selected-row| Reset selected row.
      * |reset-all-rows| Reset all rows.
      * |delete-all-rows| Delete all rows except selected one.

Element 3:
   In :guilabel:`Taxonomic Coverage Tree` you can select whole families
   or individual species.

Element 4:
   :guilabel:`Occurrence Widgets` show data in a current row in the
   :guilabel:`Occurrence Table` (element 2).
   Any change is immediately written to the table.

Element 5:
   :guilabel:`Reset` – to reset the whole plugin to its original state.

Element 6:
   :guilabel:`Insert to NOFA` – to insert data into database.

In order to insert data into database all mandatory fields have to filled
or selected.
You can do that in any order. If you think you have entered everything
don't be afraid and try to click on :guilabel:`Insert to NOFA` (element 6).
Plugin will inform you in case something is missing.

.. _metadata-tool-box:

Metadata Tool Box
=================

:guilabel:`Metadata tool box` consists of five sections.
All except :guilabel:`Reference` are mandatory.

   * :guilabel:`Location` – :ref:`more information <location>`.
   * :guilabel:`Event` – :ref:`more information <event>`.
   * :guilabel:`Dataset` – :ref:`more information <dataset-project-reference>`.
   * :guilabel:`Project` – :ref:`more information <dataset-project-reference>`.
   * :guilabel:`Reference` –
     :ref:`more information <dataset-project-reference>`.

.. _location:

Location
--------

In :guilabel:`Location` section user can set location.

.. figure:: images/location-gui.png
   :width: 85%

   Location – Graphical User Interface.

Element 1:
   You can switch between three tabs:

      * :guilabel:`Search` – to search for existing location(s) and add it
        to the location table. :ref:`More information <location-search>`.
      * :guilabel:`Edit` – to edit one specific row
        in :guilabel:`Location Table` (element 2).
        :ref:`More information <location-edit>`.
      * :guilabel:`Manual` – to add multiple locations by text.
        :ref:`More information <location-manual>`.

Element 2:
   :guilabel:`Location Table` is an overview of all entered locations.
   Data can not be edited directly in the table.
   In order to edit data select a row you want to edit
   and switch to :guilabel:`Edit` tab.
   There are several buttons that let you work with the table rows:

      * |select-row-up| Select row up.
      * |select-row-down| Select row down.
      * |add-row| Add row.
      * |delete-row| Delete selected row.
      * |reset-selected-row| Reset selected row.
      * |reset-all-rows| Reset all rows.
      * |delete-all-rows| Delete all rows except selected one.

.. |select-row-up| image:: images/select_row_up.png
.. |select-row-down| image:: images/select_row_down.png
.. |add-row| image:: images/add_row.png
.. |delete-row| image:: images/delete_row.png
.. |reset-selected-row| image:: images/reset_selected_row.png
.. |reset-all-rows| image:: images/reset_all_rows.png
.. |delete-all-rows| image:: images/delete_all_rows.png

Element 3:
   :guilabel:`Preview Button` – to add layer(s) to map canvas.
   When there is at least one existing/new location in
   :guilabel:`Location Table`, then layer
   ``preview_location-new``/``preview_location-existing`` is added.

.. _location-search:

Search
""""""

:guilabel:`Search` tab lets you search for existing locations in database
and add them to the :guilabel:`Location Table`.

.. figure:: images/location-search-gui.png
   :width: 75%

   Location – Search – Graphical User Interface.

Element 1:
   Line edit for searching for water body by name.

Element 2:
   Combo boxes that narrows search result.

Element 3:
   Button that performs search based on filters (elements 1 and 2).

Element 4:
   Button that loads search results to map canvas as a separate layer.

Element 5:
   Button that adds locationID(s) of selected feature(s) in active layer
   to the location table.

Element 6:
   Button that adds `OpenStreetMap <https://www.openstreetmap.org/>`__ basemap
   layer to map canvas.

First, enter filters (elements 1 and 2) and then validate your search
(element 3). When at least one location is found you can
load a layer containing the result to map canvas (element 4).
Finally add selected features in the layer (element 5) to the
:guilabel:`Location Table`.
You can also load `OpenStreetMap <https://www.openstreetmap.org/>`__ basemap
(element 6) to map canvas to make it easier to orientate.

.. _location-edit:

Edit
""""

In :guilabel:`Edit` tab you can edit currently selected row in the location
table. Any change is immediately written to the table.

.. figure:: images/location-edit-gui.png
   :width: 75%

   Location – Edit – Graphical User Interface.

Element 1:
   Combo box with location methods:

      * **locationID** – to enter/edit locationID.
      * **coordinates** – to enter/edit coordinates.
      * **Norwegian VatLnr** – to enter/edit Norwegian VatLnr.

Element 2:
   Area that changes according to the current method (element 1).

Select method in combo box at the top (element 1). Area below (element 2)
changes accordingly and displays widgets where you can enter/edit data.
There is only one line edit for **locationID** and **Norwegian VatLnr** methods.
Method **coordinates** offers few more widgets and lets you enter coordinates
by mouse click on map canvas.

.. _location-manual:

Manual
""""""

:guilabel:`Manual` tab allows you to add location(s) to
:guilabel:`Location Table` by text.

.. figure:: images/location-manual-gui.png
   :width: 75%

   Location – Manual – Graphical User Interface.

Element 1:
   Combo box with location methods:

      * **locationID** – to enter locationID.
      * **coordinates** – to enter coordinates.
      * **Norwegian VatLnr** – to enter Norwegian VatLnr.

Element 2:
   Area that changes according to the current method (element 1).

Element 3:
   Button that adds location(s) from text (element 2) to
   :guilabel:`Location Table`.

Select method in combo box at the top (element 1). Area below (element 2)
changes accordingly and displays widgets where you can enter/edit data.
When everything is set add location(s) (element 3)
to :guilabel:`Location Table`.

Text format with examples:
   * **locationID** – "<UUID>" separated by commas.

     .. code-block:: none

        0001b8f3-65fb-4877-8808-ca67094e1cbb, 0002bdc7-b232-4c5b-bd4d-3d4f21da24b6

   * **coordinates** – "<X> <Y> <verbatimLocality (optional)>"
     separated by commas.

     .. code-block:: none

        601404.85 6644928.24 Hovinbk, 580033.12 6633807.99 Drengsrudbk

   * **Norwegian VatLnr** – "<Norwegian VatLnr>" separated by commas.

     .. code-block:: none

        3067, 5616, 5627

.. _event:

Event
-----

:guilabel:`Event` section contains widgets with information about event.

.. figure:: images/event-gui.png
   :width: 50%

   Event – Graphical User Interface.

.. _dataset-project-reference:

Dataset, Project, Reference
---------------------------

:guilabel:`Dataset` :guilabel:`Project` and :guilabel:`Reference` sections
are all basically the same therefore only example for :guilabel:`Dataset`
is present in this manual.

.. figure:: images/dataset-gui.png
   :width: 55%

   Dataset – Graphical User Interface.

Element 1:
   Combo box with existing datasets.

Element 2:
   Button that opens a windows for adding new dataset.

Element 3:
   List with information about currently selected dataset.

You can select one of existing datasets (element 1) or you can add a new dataset
(element 2). List (element 3) displays information about selected dataset. 

.. _history:

*******
History
*******

In :guilabel:`History` tab user can view history of data insertion.

.. figure:: images/history-gui.png

   History tab – Graphical User Interface.

Element 1:
   You can switch between tabs:

      * :guilabel:`Occurrence`
      * :guilabel:`Location`
      * :guilabel:`Event`
      * :guilabel:`Dataset`
      * :guilabel:`Project`
      * :guilabel:`Reference`

Element 2:
   Table that is different for each tab.

Element 3:
   Insert date filters.

Element 4:
   Update date filters.

Element 5:
   User filter.

You can browse data insertion history of different tables (element 1).
Change filters (elements 2, 3, 4) to narrow or widen displayed data.
