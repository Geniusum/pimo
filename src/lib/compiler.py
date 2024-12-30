import lib.fasm as fasm
import lib.logger as logger
import lib.lang as lang
import lib.utils as utils
import random, copy

class Compiler():
    class InvalidPreprocessorCommand(BaseException): ...
    class SemicolonSeparation(BaseException): ...
    class BlockDelimitation(BaseException): ...
    class Evaluation(BaseException): ...
    class StackEvaluation(BaseException): ...

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
    
    def generate_id(self) -> str:
        s = ""
        s += random.choice("abcdef")
        for i in range(23):
            s += random.choice(lang.HEX_DIGITS)
        return s.upper()
    
    def raise_exception(self, line:int, exception:BaseException, *args):
        self.pimo_instance.raise_exception(exception, f"Line {line}", *args)
    
    def evaluate(self, tokens:list[lang.Token]) -> lang.Token:
        program = self.running_programs[-1]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]
        rtoken:lang.Token
        scope = self.scopes[program["id"]]

        block = {"kind": "stack", "parent": None, "elements": []}
        active_block = block
        block_started = False
        
        def evaluate_stack(stack:list) -> lang.Token:
            stack_id = self.generate_id()
            self.stacks[stack_id] = {
                "size": 128,
                "elements": []
            }
            asm.add_to_data_segment("stack_" + stack_id, "rb", self.stacks[stack_id]["size"])
            for token in stack:
                used_size = lang.get_stack_used_size(self.stacks[stack_id])
                free_size = self.stacks[stack_id]["size"] - used_size
                if isinstance(token, dict): token = evaluate_stack(token["elements"])
                if not token: continue
                if token.verify_type("integer"):
                    nb = int(token.token_string)
                    size = lang.how_much_bytes(nb)
                    if size == 1: operator = "byte"; size_ = 1
                    elif size == 2: operator = "word"; size_ = 2
                    elif size <= 4: operator = "dword"; size_ = 4
                    elif size <= 6: operator = "fword"; size_ = 6
                    elif size <= 8: operator = "qword"; size_ = 8
                    elif size <= 10: operator = "tword"; size_ = 10
                    elif size <= 16: operator = "dqword"; size_ = 16
                    elif size <= 32: operator = "qqword"; size_ = 32
                    elif size_ <= 64: operator = "dqqword"; size_ = 64
                    else: self.raise_exception(line_nb, self.StackEvaluation, "To big integer.")
                    if free_size < size_:
                        self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                    self.stacks[stack_id]["elements"].append({
                        "size": size,
                        "type": token.token_type
                    })
                    asm.add_to_code_segment("mov", asm.get_register("ax"), "stack_" + stack_id)
                    if used_size: asm.add_to_code_segment("add", asm.get_register("ax"), used_size)
                    asm.add_to_code_segment("mov", f"{operator} [{asm.get_register('ax')}]", nb)
                elif token.verify_type("decimal"):
                    nb = float(token.token_string)
                    size = lang.how_much_bytes_decimal(nb)
                    if free_size < size:
                        self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                    if size == 4: operator = "dd"
                    else: operator = "dq"
                    data_id = self.generate_id()
                    self.stacks["elements"].append({
                        "size": size,
                        "type": token.token_type,
                        "data": data_id
                    })
                    asm.add_to_data_segment("data_" + data_id, operator, nb)
                    asm.add_to_code_segment("lea", asm.get_register("si"), f"[data_{data_id}]")
                    asm.add_to_code_segment("lea", asm.get_register("di"), f"[stack_{stack_id}]")
                    asm.add_to_code_segment("mov", asm.get_register("ax"), size)
                    asm.add_to_code_segment("rep", "movsb")
                elif token.verify_type("boolean"):
                    bool = 0
                    if token.token_string.lower() == "true": bool = 1
                    size = 1
                    if free_size < size:
                        self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                    self.stacks["elements"].append({
                        "size": size,
                        "type": token.token_type
                    })
                    asm.add_to_code_segment("mov", asm.get_register("ax"), "stack_" + stack_id)
                    if used_size: asm.add_to_code_segment("add", asm.get_register("ax"), used_size)
                    asm.add_to_code_segment("mov", f"byte [{asm.get_register('ax')}]", bool)
                else:
                    self.raise_exception(line_nb, self.StackEvaluation, "Other types not yet supported.")

        for token in tokens:
            if token.verify("delimiter", lang.OPEN_HOOK):
                if not block_started: block_started = True
                new_block = {"kind": "stack", "parent": active_block, "elements": []}
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
        
        if active_block != block:
            self.raise_exception(line_nb, self.BlockDelimitation, "Unclosed block detected.")
        
        if block_started:
            evaluate_stack(block["elements"])
        
        # return rtoken
    
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
            tokens = line["tokens"]

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
            tokens:list = line["tokens"]

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
            tokens:list = line["tokens"]

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
        
        for line_index, line in enumerate(segments):
            line_nb = line["line"]
            program["line"] = line_nb
            tokens:list = line["tokens"]
            
            if not tokens: continue

            if tokens[0].verify("delimiter", lang.OPEN_HOOK):
                self.evaluate(tokens)

        for memory_id, memory in self.memories.items():
            memory_size = memory["size"]
            asm.add_to_data_segment("mem_" + memory_id, "rb", memory_size)

        if not ended:
            asm.add_to_code_segment("mov", asm.get_register("ax"), 60)
            asm.add_to_code_segment("mov", asm.get_register("di"), 0)
            asm.add_to_code_segment("syscall")
        
        self.running_programs.pop()
    
    def generate_assembly(self, filename:str, program:str=None):
        if not program: program = self.main_program
        program["asm"].save_to_file(filename)