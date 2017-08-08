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

def ins_event(con, loc_id, event_id, event_list, dtst_id, prj_id, ref_id):
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
    :param ref_id: A reference ID.
    :type ref_id: int.
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
                           "projectID",
                           "referenceID")
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
                           %(projectID)s,
                           %(referenceID)s)
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
         'projectID': prj_id,
         'referenceID': ref_id})

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
    :param occ_id: An occurrence ID.
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

def get_loc_id_nvl_list(con, locs_tpl):
    """
    Returns a list of location IDs and 'Norwegian VatLnr'.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param locs_tpl: A tuple of locations.
    :type locs_tpl: tuple.

    :returns: A list of locations IDs and 'Norwegian VatLnr'.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "locationID" lid,
                    "no_vatn_lnr"
        FROM        nofa.location
        WHERE       "no_vatn_lnr" IN %s
        ORDER BY    lid
        ''',
        (locs_tpl,))
    loc_id_nvl_list = cur.fetchall()

    return loc_id_nvl_list

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

def get_prj_info(con, prj_name, prj_org):
    """
    Returns information about a project with the given project name
    and organization.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param prj_name: A project name.
    :type prj_name: str.
    :param prj_org: A project organization.
    :type prj_org: str.

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
        WHERE       "projectName" = %s
                    AND
                    "organisation" = %s
        ''',
        (prj_name, prj_org,))
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

    dtst_list = [get_dtst_str(d[0], d[1]) for d in dtsts]

    return dtst_list

def get_dtst_str(id, name):
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
        SELECT      "projectName" pn,
                    "organisation" o
        FROM        nofa."m_project"
        ORDER BY    pn, o
        ''')
    prjs = cur.fetchall()

    prj_list = [get_prj_str(p[0], p[1]) for p in prjs]

    return prj_list

def get_prj_str(name, org):
    """
    Returns a project string "<name> - <organisation>".

    :param name: A project name.
    :type name: str.
    :param org: A project organization.
    :type org: str.

    :returns: A project string "<name> - <organisation>".
    :rtype: str.
    """

    prj_str = u'{}{}{}'.format(
        name,
        DASH_SPLIT_STR,
        org)

    return prj_str

def get_prj_name_org_from_str(prj_str):
    """
    Returns a project name and organization from the given project string
    "<name> - <organization>".

    :param prj_str: A project string "<name> - <organization>".
    :type prj_str: str.

    :returns: A project name and organization.
    :rtype: tuple.
    """

    split_prj_str = prj_str.split(DASH_SPLIT_STR)

    name = split_prj_str[0]
    org = split_prj_str[1]

    return (name, org)

def get_prj_id(con, prj_name, prj_org):
    """
    Returns a project ID with the given organization number and name.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param prj_name: A project name.
    :type prj_name: str.
    :param prj_org: A project organization.
    :type prj_org: str.

    :returns: A project ID with the given organization number and name.
    :rtype: int.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "projectID" o
        FROM        nofa."m_project"
        WHERE       "projectName" = %s
                    AND
                    "organisation" = %s

        ''',
        (prj_name, prj_org,))

    prj_id = cur.fetchone()[0]

    return prj_id

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
                    "titel",
                    "year"
        FROM        nofa."m_reference"
        ORDER BY    "author", "titel"
        ''')
    refs = cur.fetchall()

    ref_list = [get_ref_str(r[1], r[2], r[3], r[0]) for r in refs]

    return ref_list

def get_ref_str(au, ttl, yr, id):
    """
    Returns a reference string "<author>: <title> (<year>) @<ID>".

    :param au: A reference author.
    :type au: str.
    :param ttl: A reference title.
    :type ttl: str.
    :param yr: A reference year.
    :type yr: int.
    :param id: A reference ID.
    :type id: str.
    """

    ref_str = u'{}: {} ({}) @{}'.format(au, ttl, yr, id)
    
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

def get_ectp_list(con, txn_name):
    """
    Returns a list of ecotypes that is used to populate ecotype combo box.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param txn_name: A taxon name.
    :type txn_name: str.

    :returns: A list of ecotypes.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      e."vernacularName" vn
        FROM        nofa."l_ecotype" e
                    JOIN
                    nofa."l_taxon" t ON e."taxonID" = t."taxonID"
        WHERE       t."scientificName" = %s
        ORDER BY    vn;
        ''',
        (txn_name,))
    ectps = cur.fetchall()

    ectp_list = [e[0] for e in ectps]

    return ectp_list

def get_oqt_list(con):
    """
    Returns a list of organism quantity types that is used to populate
    organism quantity type combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of organism quantity types.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT    "organismQuantityType" oqt
        FROM      nofa."l_organismQuantityType"
        ORDER BY  oqt
        ''')
    oqts  = cur.fetchall()
    oqt_list = [o[0] for o in oqts]

    return oqt_list

