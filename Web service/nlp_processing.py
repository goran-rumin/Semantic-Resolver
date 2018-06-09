import pickle
from itertools import combinations

import nltk
from nltk.corpus import wordnet as wn
from nltk.stem.wordnet import WordNetLemmatizer
from nltk.tag.stanford import StanfordNERTagger


def __is_noun(tag):
    return tag in ['NN', 'NNS', 'NNP', 'NNPS']


def __is_verb(tag):
    return tag in ['VB', 'VBD', 'VBG', 'VBN', 'VBP', 'VBZ']


def __is_adverb(tag):
    return tag in ['RB', 'RBR', 'RBS']


def __is_adjective(tag):
    return tag in ['JJ', 'JJR', 'JJS']


def __penn_to_wn(tag):
    if __is_adjective(tag):
        return wn.ADJ
    elif __is_noun(tag):
        return wn.NOUN
    elif __is_adverb(tag):
        return wn.ADV
    elif __is_verb(tag):
        return wn.VERB
    return wn.NOUN


__l = WordNetLemmatizer()


def preprocess_sentence(sentence):
    tagged_sent = nltk.pos_tag(sentence)
    lemmatized_sent = []
    for tagged_word in tagged_sent:
        lemmatized_sent.append(
            (tagged_word[0], tagged_word[1], __l.lemmatize(tagged_word[0], __penn_to_wn(tagged_word[1]))))
    return lemmatized_sent


def get_NER_tagger():
    return StanfordNERTagger(
        "stanford-ner-2015-12-09/classifiers/english.all.3class.distsim.crf.ser.gz",
        "stanford-ner-2015-12-09/stanford-ner.jar")


def list_to_dict_format(sentences):
    return [{"sentence": sentence} for sentence in sentences]


def extract_all_entities(sentence):
    entities = []
    entity_length = 0
    in_entity = False
    for i in range(len(sentence)):
        word = sentence[i]
        if word[3] != "O":  # ako smo na rijeci koja je oznacena kao dio named entititija
            if in_entity == False:  # ako do sad nismo bili inicijaliziraj sve
                in_entity = True
                entity_index = i
                entity_length = 1
            elif word[3] == sentence[entity_index][3]:  # ako je rijec dio named entitija kojeg brojimo
                entity_length += 1
            else:  # ili dio drugog named entitija odmah do prvog
                entities.append((entity_index, entity_length))
                entity_index = i
                entity_length = 1
        elif in_entity == True:  # ako smo izasli iz named entitija
            in_entity = False
            entities.append((entity_index, entity_length))
    return entities


def generate_entity_pairs(entities):
    return [x for x in combinations(entities, 2)]


def normalize_relations(relations,
                        mapping={"parentOrganization": "subOrganization", "containsPlace": "containedInPlace",
                                 "memberOf": "member", "children": "parent", "brand": "isBrandOf"}):
    relations = list(relations)
    for i in range(len(relations)):
        if relations[i][0] > relations[i][1]:
            relations[i] = (relations[i][1], relations[i][0], mapping.get(relations[i][2], relations[i][2]))
    return relations


def create_relations(sentence_with_relations):
    entities = extract_all_entities(sentence_with_relations["sentence"])
    annotated_relations = normalize_relations(sentence_with_relations.get("relations", []))
    relations = generate_entity_pairs(entities)
    for i in range(len(relations)):
        relation = relations[i]
        search = [x for x in annotated_relations if x[0] == relation[0][0] and x[1] == relation[1][0]]
        if len(search) > 0:
            relations[i] = relations[i] + (search[0][2],)
        else:
            relations[i] = relations[i] + ("None",)
    return relations


def generate_features(sentence_with_relations):
    instances = []
    sentence = sentence_with_relations["sentence"]
    for relation in create_relations(sentence_with_relations):
        instance = {}
        instance["NE1_type"] = sentence[relation[0][0]][3]
        instance["NE1_length"] = relation[0][1]
        instance["NE2_type"] = sentence[relation[1][0]][3]
        instance["NE2_length"] = relation[1][1]
        instance["distance"] = relation[1][0] - (relation[0][0] + relation[0][1])
        instance["word1_type"] = sentence[relation[0][0]][1]
        instance["word2_type"] = sentence[relation[1][0]][1]

        generate_sorounding_words_features(instance, relation, sentence)
        generate_NE_overlap_features(instance, relation, sentence)
        generate_NE_position_features(instance, relation, sentence)
        generate_family_relation_features(instance, relation, sentence)
        generate_organization_relation_features(instance, relation, sentence)
        generate_syntax_features(instance, relation, sentence)
        instances.append((instance, relation[2]))
    return instances


