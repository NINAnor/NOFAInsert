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

from collections import defaultdict
import datetime
import psycopg2
import psycopg2.extras


def get_con(con_info):
    """
    Returns a connection.

    :returns: A connection.
    :rtype: psycopg2.connection
    """

    con = psycopg2.connect(**con_info)
    con.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

    return con


def _get_db_cur(con):
    """
    Returns a database cursor.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A database cursor.
    :rtype: psycopg2.cursor
    """

    return con.cursor()


def chck_nofa_tbls(con):
    """
    Checks if the database is NOFA.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: True when database is NOFA, False otherwise.
    :rtype: bool
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
    :type con: psycopg2.connection
    :param loc_id: A location ID.
    :type loc_id: uuid.UUID
    :param event_id: An event ID.
    :type event_id: uuid.UUID
    :param event_list: A list of data from event input widgets.
    :type event_list: list
    :param dtst_id: A dataset ID.
    :type dtst_id: str
    :param prj_id: A project ID.
    :type prj_id: str
    :param ref_id: A reference ID.
    :type ref_id: int
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO    nofa.event (
                           "locationID",
                           "eventID",
                           "samplingProtocol",
                           "sampleSizeUnit",
                           "sampleSizeValue",
                           "samplingEffort",
                           "dateStart",
                           "dateEnd",
                           "fieldNumber",
                           "recordedBy",
                           "eventRemarks",
                           "reliability",
                           "datasetID",
                           "projectID",
                           "referenceID")
        VALUES         (   %(locationID)s,
                           %(eventID)s,
                           %(samplingProtocol)s,
                           %(sampleSizeUnit)s,
                           %(sampleSizeValue)s,
                           %(samplingEffort)s,
                           %(dateStart)s,
                           %(dateEnd)s,
                           %(fieldNumber)s,
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
         'sampleSizeUnit': event_list[1],
         'sampleSizeValue': event_list[2],
         'samplingEffort': event_list[3],
         'dateStart': event_list[4],
         'dateEnd': event_list[5],
         'fieldNumber': event_list[6],
         'recordedBy': event_list[7],
         'eventRemarks': event_list[8],
         'reliability': event_list[9],
         'datasetID': dtst_id,
         'projectID': prj_id,
         'referenceID': ref_id})


def get_txn_id(con, txn):
    """
    Returns a taxon ID based on the given scientific name.

    :param con: A connection.
    :type con: psycopg2.connection
    :param txn: A taxon scientific name.
    :type txn: str

    :returns: A taxon ID.
    :rtype: int
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
    :type con: psycopg2.connection
    :param txn: An ecotype vernacular name.
    :type txn: str

    :returns: An ecotype ID, None when there is no ecotype.
    :rtype: int
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
    :type con: psycopg2.connection
    :param occ_id: An occurrence ID.
    :type occ_id: uuid.UUID
    :param txn_id: A taxon ID.
    :type txn_id: int
    :param ectp_id: An ecotype ID, None when there is no ecotype.
    :type ectp_id: int
    :param occ_row_list: A list of data in the row in the occurrence table.
    :type occ_row_list: list
    :param event_id: An event ID.
    :type event_id: uuid.UUID

    :returns: An ecotype ID, None when there is no ecotype.
    :rtype: int
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
                           "recordNumber",
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
                           %(recordNumber)s,
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
         'organismQuantity': occ_row_list[3],
         'occurrenceStatus': occ_row_list[4],
         'populationTrend': occ_row_list[5],
         'recordNumber': occ_row_list[6],
         'occurrenceRemarks': occ_row_list[7],
         'establishmentMeans': occ_row_list[8],
         'establishmentRemarks': occ_row_list[9],
         'spawningCondition': occ_row_list[10],
         'spawningLocation': occ_row_list[11],
         'verifiedBy': occ_row_list[12],
         'verifiedDate': occ_row_list[13],
         'modified': datetime.datetime.now(),
         'eventID': event_id})


def ins_txncvg(con, txn_id, event_id):
    """
    Insert a taxon coverage into the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param txn_id: A taxon ID.
    :type txn_id: int
    :param event_id: An event ID.
    :type event_id: uuid.UUID
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     nofa."samplingTaxaRange"(
                            "taxonID",
                            "eventID")
        VALUES         (   %(taxonID)s,
                           %(eventID)s)
        ''',
        {'taxonID': txn_id,
         'eventID': event_id})


def chck_locid(con, locid):
    """
    Checks if a location ID is in the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param locid: A location ID.
    :type locid: str

    :returns: True when location ID was found, False otherwise.
    :rtype: bool
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "locationID"
        FROM        nofa.location
        WHERE       "locationID" = %s
        ''',
        (locid,))

    locid = cur.fetchall()

    if cur.rowcount != 0:
        resp = True
    else:
        resp = False

    return resp


def get_locid_from_nvl(con, nvl):
    """
    Returns a location ID based on the given `Norwegian VatLnr`.

    :param con: A connection.
    :type con: psycopg2.connection
    :param nvl: A `Norwegian VatLnr`.
    :type nvl: int

    :returns: A location ID.
    :rtype: str
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "locationID"
        FROM        nofa.location
        WHERE       "no_vatn_lnr" = %s
        ''',
        (nvl,))

    locid = cur.fetchone()[0]

    return locid


