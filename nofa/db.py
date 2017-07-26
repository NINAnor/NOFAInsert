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

from collections import defaultdict
import datetime
import psycopg2, psycopg2.extras


DASH_SPLIT_STR = u' - '


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

def get_dtst_info(con, dtst_id):
    """
    Returns information about a dataset with the given ID.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param dtst_id: A dataset ID.
    :type dtst_id: str.
    :returns: A tuple containing cursor and a list of information
        about the dataset.
    :rtype: tuple.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "datasetID",
                    "datasetName",
                    "rightsHolder",
                    "institutionCode",
                    "license",
                    "bibliographicCitation",
                    "datasetComment",
                    "informationWithheld",
                    "dataGeneralizations"
        FROM        nofa."m_dataset"
        WHERE       "datasetID" = %s
        ''',
        (dtst_id,))
    dtst = cur.fetchone()

    return (cur, dtst)

def get_prj_info(con, prj_org, prj_no, prj_name):
    """
    Returns information about a project with the given organization,
    project number and project name.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param prj_org: A project ogranization.
    :type prj_org: str.
    :param prj_no: A project number.
    :type prj_no: str.
    :param prj_name: A project name.
    :type prj_name: str.
    :returns: A tuple containing cursor and a list of information
        about the project.
    :rtype: tuple.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "projectNumber",
                    "projectName",
                    "startYear",
                    "endYear",
                    "projectLeader",
                    "projectMembers",
                    "organisation",
                    "financer",
                    "remarks",
                    "projectID"
        FROM        nofa."m_project"
        WHERE       "organisation" = %s
                    AND
                    "projectNumber" = %s
                    AND
                    "projectName" = %s
        ''',
        (prj_org, prj_no, prj_name,))
    prj = cur.fetchone()

    return (cur, prj)

def get_ref_info(con, ref_id):
    """
    Returns information about a reference with the given reference ID.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param ref_id: A reference ID.
    :type ref_id: str.
    :returns: A tuple containing cursor and a list of information
        about the reference.
    :rtype: tuple.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "referenceID",
                    "author",
                    "referenceType",
                    "year",
                    "titel",
                    "journalName",
                    "volume",
                    "issn",
                    "isbn",
                    "page"
        FROM        nofa."m_reference"
        WHERE       "referenceID" = %s
        ''',
        (ref_id,))
    ref = cur.fetchone()

    return (cur, ref)

def get_fam_dict(con):
    """
    Returns a defaultdict with family as keys and taxons as values.

    :param con: A connection.
    :type con: psycopg2.connection.
    :returns: A defaultdict with families as keys and taxons as values.
    :rtype: collections.defaultdict.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "scientificName",
                    "family"
        FROM        nofa.l_taxon
        WHERE       "scientificName" IS NOT NULL
                    AND
                    "family" IS NOT NULL
        GROUP BY    "scientificName", "family"
        ''')
    spp = cur.fetchall()

    fam_dict = defaultdict(list)
    for s in spp:
        fam_dict[s[1]].append(s[0])

    return fam_dict

def get_dtst_list(con):
    """
    Returns a list with information about datasets that is used to populate
    dataset combo box.

    :param con: A connection.
    :type con: psycopg2.connection.
    :returns: A list with information about datasets.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "datasetID" dsid,
                    "datasetName" dsn
        FROM        nofa."m_dataset"
        ORDER BY    dsid, dsn
        ''')
    dtsts = cur.fetchall()

    dtst_list = [_get_dtst_str(d[0], d[1]) for d in dtsts]

    return dtst_list

def _get_dtst_str(id, name):
    """
    Returns a dataset string "<id> - <name>"

    :param id: A dataset ID.
    :type id: str.
    :param name: A dataset name.
    :type name: str.
    """

    dtst_str = u'{}{}{}'.format(id, DASH_SPLIT_STR, name)

    return dtst_str

def get_prj_list(con):
    """
    Returns a list with information about projects that is used to populate
    project combo box.

    :param con: A connection.
    :type con: psycopg2.connection.
    :returns: A list with information about projects.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "organisation" o,
                    "projectNumber" pno,
                    "projectName" pn,
                    "projectID" pid
        FROM        nofa."m_project"
        ORDER BY    o, pno, pn, pid
        ''')
    prjs = cur.fetchall()

    prj_list = [_get_prj_str(p[0], p[1], p[2], p[3]) for p in prjs]

    return prj_list

def _get_prj_str(org, no, name, id):
    """
    Returns a project string "<organisation> - <number> - <name> - <ID>"

    :param org: A project organization.
    :type org: str.
    :param no: A project number.
    :type no: str.
    :param name: A project name.
    :type name: str.
    :param id: A project ID.
    :type id: int.
    """

    prj_str = u'{}{}{}{}{}{}{}'.format(
        org,
        DASH_SPLIT_STR,
        no,
        DASH_SPLIT_STR,
        name,
        DASH_SPLIT_STR,
        id)

    return prj_str

def get_ref_list(con):
    """
    Returns a list with information about references that is used to populate
    reference combo box.

    :param con: A connection.
    :type con: psycopg2.connection.
    :returns: A list with information about references.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "referenceID",
                    "author",
                    "titel"
        FROM        nofa."m_reference"
        ORDER BY    "author", "titel"
        ''')
    refs = cur.fetchall()

    ref_list = [_get_ref_str(r[1], r[2], r[0]) for r in refs]

    return ref_list

def _get_ref_str(au, ttl, id):
    """
    Returns a reference string "<author>: <title> @<id>".

    :param au: A reference author.
    :type au: str.
    :param ttl: A reference title.
    :type ttl: str.
    :param id: A reference ID.
    :type id: str.
    """

    ref_str = u'{}: {} @{}'.format(au, ttl, id)
    
    return ref_str

def get_txn_list(con):
    """
    Returns a list of taxons that is used to populate taxon combo box.

    :param con: A connection.
    :type con: psycopg2.connection.
    :returns: A list of taxons.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "scientificName" sn
        FROM        nofa."l_taxon"
        WHERE       "taxonRank" IN ('species', 'hybrid', 'genus')
        ORDER BY    sn
        ''')
    txns = cur.fetchall()

    txn_list = [t[0] for t in txns]

    return txn_list