def generate_sorounding_words_features(instance, relation, sentence):  # employee
    if relation[0][0] - 1 < 0:
        instance["word1_before_type"] = ""
    else:
        instance["word1_before_type"] = sentence[relation[0][0] - 1][1]
    instance["word1_after_type"] = sentence[relation[0][0] + relation[0][1]][1]
    instance["word2_before_type"] = sentence[relation[1][0] - 1][1]
    if relation[1][0] + relation[1][1] >= len(sentence):
        instance["word2_after_type"] = ""
    else:
        instance["word2_after_type"] = sentence[relation[1][0] + relation[1][1]][1]


def generate_NE_overlap_features(instance, relation, sentence):  # spouse
    NE1, NE2 = set(), set()
    for i in range(relation[0][1]):
        NE1.add(sentence[relation[0][0] + i][2].lower())
    for i in range(relation[1][1]):
        NE2.add(sentence[relation[1][0] + i][2].lower())
    NE_common = NE1.intersection(NE2)
    instance["common_NE_words"] = len(NE_common) > 0


def generate_NE_position_features(instance, relation, sentence):
    words_between = set()
    for i in range(relation[0][0] + relation[0][1], relation[1][0]):
        words_between.add(sentence[i][3])
    instance["location_between"] = "LOCATION" in words_between
    instance["person_between"] = "PERSON" in words_between
    instance["organization_between"] = "ORGANIZATION" in words_between


def generate_family_relation_features(instance, relation, sentence):
    words_between = set()
    family_keywords = {"brother", "sister", "child", "mother", "father", "niece", "nephew", "daughter", "son"}
    spouse_relation_keywords = {"husband", "wife", "romantic", "married", "marriage", "marry", "bride", "groom"}
    for i in range(relation[0][0] + relation[0][1], relation[1][0]):
        words_between.add(sentence[i][2].lower())
    instance["family_words_len"] = len(words_between.intersection(family_keywords))
    if instance["family_words_len"] > 0:
        instance["family_word"] = words_between.intersection(family_keywords).pop()
    else:
        instance["family_word"] = ""
    instance["spouse_words_len"] = len(words_between.intersection(spouse_relation_keywords))
    if instance["spouse_words_len"] > 0:
        instance["spouse_word"] = words_between.intersection(spouse_relation_keywords).pop()
    else:
        instance["spouse_word"] = ""


def generate_organization_relation_features(instance, relation, sentence):
    organization_keywords = {"sell", "dollar", "purchase", 'acquire', 'acquisition', 'affiliate', 'agree', 'agreement',
                             'arrangement', 'business', 'buy', 'buyer', 'company', 'corp', 'corporation', 'holding',
                             'investment', 'merge', 'merger', 'negotiation', 'ordinary', 'parent', 'part', 'partners',
                             'partnership', 'share', 'shareholder', 'specifically', 'subsidiary', 'takeover', 'tender'}
    words_between = set()
    for i in range(relation[0][0] + relation[0][1], relation[1][0]):
        words_between.add(sentence[i][2].lower())
    instance["organization_words_len"] = len(words_between.intersection(organization_keywords))


def generate_syntax_features(instance, relation, sentence):
    words_between = set()
    for i in range(relation[0][0] + relation[0][1], relation[1][0]):
        words_between.add(sentence[i][2])
    instance["contains_separators"] = len({",", ";", ":", "-", "(", ")"}.intersection(words_between)) > 0


def sentence_to_features_list(sentence):
    return generate_features(sentence)


_model, _vectorizer, _encoder, _scaler = pickle.load(open("model.data", "rb"))


def predict(instances):
    if len(instances) == 0:
        return []
    X = _vectorizer.transform([x[0] for x in instances])
    X = _scaler.transform(X)
    y_predicted = _encoder.inverse_transform(_model.predict(X))
    return y_predicted