def get_dtst_info(con, dtst_id):
    """
    Returns information about a dataset with the given ID.

    :param con: A connection.
    :type con: psycopg2.connection
    :param dtst_id: A dataset ID.
    :type dtst_id: str

    :returns:
     | A tuple containing:
     |    - *list* -- a list of dataset items
     |    - *list* -- a list of dataset headers
    :rtype: tuple
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "datasetName",
                    "datasetID",
                    "ownerInstitutionCode",
                    "rightsHolder",
                    "license",
                    "accessRights",
                    "bibliographicCitation",
                    "datasetComment",
                    "informationWithheld",
                    "dataGeneralizations"
        FROM        nofa."m_dataset"
        WHERE       "datasetID" = %s
        ''',
        (dtst_id,))

    dtst_items = cur.fetchone()

    dtst_hdrs = [h[0] for h in cur.description]

    return (dtst_items, dtst_hdrs)


def get_prj_info(con, prj_id):
    """
    Returns information about a project with the given project name
    and organization.

    :param con: A connection.
    :type con: psycopg2.connection
    :param prj_id: A project ID.
    :type prj_id: int

    :returns:
     | A tuple containing:
     |    - *list* -- a list of project items
     |    - *list* -- a list of project headers
    :rtype: tuple
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "organisation",
                    "projectNumber",
                    "projectName",
                    "startYear",
                    "endYear",
                    "projectLeader",
                    "projectMembers",
                    "financer",
                    "remarks",
                    "projectID"
        FROM        nofa."m_project"
        WHERE       "projectID" = %s
        ''',
        (prj_id,))

    prj_items = cur.fetchone()

    prj_hdrs = [h[0] for h in cur.description]

    return (prj_items, prj_hdrs)


def get_ref_info(con, ref_id):
    """
    Returns information about a reference with the given reference ID.

    :param con: A connection.
    :type con: psycopg2.connection
    :param ref_id: A reference ID.
    :type ref_id: str

    :returns:
     | A tuple containing:
     |    - *list* -- a list of reference items
     |    - *list* -- a list of reference headers
    :rtype: tuple
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

    ref_items = cur.fetchone()

    ref_hdrs = [h[0] for h in cur.description]

    return (ref_items, ref_hdrs)


def get_fam_dict(con):
    """
    Returns a defaultdict with family as keys and taxons as values.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns:
     | A defaultdict:
     |    - key - *str* -- family
     |    - value - *str* -- taxons
    :rtype: collections.defaultdict
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


def get_cntry_code_list(con):
    """
    Returns a list of country codes that is used to populate
    country code combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of country codes.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      DISTINCT "countryCode" cc
        FROM        nofa."location"
        ORDER BY    cc
        ''')
    cntry_codes = cur.fetchall()

    cntry_code_list = [c[0] for c in cntry_codes]

    return cntry_code_list


