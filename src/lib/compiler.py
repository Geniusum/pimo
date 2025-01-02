import lib.fasm as fasm
import lib.logger as logger
import lib.lang as lang
# import lib.utils as utils
import lib.memory as memory
import lib.stack as stack
import random, copy

class Compiler():
    class PostCompilingVerification(BaseException): ...
    class InvalidPreprocessorCommand(BaseException): ...
    class InvalidMacro(BaseException): ...
    class SemicolonSeparation(BaseException): ...
    class BlockDelimitation(BaseException): ...
    class Evaluation(BaseException): ...
    class StackEvaluation(BaseException): ...
    class StackInitialization(BaseException): ...
    class ExitInstruction(BaseException): ...
    class IniInstruction(BaseException): ...
    class TokenToAddress(BaseException): ...
    class InstructionReading(BaseException): ...
    
    def __init__(self, pimo_instance, architecture:str="x64"):
        self.pimo_instance = pimo_instance
        self.logger:logger.Logger = self.pimo_instance.logger
        self.error_logger:logger.ErrorLogger = self.pimo_instance.error_logger
        self.ids = []
        self.programs = [
            {
                "asm": fasm.Program(architecture),
                "id": self.generate_id(),
                "line": None,
                "acmem": None,
                "acstack": None
            } # TODO : Program class
        ]
        self.main_program = self.programs[0]
        self.memories:list[memory.Memory] = []
        self.stacks:list[stack.Stack] = []
        self.scopes = {
            self.main_program["id"]: {
                "macros": {}
            } # TODO : Scope class
        }
        self.main_scope = self.scopes[self.main_program["id"]]
        self.running_programs = []
    
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
    
    def add_integer(self, nb:int, size:int=None):
        program = self.running_programs[-1]
        acstack:stack.Stack = program["acstack"]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]

        if size is None: size = lang.how_much_bytes(nb)
        bytes = lang.int_to_bytes(nb)[:size + 1]
        if not acstack.enough_size(size):
            self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
        element = acstack.push(size, "integer")
        for byte in bytes:
            asm.add_to_code_segment("mov", f"byte [%si]", byte)
            asm.add_to_code_segment("add", "%si", 1)
    
    def add_decimal(self, nb:float):
        program = self.running_programs[-1]
        acstack:stack.Stack = program["acstack"]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]

        size = lang.how_much_bytes_decimal(nb)
        bytes = lang.decimal_to_bytes(nb)[:size + 1]
        if not acstack.enough_size(size):
            self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
        acstack.push(size, "decimal")
        element = acstack.push(size, "integer")
        for byte in bytes:
            asm.add_to_code_segment("mov", f"byte [%si]", byte)
            asm.add_to_code_segment("add", "%si", 1)
    
    def add_boolean(self, bool:int):
        program = self.running_programs[-1]
        acstack:stack.Stack = program["acstack"]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]

        size = 1
        if not acstack.enough_size(size):
            self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
        acstack.push(size, "decimal")
        element = acstack.push(size, "boolean")
        asm.add_to_code_segment("mov", f"byte [%si]", bool)
        asm.add_to_code_segment("add", "%si", 1)
    
    def evaluate_stack(self, elements:list, stack_size:int) -> lang.Token:
        stack_id = self.generate_id()
        self.stacks.append(stack.Stack(stack_size, stack_id))
        program = self.running_programs[-1]
        program["acstack"] = self.stacks[-1]
        acstack:stack.Stack = program["acstack"]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]
        
        for token in elements:
            if isinstance(token, dict): token = self.evaluate_stack(token["elements"], token["size"])
            if not token: continue
            if token.verify_type("integer"):
                nb = int(token.token_string)
                self.add_integer(nb)
            elif token.verify_type("decimal"):
                nb = float(token.token_string)
                self.add_decimal(nb)
            elif token.verify_type("boolean"):
                bool = 0
                if token.token_string.lower() == "true": bool = 1
                self.add_boolean(bool)
                """elif token.verify_type("address"): # TODO: Not do that, because the operator % do that
                    size = 8
                    if asm.architecture == "x86": size = 4
                    if not acstack.enough_size(size):
                        self.raise_exception(line_nb, self.StackEvaluation, "Full stack.")
                    try: token.size
                    except: pass
                    else: size = token.size
                    if not size in [4, 8]:
                        self.raise_exception(line_nb, self.StackEvaluation, "Only x86 and x64 addresses accepted.")
                    operator = "qword" if size == 8 else "dword"
                    token_type = token.token_type
                    element = acstack.push(size, token_type)
                    asm.add_to_code_segment("mov", f"{operator} [{asm.get_register('si')}]", token.token_string)
                    asm.add_to_code_segment("add", asm.get_register("si"), element.size)
                elif token.verify("operator", lang.PERCENTAGE):
                    size = 8
                    if asm.architecture == "x86": size = 4
                    if not acstack["elements"]:
                        self.raise_exception(line_nb, self.StackEvaluation, "Empty stack, wanted an address.")
                    if not acstack["elements"][-1]["size"] != size:
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
                    acstack.pop()
                    acstack.append({
                        "size": target_size,
                        "type": target_type,
                        "operator": target_operator
                    })
                    asm.add_to_code_segment("sub", asm.get_register("si"), size)
                    asm.add_to_code_segment("mov", asm.get_register("ax"), f"{addr_operator} [{asm.get_register('si')}]")
                    asm.add_to_code_segment("mov", "al", f"{target_operator} [{asm.get_register('si')}]")
                    asm.add_to_code_segment("mov", f"{target_operator} [{asm.get_register('si')}]", "al")
                    asm.add_to_code_segment("add", asm.get_register("si"), target_size)"""
            elif token.verify("operator", lang.PLUS):
                if len(acstack["elements"]) < 2:
                    self.raise_exception(line_nb, self.StackEvaluation, "Addition operation need 2 numbers on the stack.")
                nb_b = acstack["elements"].pop()
                nb_a = acstack["elements"].pop()
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
                acstack["elements"].append({
                    "size": final_size,
                    "type": "integer",
                    "operator": final_op
                })
            elif token.verify_type("name") or token.verify("operator", lang.TILDE):
                ... # TODO
            else:
                self.raise_exception(line_nb, self.StackEvaluation, "Other types not yet supported.")

        stack_token = lang.Token("stack_" + stack_id, "address")
        stack_token.target = {
            "size": stack_size,
            "type": "address",
            "operator": lang.bytes_to_operator(stack_size)
        } # TODO: If the stack is more than 64 bytes
        return stack_token
    
    def evaluate(self, tokens:list[lang.Token]) -> lang.Token: # TODO : In this function : new memory structure + new stack structure
        program = self.running_programs[-1]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]
        rtoken:lang.Token = None  # Returned token

        block = {"kind": "stack", "parent": None, "size": 128, "elements": []}
        active_block = block
        block_started = False

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
                        # TODO: Correct this
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
            rtoken = self.evaluate_stack(block["elements"], block["size"])
        
        if rtoken is None:
            self.raise_exception(line_nb, self.Evaluation, "The expression returns nothing.")
        
        return rtoken
    
    def check_pp_static_commands(self, segments:list):
        program = self.running_programs[-1]

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

                    self.memories.append(memory.Memory(int(mem_size.token_string), mem_id.token_string))
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
                    
                    acmem = memory.find_memory_index(self.memories, mem_id.token_string)
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

    def check_macros(self, segments:list, pass_not_defined:bool=True):
        program = self.running_programs[-1]

        for line in segments:
            line_nb = line["line"]
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
                            if pass_not_defined:
                                continue  # Can be defined with a dynamic preprocessor command
                            else:
                                self.raise_exception(line_nb, self.InvalidMacro, "Macro not defined.")
                        
                        macro_tokens = self.scopes[program["id"]]["macros"][macro_name]
                        ctokens.pop(token_index)
                        for mtoken_index, mtoken in enumerate(macro_tokens):
                            ctokens.insert(token_index + mtoken_index, mtoken)
                        break
                tokens = ctokens
        
        return segments

    def check_semicolon_separations(self, segments:list):
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
        return segments

    def check_instructions(self, segments:list):
        program = self.running_programs[-1]
        asm:fasm.Program = program["asm"]
        acmem = program["acmem"]

        for line_index, line in enumerate(segments):
            line_nb = line["line"]
            program["line"] = line_nb
            tokens:list[lang.Token] = line["tokens"]
            
            if not tokens: continue

            if tokens[0].verify("delimiter", lang.OPEN_HOOK):
                self.evaluate(tokens)
            elif tokens[0].verify("instruction", "exit"):
                if not (lang.format_tokens("%in %dl", tokens, True) or lang.format_tokens("%in %i", tokens)):
                    self.raise_exception(line_nb, self.ExitInstruction, "Wanted an argument token : integer or address.")
                result_token = self.evaluate(tokens[1:])
                print(result_token)
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
                if not (lang.format_tokens("%in %t %n %o", tokens, True) or lang.format_tokens("%in %t %n", tokens)):
                    self.raise_exception(line_nb, self.IniInstruction, "Bad tokens.")
                vartype = tokens[1].token_string
                vartype_token = tokens[1]
                varname = tokens[2].token_string
                if not lang.is_a_lower_name(varname):
                    self.raise_exception(line_nb, self.IniInstruction, "The variable name must be in lowercase.")
                if varname in self.memories[acmem]["elements"].keys():
                    self.raise_exception(line_nb, self.IniInstruction, "Variable already initialized.")
                size = lang.TYPES_SIZES[vartype][0]
                token_type = lang.TYPES_SIZES[vartype][1]
                lenght = 1
                try: vartype_token.lenght
                except: pass
                else: lenght = vartype_token.lenght
                if lenght < 1:
                    self.raise_exception(line_nb, self.IniInstruction, "The type lenght must be at least 1.")
                used_size = self.memories[acmem] # TODO
                used_size = lang.get_memory_used_size(self.memories[acmem])
                free_size = self.memories[acmem]["size"] - used_size
                if size * lenght > free_size:
                    self.raise_exception(line_nb, self.IniInstruction, "Full memory.")
                self.memories[acmem]["elements"][varname] = {
                    "size": size,
                    "lenght": lenght,
                    "token_type": token_type,
                    "type": vartype,
                    "redirect": True
                }
                if len(tokens) > 3:
                    if tokens[3].verify("operator", lang.EQUAL) or (tokens[3].verify("operator", lang.PERCENTAGE) and tokens[4].verify("operator", lang.EQUAL)):
                        if tokens[3].verify("operator", lang.PERCENTAGE) and tokens[3].verify("operator", lang.EQUAL):
                            self.memories[acmem]["redirect"] = False
                            tokens.pop(3)
                        value = self.evaluate(tokens[4:])
                        asm.add_to_code_segment("mov", asm.get_register("si"), "mem_" + acmem)
                        if used_size: asm.add_to_code_segment("add", asm.get_register("si"), used_size)
                        self.mov_token_to_address(value, lang.bytes_to_operator(size * lenght), address_redirect=self.memories[acmem]["elements"][varname]["redirect"])
                    elif tokens[3].verify("operator", lang.PERCENTAGE):
                        self.memories[acmem]["elements"][varname]["redirect"] = False
                    else:
                        self.raise_exception(line_nb, self.IniInstruction, "Invalid declaration.")
            elif tokens[0].verify("operator", lang.HASHTAG): ...
            else: self.raise_exception(line_nb, self.InstructionReading, "Invalid instruction.")

    def compile(self, segments:list, program:str=None):
        if not program: program = self.main_program
        asm:fasm.Program = program["asm"]
        ended = False
        acmem = program["acmem"]

        self.running_programs.append(program)

        # Preprocessor static commands
        self.check_pp_static_commands(segments)
        
        # Macros
        self.segments = self.check_macros(segments)
        
        # Semicolon separations
        self.segments = self.check_semicolon_separations(segments)
        
        if acmem is None: self.raise_exception(len(segments), self.PostCompilingVerification, "Actual memory not defined.")
        
        # Instructions
        self.check_instructions()

        for memory_ in self.memories: # Put memories in the data segment
            memory_id = memory_.id
            memory_size = memory_.size
            asm.add_to_data_segment("mem_" + memory_id, "rb", memory_size)

        for stack_ in self.stacks: # Put stacks in the data segment
            stack_id = stack_.id
            stack_size = stack_.size
            asm.add_to_data_segment("stack_" + stack_id, "rb", stack_size)
            asm.add_to_code_segment("mov", asm.get_register("si"), stack_.with_prefix())

        if not ended: # End with exit code 0 if not already done
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
                if operator is None: operator = "byte"
                addr_size = 8
                if asm.architecture == "x86": addr_size = 4
                addr_operator = "qword" if addr_size == 8 else "dword"
                # asm.add_to_code_segment("mov", asm.get_register("ax"), token.token_string)
                asm.add_to_code_segment("mov", f"{addr_operator} [{asm.get_register('si')}]", token.token_string)
                asm.add_to_code_segment("mov", "al", f"{operator} [{asm.get_register('si')}]")
                asm.add_to_code_segment("mov", f"{operator} [{asm.get_register('si')}]", "al")
            else:
                asm.add_to_code_segment("mov", f"{operator} [{asm.get_register('si')}]", token.token_string)
        else:
            self.raise_exception(line_nb, self.TokenToAddress, "Invalid token type.")
    
    def generate_assembly(self, filename:str, program:str=None):
        if not program: program = self.main_program
        program["asm"].save_to_file(filename)