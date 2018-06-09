from threading import local

import pymysql

# module expects existing database
_DATABASE_NAME = "semantic_resolver"
_DATABASE_USER = "resolver"
_DATABASE_PASSWORD = "semantic"
_DATABASE_HOST = "192.168.99.100"

_relations_query = """SELECT relations.id, subject, predicate, object 
                    FROM relations JOIN relations_urls_map
                    ON relations.id = relations_urls_map.relation_id
                    JOIN urls ON relations_urls_map.url_id = urls.id
                    AND urls.url = %s
                    ORDER BY ABS(votes)"""
_relations_all_query = """SELECT id, subject, predicate, object FROM relations
                        WHERE saved = TRUE"""
_relations_rdf_query = """SELECT id, subject, predicate, object FROM relations
                        WHERE votes >= %s AND saved = FALSE"""
_relations_rdf_update = """UPDATE relations SET saved = TRUE
                        WHERE votes >= %s AND saved = FALSE"""
_relations_check_query = """SELECT id FROM relations 
                    WHERE subject = %s AND predicate = %s AND object = %s"""
_relations_insert = """INSERT INTO relations(subject, predicate, object) VALUES(%s, %s, %s)"""
_link_processed_query = """SELECT id 
                    FROM urls
                    WHERE urls.url = %s"""
_urls_insert = """INSERT INTO urls(url) VALUES(%s)"""
_relations_urls_insert = """INSERT INTO relations_urls_map VALUES(%s, %s)"""
_sentence_check_query = """SELECT id FROM sentences WHERE text = %s"""
_sentence_insert = """INSERT INTO sentences(text) VALUES(%s)"""
_relations_sentences_insert = """INSERT INTO relations_sentences_map VALUES(%s, %s, %s, %s)"""
_relations_vote = """UPDATE relations SET votes = votes + %s WHERE id = %s"""

_thread_local = local()


def _connect():
    return pymysql.connect(host=_DATABASE_HOST, user=_DATABASE_USER, password=_DATABASE_PASSWORD, db=_DATABASE_NAME,
                           charset="utf8")


_connection = _connect()
_cursor = _connection.cursor()


def _init():
    _cursor.execute("""CREATE TABLE IF NOT EXISTS relations(
                        id INT PRIMARY KEY AUTO_INCREMENT, 
                         subject NVARCHAR(200) NOT NULL, 
                         predicate NVARCHAR(200) NOT NULL, 
                         object NVARCHAR(200) NOT NULL, 
                         votes INT NOT NULL DEFAULT 0,
                         saved BIT(1) NOT NULL DEFAULT FALSE)""")
    _cursor.execute("""CREATE TABLE IF NOT EXISTS urls(
                        id INT PRIMARY KEY AUTO_INCREMENT, 
                        url NVARCHAR(500) NOT NULL UNIQUE)""")
    _cursor.execute("""CREATE TABLE IF NOT EXISTS relations_urls_map(
                        relation_id INT NOT NULL, 
                        url_id INT NOT NULL,
                        PRIMARY KEY(relation_id, url_id),
                        FOREIGN KEY (relation_id) REFERENCES relations(id),
                        FOREIGN KEY (url_id) REFERENCES urls(id))""")
    _cursor.execute("""CREATE TABLE IF NOT EXISTS sentences(
                        id INT PRIMARY KEY AUTO_INCREMENT,
                        text TEXT NOT NULL)""")
    _cursor.execute("""CREATE TABLE IF NOT EXISTS relations_sentences_map(
                        relation_id INT NOT NULL, 
                        sentence_id INT NOT NULL, 
                        entity1_index INT NOT NULL,
                        entity2_index INT NOT NULL,
                        PRIMARY KEY(relation_id, sentence_id),
                        FOREIGN KEY (relation_id) REFERENCES relations(id),
                        FOREIGN KEY (sentence_id) REFERENCES sentences(id))""")
    _connection.commit()


def _should_init():
    _cursor.execute("""SHOW TABLES""")
    return len(_cursor.fetchall()) == 0


def _create_connection_if_not_exists():
    if getattr(_thread_local, "connection", None) is None:
        _thread_local.connection = _connect()
    if getattr(_thread_local, "cursor", None) is None:
        _thread_local.cursor = _thread_local.connection.cursor()