def get_cnty_list(con, cntry_code):
    """
    Returns a list of counties that is used to populate
    county combo box.

    :param con: A connection.
    :type con: psycopg2.connection
    :param cntry_code: A country code.
    :type cntry_code: str

    :returns: A list of counties.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      DISTINCT "county" c
        FROM        nofa."location"
        WHERE       %(countryCode)s IS NULL OR "countryCode" = %(countryCode)s
        ORDER BY    c
        ''',
        {'countryCode': cntry_code})

    cntys = cur.fetchall()

    cnty_list = [c[0] for c in cntys]

    return cnty_list


def get_muni_list(con, cntry_code, cnty):
    """
    Returns a list of municipalities that is used to populate
    municipality combo box.

    :param con: A connection.
    :type con: psycopg2.connection
    :param cntry_code: A country code.
    :type cntry_code: str
    :param cnty: A county.
    :type cnty: str

    :returns: A list of municipalities.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      DISTINCT "municipality" m
        FROM        nofa."location"
        WHERE       (   %(countryCode)s IS NULL
                        OR
                        "countryCode" = %(countryCode)s)
                    AND
                    (%(county)s IS NULL OR "county" = %(county)s)
        ORDER BY    m
        ''',
        {'countryCode': cntry_code,
         'county': cnty})

    munis = cur.fetchall()

    muni_list = [m[0] for m in munis]

    return muni_list


def get_dtst_list(con):
    """
    Returns a list with information about datasets that is used to populate
    dataset combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list with information about datasets.
    :rtype: list
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


def get_dtst_mtdt_str(dtst_str):
    """
    Returns a dataset metadata string `<name>`.

    :param dtst_str: A dataset string `<ID> - <name>`.
    :type dtst_str: str

    :returns: A dataset metadata string `<name>`.
    :rtype: str
    """

    name, org = split_dtst_str(dtst_str)

    dtst_mtdt_str = u'{}'.format(name)

    return dtst_mtdt_str


def get_dtst_str(id, name):
    """
    Returns a dataset string `<ID> - <name>`.

    :param id: A dataset ID.
    :type id: str
    :param name: A dataset name.
    :type name: str

    :returns: A dataset string `<ID> - <name>`.
    :rtype: str
    """

    dtst_str = u'{} - {}'.format(id, name)

    return dtst_str


def split_dtst_str(dtst_str):
    """
    Splits a dataset string `<ID> - <name>` and returns
    its information.

    :param dtst_str: A dataset string `<ID> - <name>`.
    :type dtst_str: str

    :returns:
     | A tuple containing:
     |    - *str* -- dataset ID
     |    - *str* -- name
    :rtype: tuple
    """

    split_dtst_str = dtst_str.split(u' - ')

    id = split_dtst_str[0]
    name = split_dtst_str[1]

    return (id, name)


def get_prj_list(con):
    """
    Returns a list with information about projects that is used to populate
    project combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list with information about projects.
    :rtype: list
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


def get_prj_mtdt_str(prj_str):
    """
    Returns a projects metadata string `<name> - <organisation>`.

    :param prj_str: A project string `<name> - <organization>`.
    :type prj_str: str

    :returns: A projects metadata string `<name> - <organisation>`.
    :rtype: str
    """

    name, org = split_prj_str(prj_str)

    prj_mtdt_str = u'{} - {}'.format(name, org)

    return prj_mtdt_str


def get_prj_str(name, org):
    """
    Returns a project string `<name> - <organisation>`.

    :param name: A project name.
    :type name: str
    :param org: A project organization.
    :type org: str

    :returns: A project string `<name> - <organisation>`.
    :rtype: str
    """

    prj_str = u'{} - {}'.format(name, org)

    return prj_str


def split_prj_str(prj_str):
    """
    Splits a project string `<name> - <organization>` and returns
    its information.

    :param prj_str: A project string `<name> - <organization>`.
    :type prj_str: str

    :returns:
     | A tuple containing:
     |    - *str* -- project name
     |    - *str* -- organization
    :rtype: tuple
    """

    split_prj_str = prj_str.split(u' - ')

    name = split_prj_str[0]
    org = split_prj_str[1]

    return (name, org)


def get_prj_id(con, prj_name, prj_org):
    """
    Returns a project ID with the given organization number and name.

    :param con: A connection.
    :type con: psycopg2.connection
    :param prj_name: A project name.
    :type prj_name: str
    :param prj_org: A project organization.
    :type prj_org: str

    :returns: A project ID with the given organization number and name.
    :rtype: int
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
    :type con: psycopg2.connection

    :returns: A list with information about references.
    :rtype: list
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


def get_ref_mtdt_str(ref_str):
    """
    Returns a reference metadata string `<author>: <title> (<year>)`.

    :param ref_str: A reference string `<author>: <title> (<year>) @<ID>`.
    :type ref_str: str

    :returns: A reference metadata string `<author>: <title> (<year>)`.
    :rtype: str
    """

    au, ttl, yr, id = split_ref_str(ref_str)

    ref_mtdt_str = u'{}: {} ({})'.format(au, ttl, yr)

    return ref_mtdt_str


def get_ref_str(au, ttl, yr, id):
    """
    Returns a reference string `<author>: <title> (<year>) @<ID>`.

    :param au: A reference author.
    :type au: str
    :param ttl: A reference title.
    :type ttl: str
    :param yr: A reference year.
    :type yr: int
    :param id: A reference ID.
    :type id: str

    :returns: A reference string `<author>: <title> (<year>) @<ID>`.
    :rtype: str
    """

    ref_str = u'{}: {} ({}) @{}'.format(au, ttl, yr, id)

    return ref_str


def split_ref_str(ref_str):
    """
    Splits a reference string `<author>: <title> (<year>) @<ID>` and returns
    its information.

    :param ref_str: A reference string `<author>: <title> (<year>) @<ID>`.
    :type ref_str: str

    :returns:
     | A tuple containing:
     |    - *str* -- author
     |    - *str* -- year
     |    - *str* -- title
     |    - *int* -- ID
    :rtype: tuple
    """

    au = ref_str.split(u': ')[0]
    ttl = ref_str.split(u': ')[1].split(u' (')[0]
    yr = ref_str.split(u' (')[1].split(u') ')[0]
    id = int(ref_str.split(u'@')[1])

    return (au, ttl, yr, id)


def get_txn_list(con):
    """
    Returns a list of taxons that is used to populate taxon combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of taxons.
    :rtype: list
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
    :type con: psycopg2.connection
    :param txn_name: A taxon name.
    :type txn_name: str

    :returns: A list of ecotypes.
    :rtype: list
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
    :type con: psycopg2.connection

    :returns: A list of organism quantity types.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT    "organismQuantityType" oqt
        FROM      nofa."l_organismQuantityType"
        ORDER BY  oqt
        ''')
    oqts = cur.fetchall()
    oqt_list = [o[0] for o in oqts]

    return oqt_list


