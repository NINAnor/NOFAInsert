import psycopg2


# connection parameters to NODA DB official db

pg_host = r'<host>'
pg_user = r'<username>'
pg_pwd = '<password>'
pg_db = r'<db>'
pg_port = r'<port>'

try:
    con = psycopg2.connect(
        "host={} dbname={} user={} password= {} port={}"
        .format(pg_host, pg_db, pg_user, pg_pwd, pg_port))
    print u'connection successful'
except:
    print u'connection error'

cur = con.cursor()


# create plugin schema
cur.execute(
    """
    CREATE SCHEMA    plugin;
    """)

con.commit()

print u'schema "plugin" created'


# create occurrence log table
cur.execute(
    """
    CREATE TABLE    plugin.occurrence_log(
                        occurrence_log_id serial NOT NULL,
                        occurrence_id text NOT NULL,
                        event_id text NOT NULL,
                        dataset_id text NOT NULL,
                        project_id text NOT NULL,
                        reference_id integer,
                        location_id text NOT NULL,
                        test boolean DEFAULT False,
                        username text NOT NULL,
                        insert_timestamp timestamp without time zone
                            DEFAULT now(),
                        update_timestamp timestamp without time zone
                            DEFAULT now());
    COMMENT ON TABLE    plugin.occurrence_log
    IS                  'Log table storing info about all new occurrences inserted by NOFAInsert plugin.';
    """)

con.commit()

print u'table "plugin.occurrence_log" created'


# create dataset log table
cur.execute(
    """
    CREATE TABLE    plugin.dataset_log(
                        dataset_id integer NOT NULL,
                        test boolean DEFAULT False,
                        username text NOT NULL,
                        insert_timestamp timestamp without time zone
                            DEFAULT now(),
                        update_timestamp timestamp without time zone
                            DEFAULT now());
    COMMENT ON TABLE    plugin.dataset_log
    IS                  'Log table storing info about all new dataset metadata inserted by NOFAInsert plugin.';
    """)

con.commit()

print u'table "plugin.dataset_log" created'


# create project log table
cur.execute(
    """
    CREATE TABLE    plugin.project_log(
                        project_id character varying(255) NOT NULL,
                        test boolean DEFAULT False,
                        username text NOT NULL,
                        insert_timestamp timestamp without time zone
                            DEFAULT now(),
                        update_timestamp timestamp without time zone
                            DEFAULT now());
    COMMENT ON TABLE    plugin.project_log \
    IS                  'Log table storing info about all new project metadata inserted by NOFAInsert plugin.';
    """)

con.commit()

print u'table "plugin.project_log" created'


# create reference log table
cur.execute(
    """
    CREATE TABLE    plugin.reference_log(
                        reference_id integer NOT NULL,
                        test boolean DEFAULT False,
                        username text NOT NULL,
                        insert_timestamp timestamp without time zone
                            DEFAULT now(),
                        update_timestamp timestamp without time zone
                            DEFAULT now());
    COMMENT ON TABLE    plugin.reference_log
    IS                  'Log table storing info about all new reference metadata inserted by NOFAInsert plugin.';
    """)

con.commit()

print u'table "plugin.reference_log" created'


# create location log table
cur.execute(
    """
    CREATE TABLE    plugin.location_log(
                        location_id uuid NOT NULL,
                        test boolean DEFAULT False,
                        username text NOT NULL,
                        location_name text DEFAULT NULL,
                        insert_timestamp timestamp without time zone
                            DEFAULT now(),
                        update_timestamp timestamp without time zone
                            DEFAULT now());
    COMMENT ON TABLE    plugin.location_log
    IS                  'Log table storing info about all new locations inserted by NOFAInsert plugin.';
    """)

con.commit()

print u'table "plugin.location_log" created'


# create event log table
cur.execute(
    """
    CREATE TABLE    plugin.event_log(
                        event_id uuid NOT NULL,
                        location_id text NOT NULL,
                        dataset_id text NOT NULL,
                        project_id text NOT NULL,
                        reference_id integer,
                        test boolean DEFAULT False,
                        username text NOT NULL,
                        insert_timestamp timestamp without time zone
                            DEFAULT now(),
                        update_timestamp timestamp without time zone
                            DEFAULT now());
    COMMENT ON TABLE    plugin.event_log
    IS                  'Log table storing info about all new events inserted by NOFAInsert plugin.';
    """)
 
con.commit()
 
print u'table "plugin.event_log" created'


con.close()

print u'connection closed'
