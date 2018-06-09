import logging
import sched
from threading import Thread

import rdflib
from rdflib import URIRef
from rdflib.namespace import RDF

import database_mysql as db

_scheduler = sched.scheduler()
_logger = logging.getLogger(__name__)

_graph_file_name = "web/graph.xml"

_types = {"parentOrganization": {"entity1": "Organization", "entity2": "Organization", "symmetric": False},
          "employee": {"entity1": "Organization", "entity2": "Person", "symmetric": False},
          "brand": {"entity1": "Organization", "entity2": "Organization", "symmetric": False},
          "subOrganization": {"entity1": "Organization", "entity2": "Organization", "symmetric": False},
          "spouse": {"entity1": "Person", "entity2": "Person", "symmetric": True},
          "relatedTo": {"entity1": "Person", "entity2": "Person", "symmetric": True},
          "homeLocation": {"entity1": "Person", "entity2": "Location", "symmetric": False},
          "colleague": {"entity1": "Person", "entity2": "Person", "symmetric": True},
          "children": {"entity1": "Person", "entity2": "Person", "symmetric": False},
          "parent": {"entity1": "Person", "entity2": "Person", "symmetric": False},
          "location": {"entity1": "Organization", "entity2": "Location", "symmetric": False},
          "containedInPlace": {"entity1": "Location", "entity2": "Location", "symmetric": False},
          "containsPlace": {"entity1": "Location", "entity2": "Location", "symmetric": False}
          }


def get_triples():
    relations = _retry(db.get_all_confirmed_relations)
    new_relations = []
    for relation in relations:
        if _types[relation["predicate"]]["symmetric"]:
            new_relations.append({"subject": relation["object"], "predicate": relation["predicate"],
                                  "object": relation["subject"]})
        new_relations.append({"subject": relation["subject"], "predicate": "type",
                              "object": "http://schema.org/" + _types[relation["predicate"]]["entity1"]})
        new_relations.append({"subject": relation["object"], "predicate": "type",
                              "object": "http://schema.org/" + _types[relation["predicate"]]["entity2"]})
    relations.extend(new_relations)
    return relations


def save_rdf():
    graph = rdflib.Graph()
    graph.parse(_graph_file_name, format="xml")
    relations = _retry(db.get_unconfirmed_relations_with_votes)
    for relation in relations:
        subject = URIRef(relation["subject"])
        predicate = URIRef("http://schema.org/" + relation["predicate"])
        obj = URIRef(relation["object"])
        graph.add((subject, predicate, obj))
        if _types[relation["predicate"]]["symmetric"]:
            graph.add((obj, predicate, subject))
        graph.add((subject, RDF.type, URIRef("http://schema.org/" + _types[relation["predicate"]]["entity1"])))
        graph.add((obj, RDF.type, URIRef("http://schema.org/" + _types[relation["predicate"]]["entity2"])))

    graph.bind("schema", URIRef("http://schema.org/"))

    graph.serialize(destination=_graph_file_name, format='xml')

    _logger.info("RDF dump finished for %s relations", len(relations))
    _scheduler.enter(3 * 60 * 60, 1, save_rdf)


def _retry(provider):
    while True:
        try:
            return provider()
        except Exception as e:
            _logger.error("Error while fetching relations: %s", e)


class SchedulerThread(Thread):
    def run(self):
        _scheduler.enter(1, 1, save_rdf)
        _scheduler.run()


def start():
    SchedulerThread().start()