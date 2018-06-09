import re

with open("semantic_resolver_evaluation_results.txt") as file1, open(
        "semantic_resolver_evaluation_results2.txt") as file2:
    for line1, line2 in zip(file1.readlines(), file2.readlines()):
        line1 = line1.strip()
        line2 = line2.strip()
        m = re.search('({.*}|set\(\))', line1)
        set1 = eval(m.group(0))
        m = re.search('({.*}|set\(\))', line2)
        set2 = eval(m.group(0))
        print(set1 - set2, set2 - set1)