def get_occstat_list(con):
    """
    Returns a list of occurrence statuses that is used to populate
    occurrence status combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of occurrence statuses.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT    "occurrenceStatus" os
        FROM      nofa."l_occurrenceStatus"
        ORDER BY  os
        ''')
    occstats  = cur.fetchall()
    occstat_list = [o[0] for o in occstats]

    return occstat_list

def get_poptrend_list(con):
    """
    Returns a list of population trends that is used to populate
    population trend combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of population trends.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "populationTrend" pt
        FROM        nofa."l_populationTrend"
        WHERE       "populationTrend" is not null
        ORDER BY    pt
        ''')
    poptrends  = cur.fetchall()
    poptrend_list = [p[0] for p in poptrends]

    return poptrend_list

def get_estbms_list(con):
    """
    Returns a list of establishment means that is used to populate
    establishment means combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of establishment means.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "establishmentMeans" em
        FROM        nofa."l_establishmentMeans"
        ORDER BY    em
        ''')
    estbms  = cur.fetchall()
    estbms_list = [e[0] for e in estbms]

    return estbms_list

def get_smpp_list(con):
    """
    Returns a list of sampling protocols that is used to populate
    sampling protocol combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of sampling protocols.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "samplingProtocol" sp
        FROM        nofa."l_samplingProtocol"
        ORDER BY    sp
        ''')
    smpps  = cur.fetchall()
    smpp_list = [s[0] for s in smpps]

    return smpp_list

def get_reliab_list(con):
    """
    Returns a list of reliabilities that is used to populate
    reliability combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of reliabilities.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "reliability" r
        FROM        nofa."l_reliability"
        ORDER BY    r
        ''')
    relias  = cur.fetchall()
    relia_list = [r[0] for r in relias]

    return relia_list

def get_smpsu_list(con):
    """
    Returns a list of sample size units that is used to populate
    sample size unit combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of sample size units.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "sampleSizeUnit" s
        FROM        nofa."l_sampleSizeUnit"
        ORDER BY    s
        ''')
    smpsus  = cur.fetchall()
    smpsu_list = [s[0] for s in smpsus]

    return smpsu_list

def get_spwnc_list(con):
    """
    Returns a list of spawning conditions that is used to populate
    spawning condition combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of spawning conditions.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "spawningCondition" s
        FROM        nofa."l_spawningCondition"
        ORDER BY    s
        ''')
    spwncs  = cur.fetchall()
    spwnc_list = [s[0] for s in spwncs]

    return spwnc_list

def get_spwnl_list(con):
    """
    Returns a list of spawning locations that is used to populate
    spawning location combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of spawning locations.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "spawningLocation" s
        FROM        nofa."l_spawningLocation"
        ORDER BY    s
        ''')
    spwnls  = cur.fetchall()
    spwnl_list = [s[0] for s in spwnls]

    return spwnl_list

def get_inst_list(con):
    """
    Returns a list of institutions that is used to populate
    institution combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of institutions.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      distinct "institutionCode" i
        FROM        nofa."m_dataset"
        ORDER BY    i;
        ''')
    insts = cur.fetchall()

    inst_list = [i[0] for i in insts]

    return inst_list

