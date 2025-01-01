import lib.fasm as fasm
import lib.logger as logger
import lib.lang as lang
import lib.utils as utils
import random, copy

class Compiler():
    class PostCompilingVerification(BaseException): ...
    class InvalidPreprocessorCommand(BaseException): ...
    class SemicolonSeparation(BaseException): ...
    class BlockDelimitation(BaseException): ...
    class Evaluation(BaseException): ...
    class StackEvaluation(BaseException): ...
    class StackInitialization(BaseException): ...
    class ExitInstruction(BaseException): ...
    class IniInstruction(BaseException): ...
    
    def __init__(self, pimo_instance, architecture:str="x64"):
        self.pimo_instance = pimo_instance
        self.logger:logger.Logger = self.pimo_instance.logger
        self.error_logger:logger.ErrorLogger = self.pimo_instance.error_logger
        self.programs = [
            {
                "asm": fasm.Program(architecture),
                "id": self.generate_id(),
                "line": None,
                "acmem": None
            }
        ]
        self.main_program = self.programs[0]
        self.memories = {}
        self.stacks = {}
        self.scopes = {
            self.main_program["id"]: {
                "macros": {}
            }
        }
        self.main_scope = self.scopes[self.main_program["id"]]
        self.running_programs = []
        self.ids = []
    
    def generate_id(self) -> str:
        s = ""
        s += random.choice("abcdef")
        for i in range(23):
            s += random.choice(lang.HEX_DIGITS)
        s = s.upper()
        if s in self.ids: s = self.generate_id()
        self.ids.append(s)
        return s
    
    def raise_exception(self, line:int, exception:BaseException, *args):
        self.pimo_instance.raise_exception(exception, f"Line {line}", *args)
    
    def evaluate(self, tokens:list[lang.Token]) -> lang.Token:
        program = self.running_programs[-1]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]
        rtoken:lang.Token
        scope = self.scopes[program["id"]]

        block = {"kind": "stack", "parent": None, "size": 128, "elements": []}
        active_block = block
        block_started = False
        
        def evaluate_stack(stack:list, stack_size:int) -> lang.Token:
            stack_id = self.generate_id()
            self.stacks[stack_id] = {
                "size": stack_size,
                "elements": []
            }
            active_stack = self.stacks[stack_id]
            asm.add_to_data_segment("stack_" + stack_id, "rb", active_stack["size"])
            asm.add_to_code_segment("mov", asm.get_register("si"), "stack_" + stack_id)

            def add_integer(nb:int, size:int=None):
                if size is None: size = lang.how_much_bytes(nb)
                operator, size_ = lang.bytes_to_operator(size), lang.operator_to_bytes(lang.bytes_to_operator(size))
                if operator is None or size_ is None:
                    self.raise_exception(line_nb, self.StackEvaluation, "To big integer.")
                if free_size < size_:
                    self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                active_stack["elements"].append({
                    "size": size_,
                    "type": token.token_type,
                    "operator": operator
                })
                asm.add_to_code_segment("mov", f"{operator} [{asm.get_register('si')}]", nb)
                asm.add_to_code_segment("add", asm.get_register("si"), size_)
            
            def add_decimal(nb:float):
                size = lang.how_much_bytes_decimal(nb)
                if free_size < size:
                    self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                if size == 4: operator = "dd"
                else: operator = "dq"
                data_id = self.generate_id()
                active_stack["elements"].append({
                    "size": size,
                    "type": token.token_type,
                    "data": data_id,
                    "operator": "dword" if operator == "dd" else "qword"
                })
                asm.add_to_data_segment("data_" + data_id, operator, nb)
                asm.add_to_code_segment("lea", asm.get_register("si"), f"[data_{data_id}]")
                asm.add_to_code_segment("lea", asm.get_register("di"), f"[stack_{stack_id}]")
                asm.add_to_code_segment("mov", asm.get_register("ax"), size)
                asm.add_to_code_segment("rep", "movsb")
            
            def add_boolean(bool:int):
                size = 1
                if free_size < size:
                    self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                active_stack["elements"].append({
                    "size": size,
                    "type": token.token_type,
                    "operator": "byte"
                })
                asm.add_to_code_segment("mov", f"byte [{asm.get_register('si')}]", bool)
                asm.add_to_code_segment("add", asm.get_register("si"), size)

            for token in stack:
                used_size = lang.get_stack_used_size(active_stack)
                free_size = active_stack["size"] - used_size
                if isinstance(token, dict): token = evaluate_stack(token["elements"], token["size"])
                if not token: continue
                if token.verify_type("integer"):
                    nb = int(token.token_string)
                    add_integer(nb)
                elif token.verify_type("decimal"):
                    nb = float(token.token_string)
                    add_decimal(nb)
                elif token.verify_type("boolean"):
                    bool = 0
                    if token.token_string.lower() == "true": bool = 1
                    add_boolean(bool)
                elif token.verify_type("address"):
                    size = 8
                    if asm.architecture == "x86": size = 4
                    if free_size < size:
                        self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                    operator = "qword" if size == 8 else "dword"
                    active_stack["elements"].append({
                        "size": size,
                        "type": token.token_type,
                        "operator": operator
                    })
                    asm.add_to_code_segment("mov", f"{operator} [{asm.get_register('si')}]", token.token_string)
                    asm.add_to_code_segment("add", asm.get_register("si"), size)
                elif token.verify("operator", lang.PERCENTAGE):
                    size = 8
                    if asm.architecture == "x86": size = 4
                    if not active_stack["elements"]:
                        self.raise_exception(line_nb, self.StackEvaluation, "Empty stack, wanted an address.")
                    if not active_stack["elements"][-1]["size"] != size:
                        self.raise_exception(line_nb, self.StackEvaluation, "Wanted a valid address.")
                    addr_operator = "qword" if size == 8 else "dword"
                    target_size = 1
                    target_operator = "byte"
                    try: token.target
                    except: pass
                    else:
                        target_size = token.target["size"]
                        target_operator, target_size = lang.bytes_to_operator(target_size), lang.operator_to_bytes(lang.bytes_to_operator(target_size))
                        target_type = token.target["type"]
                    if free_size < target_size:
                        self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                    active_stack.pop()
                    active_stack.append({
                        "size": target_size,
                        "type": target_type,
                        "operator": target_operator
                    })
                    asm.add_to_code_segment("sub", asm.get_register("si"), size)
                    asm.add_to_code_segment("mov", asm.get_register("ax"), f"{addr_operator} [{asm.get_register("si")}]")
                    asm.add_to_code_segment("mov", "al", f"{target_operator} [{asm.get_register("si")}]")
                    asm.add_to_code_segment("mov", f"{target_operator} [{asm.get_register("si")}]", "al")
                    asm.add_to_code_segment("add", asm.get_register("si"), target_size)
                elif token.verify("operator", lang.PLUS):
                    if len(active_stack["elements"]) < 2:
                        self.raise_exception(line_nb, self.StackEvaluation, "Addition operation need 2 numbers on the stack.")
                    nb_b = active_stack["elements"].pop()
                    nb_a = active_stack["elements"].pop()
                    asm.add_to_code_segment("sub", asm.get_register("si"), nb_b["size"])
                    asm.add_to_code_segment("movzx", asm.get_register("bx"), f"{nb_b['operator']} [{asm.get_register('si')}]")
                    asm.add_to_code_segment("sub", asm.get_register("si"), nb_a["size"])
                    asm.add_to_code_segment("movzx", asm.get_register("cx"), f"{nb_a['operator']} [{asm.get_register('si')}]")
                    asm.add_to_code_segment("add", asm.get_register("bx"), asm.get_register("cx"))
                    if nb_a["size"] >= nb_b["size"]:
                        final_op = nb_a["operator"]
                        final_size = nb_a["size"]
                    else:
                        final_op = nb_b["operator"]
                        final_size = nb_b["size"]
                    asm.add_to_code_segment("mov", f"{final_op} [{asm.get_register('si')}]", "bl")
                    asm.add_to_code_segment("add", asm.get_register('si'), final_size)
                    active_stack["elements"].append({
                        "size": final_size,
                        "type": "integer",
                        "operator": final_op
                    })
                else:
                    self.raise_exception(line_nb, self.StackEvaluation, "Other types not yet supported.")

            stack_token = lang.Token("stack_" + stack_id, "address")
            stack_token.target = {
                "size": stack_size,
                "type": "address",
                "operator": lang.bytes_to_operator(stack_size)
            } # TODO: If the stack is more than 64 bytes
            return stack_token

        for token in tokens:
            if token.verify("delimiter", lang.OPEN_HOOK):
                size = 128
                try: token.stack_size
                except: pass
                else: size = token.stack_size
                if size < 1:
                    self.raise_exception(line_nb, self.StackInitialization, "The stack must have at least 1 byte of size.")
                if not block_started:
                    block_started = True
                    block["parent"] = "first"
                    block["size"] = size
                else:
                    new_block = {"kind": "stack", "parent": active_block, "size": size, "elements": []}
                    active_block["elements"].append(new_block)
                    active_block = new_block
            elif token.verify("delimiter", lang.CLOSED_HOOK):
                if active_block["parent"] is None:
                    self.raise_exception(line_nb, self.BlockDelimitation, "Can't close a non-existant block.")
                active_block = active_block["parent"]
            else:
                if block_started:
                    if active_block is None:
                        self.raise_exception(line_nb, self.BlockDelimitation, "Invalid block structure.")
                    active_block["elements"].append(token)
                else:
                    if token.token_type.lower() in ["integer", "decimal", "boolean"]:
                        rtoken = token
                    elif token.verify_type("name") or token.verify("operator", lang.TILDE):
                        if token.verify("operator", lang.TILDE): token = lang.Token(program["id"], "name")
                        if lang.is_a_upper_name(token.token_string):
                            if not token.token_string in self.memories.keys():
                                self.raise_exception(line_nb, self.Evaluation, f"The identified memory doesn't exists.")
                            asm.add_to_code_segment("mov", asm.register_prefix("ax"), "mem_" + token.token_string)
                            rtoken = lang.Token("%ax", "register")
                        elif lang.is_a_lower_name(token.token_string):
                            mem = self.memories[program["acmem"]]
                            if not token.token_string in mem["elements"].keys():
                                self.raise_exception(line_nb, self.Evaluation, f"The identified element doesn't exists in the memory '{program['acmem']}'")
                            asm.add_to_code_segment("mov", asm.register_prefix("ax"), "mem_" + program["acmem"])
                            asm.add_to_code_segment("add", asm.register_prefix("ax"), int(token.token_string))
                            rtoken = lang.Token("%ax", "register")
                        else:
                            self.raise_exception(line_nb, self.Evaluation, f"Unknown name.")
                    else:
                        self.raise_exception(line_nb, self.Evaluation, f"Wanted a litteral value or a variable, not a '{token.token_type}'.")
        
        if active_block != block and block["parent"] != "first":
            self.raise_exception(line_nb, self.BlockDelimitation, "Unclosed block detected.")
        
        if block_started:
            rtoken = evaluate_stack(block["elements"], block["size"])
        
        return rtoken
    
    def compile(self, segments:list, program:str=None):
        if not program: program = self.main_program
        asm:fasm.Program = program["asm"]
        ended = False
        actual_memory = program["acmem"]
        actual_memory = None

        self.running_programs.append(program)

        # Preprocessor static commands
        for line in segments:
            line_nb = line["line"]
            tokens:list[lang.Token] = line["tokens"]

            if not tokens: continue
            
            if tokens[0].verify("operator", lang.HASHTAG):
                if not len(tokens) >= 2:
                    self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "At least 2 tokens.")
                
                ppcommand = tokens[1]
                if ppcommand.verify("pposcommand", "mem"):
                    if not (lang.format_tokens("%o %pposc %o %i", tokens) or lang.format_tokens("%o %pposc %n %i", tokens)):
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "Wanted 4 valid tokens.")
                    mem_id = tokens[2]
                    
                    if mem_id.verify("operator", lang.TILDE):
                        mem_id = lang.Token(program["id"], "name")
                    elif mem_id.verify_type("name"):
                        if not lang.is_a_upper_name(mem_id.token_string):
                            self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "The memory name must be in uppercase.")
                    else:
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "Invalid memory identifier.")

                    mem_size = tokens[3]

                    if int(mem_size.token_string) < 1:
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "The memory must have at least 1 byte of size.")

                    self.memories[mem_id.token_string] = {
                        "size": int(mem_size.token_string),
                        "elements": {}
                    }
                elif ppcommand.verify("ppcommand", "acmem"):
                    if not (lang.format_tokens("%o %ppc %o", tokens) or lang.format_tokens("%o %ppc %n", tokens)):
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "Wanted 3 valid tokens.")
                    mem_id = tokens[2]

                    if mem_id.verify("operator", lang.TILDE):
                        mem_id = lang.Token(program["id"], "name")
                    elif mem_id.verify_type("name"):
                        if not lang.is_a_upper_name(mem_id.token_string):
                            self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "The memory name must be in uppercase.")
                    else:
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "Invalid memory identifier.")

                    if not mem_id.token_string in self.memories.keys():
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "The identified memory doesn't exists.")
                    
                    actual_memory = mem_id.token_string
                elif ppcommand.verify("ppcommand", "define"):
                    if not lang.format_tokens("%o %ppc %n", tokens, True):
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "At least 3 tokens.")

                    macro_name = tokens[2]
                    if not lang.is_a_upper_name(macro_name.token_string):
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "The macro name must be in uppercase.")

                    if not len(tokens) > 3:
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "Can't define an empty macro.")
                    
                    macro_tokens = tokens[3:]

                    for mtoken in macro_tokens:
                        if mtoken.verify("macro", macro_name.token_string):
                            self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "Cannot call a macro within itself.")

                    self.scopes[program["id"]]["macros"][macro_name.token_string] = macro_tokens
                else:
                    self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "Wanted a valid preprocessor command name.")
        
        for line in segments:
            tokens:list[lang.Token] = line["tokens"]

            if not tokens: continue

            def has_macro_tokens(tokens) -> bool:
                for token in tokens:
                    if token.verify_type("macro"): return True
                return False

            while has_macro_tokens(tokens):
                ctokens = copy.copy(tokens)
                for token_index, token in enumerate(tokens):
                    if token.verify_type("macro"):
                        macro_name = token.token_string.upper()
                        if not macro_name in self.scopes[program["id"]]["macros"].keys():
                            continue  # Can be defined with a dynamic preprocessor command
                        
                        macro_tokens = self.scopes[program["id"]]["macros"][macro_name]
                        ctokens.pop(token_index)
                        for mtoken_index, mtoken in enumerate(macro_tokens):
                            ctokens.insert(token_index + mtoken_index, mtoken)
                        break
                tokens = ctokens
        
        for line_index, line in enumerate(segments):
            line_nb = line["line"]
            tokens:list[lang.Token] = line["tokens"]

            if not tokens: continue
            
            nlines = [[]]

            for token_index, token in enumerate(tokens):
                if token.verify("delimiter", lang.SEMICOLON):
                    if not len(tokens[:token_index]):
                        self.raise_exception(line_nb, self.SemicolonSeparation, "No tokens before the semicolon.")

                    nlines.append([])
                else:
                    nlines[-1].append(token)
            
            while [] in nlines:
                nlines.remove([])
            
            if len(nlines) > 1:
                segments.pop(line_index)
                for nline_index, nline in enumerate(nlines):
                    segments.insert(line_index + nline_index, {
                        "line": line_nb,
                        "tokens": nline
                    })
        
        if actual_memory is None:
            self.raise_exception(len(segments), self.PostCompilingVerification, "Actual memory not defined.")
        
        for line_index, line in enumerate(segments):
            line_nb = line["line"]
            program["line"] = line_nb
            tokens:list[lang.Token] = line["tokens"]
            
            if not tokens: continue

            if tokens[0].verify("delimiter", lang.OPEN_HOOK):
                self.evaluate(tokens)
            elif tokens[0].verify("instruction", "exit"):
                if not (lang.format_tokens("%n %dl", tokens, True) or lang.format_tokens("%n %i", tokens)):
                    self.raise_exception(line_nb, self.ExitInstruction, "Wanted an argument token : integer or address.")
                result_token = self.evaluate(tokens[1:])
                if not (result_token.verify_type("integer") or result_token.verify_type("address")):
                    self.raise_exception(line_nb, self.ExitInstruction, "Wanted an argument token : integer or address.")
                asm.add_to_code_segment("mov", asm.get_register("ax"), 60)
                if result_token.verify_type("address"):
                    asm.add_to_code_segment("mov", asm.get_register("si"), result_token.token_string)
                    asm.add_to_code_segment("movzx", asm.get_register("di"), f"byte [{asm.get_register('si')}]")
                elif result_token.verify_type("integer"):
                    asm.add_to_code_segment("mov", asm.get_register("di"), result_token.token_string)
                asm.add_to_code_segment("syscall")
                ended = True
            elif tokens[0].verify("instruction", "ini"):
                if not (lang.format_tokens("%in %t %n %o", tokens, True) or lang.format_tokens("%in %t %n")):
                    self.raise_exception(line_nb, self.IniInstruction, "Bad tokens.")
                vartype = tokens[1]
                varname = tokens[2]
                if not lang.is_a_lower_name(varname):
                    self.raise_exception(line_nb, self.IniInstruction, "The variable name must be in lowercase.")
                if varname in self.memories[actual_memory]["elements"].keys():
                    self.raise_exception(line_nb, self.IniInstruction, "Variable already initialized.")
                size = lang.TYPES_SIZES[vartype][0]
                token_type = lang.TYPES_SIZES[vartype][1]
                lenght = 1
                try: vartype.lenght
                except: pass
                else: lenght = vartype.lenght
                if lenght < 1:
                    self.raise_exception(line_nb, self.IniInstruction, "The type lenght must be at least 1.")
                used_size = lang.get_memory_used_size(self.memories[actual_memory])
                free_size = self.memories[actual_memory]["size"] - used_size
                if size * lenght < free_size:
                    self.raise_exception(line_nb, self.IniInstruction, "Full memory.")
                self.memories[actual_memory]["elements"][varname] = {
                    "size": size,
                    "lenght": lenght,
                    "token_type": token_type,
                    "type": vartype,
                    "redirect": True
                }
                if len(tokens) > 2:
                    if tokens[3].verify("operator", lang.EQUAL) or (tokens[3].verify("operator", lang.PERCENTAGE) and tokens[3].verify("operator", lang.EQUAL)):
                        if tokens[3].verify("operator", lang.PERCENTAGE) and tokens[3].verify("operator", lang.EQUAL):
                            self.memories[actual_memory]["redirect"] = False
                            tokens.pop(3)
                        value = self.evaluate(tokens[4:])
                        asm.add_to_code_segment("mov", asm.get_register("si"), "mem_" + actual_memory)
                        asm.add_to_code_segment("add", asm.get_register("si"), used_size)
                        if self.memories[actual_memory]["redirect"]:
                            ...
                        else:
                            self.mov_token_to_address(value)
                    elif tokens[3].verify("operator", lang.PERCENTAGE):
                        self.memories[actual_memory]["redirect"] = False
                    else:
                        self.raise_exception(line_nb, self.IniInstruction, "Invalid declaration.")

        for memory_id, memory in self.memories.items():
            memory_size = memory["size"]
            asm.add_to_data_segment("mem_" + memory_id, "rb", memory_size)

        if not ended:
            asm.add_to_code_segment("mov", asm.get_register("ax"), 60)
            asm.add_to_code_segment("mov", asm.get_register("di"), 0)
            asm.add_to_code_segment("syscall")
        
        self.running_programs.pop()
    
    def mov_token_to_address(self, token:lang.Token, operator:str=None, address_redirect:bool=False):
        program = self.running_programs[-1]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]

        if token.verify_type("integer"):
            nb = int(token.token_string)
            if operator is None:
                size = lang.how_much_bytes(nb)
                operator = lang.bytes_to_operator(size)
            asm.add_to_code_segment("mov", f"{operator} [{asm.get_register('si')}]", nb)
        # TODO: Do more token types.
        elif token.verify_type("address"):
            if address_redirect:
                if operator is None:
                    size = 8
                    if asm.architecture == "x86": size = 4
                    operator = "qword" if size == 8 else "dword"
                asm.add_to_code_segment("mov", asm.get_register("si"), token.token_string)
                asm.add_to_code_segment("movzx", asm.get_register("di"), f"byte [{asm.get_register('si')}]")
    
    def generate_assembly(self, filename:str, program:str=None):
        if not program: program = self.main_program
        program["asm"].save_to_file(filename)