def get_occstat_list(con):
    """
    Returns a list of occurrence statuses that is used to populate
    occurrence status combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of occurrence statuses.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT    "occurrenceStatus" os
        FROM      nofa."l_occurrenceStatus"
        ORDER BY  os
        ''')
    occstats = cur.fetchall()
    occstat_list = [o[0] for o in occstats]

    return occstat_list


def get_poptrend_list(con):
    """
    Returns a list of population trends that is used to populate
    population trend combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of population trends.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "populationTrend" pt
        FROM        nofa."l_populationTrend"
        WHERE       "populationTrend" is not null
        ORDER BY    pt
        ''')
    poptrends = cur.fetchall()
    poptrend_list = [p[0] for p in poptrends]

    return poptrend_list


def get_estbms_list(con):
    """
    Returns a list of establishment means that is used to populate
    establishment means combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of establishment means.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "establishmentMeans" em
        FROM        nofa."l_establishmentMeans"
        ORDER BY    em
        ''')
    estbms = cur.fetchall()
    estbms_list = [e[0] for e in estbms]

    return estbms_list


def get_smpp_list(con):
    """
    Returns a list of sampling protocols that is used to populate
    sampling protocol combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of sampling protocols.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "samplingProtocol" sp
        FROM        nofa."l_samplingProtocol"
        ORDER BY    sp
        ''')
    smpps = cur.fetchall()
    smpp_list = [s[0] for s in smpps]

    return smpp_list


def get_reliab_list(con):
    """
    Returns a list of reliabilities that is used to populate
    reliability combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of reliabilities.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "reliability" r
        FROM        nofa."l_reliability"
        ORDER BY    r
        ''')
    relias = cur.fetchall()
    relia_list = [r[0] for r in relias]

    return relia_list


def get_smpsu_list(con):
    """
    Returns a list of sample size units that is used to populate
    sample size unit combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of sample size units.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "sampleSizeUnit" s
        FROM        nofa."l_sampleSizeUnit"
        ORDER BY    s
        ''')
    smpsus = cur.fetchall()
    smpsu_list = [s[0] for s in smpsus]

    return smpsu_list


def get_spwnc_list(con):
    """
    Returns a list of spawning conditions that is used to populate
    spawning condition combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of spawning conditions.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "spawningCondition" s
        FROM        nofa."l_spawningCondition"
        ORDER BY    s
        ''')
    spwncs = cur.fetchall()
    spwnc_list = [s[0] for s in spwncs]

    return spwnc_list


def get_spwnl_list(con):
    """
    Returns a list of spawning locations that is used to populate
    spawning location combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of spawning locations.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "spawningLocation" s
        FROM        nofa."l_spawningLocation"
        ORDER BY    s
        ''')
    spwnls = cur.fetchall()
    spwnl_list = [s[0] for s in spwnls]

    return spwnl_list


def get_inst_list(con):
    """
    Returns a list of institutions that is used to populate
    institution combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of institutions.
    :rtype: list
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
    :type con: psycopg2.connection

    :returns: A list of access rights.
    :rtype: list
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
    :type con: psycopg2.connection
    :param id: A dataset ID.
    :type id: str

    :returns: A number of datasets with the given ID.
    :rtype: int
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


def ins_dtst(con, dtst_list):
    """
    Insert an event to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param dtst_list: A dataset list
    :type dtst_list: list
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
        {'datasetName': dtst_list[0],
         'datasetID': dtst_list[1],
         'ownerInstitutionCode': dtst_list[2],
         'rightsHolder': dtst_list[3],
         'license': dtst_list[4],
         'accessRights': dtst_list[5],
         'bibliographicCitation': dtst_list[6],
         'datasetComment': dtst_list[7],
         'informationWithheld': dtst_list[8],
         'dataGeneralizations': dtst_list[9]})


def ins_prj(con, prj_list):
    """
    Insert an event to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param prj_list: A project list
    :type prj_list: list

    :returns: A project ID.
    :rtype: int
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
        RETURNING       "projectID"
        ''',
        {'organisation': prj_list[0],
         'projectNumber': prj_list[1],
         'projectName': prj_list[2],
         'startYear': prj_list[3],
         'endYear': prj_list[4],
         'projectLeader': prj_list[5],
         'projectMembers': prj_list[6],
         'financer': prj_list[7],
         'remarks': prj_list[8]})

    id = cur.fetchone()[0]

    return id


