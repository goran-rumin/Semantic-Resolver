from semantic import DBPediaSemanticResolver, YAGOSemanticResolver, WikiDataSemanticResolver, CompositeSemanticResolver
import nlp_processing as pre
import processing as proc
from processing import EntityResolver

resolver = CompositeSemanticResolver(DBPediaSemanticResolver(), YAGOSemanticResolver(), WikiDataSemanticResolver())
counter = 1  # entity counter
processed_entities = set()
results = open("evaluation/semantic_resolver_evaluation_results.txt", "a", encoding="utf-8")
#texts 1-5 BBC, 6-10 CNN

def process_text(text):
    global counter
    sentences = proc.process_text(text)
    e_resolver = create_entity_resolver(sentences)
    for sentence in sentences:
        entities = pre.extract_all_entities(sentence["sentence"])
        sentence_string = " ".join([x[0] for x in sentence["sentence"]])
        for entity_index in entities:
            entity = []
            for i in range(entity_index[0], entity_index[0] + entity_index[1]):
                entity.append(sentence["sentence"][i][0])
            print("Unresolved entity: ", entity)
            entity = e_resolver.resolve_entity(entity, sentence["sentence"][entity_index[0]][3])
            if tuple(entity) in processed_entities:
                continue
            processed_entities.add(tuple(entity))
            print(counter, entity)
            results.write(str(counter) + " " + str(entity) + " " + str(resolver.resolve(entity, sentence["sentence"][entity_index[0]][3], {"sentence": sentence_string})) + "\n")
            counter += 1


def create_entity_resolver(sentences):
    e_resolver = EntityResolver(["PERSON", "LOCATION", "ORGANIZATION"])
    for sentence in sentences:
        relations = pre.generate_entity_pairs(pre.extract_all_entities(sentence["sentence"]))
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


for i in range(1, 12):
    with open("evaluation/texts/tekst" + str(i) + ".txt", "r") as input_file:
        process_text(input_file.read().replace("\n", ""))
resolver.stop()
results.close()