def get_acs_list(con):
    """
    Returns a list of access rights that is used to populate
    access rights combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of access rights.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      distinct "accessRights" ar
        FROM        nofa."m_dataset"
        ORDER BY    ar;
        ''')
    acs_rghts = cur.fetchall()

    acs_rght_list = [ar[0] for ar in acs_rghts]

    return acs_rght_list

def get_dtst_cnt(con, id):
    """
    Returns a number of datasets with the given ID.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param id: A dataset ID.
    :type id: str.

    :returns: A number of datasets with the given ID.
    :rtype: int.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "datasetID"
        FROM        nofa."m_dataset"
        WHERE       "datasetID" = %s;
        ''',
        (id,))

    dtst_cnt = cur.rowcount

    return dtst_cnt

def ins_dtst(con, name, id, inst, rght, lic, acs, cit, cmnt, info, dtgen):
    """
    Insert an event to the database.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param name: A dataset name.
    :type name: str.
    :param id: A dataset ID.
    :type id: uuid.UUID.
    :param inst: An institution.
    :type inst: str.
    :param rght: A rights holder.
    :type rght: str.
    :param lic: A license.
    :type lic: str.
    :param acs: An access rights.
    :type acs: str.
    :param cit: A bibliographic citation.
    :type cit: str.
    :param cmnt: A comment.
    :type cmnt: str.
    :param info: An information withheld.
    :type info: str.
    :param dtgen: A data generalizations.
    :type dtgen: str.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     nofa.m_dataset (
                            "datasetName",
                            "datasetID",
                            "ownerInstitutionCode",
                            "rightsHolder",
                            "license",
                            "accessRights",
                            "bibliographicCitation",
                            "datasetComment",
                            "informationWithheld",
                            "dataGeneralizations")
        VALUES          (   %(datasetName)s,
                            %(datasetID)s,
                            %(ownerInstitutionCode)s,
                            %(rightsHolder)s,
                            %(license)s,
                            %(accessRights)s,
                            %(bibliographicCitation)s,
                            %(datasetComment)s,
                            %(informationWithheld)s,
                            %(dataGeneralizations)s)
        ''',
        {'datasetName': name,
         'datasetID': id,
         'ownerInstitutionCode': inst,
         'rightsHolder': rght,
         'license': lic,
         'accessRights': acs,
         'bibliographicCitation': cit,
         'datasetComment': cmnt,
         'informationWithheld': info,
         'dataGeneralizations': dtgen})

def ins_prj(con, org, no, name, styr, endyr, ldr, mbr, fncr, rmk):
    """
    Insert an event to the database.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param org: A organization.
    :type org: str.
    :param no: A project number.
    :type no: int.
    :param name: A project name.
    :type name: str.
    :param styr: A start year.
    :type styr: int.
    :param endyr: An end year.
    :type endyr: int.
    :param ldr: A project leader.
    :type ldr: str.
    :param mbr: Project members.
    :type mbr: str.
    :param fncr: A financer.
    :type fncr: str.
    :param rmk: Project remarks.
    :type rmk: str.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     nofa.m_project (
                            "organisation",
                            "projectNumber",
                            "projectName",
                            "startYear",
                            "endYear",
                            "projectLeader",
                            "projectMembers",
                            "financer",
                            "remarks")
        VALUES          (   %(organisation)s,
                            %(projectNumber)s,
                            %(projectName)s,
                            %(startYear)s,
                            %(endYear)s,
                            %(projectLeader)s,
                            %(projectMembers)s,
                            %(financer)s,
                            %(remarks)s)
        ''',
        {'organisation': org,
         'projectNumber': no,
         'projectName': name,
         'startYear': styr,
         'endYear': endyr,
         'projectLeader': ldr,
         'projectMembers': mbr,
         'financer': fncr,
         'remarks': rmk})

def get_reftp_list(con):
    """
    Returns a list of reference types that is used to populate
    reference type combo box.

    :param con: A connection.
    :type con: psycopg2.connection.

    :returns: A list of reference types.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "referenceType" rt
        FROM        nofa."l_referenceType"
        ORDER BY    rt
        ''')
    reftps = cur.fetchall()

    reftp_list = [r[0] for r in reftps]

    return reftp_list

def ins_ref(con, ttl, au, yr, isbn, issn, tp, jrn, vol, pg):
    """
    Insert an event to the database.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param ttl: A reference title.
    :type ttl: str.
    :param au: A reference author.
    :type au: str.
    :param yr: A reference year.
    :type yr: int.
    :param isbn: A reference ISBN.
    :type isbn: str.
    :param issn: A reference ISSN.
    :type issn: str.
    :param tp: A reference type
    :type tp: str.
    :param jrn: A journal.
    :type jrn: str.
    :param vol: A volume.
    :type vol: str.
    :param pg: A page(s).
    :type pg: str.

    :returns: A reference ID.
    :rtype: int.
    """

    cur = _get_db_cur(con)
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
        RETURNING       "referenceID"
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

    return id

def get_pt_str(utme, utmn):
    """
    Returns a point string with the given UTM easting and northing.

    :param utme: UTM easting.
    :type utme: float.
    :param utmn: UTM northing.
    :type utmn: float.

    :returns: A point string.
    :rtype: str.
    """

    pt_str = 'POINT({} {})'.format(utme, utmn)

    return pt_str

def get_utm33_geom(con, geom_str, srid):
    """
    Returns a geometry in UTM33 (EPSG: 25833).

    :param con: A connection.
    :type con: psycopg2.connection.
    :param geom_str: A geometry string.
    :type geom_str: str.
    :param srid: SRID.
    :type srid: int.

    :returns: A geometry in UTM33 (EPSG: 25833).
    :rtype: str.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      ST_Transform(
                        ST_GeomFromText(%s, %s),
                        25833)
        ''',
        (geom_str, srid,))

    utm33_geom = cur.fetchone()[0]

    return utm33_geom

