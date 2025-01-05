import lib.fasm as fasm
import lib.logger as logger
import lib.lang as lang
import lib.utils as utils
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
                "acstack": None,
                "ended": False
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
        size = 8
        s = ""
        s += random.choice("abcdef")
        for i in range(size - 1):
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
    
    def evaluate_stack(self, block:lang.Block) -> lang.Token:
        stack_id = self.generate_id()
        stack_size = 128
        try: block.start_token.size
        except: pass
        else: stack_size = block.start_token.size
        self.stacks.append(stack.Stack(stack_size, stack_id))
        program = self.running_programs[-1]
        program["acstack"] = self.stacks[-1]
        acstack:stack.Stack = program["acstack"]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]
        asm.add_to_code_segment("mov", "%si", acstack.with_prefix())
        asm.comment_code(f"Started stack '{acstack.with_prefix()}' of size {stack_size}")
        elements = block.elements
        
        for token in elements:
            if isinstance(token, lang.Block): token = self.evaluate_stack(token)
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
                if len(acstack.elements) < 2:
                    self.raise_exception(line_nb, self.StackEvaluation, "Addition operation need 2 numbers on the stack.")
                nb_b = acstack.pop()
                nb_a = acstack.pop()
                nb_b_operator = lang.bytes_to_operator(nb_b.size)
                nb_a_operator = lang.bytes_to_operator(nb_a.size) # TODO : Use operators
                rsize = 8
                if asm.architecture == "x86": rsize = 4
                if nb_b.size > rsize or nb_a.size > rsize:
                    self.raise_exception(line_nb, self.StackEvaluation, "Addition operation can support at maximum numbers of 8 bytes.")
                asm.comment_code("Add stack operator")
                asm.add_to_code_segment("sub", "%si", nb_b.size)
                if nb_b.size < rsize: asm.add_to_code_segment("movzx", "%bx", f"{nb_b_operator} [%si]")
                else: asm.add_to_code_segment("mov", "%bx", f"[%si]")
                asm.add_to_code_segment("sub", "%si", nb_a.size)
                if nb_a.size < rsize: asm.add_to_code_segment("movzx", "%cx", f"{nb_a_operator} [%si]")
                else: asm.add_to_code_segment("mov", "%cx", f"[%si]")

                """asm.add_to_code_segment("mov", "%di", "%bx")
                for byte_index, byte in enumerate(nb_b.bytes):
                    asm.add_to_code_segment("sub", "%si", 1)
                    asm.add_to_code_segment("mov", "al", "byte [%si]")
                    asm.add_to_code_segment("mov", "byte [%di]", "al")
                    asm.add_to_code_segment("add", "%di", 1)"""
                """asm.add_to_code_segment("sub", "%si", len(nb_b.bytes))
                for byte_index, byte in enumerate(nb_b.bytes):
                    if byte_index: asm.add_to_code_segment("mov", "al", f"byte [%si + {byte_index}]")
                    else: asm.add_to_code_segment("mov", "al", "byte [%si]")
                    if byte_index: asm.add_to_code_segment("mov", f"byte [%bx + {byte_index}]", "al")
                    else: asm.add_to_code_segment("mov", f"byte [%bx]", "al")
                for byte_index in reversed(range(rsize - len(nb_b.bytes))):
                    byte_index = rsize - byte_index - 1
                    if byte_index: asm.add_to_code_segment("mov", f"byte [%bx + {byte_index}]", 0)
                    else: asm.add_to_code_segment("mov", f"byte [%bx]", 0)
                asm.add_to_code_segment("sub", "%si", len(nb_a.bytes))"""
                """for byte_index, byte in enumerate(nb_a.bytes):
                    if byte_index: asm.add_to_code_segment("mov", "al", f"byte [%si + {byte_index}]")
                    else: asm.add_to_code_segment("mov", "al", "byte [%si]")
                    if byte_index: asm.add_to_code_segment("mov", f"byte [%cx + {byte_index}]", "al")
                    else: asm.add_to_code_segment("mov", f"byte [%cx]", "al")
                for byte_index in reversed(range(rsize - len(nb_b.bytes))):
                    byte_index = rsize - byte_index - 1
                    if byte_index: asm.add_to_code_segment("mov", f"byte [%cx + {byte_index}]", 0)
                    else: asm.add_to_code_segment("mov", f"byte [%cx]", 0)
                # asm.add_to_code_segment("movzx", "%bx", "byte [%si]")"""
                """asm.add_to_code_segment("mov", "%di", "%cx")
                for byte_index, byte in enumerate(nb_b.bytes):
                    asm.add_to_code_segment("sub", "%si", 1)
                    asm.add_to_code_segment("mov", "al", "byte [%si]")
                    asm.add_to_code_segment("mov", "byte [%di]", "al")
                    asm.add_to_code_segment("add", "%di", 1)"""
                # asm.add_to_code_segment("sub", "%si", len(nb_b.bytes))
                # asm.add_to_code_segment("movzx", "%cx", "byte [%si]")
                
                asm.add_to_code_segment("add", "%bx", "%cx")
                """if nb_a.size >= nb_b.size:  # TODO: Find an other way
                    final_size = nb_a.size
                else:
                    final_size = nb_b.size
                final_operator = lang.bytes_to_operator(final_size)"""
                
                asm.add_to_code_segment("mov", f"{lang.bytes_to_operator(rsize)} [%si]", "%bx")
                asm.add_to_code_segment("add", "%si", rsize)
                
                # asm.add_to_code_segment("mov", "%di", "%bx")
                # for i in range(final_size):
                #     asm.add_to_code_segment("mov", "al", "byte [%di]")
                #     asm.add_to_code_segment("mov", "byte [%si]", "al")
                #     asm.add_to_code_segment("add", "%si", 1)
                """for byte_index in range(final_size):
                    if byte_index: asm.add_to_code_segment("mov", "al", f"byte [%bx + {byte_index}]")
                    else: asm.add_to_code_segment("mov", "al", "byte [%bx]")
                    asm.add_to_code_segment("mov", "byte [%si]", "al")
                    asm.add_to_code_segment("add", "%si", 1)"""
                # asm.add_to_code_segment("mov", "%si", "%bx")  # Need to support other size
                # asm.add_to_code_segment("add", "%si", final_size)  # TODO : Change

                acstack.push(rsize, "integer")
                asm.comment_code("End add stack operator")
            elif token.verify_type("name") or token.verify("operator", lang.TILDE):
                if lang.is_a_lower_name(token.token_string):
                    varname = token.token_string
                    element:memory.MemoryElement = self.memories[program["acmem"]].get_element(varname)
                    if not element:
                        self.raise_exception(line_nb, self.StackEvaluation, "Unknown variable.")
                    for byte in element.bytes:
                        asm.add_to_code_segment("mov", "%ax", self.memories[program["acmem"]].with_prefix())
                        if byte.position: asm.add_to_code_segment("add", "%ax", byte.position)
                        asm.add_to_code_segment("mov", "al", "byte [%ax]")
                        asm.add_to_code_segment("mov", "byte [%si]", "al")
                        asm.add_to_code_segment("add", "%si", 1)
                    acstack.push(element.size, token.token_type)
                elif lang.is_a_upper_name(token.token_string) or token.verify("operator", lang.TILDE):
                    ... # TODO
                else:
                    self.raise_exception(line_nb, self.StackEvaluation, "Unknown name.")
            else:
                self.raise_exception(line_nb, self.StackEvaluation, "Other types not yet supported.")

        stack_token = lang.Token("stack_" + stack_id, "address")
        stack_token.target = {
            "size": stack_size,
            "type": "address"
        } # TODO: If the stack is more than 64 bytes  # TODO: Check if it's util
        return stack_token
    
    # Deprecated, TODO : Delete this
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
                    
                    if memory.find_memory_index(self.memories, mem_id.token_string):
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "Memory already defined.")

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

                    program["acmem"] = memory.find_memory_index(self.memories, mem_id.token_string)
                    if program["acmem"] is None:
                        self.raise_exception(line_nb, self.InvalidPreprocessorCommand, "The identified memory doesn't exists.")
                elif ppcommand.verify("pposcommand", "define"):
                    if not lang.format_tokens("%o %pposc %n", tokens, True):
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

    def check_macros(self, blocks: list, pass_not_defined: bool = True):
        program = self.running_programs[-1]

        def has_macro_tokens(blocks: list) -> bool:
            for element in blocks:
                if isinstance(element, lang.Block):
                    if has_macro_tokens(element.elements): return True
                elif element.verify_type("macro"):
                    return True
            return False

        while has_macro_tokens(blocks):
            updated_blocks = []
            for element in blocks:
                if isinstance(element, lang.Block):
                    element.elements = self.check_macros(element.elements, pass_not_defined)
                    updated_blocks.append(element)
                    continue

                if element.verify_type("macro"):
                    macro_name = element.token_string.upper()
                    if macro_name not in self.scopes[program["id"]]["macros"]:
                        if pass_not_defined:
                            continue
                        else:
                            self.raise_exception(element.line, self.InvalidMacro, f"Macro '{macro_name}' not defined.")
                    
                    macro_tokens = self.scopes[program["id"]]["macros"][macro_name]
                    updated_blocks.extend(macro_tokens)
                else:
                    updated_blocks.append(element)

            blocks = updated_blocks

        return blocks

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

    def check_instructions(self, blocks:list):
        program = self.running_programs[-1]
        asm:fasm.Program = program["asm"]

        instructions = lang.split_tokens(blocks, "delimiter", lang.SEMICOLON)

        for instruction in instructions:
            tokens:list[lang.Token] = instruction
            if not tokens: continue

            for token in tokens:
                if isinstance(token, lang.Block): continue
                try: line_nb = token.line
                except: continue
                else: break
            
            program["line"] = line_nb

            arguments = lang.split_tokens(tokens[1:], "delimiter", lang.COMMA)
            s_arguments = tokens[1:]

            if tokens[0].verify("instruction", "exit"):
                asm.comment_code("Exit instruction")
                if not len(arguments) != 2:
                    self.raise_exception(line_nb, self.ExitInstruction, f"Wanted 1 argument, counted {len(arguments)}.")
                if not (lang.is_a_stack(tokens[1]) or tokens[1].verify_type("integer") or tokens[1].verify_type("name")):
                    self.raise_exception(line_nb, self.ExitInstruction, "Wanted first argument : integer, variable or stack.")
                exit_code = self.evaluate_stack(tokens[1]) if lang.is_a_stack(tokens[1]) else tokens[1]
                if not (exit_code.verify_type("integer") or exit_code.verify_type("address") or exit_code.verify_type("name")):
                    self.raise_exception(line_nb, self.ExitInstruction, "Wanted first argument result : integer or address.")
                asm.add_to_code_segment("mov", asm.get_register("ax"), 60)
                if exit_code.verify_type("address"):
                    asm.add_to_code_segment("mov", asm.get_register("si"), exit_code.token_string)
                    asm.add_to_code_segment("movzx", asm.get_register("di"), f"byte [{asm.get_register('si')}]")
                elif exit_code.verify_type("integer"):
                    asm.add_to_code_segment("mov", asm.get_register("di"), exit_code.token_string)
                elif exit_code.verify_type("name"):
                    varname = exit_code.token_string
                    if lang.is_a_lower_name(varname):
                        if not self.memories[program["acmem"]].name_exists(varname):
                            self.raise_exception(line_nb, self.ExitInstruction, "Variable not defined.")
                        
                        varelement:memory.MemoryElement = self.memories[program["acmem"]].get_element(varname)
                        if varelement.token_type != "integer":
                            self.raise_exception(line_nb, self.ExitInstruction, "Wanted an unsigned integer.")
                        rsize = 8
                        if asm.architecture == "x86": rsize = 4
                        if varelement.size > rsize:
                            self.raise_exception(line_nb, self.ExitInstruction, "Exit code supports at maximum 8 bytes of size.")
                        
                        for byte_index, byte in enumerate(varelement.bytes):
                            byte_position = byte.position

                            asm.add_to_code_segment("mov", "%si", self.memories[program["acmem"]].with_prefix())
                            if byte_position: asm.add_to_code_segment("add", "%si", byte_position)
                            if byte_index:
                                asm.add_to_code_segment("mov", "al", f"byte [%si + {byte_index}]")
                                asm.add_to_code_segment("mov", f"byte [%di + {byte_index}]", "al")
                            else:
                                asm.add_to_code_segment("mov", "al", f"byte [%si]")
                                asm.add_to_code_segment("mov", f"byte [%di]", "al")
                    elif lang.is_a_upper_name(varname):
                        self.raise_exception(line_nb, self.ExitInstruction, "Memory not supported here.")
                    else:
                        self.raise_exception(line_nb, self.ExitInstruction, "Unknown name.")
                asm.add_to_code_segment("syscall")
                program["ended"] = True
            elif tokens[0].verify("instruction", "ini"):
                asm.comment_code("Ini instruction")
                if not len(s_arguments) in [2, 3, 4, 5]:
                    self.raise_exception(line_nb, self.ExitInstruction, f"Wanted 2 to 5 arguments, counted {len(s_arguments)}.")
                
                redirect = True
                value_token = None

                if len(s_arguments) == 2:
                    if not (lang.are_tokens([tokens[1], tokens[2]])) or not (tokens[1].verify_type("type") and tokens[2].verify_type("name")):
                        self.raise_exception(line_nb, self.IniInstruction, "Wanted a variable type and a variable name.")
                    vartype_token = tokens[1]
                    varname_token = tokens[2]
                elif len(s_arguments) == 3:
                    if not (lang.are_tokens([tokens[1], tokens[2], tokens[3]])) or not (tokens[1].verify_type("type") and tokens[2].verify_type("name") and tokens[3].verify("operator", lang.PERCENTAGE)):
                        self.raise_exception(line_nb, self.IniInstruction, "Wanted a variable type and a variable name and a percentage operator.")
                    vartype_token = tokens[1]
                    varname_token = tokens[2]
                    redirect = False
                elif len(s_arguments) == 4:
                    if not (lang.are_tokens([tokens[1], tokens[2], tokens[3]])) or not (tokens[1].verify_type("type") and tokens[2].verify_type("name") and tokens[3].verify("operator", lang.EQUAL) and (lang.is_a_stack(tokens[4]) or lang.is_a_token(tokens[4]))):
                        self.raise_exception(line_nb, self.IniInstruction, "Wanted a variable type and a variable name and a value.")
                    vartype_token = tokens[1]
                    varname_token = tokens[2]
                    value_token = tokens[4]
                elif len(s_arguments) == 5:
                    if not (lang.are_tokens([tokens[1], tokens[2], tokens[3], tokens[4]])) or not (tokens[1].verify_type("type") and tokens[2].verify_type("name") and tokens[3].verify("operator", lang.PERCENTAGE)) and tokens[4].verify("operator", lang.EQUAL) and (lang.is_a_stack(tokens[5]) or lang.is_a_token(tokens[5])):
                        self.raise_exception(line_nb, self.IniInstruction, "Wanted a variable type and a variable name, a percentage operator and a value.")
                    vartype_token = tokens[1]
                    varname_token = tokens[2]
                    value_token = tokens[5]
                    redirect = False
                
                vartype = vartype_token.token_string
                varname = varname_token.token_string
                if not lang.is_a_lower_name(varname):
                    self.raise_exception(line_nb, self.IniInstruction, "The variable name must be in lowercase.")
                if self.memories[program["acmem"]].name_exists(varname):
                    self.raise_exception(line_nb, self.IniInstruction, "Variable already initialized.")
                size = lang.TYPES_SIZES[vartype][0]
                token_type = lang.TYPES_SIZES[vartype][1]
                lenght = 1
                try: vartype_token.lenght
                except: pass
                else: lenght = vartype_token.lenght
                if lenght < 1:
                    self.raise_exception(line_nb, self.IniInstruction, "The type lenght must be at least 1.")
                used_size = len(self.memories[program["acmem"]].get_used_bytes())
                free_size = len(self.memories[program["acmem"]].get_free_bytes())
                if size * lenght > free_size:
                    self.raise_exception(line_nb, self.IniInstruction, "Full memory.")
                self.memories[program["acmem"]].elements.append(memory.MemoryElement(varname, size, lenght, vartype, token_type, redirect))
                asm.comment_code(f"Add to memory '{self.memories[program['acmem']].with_prefix()}' the element '{varname}' of type {vartype}<{lenght}>")
                if not value_token is None:
                    value = self.evaluate_stack(value_token) if lang.is_a_stack(value_token) else value_token
                    asm.add_to_code_segment("mov", "%si", self.memories[program["acmem"]].with_prefix())  # TODO: Flexible allocation
                    if used_size: asm.add_to_code_segment("add", "%si", used_size)
                    self.mov_token_to_address(value, size, address_redirect=self.memories[program["acmem"]].elements[-1].redirect)
                    for i in range(size * lenght):
                        self.memories[program["acmem"]].elements[-1].bytes.append(memory.MemoryByte(used_size + i))
            else: self.raise_exception(line_nb, self.InstructionReading, "Invalid instruction.")

    def compile(self, segments:list[lang.Token], blocks:list[lang.Block], program:str=None):
        if not program: program = self.main_program
        asm:fasm.Program = program["asm"]

        self.running_programs.append(program)

        # Preprocessor static commands
        self.check_pp_static_commands(segments)
        
        # Macros
        blocks = self.check_macros(blocks, False)
        
        # Semicolon separations
        # segments = self.check_semicolon_separations(segments)
        
        if program["acmem"] is None: self.raise_exception(len(segments), self.PostCompilingVerification, "Actual memory not defined.")
        
        # Instructions
        self.check_instructions(blocks)

        for memory_ in self.memories: # Put memories in the data segment
            memory_id = memory_.id
            memory_size = memory_.size
            asm.add_to_data_segment("mem_" + memory_id, "rb", memory_size)

        for stack_ in self.stacks: # Put stacks in the data segment
            stack_id = stack_.id
            stack_size = stack_.size
            asm.add_to_data_segment("stack_" + stack_id, "rb", stack_size)
            asm.add_to_code_segment("mov", "%si", stack_.with_prefix())

        if not program["ended"]: # End with exit code 0 if not already done
            asm.comment_code("Default exit")
            asm.add_to_code_segment("mov", "%ax", 60)
            asm.add_to_code_segment("mov", "%di", 0)
            asm.add_to_code_segment("syscall")
        
        self.running_programs.pop()
    
    def mov_token_to_address(self, token:lang.Token, size:int=None, address_redirect:bool=False):
        program = self.running_programs[-1]
        line_nb = program["line"]
        asm:fasm.Program = program["asm"]

        if token.verify_type("integer"):
            nb = int(token.token_string)
            if size is None:
                size = lang.how_much_bytes(nb)
            bytes = lang.int_to_bytes(nb)[:size + 1]
            for byte in bytes:
                asm.add_to_code_segment("mov", f"byte [%si]", byte)
                asm.add_to_code_segment("add", "%si", 1)
        # TODO: Do more token types.
        elif token.verify_type("address"):
            if address_redirect:
                if size is None: size = 1
                addr_size = 8
                if asm.architecture == "x86": addr_size = 4
                addr_operator = "qword" if addr_size == 8 else "dword"
                asm.add_to_code_segment("mov", f"%ax", token.token_string)
                for i in range(size):
                    asm.add_to_code_segment("mov", "al", "byte [%ax]")
                    asm.add_to_code_segment("mov", "byte [%si]", "al")
                    asm.add_to_code_segment("add", "%si", 1)
            else:
                asm.add_to_code_segment("mov", f"{size} [%si]", token.token_string)
        else:
            self.raise_exception(line_nb, self.TokenToAddress, "Invalid token type.")
    
    def generate_assembly(self, filename:str, program:str=None):
        if not program: program = self.main_program
        program["asm"].save_to_file(filename)