def get_reftp_list(con):
    """
    Returns a list of reference types that is used to populate
    reference type combo box.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of reference types.
    :rtype: list
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


def ins_ref(con, ref_list):
    """
    Insert an event to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param ref_list: A reference list
    :type ref_list: list

    :returns: A reference ID.
    :rtype: int
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
        {'title': ref_list[0],
         'author': ref_list[1],
         'year': ref_list[2],
         'isbn': ref_list[3],
         'issn': ref_list[4],
         'referenceType': ref_list[5],
         'journalName': ref_list[6],
         'volume': ref_list[7],
         'page': ref_list[8]})

    id = cur.fetchone()[0]

    return id


def get_pt_str(x, y):
    """
    Returns a point string with the given coordinates.

    :param x: X coordinate.
    :type x: float
    :param y: Y coordinate.
    :type y: float

    :returns: A point string.
    :rtype: str
    """

    pt_str = 'POINT({} {})'.format(x, y)

    return pt_str


def get_utm33_geom(con, geom_str, srid):
    """
    Returns a geometry in UTM33 (EPSG: 25833).

    :param con: A connection.
    :type con: psycopg2.connection
    :param geom_str: A geometry string.
    :type geom_str: str
    :param srid: SRID.
    :type srid: int

    :returns: A geometry in UTM33 (EPSG: 25833).
    :rtype: str
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


def get_nrst_locid(con, utm33_geom):
    """
    Returns an ID of the nearest location.

    :param con: A connection.
    :type con: psycopg2.connection
    :param utm33_geom: A geometry in UTM33 (EPSG: 25833).
    :type utm33_geom: str

    :returns: A location ID. None where there is no lake within
        the given distance.
    :rtype: uuid.UUID
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "locationID"
        FROM        nofa."location" l
        ORDER BY    ST_Distance(%s, l.geom)
        LIMIT       1
        ''',
        (utm33_geom,))

    locid = cur.fetchone()[0]

    return locid


def ins_new_loc(con, locid, utm33_geom, verb_loc):
    """
    Insert a new location and returns its location ID.

    :param con: A connection.
    :type con: psycopg2.connection
    :param locid: A location ID.
    :type locid: uuid.UUID
    :param utm33_geom: A geometry in UTM33 (EPSG: 25833).
    :type utm33_geom: str
    :param verb_loc: A verbatimLocality.
    :type verb_loc: str
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     nofa.location (
                            "locationID",
                            "locationType",
                            "geom",
                            "verbatimLocality")
        VALUES          (   %(locationID)s,
                            %(locationType)s,
                            %(geom)s,
                            %(verbatimLocality)s)
        ''',
        {'locationID': locid,
         'locationType': 'samplingPoint lake',
         'geom': utm33_geom,
         'verbatimLocality': verb_loc})


def get_mpt_str(x, y):
    """
    Returns a multi point string with the given coordinates.

    :param x: X coordinate.
    :type x: float
    :param y: Y coordinate.
    :type y: float

    :returns: A multi point string.
    :rtype: str
    """

    mpt_str = 'MULTIPOINT({} {})'.format(x, y)

    return mpt_str


def get_loc_by_fltrs(con, wb, cntry_code, cnty, muni):
    """
    Returns location IDs with the given filters.

    :param con: A connection.
    :type con: psycopg2.connection
    :param wb: A water body.
    :type wb: str
    :param cntry_code: A country code.
    :type cntry_code: str
    :param cnty: A county.
    :type cnty: str
    :param muni: A municipality.
    :type muni: str

    :returns: A list of location IDs.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      "locationID"
        FROM        nofa.location loc
        WHERE       (%(waterBody)s IS NULL OR "waterBody" LIKE %(waterBody)s)
                    AND
                    (   %(countryCode)s IS NULL
                        OR
                        "countryCode" = %(countryCode)s)
                    AND
                    (%(county)s IS NULL OR "county" = %(county)s)
                    AND
                    (   %(municipality)s IS NULL
                        OR
                        "municipality" = %(municipality)s)
        ''',
        {'waterBody': '%' + wb + '%' if wb else wb,
         'countryCode': cntry_code,
         'county': cnty,
         'municipality': muni})

    locids = cur.fetchall()

    locid_list = [l[0] for l in locids]

    return locid_list


def ins_occ_log(con, occ_id, event_id, dtst_id, prj_id, ref_id, loc_id, usr):
    """
    Insert an occurrence log to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param occ_id: An occurrence ID.
    :type occ_id: uuid.UUID
    :param event_id: An event ID.
    :type event_id: uuid.UUID
    :param dtst_id: A dataset ID.
    :type dtst_id: str
    :param prj_id: A project ID.
    :type prj_id: str
    :param ref_id: A reference ID.
    :type ref_id: int
    :param loc_id: A location ID.
    :type loc_id: uuid.UUID
    :param usr: An username.
    :type usr: str
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


