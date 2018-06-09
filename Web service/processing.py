from itertools import product

from nltk.tokenize import sent_tokenize, word_tokenize

import nlp_processing as nlp
from semantic import *

domain = "http://www.fer.hr"

relations_order_mappings = {"employee": ("ORGANIZATION", "PERSON"), "location": ("ORGANIZATION", "LOCATION"),
                            "homeLocation": ("PERSON", "LOCATION")}


class EntityResolver:
    def __init__(self, ner_types):
        self.__entity_sets = {}
        for ner_type in ner_types:
            self.__entity_sets[ner_type] = ngram.NGram(key=lambda x: x.lower(), threshold=0.25, pad_char=" ")

    def add_entity(self, entity, ner_type):
        existing_item = self.__entity_sets[ner_type].finditem(" ".join(entity))
        if existing_item is None:
            self.__entity_sets[ner_type].add(" ".join(entity))
        elif len(existing_item) < len(" ".join(entity)):
            self.__entity_sets[ner_type].remove(existing_item)
            self.__entity_sets[ner_type].add(" ".join(entity))

    def resolve_entity(self, entity, ner_type):
        existing_item = self.__entity_sets[ner_type].finditem(" ".join(entity))
        if existing_item is None:
            return entity
        return existing_item.split(" ")


def process_text(text):
    sentences = [word_tokenize(sentence) for sentence in sent_tokenize(text)]
    ner_tagged_sentences = nlp.get_NER_tagger().tag_sents(sentences)
    pos_lemma_tagged_sentences = [nlp.preprocess_sentence(sentence) for sentence in sentences]
    sentences = []
    for ner_sent, pos_lemma_sent in zip(ner_tagged_sentences, pos_lemma_tagged_sentences):
        sentences.append([(x[0], x[1], x[2], y[1]) for x, y in zip(pos_lemma_sent, ner_sent)])
    return nlp.list_to_dict_format(sentences)


def create_entity_resolver(sentences):
    e_resolver = EntityResolver(["PERSON", "LOCATION", "ORGANIZATION"])
    for sentence in sentences:
        relations = nlp.generate_entity_pairs(nlp.extract_all_entities(sentence["sentence"]))
        for relation in relations:
            entity1 = []
            for i in range(relation[0][0], relation[0][0] + relation[0][1]):
                entity1.append(sentence["sentence"][i][0])
            entity2 = []
            for i in range(relation[1][0], relation[1][0] + relation[1][1]):
                entity2.append(sentence["sentence"][i][0])
            e_resolver.add_entity(entity1, sentence["sentence"][relation[0][0]][3])
            e_resolver.add_entity(entity2, sentence["sentence"][relation[1][0]][3])
    return e_resolver


def resolve_relations(text, extra_output=False):
    extracted = []
    extra_output_sentences = []
    sentences = process_text(text)
    e_resolver = create_entity_resolver(sentences)
    _resolver = CachedSemanticResolver(
        CompositeSemanticResolver(DBPediaSemanticResolver(), YAGOSemanticResolver(), WikiDataSemanticResolver()))
    for sentence in sentences:
        relations = nlp.generate_entity_pairs(nlp.extract_all_entities(sentence["sentence"]))
        predictions = nlp.predict(nlp.sentence_to_features_list(sentence))
        sentence_string = " ".join([x[0] for x in sentence["sentence"]])
        for relation, prediction in zip(relations, predictions):
            if prediction == "None":
                continue
            entity1 = []
            type1 = sentence["sentence"][relation[0][0]][3]
            for i in range(relation[0][0], relation[0][0] + relation[0][1]):
                entity1.append(sentence["sentence"][i][0])
            entity1 = e_resolver.resolve_entity(entity1, type1)
            entity2 = []
            type2 = sentence["sentence"][relation[1][0]][3]
            for i in range(relation[1][0], relation[1][0] + relation[1][1]):
                entity2.append(sentence["sentence"][i][0])
            entity2 = e_resolver.resolve_entity(entity2, type2)
            entity1_uris = _resolver.resolve(entity1, type1, {"sentence": sentence_string})
            if len(entity1_uris) == 0:
                entity1_uris = {domain + "/" + "_".join(entity1)}
            entity2_uris = _resolver.resolve(entity2, type2, {"sentence": sentence_string})
            if len(entity2_uris) == 0:
                entity2_uris = {domain + "/" + "_".join(entity2)}
            order_mapping = relations_order_mappings.get(prediction, None)
            if order_mapping is not None:
                if type1 != order_mapping[0]:
                    entity1_uris, entity2_uris = entity2_uris, entity1_uris
            extracted.append((entity1_uris, prediction, entity2_uris))
            if extra_output:
                extra_output_sentences.append({"relations_index": len(extracted) - 1, "sentence": sentence_string,
                                       "entity1_index": relation[0][0], "entity2_index": relation[1][0]})
    return extracted if not extra_output else (extracted, extra_output_sentences)


def relation_as_triples(relation):
    return {x for x in product(relation[0], [relation[1]], relation[2])}
