import logging
from abc import abstractmethod, ABC
from collections import defaultdict
from queue import Queue, Empty
from threading import Thread, Semaphore, Lock

import ngram
from SPARQLWrapper import SPARQLWrapper, JSON, POST

import tfidf

_logger = logging.getLogger(__name__)


class SemanticResolver(Thread, ABC):
    def __init__(self, sparql_endpoint, query_timeout=120):
        super().__init__()
        self._running = True
        self._sparql = SPARQLWrapper(sparql_endpoint)
        self._sparql.setMethod(POST)
        self._sparql.setReturnFormat(JSON)
        self.query_timeout = query_timeout
        self._sparql.setTimeout(self.query_timeout)
        self._job_queue = Queue()
        self._relevance_query = """
        SELECT ?entity (COUNT(?relatedValues) AS ?count)
        WHERE { ?entity ?p ?relatedValues .
        FILTER(##EXPANSION##)
        }
        GROUP BY ?entity
        """
        self._relevance_query_expansion = " ?entity = <##ENTITY##> "
        self._search_separator = ".+"

    def run(self):
        while self._running:
            try:
                job = self._job_queue.get(timeout=5)
            except Empty:
                continue
            job["callback"](self.resolve(job["entity"], job["type"], job["context"]))

    def stop(self):
        self._running = False

    def resolve_async(self, entity, type, context, callback):
        self._job_queue.put({"entity": entity, "type": type, "callback": callback, "context": context})

    @staticmethod
    def escape_string(string):
        return string.replace("'", "\\'").replace("(", "\\\\(").replace(")", "\\\\)")

    @staticmethod
    def contains_unsupported_character(string):
        return '"' in string or '`' in string or '\\' in string

    def resolve(self, entity, type, context):
        type = self._get_type_ontology_mappings().get(type, type)
        self._sparql.setQuery(
            self._get_query().replace("##TYPE##", type).replace("##NAME##", self.escape_string(
                self._search_separator.join(entity))))
        try:
            results = self._sparql.query().convert()
        except Exception as e:
            _logger.error("Exception in %s resolve for entity \"%s\": %s", self.__class__.__name__, " ".join(entity), e)
            return []
        resolved_entities = defaultdict(set)
        abstracts = {}
        for result in results["results"]["bindings"]:
            if self.contains_unsupported_character(result["entity"]["value"]):
                continue
            resolved_entities[result["label"]["value"]].add(result["entity"]["value"])
            abstracts[result["entity"]["value"]] = result["abstract"]["value"] if "abstract" in result.keys() else ""
        return self._find_matching_entity(resolved_entities,
                                          self.get_relevances(list(
                                              {entity for entity_set in resolved_entities.values() for
                                               entity in entity_set})),
                                          self._get_context_relevances(abstracts, context),
                                          " ".join(entity))

    def get_relevances(self, subjects):
        if len(subjects) == 0:
            return {}
        subjects_chunked = [subjects[x:x + 500] for x in range(0, len(subjects), 500)]
        relevances = {}
        for subjects_chunk in subjects_chunked:
            condition = " || ".join(
                map(lambda x: self._relevance_query_expansion.replace("##ENTITY##", x), subjects_chunk))
            self._sparql.setQuery(self._relevance_query.replace("##EXPANSION##", condition))
            try:
                results = self._sparql.query().convert()
                for result in results["results"]["bindings"]:
                    relevances[result["entity"]["value"]] = int(result["count"]["value"])
            except Exception as e:
                _logger.error("Exception in %s get_relevances: %s", self.__class__.__name__, e)
        try:
            max_value = max(relevances.values())  # normalization
            for key in relevances.keys():
                relevances[key] /= max_value
        except ValueError:
            pass
        return relevances

    @staticmethod
    def _get_context_relevances(entity_abstract_map, context):
        entities, abstracts = [], []
        for key, value in entity_abstract_map.items():
            entities.append(key)
            abstracts.append(value)
        scores = tfidf.get_scores(context["sentence"], abstracts)
        return {entity: score if score != 0 else 0.0001 for entity, score in zip(entities, scores)}

    @abstractmethod
    def _get_query(self):
        pass

    @abstractmethod
    def _get_type_ontology_mappings(self):
        pass

    @staticmethod
    def _find_matching_entity(resolved_entities, external_relevances, context_relevances, text_entity):
        # resolved_entities format: {"label": {"url1", "url2", ...}, ...}
        # external_relevances format: {"url": relevance, ...}
        if len(resolved_entities.items()) == 0:
            return []
        ngram_search = ngram.NGram(resolved_entities.keys(), key=lambda x: x.lower(), threshold=0, pad_char=" ")
        items = ngram_search.searchitem(text_entity)  # format [("label", relevance), ...]
        if items is None or len(items) == 0:
            return []
        items = [(url, x[1] * external_relevances.get(url, 0.0001) * context_relevances.get(url, 0.0001)) for x in items
                 for url
                 in resolved_entities[x[0]]]
        items = sorted(items, key=lambda x: -x[1])
        return [items[0][0]]