def ins_loc_log(con, id, name, usr):
    """
    Insert a location log to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param id: A location ID.
    :type id: str
    :param name: A location name.
    :type name: str
    :param usr: An username.
    :type usr: str
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     plugin.location_log(
                            location_id,
                            location_name,
                            username)
        VALUES          (   %(location_id)s,
                            %(location_name)s,
                            %(username)s)
        ''',
        {'location_id': id,
         'location_name': name,
         'username': usr})


def ins_event_log(con, loc_id, event_id, dtst_id, prj_id, ref_id, usr):
    """
    Insert an event log to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param loc_id: A location ID.
    :type loc_id: str
    :param event_id: An event ID.
    :type event_id: uuid.UUID
    :param dtst_id: A dataset ID.
    :type dtst_id: str
    :param prj_id: A project ID.
    :type prj_id: str
    :param ref_id: A reference ID.
    :type ref_id: int
    :param usr: An username.
    :type usr: str
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     plugin.event_log(
                            event_id,
                            location_id,
                            dataset_id,
                            project_id,
                            reference_id,
                            username)
        VALUES          (   %(event_id)s,
                            %(location_id)s,
                            %(dataset_id)s,
                            %(project_id)s,
                            %(reference_id)s,
                            %(username)s)
        ''',
        {'event_id': event_id,
         'location_id': loc_id,
         'dataset_id': dtst_id,
         'project_id': prj_id,
         'reference_id': ref_id,
         'username': usr})


def ins_dtst_log(con, id, usr):
    """
    Insert a dataset log to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param id: A dataset ID.
    :type id: str
    :param usr: An username.
    :type usr: str
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


def ins_prj_log(con, id, usr):
    """
    Insert a project log to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param id: A project ID.
    :type id: str
    :param usr: An username.
    :type usr: str
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        INSERT INTO     plugin.project_log(
                            project_id,
                            username)
        VALUES          (   %(project_id)s,
                            %(username)s)
        ''',
        {'project_id': id,
         'username': usr})


def ins_ref_log(con, id, usr):
    """
    Insert a reference log to the database.

    :param con: A connection.
    :type con: psycopg2.connection
    :param id: A reference ID.
    :type id: str
    :param usr: An username.
    :type usr: str
    """

    cur = _get_db_cur(con)
    insert_location_log = cur.execute(
        '''
        INSERT INTO     plugin.reference_log(
                            reference_id,
                            username)
        VALUES          (   %(reference_id)s,
                            %(username)s)
        ''',
        {'reference_id': id,
         'username': usr})