def _insert_sentence_if_not_exists(sentence):
    _create_connection_if_not_exists()
    _thread_local.cursor.execute(_sentence_check_query, (sentence,))
    ids = _thread_local.cursor.fetchall()
    if len(ids) > 1:
        raise Exception("Database has two same sentences")
    if len(ids) == 1:
        return ids[0][0]
    _thread_local.cursor.execute(_sentence_insert, (sentence,))
    _thread_local.cursor.execute(_sentence_check_query, (sentence,))
    _thread_local.connection.commit()
    return _thread_local.cursor.fetchone()[0]


def _insert_triple_if_not_exists(subject, predicate, object):
    _create_connection_if_not_exists()
    _thread_local.cursor.execute(_relations_check_query, (subject, predicate, object))
    ids = _thread_local.cursor.fetchall()
    if len(ids) > 1:
        raise Exception("Database has two same relations")
    if len(ids) == 1:
        return ids[0][0]
    _thread_local.cursor.execute(_relations_insert, (subject, predicate, object))
    _thread_local.cursor.execute(_relations_check_query, (subject, predicate, object))
    _thread_local.connection.commit()
    return _thread_local.cursor.fetchone()[0]


def _insert_url_if_not_exists(url):
    _create_connection_if_not_exists()
    _thread_local.cursor.execute(_link_processed_query, (url,))
    ids = _thread_local.cursor.fetchall()
    if len(ids) > 1:
        raise Exception("Database has two same urls")
    if len(ids) == 1:
        return ids[0][0]
    _thread_local.cursor.execute(_urls_insert, (url,))
    _thread_local.cursor.execute(_link_processed_query, (url,))
    _thread_local.connection.commit()
    return _thread_local.cursor.fetchone()[0]


def is_link_processed(link):
    _create_connection_if_not_exists()
    _thread_local.cursor.execute(_link_processed_query, (link,))
    count = len(_thread_local.cursor.fetchall())
    _thread_local.connection.commit()
    return count != 0


def get_relations(link):
    _create_connection_if_not_exists()
    _thread_local.cursor.execute(_relations_query, (link,))
    relations = []
    for relation in _thread_local.cursor:
        relations.append({"id": relation[0], "subject": relation[1], "predicate": relation[2], "object": relation[3]})
    _thread_local.connection.commit()
    return relations


def get_unconfirmed_relations_with_votes(votes_num_threshold=5):
    _create_connection_if_not_exists()
    _thread_local.cursor.execute(_relations_rdf_query, (votes_num_threshold,))
    relations = []
    for relation in _thread_local.cursor:
        relations.append({"id": relation[0], "subject": relation[1], "predicate": relation[2], "object": relation[3]})
    _thread_local.cursor.execute(_relations_rdf_update, (votes_num_threshold,))
    _thread_local.connection.commit()
    return relations


def get_all_confirmed_relations():
    _create_connection_if_not_exists()
    _thread_local.cursor.execute(_relations_all_query)
    relations = []
    for relation in _thread_local.cursor:
        relations.append({"id": relation[0], "subject": relation[1], "predicate": relation[2], "object": relation[3]})
    _thread_local.connection.commit()
    return relations


def save_relations(link, data):
    _create_connection_if_not_exists()
    if is_link_processed(link):
        raise ValueError(link + " is already processed")
    url_id = _insert_url_if_not_exists(link)
    for relation in data:
        sentence_id = _insert_sentence_if_not_exists(relation["sentence"])
        for triple in relation["triples"]:
            relation_id = _insert_triple_if_not_exists(*triple)
            _thread_local.cursor.execute(_relations_sentences_insert, (
                relation_id, sentence_id, relation["entity1_index"], relation["entity2_index"]))
            _thread_local.cursor.execute(_relations_urls_insert, (relation_id, url_id))
            _thread_local.connection.commit()


def save_vote(relation_id, vote_change):
    _create_connection_if_not_exists()
    _thread_local.cursor.execute(_relations_vote, (vote_change, relation_id))
    _thread_local.connection.commit()
    if _thread_local.cursor.rowcount == 0:
        raise ValueError("Unknown relation id")


if _should_init():
    _init()
