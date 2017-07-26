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

import datetime
import psycopg2, psycopg2.extras


def get_con(con_info):
    """
    Returns a connection.

    :returns: A connection.
    :rtype: psycopg2.connection.
    """

    con = psycopg2.connect(**con_info)
    con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    return con


def _get_db_cur(con):
    """
    Returns a database cursor.
    
    :param con: A connection.
    :type con: psycopg2.connection.
    :returns: A database cursor.
    :rtype: psycopg2.cursor.
    """

    return con.cursor()


def check_nofa_tbls(con):
    """
    Checks if the database is NOFA.

    :param con: A connection.
    :type con: psycopg2.connection.
    :returns: True when database is NOFA, False otherwise.
    :rtype: bool.
    """

    cur = _get_db_cur(con)

    cur.execute(
        '''
        SELECT    table_name
        FROM      information_schema.tables
        WHERE     table_schema = 'nofa'
                  AND
                  table_name IN ('location', 'event', 'occurrence')
        ''')

    if cur.rowcount == 3:
        resp = True
    else:
        resp = False

    return resp

def ins_event(con, loc_id, event_id, event_list, dtst_id, prj_id):
    """
    Insert an event to the database.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param loc_id: A location ID.
    :type loc_id: uuid.UUID.
    :param event_id: An event ID.
    :type event_id: uuid.UUID.
    :param event_list: A list of data from event input widgets.
    :type event_list: list.
    :param dtst_id: A dataset ID.
    :type dtst_id: str.
    :param prj_id: A project ID.
    :type prj_id: str.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO    nofa.event (
                           "locationID",
                           "eventID",
                           "samplingProtocol",
                           "sampleSizeValue",
                           "sampleSizeUnit",
                           "samplingEffort",
                           "dateStart",
                           "dateEnd",
                           "recordedBy",
                           "eventRemarks",
                           "reliability",
                           "datasetID",
                           "projectID")
        VALUES         (   %(locationID)s,
                           %(eventID)s,
                           %(samplingProtocol)s,
                           %(sampleSizeValue)s,
                           %(sampleSizeUnit)s,
                           %(samplingEffort)s,
                           %(dateStart)s,
                           %(dateEnd)s,
                           %(recordedBy)s,
                           %(eventRemarks)s,
                           %(reliability)s,
                           %(datasetID)s,
                           %(projectID)s)
        ''',
        {'locationID': loc_id,
         'eventID': event_id,
         'samplingProtocol': event_list[0],
         'sampleSizeValue': event_list[1],
         'sampleSizeUnit': event_list[2],
         'samplingEffort': event_list[3],
         'dateStart': event_list[4],
         'dateEnd': event_list[5],
         'recordedBy': event_list[6],
         'eventRemarks': event_list[7],
         'reliability': event_list[8],
         'datasetID': dtst_id,
         'projectID': prj_id})

def get_txn_id(con, txn):
    """
    Returns a taxon ID based on the given scientific name.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param txn: A taxon scientific name.
    :type txn: str.
    :returns: A taxon ID.
    :rtype: int.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "taxonID"
        FROM        nofa."l_taxon"
        WHERE       "scientificName" = %s
        ''',
        (txn,))

    txn_id = cur.fetchone()[0]

    return txn_id

def get_ectp_id(con, ectp):
    """
    Returns an ecotype ID based on the given vernacular name.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param txn: An ecotype vernacular name.
    :type txn: str.
    :returns: An ecotype ID, None when there is no ecotype.
    :rtype: int.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "ecotypeID"
        FROM        nofa."l_ecotype"
        WHERE       "vernacularName" = %s
        ''',
        (ectp,))

    ectp_id = cur.fetchone()[0] if cur.rowcount != 0 else None

    return ectp_id

def ins_occ(con, occ_id, txn_id, ectp_id, occ_row_list, event_id):
    """
    insert an occurrence to the database.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param occ_id: A occurrence ID.
    :type occ_id: uuid.UUID.
    :param txn_id: A taxon ID.
    :type txn_id: int.
    :param ectp_id: An ecotype ID, None when there is no ecotype.
    :type ectp_id: int.
    :param occ_row_list: A list of data in the row in the occurrence table.
    :type occ_row_list: list.
    :param event_id: An event ID.
    :type event_id: uuid.UUID.
    :returns: An ecotype ID, None when there is no ecotype.
    :rtype: int.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO    nofa."occurrence" (
                           "occurrenceID",
                           "taxonID",
                           "ecotypeID",
                           "organismQuantityType",
                           "organismQuantity",
                           "occurrenceStatus",
                           "populationTrend",
                           "occurrenceRemarks",
                           "establishmentMeans",
                           "establishmentRemarks",
                           "spawningCondition",
                           "spawningLocation",
                           "verifiedBy",
                           "verifiedDate",
                           "modified",
                           "eventID")
        VALUES         (   %(occurrenceID)s,
                           %(taxonID)s,
                           %(ecotypeID)s,
                           %(organismQuantityType)s,
                           %(organismQuantity)s,
                           %(occurrenceStatus)s,
                           %(populationTrend)s,
                           %(occurrenceRemarks)s,
                           %(establishmentMeans)s,
                           %(establishmentRemarks)s,
                           %(spawningCondition)s,
                           %(spawningLocation)s,
                           %(verifiedBy)s,
                           %(verifiedDate)s,
                           %(modified)s,
                           %(eventID)s)
        ''',
        {'occurrenceID': occ_id,
         'taxonID': txn_id,
         'ecotypeID': ectp_id,
         'organismQuantityType': occ_row_list[2],
         'organismQuantity': float(occ_row_list[3]) \
            if len(occ_row_list[3]) != 0 else None,
         'occurrenceStatus': occ_row_list[4],
         'populationTrend': occ_row_list[5],
         'occurrenceRemarks': occ_row_list[6],
         'establishmentMeans': occ_row_list[7],
         'establishmentRemarks': occ_row_list[8],
         'spawningCondition': occ_row_list[9],
         'spawningLocation': occ_row_list[10],
         'verifiedBy': occ_row_list[11],
         'verifiedDate': occ_row_list[12],
         'modified': datetime.datetime.now(),
         'eventID': event_id})

def ins_txncvg(con, txn_id, event_id):
    """
    Insert a taxon coverage into the database.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param txn_id: A taxon ID.
    :type txn_id: int.
    :param event_id: An event ID.
    :type event_id: uuid.UUID.
    """

    # OS.NINA
    # this query does not work
    # TODO - solve PK 
    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     nofa."taxonomicCoverage"(
                            "taxonID_l_taxon",
                            "eventID_observationEvent")
        VALUES          (%s, %s)
        ''',
        (txn_id, event_id))

def get_loc_id_list(con, locs_tpl):
    """
    Returns a list of location IDs.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param locs_tpl: A tuple of locations.
    :type locs_tpl: tuple.
    :returns: A list of locations IDs.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      distinct "locationID" lid
        FROM        nofa.location
        WHERE       "no_vatn_lnr" IN %s
        ORDER BY    lid
        ''',
        (locs_tpl,))
    loc_ids = cur.fetchall()

    loc_id_list = [l[0] for l in loc_ids]

    return loc_id_list

