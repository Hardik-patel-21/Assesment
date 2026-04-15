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


#que 1
def flatten_dict(d, parent_key='', sep='.'):
    items=[]
    for k,v in d.items():
        new_key=f"{parent_key}{sep}{k}" if parent_key else new_key
        if instance(v,dict):
            items.extend(flatten_dict(v,new_key,sep=sep).items())
        else:
            items.append((new_key,v))
    return dict(items)

example={"a":{"b":1},"c":{"d":2}}
flatten_dict=flatten_dict(example)
print(flatten_dict)

#que 2

def duplicated_list(lst):
    seen=set()
    result=[]
    for item in lst:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result

duplicated_list=[3, 1, 2, 3, 2, 4, 1]
deduplicated_list=deduplicated_list(duplicated_list)
print(deduplicated_list)

#que3
from collections import defaultdict
def group_by_key(lst,key):
    grouped=defaultdict(list)
    for item in lst:
        grouped[item[key]].append(item['name'])
    return dict(grouped)
employees = [
    {"dept": "eng", "name": "Alice"},
    {"dept": "eng", "name": "Bob"},
    {"dept": "sales", "name": "Carol"},
]
grouped_result=group_by_key(employees,"dept")
print(grouped_result)