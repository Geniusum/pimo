import lib.logger as logger
import lib.utils as utils
import lib.lang as lang
import copy

class Parser():
    class InvalidStringReference(BaseException): ...
    class NotUpperCaseMacroName(BaseException): ...
    class BlockDelimitation(BaseException): ...

    def __init__(self, pimo_instance):
        self.strings = {}
        self.pimo_instance = pimo_instance
        self.logger:logger.Logger = self.pimo_instance.logger
        self.error_logger:logger.ErrorLogger = self.pimo_instance.error_logger
    
    def genStringID(self, id:int):
        r = lang.AMPERSAND
        r += str(id)
        if r in self.strings.keys():
            r = self.genStringID()
        return r
    
    def mkStringReference(self, string:str, id:str):
        self.strings[id] = string

    def refAllStrings(self, exp:str):
        ls = {
            "string": ["\"", "'"],
            "backslash": ["\\\\"],
            "new_line": ["\\n"],
            "tab": ["\\t"],
            "db_quotes": ["\\\""],
            "quote": ["\\'"],
            "db_slash": [r"\s"],
            "com_open": [r"\so"],
            "com_close": [r"\sc"],
            "semicolon": [r"\sm"]
        }
        for i in ls["backslash"]:
            exp = exp.replace(i, "\\")
        for k, h in {"new_line": "\n", "tab": "\t", "db_quotes": "š", "quote": "ž", "db_slash": "//", "com_open": "/*", "com_close": "*/", "semicolon": "sm"}.items():
            for i in ls[k]:
                exp = exp.replace(i, h)
        string = False
        buffer = ""
        buffer2 = ""
        current_sep = ""
        strings = []
        iid = 1
        for char in [*exp]:
            ex = char in ls["string"]
            if current_sep != "":
                ex = char == current_sep
            if ex:
                if string:
                    current_sep = ""
                    string = False
                    id = self.genStringID(iid)
                    buffer = buffer.replace("š", "\"").replace("ž", "\'")
                    strings.append([buffer, id])
                    buffer = ""
                    buffer2 += id
                    iid += 1
                else:
                    string = True
                    current_sep = char
            else:
                if string:
                    buffer += char
                else:
                    buffer2 += char
        for string_ in strings:
            string = string_[0]
            id = string_[1]
            self.mkStringReference(string, id)
        return buffer2
    
    def getStringFromRefID(self, id:str):
        for string_id, string in self.strings.items():
            if id == string_id: return string
    
    def raise_sourcecode_exception(self, line_content:str, line:int, column:int, exception:BaseException):
        self.pimo_instance.raise_exception(exception, f"Line {line}", line_content.strip(), f"{' ' * column}^")
    
    def raise_exception(self, line:int, exception:BaseException, *args):
        self.pimo_instance.raise_exception(exception, f"Line {line}", *args)

    def parse(self, content:str):
        segments = []

        content = self.refAllStrings(content)

        lines = content.splitlines()

        for line_index, line in enumerate(lines):
            line.replace("\t", "")
            segments.append({"line": line_index + 1, "tokens": [], "parts": []})
            parts = segments[-1]["parts"]
            for char in line:
                if char in lang.NM_CHARS:
                    if not len(parts):
                        parts.append("")
                        
                    parts[-1] += char
                elif char == lang.SPACE:
                    parts.append("")
                else:
                    parts.append(char)
                    parts.append("")
            
            while "" in parts:
                try: parts.remove("")
                except: pass

            parts_to_skip = 0
            line_recreation_ = " ".join(parts)
            line_recreation = utils.multi_replace(line_recreation_, {
                "& ": "&"
            })
            lr_diff = len(line_recreation_) - len(line_recreation)
            for index, part in enumerate(parts):
                if parts_to_skip:
                    parts_to_skip -= 1
                    continue
                
                part_column = len(" ".join(parts[:index])) - lr_diff + 2

                token:lang.Token
                next_part = utils.get_item_safe(parts, index + 1)
                next_part_2 = utils.get_item_safe(parts, index + 2)
                next_part_3 = utils.get_item_safe(parts, index + 3)
                next_part_4 = utils.get_item_safe(parts, index + 4)

                if part + next_part == lang.DOUBLE_SLASH:
                    break
                elif part + next_part == lang.DOUBLE_HASHTAG:
                    token = lang.Token(lang.DOUBLE_HASHTAG)
                    parts_to_skip = 1
                elif part == lang.AMPERSAND and lang.is_an_integer(next_part):
                    string_id = str(int(next_part))
                    string = self.getStringFromRefID(lang.AMPERSAND + string_id)
                    if not string:
                        self.raise_sourcecode_exception(line_recreation, segments[-1]["line"], part_column, self.InvalidStringReference)
                    token = lang.Token(string, "string")
                    parts_to_skip = 1
                    parts_to_skip = 2
                elif lang.is_a_decimal(part + next_part + next_part_2) and next_part_3 == lang.COLON and lang.is_a_type(next_part_4):
                    token = lang.Token(part + next_part + next_part_2)
                    token.type = lang.get_type_from_token(lang.Token(next_part_4, "type"))
                    parts_to_skip = 4
                elif lang.is_a_decimal(part + next_part + next_part_2):
                    token = lang.Token(part + next_part + next_part_2)
                    parts_to_skip = 2
                elif part == lang.PARAGRAPH and lang.is_a_valid_name(next_part):
                    macro_name = next_part
                    if not lang.is_an_upper_name(macro_name):
                        self.raise_sourcecode_exception(line_recreation, segments[-1]["line"], part_column, self.NotUpperCaseMacroName)
                    token = lang.Token(macro_name, "macro")
                    parts_to_skip = 1
                elif part == lang.PERCENTAGE and lang.is_a_register(next_part):
                    token = lang.Token(lang.PERCENTAGE + next_part, "register")
                    parts_to_skip = 1
                elif lang.is_a_type(part) and next_part == lang.LESS_THAN and lang.is_an_integer(next_part_2) and next_part_3 == lang.GREATER_THAN:
                    token = lang.Token(part, "type")
                    token.lenght = int(next_part_2)
                    parts_to_skip = 3
                elif lang.is_an_integer(part) and next_part == lang.COLON and next_part_2 == lang.OPEN_HOOK:
                    token = lang.Token(lang.OPEN_HOOK, "delimiter")
                    token.size = int(part)
                    parts_to_skip = 2
                elif lang.is_a_valid_name(part) and lang.is_an_upper_name(part) and next_part + next_part_2 == lang.DOUBLE_COLON and lang.is_a_valid_name(next_part_3) and lang.is_a_lower_name(next_part_3):
                    token = lang.Token(next_part_3, "name")
                    token.memory = part
                    parts_to_skip = 3
                elif lang.is_an_integer(part) and next_part == lang.COLON and next_part_2 == lang.PERCENTAGE:
                    token = lang.Token(lang.PERCENTAGE, "operator")
                    token.size = int(part)
                    parts_to_skip = 2
                elif (
                    lang.is_an_integer(part) or lang.is_a_valid_name(part) or lang.is_a_boolean(part) or part == lang.CLOSE_HOOK
                ) and next_part == lang.COLON and lang.is_a_type(next_part_2):
                    token = lang.Token(part)
                    token.type = lang.get_type_from_token(lang.Token(next_part_2, "type"))
                    parts_to_skip = 2
                elif part + next_part == lang.DOT_PERCENTAGE:
                    token = lang.Token(lang.DOT_PERCENTAGE, "operator")
                    parts_to_skip = 1
                elif part + next_part + next_part_2 == lang.DOT_DOT_PERCENTAGE:
                    token = lang.Token(lang.DOT_DOT_PERCENTAGE, "operator")
                    parts_to_skip = 2
                elif part + next_part == lang.EQUAL_EQUAL:
                    token = lang.Token(lang.EQUAL_EQUAL, "operator")
                    parts_to_skip = 1
                elif part + next_part == lang.BANG_EQUAL:
                    token = lang.Token(lang.BANG_EQUAL, "operator")
                    parts_to_skip = 1
                elif part + next_part == lang.LESS_EQUAL:
                    token = lang.Token(lang.LESS_EQUAL, "operator")
                    parts_to_skip = 1
                elif part + next_part == lang.GREATER_EQUAL:
                    token = lang.Token(lang.GREATER_EQUAL, "operator")
                    parts_to_skip = 1
                else:
                    token = lang.Token(part)
                
                segments[-1]["tokens"].append(token)
            
            segments[-1].pop("parts")

        return segments

    def parse_blocks(self, segments:str):
        root = lang.Block("root")
        active_block = root
        
        for line_index, line in enumerate(segments):
            line_nb = line["line"]

            tokens:list[lang.Token] = line["tokens"]

            if not tokens: continue

            if tokens[0].verify("operator", lang.HASHTAG): continue

            for token_index, token in enumerate(tokens):
                if token.verify("delimiter", lang.OPEN_HOOK):
                    stack_block = lang.Block("stack", active_block, token)
                    try: stack_block.size = token.size
                    except: pass
                    active_block.elements.append(stack_block)
                    active_block = stack_block
                    active_block.line = line_nb
                elif token.verify("delimiter", lang.OPEN_CURLY_BRACE):
                    segment_block = lang.Block("segment", active_block, token)
                    active_block.elements.append(segment_block)
                    active_block = segment_block
                    active_block.line = line_nb
                elif token.verify("delimiter", lang.OPEN_BRACKET):
                    segment_block = lang.Block("options", active_block, token)
                    active_block.elements.append(segment_block)
                    active_block = segment_block
                    active_block.line = line_nb
                elif token.verify("delimiter", lang.CLOSE_HOOK):
                    if active_block == root:
                        self.raise_exception(line_nb, self.BlockDelimitation, "Can't close a non-existant block.")
                    if active_block.kind != "stack":
                        self.raise_exception(line_nb, self.BlockDelimitation, "Can't close a non-stack block.")
                    
                    try: active_block.type = token.type
                    except: pass
                    active_block = active_block.parent
                elif token.verify("delimiter", lang.CLOSE_CURLY_BRACE):
                    if active_block == root:
                        self.raise_exception(line_nb, self.BlockDelimitation, "Can't close a non-existant block.")
                    if active_block.kind != "segment":
                        self.raise_exception(line_nb, self.BlockDelimitation, "Can't close a non-segment block.")
                    
                    active_block = active_block.parent
                elif token.verify("delimiter", lang.CLOSE_BRACKET):
                    if active_block == root:
                        self.raise_exception(line_nb, self.BlockDelimitation, "Can't close a non-existant block.")
                    if active_block.kind != "options":
                        self.raise_exception(line_nb, self.BlockDelimitation, "Can't close a non-options block.")
                    
                    active_block = active_block.parent
                else:
                    token.line = line_nb
                    token.parent_block = active_block
                    active_block.elements.append(token)
        
        return root.elements
    
    def parse_rest(self, blocks:lang.Block):
        old_blocks = None
        while old_blocks != blocks:
            old_blocks = copy.copy(blocks)
            for element_index, element in enumerate(blocks):
                if lang.is_a_token(element):
                    last_element = utils.get_item_safe(blocks, element_index - 1)
                    if not lang.is_a_token(last_element): last_element = lang.Token("")

                    next_element = utils.get_item_safe(blocks, element_index + 1)
                    if not lang.is_a_token(next_element): next_element = lang.Token("")

                    next_element_2 = utils.get_item_safe(blocks, element_index + 2)
                    if not lang.is_a_token(next_element_2): next_element_2 = lang.Token("")

                    if last_element.verify_type("name") and element.verify("operator", lang.DOT) and next_element.verify_type("name"):
                        last_element.token_string += f".{next_element.token_string}"
                        blocks.remove(element)
                        blocks.pop(element_index + 1)
                    elif last_element.verify_type("name") and element.verify("operator", lang.DOT) and next_element.verify("operator", lang.CARET):
                        last_element.token_string += f".^"
                        blocks.remove(element)
                        blocks.pop(element_index + 1)
                    elif last_element.verify("operator", lang.CARET) and element.verify("operator", lang.DOT) and next_element.verify_type("name"):
                        next_element.token_string += f".^"
                        blocks.remove(element)
                        blocks.pop(element_index + 1)
                else:
                    element.elements = self.parse_rest(element.elements)
        
        for element_index, element in enumerate(blocks):
            if lang.is_a_token(element):
                last_element = utils.get_item_safe(blocks, element_index - 1)
                if not lang.is_a_token(last_element): last_element = lang.Token("")

                next_element = utils.get_item_safe(blocks, element_index + 1)
                next_element_b = utils.get_item_safe(blocks, element_index + 1)
                if not lang.is_a_token(next_element): next_element = lang.Token("")

                next_element_2 = utils.get_item_safe(blocks, element_index + 2)
                if not lang.is_a_token(next_element_2): next_element_2 = lang.Token("")

                if element.verify_type("name") and next_element.verify("operator", lang.COLON) and next_element_2.verify_type("type"):
                    element.type = lang.get_type_from_token(next_element_2)
                    blocks.pop(element_index + 1)
                    blocks.pop(element_index + 2)
                elif element.verify_type("name") and lang.is_options(next_element_b):
                    element.options = next_element_b
                    blocks.pop(element_index + 1)
            else:
                element.elements = self.parse_rest(element.elements)
        
        return blocks