def get_hist_occ_list(
        con, usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end):
    """
    Returns a list of history occurrences that is used to populate
    occurrence history table.
    Also returns a list of history occurrences headers.
    Data are filtered based on input values.

    :param con: A connection.
    :type con: psycopg2.connection
    :param usr: An username.
    :type usr: str
    :param ins_dt_strt: Insert date start.
    :type ins_dt_strt: datetime.date
    :param ins_dt_end: Insert date end.
    :type ins_dt_end: datetime.date
    :param upd_dt_strt: Update date start.
    :type upd_dt_strt: datetime.date
    :param upd_dt_end: Update date end.
    :type upd_dt_end: datetime.date

    :returns:
     | A tuple containing:
     |    - *list* -- a list of history occurrences
     |     - *list* -- a list of history occurrences headers
    :rtype: tuple
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      occurrence_id,
                    event_id,
                    dataset_id,
                    project_id,
                    reference_id,
                    location_id,
                    username,
                    insert_timestamp,
                    update_timestamp
        FROM        plugin.occurrence_log
        WHERE       (%(username)s IS NULL OR "username" LIKE %(username)s)
                    AND
                    date(insert_timestamp)
                        BETWEEN %(ins_dt_strt)s AND %(ins_dt_end)s
                    AND
                    date(update_timestamp)
                        BETWEEN %(upd_dt_strt)s AND %(upd_dt_end)s
        ''',
        {'username': usr,
         'ins_dt_strt': ins_dt_strt,
         'ins_dt_end': ins_dt_end,
         'upd_dt_strt': upd_dt_strt,
         'upd_dt_end': upd_dt_end})

    hist_occ_list = cur.fetchall()

    hist_occ_hdrs = [d[0] for d in cur.description]

    return (hist_occ_list, hist_occ_hdrs)


def get_hist_loc_list(
        con, usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end):
    """
    Returns a list of history locations that is used to populate
    location history table.
    Also returns a list of history locations headers.
    Data are filtered based on input values.

    :param con: A connection.
    :type con: psycopg2.connection
    :param usr: An username.
    :type usr: str
    :param ins_dt_strt: Insert date start.
    :type ins_dt_strt: datetime.date
    :param ins_dt_end: Insert date end.
    :type ins_dt_end: datetime.date
    :param upd_dt_strt: Update date start.
    :type upd_dt_strt: datetime.date
    :param upd_dt_end: Update date end.
    :type upd_dt_end: datetime.date

    :returns:
     | A tuple containing:
     |    - *list* -- a list of history locations
     |    - *list* -- a list of history locations headers
    :rtype: tuple
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      location_id,
                    location_name,
                    username,
                    insert_timestamp,
                    update_timestamp
        FROM        plugin.location_log
        WHERE       (%(username)s IS NULL OR "username" LIKE %(username)s)
                    AND
                    date(insert_timestamp)
                        BETWEEN %(ins_dt_strt)s AND %(ins_dt_end)s
                    AND
                    date(update_timestamp)
                        BETWEEN %(upd_dt_strt)s AND %(upd_dt_end)s
        ''',
        {'username': usr,
         'ins_dt_strt': ins_dt_strt,
         'ins_dt_end': ins_dt_end,
         'upd_dt_strt': upd_dt_strt,
         'upd_dt_end': upd_dt_end})

    hist_loc_list = cur.fetchall()

    hist_loc_hdrs = [d[0] for d in cur.description]

    return (hist_loc_list, hist_loc_hdrs)


def get_hist_event_list(
        con, usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end):
    """
    Returns a list of history events that is used to populate
    event history table.
    Also returns a list of history events headers.
    Data are filtered based on input values.

    :param con: A connection.
    :type con: psycopg2.connection
    :param usr: An username.
    :type usr: str
    :param ins_dt_strt: Insert date start.
    :type ins_dt_strt: datetime.date
    :param ins_dt_end: Insert date end.
    :type ins_dt_end: datetime.date
    :param upd_dt_strt: Update date start.
    :type upd_dt_strt: datetime.date
    :param upd_dt_end: Update date end.
    :type upd_dt_end: datetime.date

    :returns:
     | A tuple containing:
     |    - *list* -- a list of history events
     |    - *list* -- a list of history events headers
    :rtype: tuple
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      event_id,
                    location_id,
                    dataset_id,
                    project_id,
                    reference_id,
                    username,
                    insert_timestamp,
                    update_timestamp
        FROM        plugin.event_log
        WHERE       (%(username)s IS NULL OR "username" LIKE %(username)s)
                    AND
                    date(insert_timestamp)
                        BETWEEN %(ins_dt_strt)s AND %(ins_dt_end)s
                    AND
                    date(update_timestamp)
                        BETWEEN %(upd_dt_strt)s AND %(upd_dt_end)s
        ''',
        {'username': usr,
         'ins_dt_strt': ins_dt_strt,
         'ins_dt_end': ins_dt_end,
         'upd_dt_strt': upd_dt_strt,
         'upd_dt_end': upd_dt_end})

    hist_event_list = cur.fetchall()

    hist_event_hdrs = [d[0] for d in cur.description]

    return (hist_event_list, hist_event_hdrs)