class DBPediaSemanticResolver(SemanticResolver):
    def __init__(self):
        super().__init__("http://dbpedia.org/sparql")
        self.__query = """
        PREFIX dbo: <http://dbpedia.org/ontology/>
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        SELECT DISTINCT ?entity ?label ?abstract
        WHERE { ?entity rdf:type dbo:##TYPE## .
        ?entity rdfs:label ?label .
        FILTER (LANG(?label) = "en") .
        FILTER (REGEX(STR(?label), '##NAME##', 'i')) .
        OPTIONAL {
            ?entity dbo:abstract ?abstract .
            FILTER(LANG(?abstract) = "en")
        }
        }
        """
        self.sameAs_query = """
        PREFIX owl: <http://www.w3.org/2002/07/owl#>
        SELECT ?entity
        WHERE {
        <##ENTITY##> owl:sameAs ?entity
        }
        """

    def resolve(self, entity, type, context):
        entity = super().resolve(entity, type, context)
        if len(entity) == 0:
            return entity
        self._sparql.setQuery(self.sameAs_query.replace("##ENTITY##", entity[0]))
        try:
            results = self._sparql.query().convert()
        except Exception as e:
            _logger.error("Exception in sameAs for entity \"%s\": %s", " ".join(entity), e)
            return entity
        entities = []
        entities.extend(entity)
        for result in results["results"]["bindings"]:
            if "wikidata.org/entity" in result["entity"]["value"]:
                entities.append(result["entity"]["value"])
        return entities

    def _get_query(self):
        return self.__query

    def _get_type_ontology_mappings(self):
        return {"ORGANIZATION": "Organisation", "PERSON": "Person", "LOCATION": "Location"}


class YAGOSemanticResolver(SemanticResolver):
    def __init__(self):
        super().__init__("https://linkeddata1.calcul.u-psud.fr/sparql")
        self.__query = """
        PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX yago: <http://yago-knowledge.org/resource/>
        SELECT DISTINCT ?entity ?label ('' AS ?abstract)
        WHERE { GRAPH <http://www.yago-knowledge.org> {
            ?entity rdf:type yago:##TYPE## .
            ?entity rdfs:label ?label .
            FILTER (LANG(?label) = "eng") .
            FILTER (REGEX(STR(?label), '##NAME##', 'i'))
            }
        }
        """

    def _get_query(self):
        return self.__query

    def _get_type_ontology_mappings(self):
        return {"ORGANIZATION": "wordnet_organization_108008335", "PERSON": "wordnet_person_100007846",
                "LOCATION": "wordnet_location_100027167"}


class WikiDataSemanticResolver(SemanticResolver):
    def __init__(self):
        super().__init__("https://query.wikidata.org/sparql")
        self.__query = """
        PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
        PREFIX wdt: <http://www.wikidata.org/prop/direct/>
        PREFIX wd: <http://www.wikidata.org/entity/>
        SELECT DISTINCT ?entity ('##NAME##' AS ?label) ?abstract
        WHERE {
        ?entity wdt:P31/wdt:P279* wd:##TYPE## .
        ?entity rdfs:label '##NAME##'@en .
        OPTIONAL{ 
            ?entity schema:description ?abstract .
            FILTER(LANG(?abstract) = "en")
        }
        }
        """
        self._search_separator = " "

    def _get_query(self):
        return self.__query

    def _get_type_ontology_mappings(self):
        return {"ORGANIZATION": "Q43229", "PERSON": "Q5", "LOCATION": "Q17334923"}


class CompositeSemanticResolver:
    def __init__(self, *resolvers):
        self.safe_lock = Lock()
        self.return_lock = Semaphore(0)
        self.resolvers = resolvers
        for resolver in resolvers:
            resolver.start()

    def resolve(self, entity, type, context):
        entities = set()
        for resolver in self.resolvers:
            resolver.resolve_async(entity, type, context, lambda resolved: self._on_resolve(resolved, entities))
        for resolver in self.resolvers:
            self.return_lock.acquire()
        return entities

    def _on_resolve(self, resolved, entities):
        with self.safe_lock:
            entities.update(resolved)
            self.return_lock.release()

    def stop(self):
        for resolver in self.resolvers:
            resolver.stop()


class CachedSemanticResolver:
    def __init__(self, semantic_resolver):
        self._semantic_resolver = semantic_resolver
        self._cache = {}

    def resolve(self, entity, type, context):
        elements = self._cache.get(" ".join(entity), None)
        if elements is None:
            elements = self._semantic_resolver.resolve(entity, type, context)
            self._cache[" ".join(entity)] = elements
        return elements
