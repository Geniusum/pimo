def void(*args, **kwargs): return None

indentation = "  ⋅ "

def name(object:any) -> str:
    return f'{object=}'.split('=')[0]

def dump(iterable, indent:int=0):
    buffer = ""
    d = f"\n{indentation * (indent + 1)}"
    if isinstance(iterable, list):
        for index, item in enumerate(iterable):
            if type(item) in [list, dict]:
                buffer += f"{indentation * indent}#{index} {type(item)} :\n"
                buffer += dump(item, indent + 1)
            else:
                buffer += f"{indentation * indent}#{index} {type(item)} {d.join(str(item).splitlines())}\n"
    elif isinstance(iterable, dict):
        for key, item in iterable.items():
            if type(item) in [list, dict]:
                buffer += f"{indentation * indent}{type(item)} {key}:\n"
                buffer += dump(item, indent + 1)
            else:
                buffer += f"{indentation * indent}{type(item)} {key}: {d.join(str(item).splitlines())}\n"
    else:
        buffer += f"{indentation * indent}{type(iterable)} {d.join(str(iterable).splitlines())}\n"
    return buffer

def get_item_safe(list:list, index:int):
    if index + 1 > len(list): return ""
    return list[index]

def multi_replace(s:str, replaces:dict):
    for key, value in replaces.items():
        s = s.replace(key, value)
    return s