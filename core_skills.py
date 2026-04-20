from collections import defaultdict

# 1. Flatten this nested dictionary into {"a.b": 1, "a.c.d": 2}
nested_dict = {"a": {"b": 1, "c": {"d": 2}}}

# 2. Deduplicate this list preserving order → [3, 1, 2, 4]
duplicated_list = [3, 1, 2, 3, 2, 4, 1]

# 3. Group by "dept" → {"eng": ["Alice", "Bob"], "sales": ["Carol"]}
employees = [
    {"dept": "eng", "name": "Alice"},
    {"dept": "eng", "name": "Bob"},
    {"dept": "sales", "name": "Carol"},
]

#Que 1
def flatten_dict(d, parent_key="", sep="."):
    items = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)
print(flatten_dict(nested_dict))

#Que 2
def deduplicate_list(lst):
    seen = set()
    result = []
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result
print(deduplicate_list(duplicated_list))

#Que 3
def group_by_key(lst, key):
    grouped = defaultdict(list)
    for item in lst:
        grouped[item[key]].append(item["name"])
    return dict(grouped)
print(group_by_key(employees, "dept"))