def get_hist_dtst_list(
        con, usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end):
    """
    Returns a list of history datasets that is used to populate
    dataset history table.
    Also returns a list of history datasets headers.
    Data are filtered based on input values.

    :param con: A connection.
    :type con: psycopg2.connection
    :param usr: An username.
    :type usr: str
    :param ins_dt_strt: Insert date start.
    :type ins_dt_strt: datetime.date
    :param ins_dt_end: Insert date end.
    :type ins_dt_end: datetime.date
    :param upd_dt_strt: Update date start.
    :type upd_dt_strt: datetime.date
    :param upd_dt_end: Update date end.
    :type upd_dt_end: datetime.date

    :returns:
     | A tuple containing:
     |    - *list* -- a list of history datasets
     |    - *list* -- a list of history datasets headers
    :rtype: tuple
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      dataset_id,
                    username,
                    insert_timestamp,
                    update_timestamp
        FROM        plugin.dataset_log
        WHERE       (%(username)s IS NULL OR "username" LIKE %(username)s)
                    AND
                    date(insert_timestamp)
                        BETWEEN %(ins_dt_strt)s AND %(ins_dt_end)s
                    AND
                    date(update_timestamp)
                        BETWEEN %(upd_dt_strt)s AND %(upd_dt_end)s
        ''',
        {'username': usr,
         'ins_dt_strt': ins_dt_strt,
         'ins_dt_end': ins_dt_end,
         'upd_dt_strt': upd_dt_strt,
         'upd_dt_end': upd_dt_end})

    hist_dtst_list = cur.fetchall()

    hist_dtst_hdrs = [d[0] for d in cur.description]

    return (hist_dtst_list, hist_dtst_hdrs)


def get_hist_prj_list(
        con, usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end):
    """
    Returns a list of history projects that is used to populate
    project history table.
    Also returns a list of history projects headers.
    Data are filtered based on input values.

    :param con: A connection.
    :type con: psycopg2.connection
    :param usr: An username.
    :type usr: str
    :param ins_dt_strt: Insert date start.
    :type ins_dt_strt: datetime.date
    :param ins_dt_end: Insert date end.
    :type ins_dt_end: datetime.date
    :param upd_dt_strt: Update date start.
    :type upd_dt_strt: datetime.date
    :param upd_dt_end: Update date end.
    :type upd_dt_end: datetime.date

    :returns:
     | A tuple containing:
     |    - *list* -- a list of history projects
     |    - *list* -- a list of history projects headers
    :rtype: tuple
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      project_id,
                    username,
                    insert_timestamp,
                    update_timestamp
        FROM        plugin.project_log
        WHERE       (%(username)s IS NULL OR "username" LIKE %(username)s)
                    AND
                    date(insert_timestamp)
                        BETWEEN %(ins_dt_strt)s AND %(ins_dt_end)s
                    AND
                    date(update_timestamp)
                        BETWEEN %(upd_dt_strt)s AND %(upd_dt_end)s
        ''',
        {'username': usr,
         'ins_dt_strt': ins_dt_strt,
         'ins_dt_end': ins_dt_end,
         'upd_dt_strt': upd_dt_strt,
         'upd_dt_end': upd_dt_end})

    hist_prj_list = cur.fetchall()

    hist_prj_hdrs = [d[0] for d in cur.description]

    return (hist_prj_list, hist_prj_hdrs)


def get_hist_ref_list(
        con, usr, ins_dt_strt, ins_dt_end, upd_dt_strt, upd_dt_end):
    """
    Returns a list of history references that is used to populate
    reference history table.
    Also returns a list of history references headers.
    Data are filtered based on input values.

    :param con: A connection.
    :type con: psycopg2.connection
    :param usr: An username.
    :type usr: str
    :param ins_dt_strt: Insert date start.
    :type ins_dt_strt: datetime.date
    :param ins_dt_end: Insert date end.
    :type ins_dt_end: datetime.date
    :param upd_dt_strt: Update date start.
    :type upd_dt_strt: datetime.date
    :param upd_dt_end: Update date end.
    :type upd_dt_end: datetime.date

    :returns:
     | A tuple containing:
     |    - *list* -- a list of history references
     |    - *list* -- a list of history references headers
    :rtype: tuple
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      reference_id,
                    username,
                    insert_timestamp,
                    update_timestamp
        FROM        plugin.reference_log
        WHERE       (%(username)s IS NULL OR "username" LIKE %(username)s)
                    AND
                    date(insert_timestamp)
                        BETWEEN %(ins_dt_strt)s AND %(ins_dt_end)s
                    AND
                    date(update_timestamp)
                        BETWEEN %(upd_dt_strt)s AND %(upd_dt_end)s
        ''',
        {'username': usr,
         'ins_dt_strt': ins_dt_strt,
         'ins_dt_end': ins_dt_end,
         'upd_dt_strt': upd_dt_strt,
         'upd_dt_end': upd_dt_end})

    hist_ref_list = cur.fetchall()

    hist_ref_hdrs = [d[0] for d in cur.description]

    return (hist_ref_list, hist_ref_hdrs)


def get_usr_list(con):
    """
    Returns a list of users whose accounts are active.

    :param con: A connection.
    :type con: psycopg2.connection

    :returns: A list of users whose accounts are active.
    :rtype: list
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      usename u
        FROM        pg_catalog.pg_user
        WHERE       CURRENT_TIMESTAMP < valuntil
        ORDER BY    u
        ''')

    usrs = cur.fetchall()

    usr_list = [u[0] for u in usrs]

    return usr_list


def get_col_def_val(con, schema, tbl, col):
    """
    Returns a column default value for the given table in the given schema.
    This function returns a default value with database function or cast.

    :param con: A connection.
    :type con: psycopg2.connection
    :param schema: A schema.
    :type schema: str
    :param tbl: A table.
    :type tbl: str
    :param col: A column.
    :type col: str

    :returns: A column default value.
    :rtype: str
    """

    cur = _get_db_cur(con)
    cur.execute(
        '''
        SELECT      column_default
        FROM        information_schema.columns
        WHERE       table_schema = %(schema)s
                    AND
                    table_name = %(table)s
                    AND
                    column_name = %(column)s
        ''',
        {'schema': schema,
         'table': tbl,
         'column': col})

    col_def_val = cur.fetchone()[0]

    return col_def_val