def get_nrst_loc_id(con, utm33_geom, max_dist):
    """
    Returns an ID of the nearest location.
    First it searches for a lake within the given distance and then it joins
    it to location table to get ID of the location.
    When there is no lake with the given distance, then it returns None.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param utm33_geom: A geometry.
    :type utm33_geom: str.
    :param max_dist: A maximum distance in meters.
    :type max_dist: int.

    :returns: A location ID. None where there is no lake within
        the given distance.
    :rtype: uuid.UUID.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        WITH nl AS (
            SELECT      l.id AS id,
                        l.geom AS geom,
                        ST_Distance(l.geom, %(utm33_geom)s) AS dist
            FROM        nofa."lake" l
            WHERE       ST_DWithin(geom, %(utm33_geom)s, %(max_dist)s)
            ORDER BY    geom <-> %(utm33_geom)s
            LIMIT       1)
        SELECT      l."locationID"
        FROM        nofa."location" l
                    JOIN
                    nl ON nl.id = l."waterBodyID"
        ''',
        {'utm33_geom': utm33_geom,
         'max_dist': max_dist})

    try:
        loc_id = cur.fetchone()[0]
    except TypeError:
        loc_id = None

    return loc_id

def ins_new_loc(con, loc_id, utm33_geom, loc_name):
    """
    Insert a new location and returns its location ID.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param loc_id: A location ID.
    :type loc_id:uuid.UUID.
    :param utm33_geom: A geometry in UTM33 (EPSG: 25833).
    :type utm33_geom: str.
    :param loc_name: A location name.
    :type loc_name: str.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     nofa.location (
                            "locationID",
                            "locationType",
                            "geom",
                            "waterBody")
        VALUES          (   %(locationID)s,
                            %(locationType)s,
                            %(geom)s,
                            %(waterBody)s)
        ''',
        {'locationID': loc_id,
         'locationType': 'samplingPoint lake',
         'geom': utm33_geom,
         'waterBody': loc_name})

def get_mpt_str(utme, utmn):
    """
    Returns a multi point string with the given UTM easting and northing.

    :param utme: UTM easting.
    :type utme: float.
    :param utmn: UTM northing.
    :type utmn: float.

    :returns: A multi point string.
    :rtype: str.
    """

    mpt_str = 'MULTIPOINT({} {})'.format(utme, utmn)

    return mpt_str

def get_loc_by_wb_name(con, wb_name):
    """
    Returns location IDs with the given water body name.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param wb_name: A water body name.
    :type wb_name: str.

    :returns: A list of location IDs.
    :rtype: list.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "locationID"
        FROM        nofa.location loc
        WHERE       "waterBody" LIKE %s
        ''',
        ('%' + wb_name + '%',))
    locids = cur.fetchall()

    locid_list = [l[0] for l in locids]

    return locid_list

def ins_occ_log(con, occ_id, event_id, dtst_id, prj_id, ref_id, loc_id, usr):
    """
    Insert an occurrence log to the database.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param occ_id: An occurrence ID.
    :type occ_id: uuid.UUID.
    :param event_id: An event ID.
    :type event_id: uuid.UUID.
    :param dtst_id: A dataset ID.
    :type dtst_id: str.
    :param prj_id: A project ID.
    :type prj_id: str.
    :param ref_id: A reference ID.
    :type ref_id: int.
    :param loc_id: A location ID.
    :type loc_id: uuid.UUID.
    :param usr: An username.
    :type usr: str.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     plugin.occurrence_log (
                            occurrence_id,
                            event_id,
                            dataset_id,
                            project_id,
                            reference_id,
                            location_id,
                            username)
        VALUES          (   %(occurrence_id)s,
                            %(event_id)s,
                            %(dataset_id)s,
                            %(project_id)s,
                            %(reference_id)s,
                            %(location_id)s,
                            %(username)s)
        ''',
        {'occurrence_id': occ_id,
         'event_id': event_id,
         'dataset_id': dtst_id,
         'project_id': prj_id,
         'reference_id': ref_id,
         'location_id': loc_id,
         'username': usr})

def ins_dtst_log(con, id, usr):
    """
    Insert a dataset log to the database.

    :param con: A connection.
    :type con: psycopg2.connection.
    :param id: A dataset ID.
    :type id: str.
    :param usr: An username.
    :type usr: str.
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     plugin.dataset_log(
                            dataset_id,
                            username)
        VALUES          (   %(dataset_id)s,
                            %(username)s)
        ''',
        {'dataset_id': id,
         'username': usr})
