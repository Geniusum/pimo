import lib.fasm as fasm
import lib.logger as logger
import lib.lang as lang
import lib.utils as utils
import lib.memory as memory
import lib.program as program
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
    class WriteInstruction(BaseException): ...
    class IniInstruction(BaseException): ...
    class TokenToAddress(BaseException): ...
    class InstructionReading(BaseException): ...
    class MemoryFinding(BaseException): ...
    class NameFinding(BaseException): ...
    class VariableValueAssignation(BaseException): ...
    
    def __init__(self, pimo_instance):
        self.pimo_instance = pimo_instance
        self.logger:logger.Logger = self.pimo_instance.logger
        self.error_logger:logger.ErrorLogger = self.pimo_instance.error_logger
        self.ids = []
        self.running_programs:list[program.Program] = []
        self.programs:list[program.Program] = [program.Program(pimo_instance.sourcecode, fasm.Program(self), self.generate_id())]
        self.main_program = self.programs[0]
        self.memories:list[memory.Memory] = []
        self.stacks:list[stack.Stack] = []
        self.scopes = {
            self.main_program["id"]: {
                "macros": {}
            } # TODO : Scope class
        }
        self.main_scope = self.scopes[self.main_program["id"]]
    
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
    
    def raise_exception(self, exception:BaseException, *args, line:int=None):
        if line is None: line = self.running_programs[-1]["line"]
        self.pimo_instance.raise_exception(exception, f"Line {line}", *args)

    def add_integer(self, nb:int, size:int=None):
        program = self.running_programs[-1]
        acstack:stack.Stack = program["acstack"]
        asm:fasm.Program = program["asm"]

        if size is None: size = lang.how_much_bytes(nb)
        bytes = lang.int_to_bytes(nb)[:size + 1]
        if not acstack.enough_size(size):
            self.raise_exception(self.StackEvaluation, "Full stack.")
        element = acstack.push(size, "integer")
        for byte in bytes:
            asm.code.add_ins("mov", f"byte [%si]", byte)
            asm.code.add_ins("add", "%si", 1)
    
    def add_decimal(self, nb:float):
        program = self.running_programs[-1]
        acstack:stack.Stack = program["acstack"]
        asm:fasm.Program = program["asm"]

        size = lang.how_much_bytes_decimal(nb)
        bytes = lang.decimal_to_bytes(nb)[:size + 1]
        if not acstack.enough_size(size):
            self.raise_exception(self.StackEvaluation, "Full stack.")
        acstack.push(size, "decimal")
        element = acstack.push(size, "integer")
        for byte in bytes:
            asm.code.add_ins("mov", f"byte [%si]", byte)
            asm.code.add_ins("add", "%si", 1)
    
    def add_boolean(self, bool:int):
        program = self.running_programs[-1]
        acstack:stack.Stack = program["acstack"]
        asm:fasm.Program = program["asm"]

        size = 1
        if not acstack.enough_size(size):
            self.raise_exception(self.StackEvaluation, "Full stack.")
        acstack.push(size, "decimal")
        element = acstack.push(size, "boolean")
        asm.code.add_ins("mov", f"byte [%si]", bool)
        asm.code.add_ins("add", "%si", 1)
    
    def evaluate_stack(self, block:lang.Block) -> lang.Token:
        stack_id = self.generate_id()
        stack_size = 128
        try: block.start_token.stack_size
        except: pass
        else: stack_size = block.start_token.stack_size
        self.stacks.append(stack.Stack(stack_size, stack_id))
        program = self.running_programs[-1]
        program["acstack"] = self.stacks[-1]
        acstack:stack.Stack = program["acstack"]
        asm:fasm.Program = program["asm"]
        asm.code.add_ins("mov", "%si", acstack.with_prefix())
        asm.code.add_comment(f"Started stack '{acstack.with_prefix()}' of size {stack_size}")
        elements = block.elements
        
        for token in elements:
            if lang.is_a_stack(token): token = self.evaluate_stack(token)
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
            elif token.verify("operator", lang.PLUS):
                if len(acstack.elements) < 2:
                    self.raise_exception(self.StackEvaluation, "Addition operation need 2 numbers on the stack.")
                nb_b = acstack.pop()
                nb_a = acstack.pop()
                nb_b_operator = lang.bytes_to_operator(nb_b.size)
                nb_a_operator = lang.bytes_to_operator(nb_a.size) # TODO : Use operators
                rsize = 8
                if asm.architecture == "x86": rsize = 4
                if nb_b.size > rsize or nb_a.size > rsize:
                    self.raise_exception(self.StackEvaluation, "Addition operation can support at maximum numbers of 8 bytes.")
                asm.code.add_comment("Add stack operator")
                asm.code.add_ins("sub", "%si", nb_b.size)
                if nb_b.size < rsize: asm.code.add_ins("movzx", "%bx", f"{nb_b_operator} [%si]")
                else: asm.code.add_ins("mov", "%bx", f"[%si]")
                asm.code.add_ins("sub", "%si", nb_a.size)
                if nb_a.size < rsize: asm.code.add_ins("movzx", "%cx", f"{nb_a_operator} [%si]")
                else: asm.code.add_ins("mov", "%cx", f"[%si]")
                
                asm.code.add_ins("add", "%bx", "%cx")
                
                asm.code.add_ins("mov", f"{lang.bytes_to_operator(rsize)} [%si]", "%bx")
                asm.code.add_ins("add", "%si", rsize)

                acstack.push(rsize, "integer")
                asm.code.add_comment("End add stack operator")
            elif token.verify("operator", lang.PERCENTAGE):
                print(acstack.get_used_positions())
                addr_size = 8
                if asm.architecture == "x86": addr_size = 4
                if not acstack.elements:
                    self.raise_exception(self.StackEvaluation, "Empty stack.")
                addr = acstack.pop()
                if addr.size != addr_size:
                    self.raise_exception(self.StackEvaluation, "Wanted an address.")
                addr_operator = lang.bytes_to_operator(addr_size)
                target_size = 1
                try: token.size
                except: pass
                else: target_size = token.size
                if target_size < 1:
                    self.raise_exception(self.StackEvaluation, "The target size must be at least of 1 byte of size.")
                asm.code.add_ins("sub", "%si", addr_size)
                asm.code.add_ins("mov", "%di", f"{addr_operator} [%si]")
                for i in range(target_size): # TODO: Make a placement operator for alligned allocation, TODO: Make a loop instead
                    asm.code.add_ins("mov", "al", "byte [%di]")
                    asm.code.add_ins("mov", "byte [%si]", "al")
                    asm.code.add_ins("add", "%si", 1)
                    asm.code.add_ins("add", "%di", 1)
                acstack.push(target_size, "integer")
                print(acstack.get_used_positions())
            elif token.verify_type("name") or token.verify("operator", lang.TILDE):
                if token.verify("operator", lang.TILDE):
                    token = lang.Token(self.memories[program["acmem"]].with_prefix(), "name")
                unit = self.get_name(token)
                if isinstance(unit, memory.MemoryElement):
                    element = unit
                    for byte in element.bytes:
                        asm.code.add_ins("mov", "%ax", self.memories[program["acmem"]].with_prefix())
                        if byte.position: asm.code.add_ins("add", "%ax", byte.position)
                        asm.code.add_ins("mov", "al", "byte [%ax]")
                        asm.code.add_ins("mov", "byte [%si]", "al")
                        asm.code.add_ins("add", "%si", 1)
                    acstack.push(element.size, token.token_type)
                elif isinstance(unit, memory.Memory):
                    rsize = 8
                    if asm.architecture == "x86": rsize = 4
                    roperator = lang.bytes_to_operator(rsize)
                    asm.code.add_ins("mov", f"{roperator} [%si]", unit.with_prefix())
                    asm.code.add_ins("add", "%si", rsize)
                    acstack.push(rsize, token.token_type)
            elif token.verify_type("address"):
                rsize = 8
                if asm.architecture == "x86": rsize = 4
                roperator = lang.bytes_to_operator(rsize)
                asm.code.add_ins("mov", f"{roperator} [%si]", token.token_string)
                asm.code.add_ins("add", "%si", rsize)
                acstack.push(rsize, token.token_type)
            elif token.verify_type("string"):
                chars = [*token.token_string]
                for char in chars:
                    if not acstack.enough_size(1):
                        self.raise_exception(self.StackEvaluation, "Full stack.")
                    asm.code.add_ins("mov", "byte [%si]", min(max(0, ord(char)), 255))
                    asm.code.add_ins("add", "%si", 1)
                    acstack.push(1, "string")
            else:
                self.raise_exception(self.StackEvaluation, "Other types not yet supported.")

        stack_token = lang.Token(acstack.with_prefix(), "address")
        stack_token.size = stack_size
        return stack_token
    
    def check_pp_static_commands(self, segments:list):
        program = self.running_programs[-1]

        for line in segments:
            tokens:list[lang.Token] = line["tokens"]

            if not tokens: continue
            
            if tokens[0].verify("operator", lang.HASHTAG):
                if not len(tokens) >= 2:
                    self.raise_exception(self.InvalidPreprocessorCommand, "At least 2 tokens.")
                
                ppcommand = tokens[1]
                if ppcommand.verify("pposcommand", "mem"):
                    if not (lang.format_tokens("%o %pposc %o %i", tokens) or lang.format_tokens("%o %pposc %n %i", tokens)):
                        self.raise_exception(self.InvalidPreprocessorCommand, "Wanted 4 valid tokens.")
                    mem_id = tokens[2]
                    
                    if mem_id.verify("operator", lang.TILDE):
                        mem_id = lang.Token(program["id"], "name")
                    elif mem_id.verify_type("name"):
                        if not lang.is_an_upper_name(mem_id.token_string):
                            self.raise_exception(self.InvalidPreprocessorCommand, "The memory name must be in uppercase.")
                    else:
                        self.raise_exception(self.InvalidPreprocessorCommand, "Invalid memory identifier.")
                    
                    if memory.find_memory_index(self.memories, mem_id.token_string):
                        self.raise_exception(self.InvalidPreprocessorCommand, "Memory already defined.")

                    mem_size = tokens[3]

                    if int(mem_size.token_string) < 1:
                        self.raise_exception(self.InvalidPreprocessorCommand, "The memory must have at least 1 byte of size.")

                    self.memories.append(memory.Memory(int(mem_size.token_string), mem_id.token_string))
                elif ppcommand.verify("ppcommand", "acmem"):
                    if not (lang.format_tokens("%o %ppc %o", tokens) or lang.format_tokens("%o %ppc %n", tokens)):
                        self.raise_exception(self.InvalidPreprocessorCommand, "Wanted 3 valid tokens.")
                    mem_id = tokens[2]

                    if mem_id.verify("operator", lang.TILDE):
                        mem_id = lang.Token(program["id"], "name")
                    elif mem_id.verify_type("name"):
                        if not lang.is_an_upper_name(mem_id.token_string):
                            self.raise_exception(self.InvalidPreprocessorCommand, "The memory name must be in uppercase.")
                    else:
                        self.raise_exception(self.InvalidPreprocessorCommand, "Invalid memory identifier.")

                    program["acmem"] = memory.find_memory_index(self.memories, mem_id.token_string)
                    if program["acmem"] is None:
                        self.raise_exception(self.InvalidPreprocessorCommand, "The identified memory doesn't exists.")
                elif ppcommand.verify("pposcommand", "define"):
                    if not lang.format_tokens("%o %pposc %n", tokens, True):
                        self.raise_exception(self.InvalidPreprocessorCommand, "At least 3 tokens.")

                    macro_name = tokens[2]
                    if not lang.is_an_upper_name(macro_name.token_string):
                        self.raise_exception(self.InvalidPreprocessorCommand, "The macro name must be in uppercase.")

                    if not len(tokens) > 3:
                        self.raise_exception(self.InvalidPreprocessorCommand, "Can't define an empty macro.")
                    
                    macro_tokens = tokens[3:]

                    for mtoken in macro_tokens:
                        if mtoken.verify("macro", macro_name.token_string):
                            self.raise_exception(self.InvalidPreprocessorCommand, "Cannot call a macro within itself.")

                    self.scopes[program["id"]]["macros"][macro_name.token_string] = macro_tokens
                else:
                    self.raise_exception(self.InvalidPreprocessorCommand, "Wanted a valid preprocessor command name.")

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

    def check_instructions(self, blocks:list):
        program = self.running_programs[-1]
        asm:fasm.Program = program["asm"]

        instructions = lang.split_tokens(blocks, "delimiter", lang.SEMICOLON)

        for instruction in instructions:
            tokens:list[lang.Token] = instruction
            if not tokens: continue

            for token in tokens:
                if isinstance(token, lang.Block): continue
                try: program["line"] = token.line
                except: continue
                else: break

            arguments = lang.split_tokens(tokens[1:], "delimiter", lang.COMMA)
            s_arguments = tokens[1:]

            if tokens[0].verify("instruction", "exit"):
                asm.code.add_comment("Exit instruction")
                if not len(arguments) != 2:
                    self.raise_exception(self.ExitInstruction, f"Wanted 1 argument, counted {len(arguments)}.")
                if not (lang.is_a_stack(tokens[1]) or tokens[1].verify_type("integer") or tokens[1].verify_type("name")):
                    self.raise_exception(self.ExitInstruction, "Wanted first argument : integer, variable or stack.")
                exit_code = self.evaluate_stack(tokens[1]) if lang.is_a_stack(tokens[1]) else tokens[1]
                if not (exit_code.verify_type("integer") or exit_code.verify_type("address") or exit_code.verify_type("name")):
                    self.raise_exception(self.ExitInstruction, "Wanted first argument result : integer or address.")
                asm.code.add_ins("mov", "%ax", 60)
                if exit_code.verify_type("address"):
                    asm.code.add_ins("mov", "%si", exit_code.token_string)
                    asm.code.add_ins("movzx", "%di", f"byte [%si]")
                elif exit_code.verify_type("integer"):
                    asm.code.add_ins("mov", "%di", exit_code.token_string)
                elif exit_code.verify_type("name"):
                    varname = exit_code.token_string
                    if lang.is_a_lower_name(varname):
                        if not self.memories[program["acmem"]].name_exists(varname):
                            self.raise_exception(self.ExitInstruction, "Variable not defined.")
                        
                        varelement:memory.MemoryElement = self.memories[program["acmem"]].get_element(varname)
                        if varelement.token_type != "integer":
                            self.raise_exception(self.ExitInstruction, "Wanted an unsigned integer.")
                        if varelement.size != 1:
                            self.raise_exception(self.ExitInstruction, "Exit code are 1 byte unsigned integer.")
                        
                        asm.code.add_ins("xor", "rdi", "rdi")

                        byte = varelement.bytes[0]
                        byte_position = byte.position

                        asm.code.add_ins("mov", "%si", self.memories[program["acmem"]].with_prefix())
                        if byte_position: asm.code.add_ins("add", "%si", byte_position)
                        asm.code.add_ins("mov", "bl", "byte [%si]")
                        asm.code.add_ins("movzx", "%di", "bl")
                    elif lang.is_an_upper_name(varname):
                        self.raise_exception(self.ExitInstruction, "Memory not supported here.")
                    else:
                        self.raise_exception(self.ExitInstruction, "Unknown name.")
                asm.code.add_ins("syscall")
                program["ended"] = True
            elif tokens[0].verify("instruction", "write"):
                asm.code.add_comment("Write instruction")
                if len(s_arguments) != 1:
                    self.raise_exception(self.WriteInstruction, f"Wanted 1 argument, counted {len(s_arguments)}.")
                if lang.is_a_token(tokens[1]) and tokens[1].verify("operator", lang.TILDE):
                    tokens[1] = lang.Token(self.memories[program["acmem"]].id, "name")
                if not (lang.is_a_stack(tokens[1]) or tokens[1].verify_type("integer") or tokens[1].verify_type("name")):
                    self.raise_exception(self.WriteInstruction, "Wanted first argument : memory, variable or stack.")
                to_write = self.evaluate_stack(tokens[1]) if lang.is_a_stack(tokens[1]) else tokens[1]
                if not to_write.token_type in ["name", "address"]:
                    self.raise_exception(self.WriteInstruction, "Wanted first argument : a name or an address.")
                asm.code.add_ins("mov", "%ax", 1)
                asm.code.add_ins("mov", "%di", 1)
                if to_write.verify_type("name"):
                    varelement = self.get_name(to_write)
                    if isinstance(varelement, memory.MemoryElement):
                        asm.code.add_ins("mov", "%si", self.memories[program["acmem"]].with_prefix())  # TODO: Support other memories
                        if varelement.bytes[0].position: asm.code.add_ins("add", "%si", varelement.bytes[0].position)
                        asm.code.add_ins("mov", "%dx", varelement.lenght)
                    elif isinstance(varelement, memory.Memory):
                        asm.code.add_ins("mov", "%si", varelement.with_prefix())
                        asm.code.add_ins("mov", "%dx", varelement.size)
                elif to_write.verify_type("address"):
                    size = 1
                    try: to_write.size
                    except: pass
                    else: size = to_write.size
                    asm.code.add_ins("mov", "%si", to_write.token_string)
                    asm.code.add_ins("mov", "%dx", size)
                asm.code.add_ins("syscall")
            elif tokens[0].verify("instruction", "ini"):
                asm.code.add_comment("Ini instruction")
                if not len(s_arguments) in [2, 3, 4, 5]:
                    self.raise_exception(self.ExitInstruction, f"Wanted 2 to 5 arguments, counted {len(s_arguments)}.")
                
                redirect = True
                value_token = None

                if len(s_arguments) == 2:
                    if not (lang.are_tokens([tokens[1], tokens[2]])) or not (tokens[1].verify_type("type") and tokens[2].verify_type("name")):
                        self.raise_exception(self.IniInstruction, "Wanted a variable type and a variable name.")
                    vartype_token = tokens[1]
                    varname_token = tokens[2]
                elif len(s_arguments) == 3:
                    if not (lang.are_tokens([tokens[1], tokens[2], tokens[3]])) or not (tokens[1].verify_type("type") and tokens[2].verify_type("name") and tokens[3].verify("operator", lang.PERCENTAGE)):
                        self.raise_exception(self.IniInstruction, "Wanted a variable type and a variable name and a percentage operator.")
                    vartype_token = tokens[1]
                    varname_token = tokens[2]
                    redirect = False
                elif len(s_arguments) == 4:
                    if not (lang.are_tokens([tokens[1], tokens[2], tokens[3]])) or not (tokens[1].verify_type("type") and tokens[2].verify_type("name") and tokens[3].verify("operator", lang.EQUAL) and (lang.is_a_stack(tokens[4]) or lang.is_a_token(tokens[4]))):
                        self.raise_exception(self.IniInstruction, "Wanted a variable type and a variable name and a value.")
                    vartype_token = tokens[1]
                    varname_token = tokens[2]
                    value_token = tokens[4]
                elif len(s_arguments) == 5:
                    if not (lang.are_tokens([tokens[1], tokens[2], tokens[3], tokens[4]])) or not (tokens[1].verify_type("type") and tokens[2].verify_type("name") and tokens[3].verify("operator", lang.PERCENTAGE)) and tokens[4].verify("operator", lang.EQUAL) and (lang.is_a_stack(tokens[5]) or lang.is_a_token(tokens[5])):
                        self.raise_exception(self.IniInstruction, "Wanted a variable type and a variable name, a percentage operator and a value.")
                    vartype_token = tokens[1]
                    varname_token = tokens[2]
                    value_token = tokens[5]
                    redirect = False
                
                vartype = vartype_token.token_string
                varname = varname_token.token_string
                if not lang.is_a_lower_name(varname):
                    self.raise_exception(self.IniInstruction, "The variable name must be in lowercase.")
                if self.memories[program["acmem"]].name_exists(varname):
                    self.raise_exception(self.IniInstruction, "Variable already initialized.")
                size = lang.TYPES_SIZES[vartype][0]
                token_type = lang.TYPES_SIZES[vartype][1]
                if vartype == "str" and asm.architecture == "x86": size = 4
                if vartype == "addr" and asm.architecture == "x86": size = 4
                lenght = 1
                try: vartype_token.lenght
                except: pass
                else: lenght = vartype_token.lenght
                if lenght < 1:
                    self.raise_exception(self.IniInstruction, "The type lenght must be at least 1.")
                used_size = len(self.memories[program["acmem"]].get_used_bytes())
                free_size = len(self.memories[program["acmem"]].get_free_bytes())
                if size * lenght > free_size:
                    self.raise_exception(self.IniInstruction, "Full memory.")
                self.memories[program["acmem"]].elements.append(memory.MemoryElement(varname, size, lenght, vartype, token_type, redirect))
                asm.code.add_comment(f"Add to memory '{self.memories[program['acmem']].with_prefix()}' the element '{varname}' of type {vartype}<{lenght}>")
                if not value_token is None:
                    value = self.evaluate_stack(value_token) if lang.is_a_stack(value_token) else value_token
                    if used_size: asm.code.add_ins("add", "%si", used_size)
                    for i in range(size * lenght):
                        self.memories[program["acmem"]].elements[-1].bytes.append(self.memories[program["acmem"]].get_free_bytes()[0])
                    self.mov_token_to_address(value, self.memories[program["acmem"]].elements[-1])
            elif tokens[0].verify_type("name"):
                asm.code.add_comment("Variable value assignation")
                if not len(s_arguments) == 2:
                    self.raise_exception(self.VariableValueAssignation, f"Wanted 2 arguments, counted {len(s_arguments)}.")
                if not tokens[1].verify("operator", lang.EQUAL):
                    self.raise_exception(self.VariableValueAssignation, "Need to have an equal operator.")
                varname = tokens[0]
                varvalue = tokens[2]
                if not (lang.is_a_token(varvalue) or lang.is_a_stack(varvalue)):
                    self.raise_exception(self.VariableValueAssignation, f"Wanted a valid variable value.")
                varelement = self.get_name(varname)
                if not isinstance(varelement, memory.MemoryElement):
                    self.raise_exception(self.VariableValueAssignation, "Not a variable name.")
                varelement.bytes = []
                varmemory = self.memories[program["acmem"]]
                try: varname.memory
                except: pass
                else: varmemory = varname.memory

                value = self.evaluate_stack(varvalue) if lang.is_a_stack(varvalue) else varvalue
                if used_size: asm.code.add_ins("add", "%si", used_size)
                for i in range(size * lenght):
                    varelement.bytes.append(varmemory.get_free_bytes()[0])
                self.mov_token_to_address(value, varelement)
            else: self.raise_exception(self.InstructionReading, "Invalid instruction.")

    def get_memory(self, name:str) -> memory.Memory:
        if not lang.is_an_upper_name(name):
            self.raise_exception(self.MemoryFinding, "Memory name not in upper case.")
        founded = memory.find_memory_index(self.memories, name)
        if founded is None:
            self.raise_exception(self.MemoryFinding, "Memory not defined.")
        return self.memories[founded]

    def get_name(self, name_token:lang.Token) -> memory.Memory|memory.MemoryElement:
        program = self.running_programs[-1]
        if lang.is_a_lower_name(name_token.token_string):
            varname = name_token.token_string
            varmemory = self.memories[program["acmem"]]
            try: name_token.memory
            except: pass
            else: varmemory = name_token.memory
            varmemory = self.get_memory(varmemory.id)
            if not varmemory.name_exists(varname):
                self.raise_exception(self.NameFinding, "Variable not defined.")
            varelement = varmemory.get_element(varname)
            return varelement
        elif lang.is_an_upper_name(name_token.token_string):
            varmemory = memory.find_memory_index(self.memories, name_token.token_string)
            if varmemory is None:
                self.raise_exception(self.NameFinding, "Memory not defined.")
            varmemory = self.memories[varmemory]
            return varmemory
        else:
            self.raise_exception(self.NameFinding, "Unknown name.")

    def compile(self, segments:list[lang.Token], blocks:list[lang.Block], program:str=None):
        if not program: program = self.main_program
        asm:fasm.Program = program["asm"]

        self.running_programs.append(program)

        # Preprocessor static commands
        self.check_pp_static_commands(segments)
        
        # Macros...
        blocks = self.check_macros(blocks, False)
        
        # Semicolon separations
        # segments = self.check_semicolon_separations(segments)
        
        if program["acmem"] is None: self.raise_exception(len(segments), self.PostCompilingVerification, "Actual memory not defined.")
        
        # Instructions
        self.check_instructions(blocks)

        for memory_ in self.memories: # Put memories in the data segment
            memory_id = memory_.id
            memory_size = memory_.size
            asm.data.add_def("mem_" + memory_id, "rb", memory_size)

        for stack_ in self.stacks: # Put stacks in the data segment
            stack_id = stack_.id
            stack_size = stack_.size
            asm.data.add_def("stack_" + stack_id, "rb", stack_size)
            asm.code.add_ins("mov", "%si", stack_.with_prefix())

        if not program["ended"]: # End with exit code 0 if not already done
            asm.code.add_comment("Default exit")
            asm.code.add_ins("mov", "%ax", 60)
            asm.code.add_ins("mov", "%di", 0)
            asm.code.add_ins("syscall")
        
        self.running_programs.pop()
    
    def mov_token_to_address(self, token:lang.Token, var:memory.MemoryElement): # TODO: Change this function name
        program = self.running_programs[-1]
        asm:fasm.Program = program["asm"]
        varbytes = var.bytes
        size = var.size
        address_redirect = var.redirect

        if token.verify_type("integer"):
            nb = int(token.token_string)
            if size is None:
                size = lang.how_much_bytes(nb)
            bytes = lang.int_to_bytes(nb)[:size + 1]
            for byte_index, byte in enumerate(bytes):
                varbyte = varbytes[byte_index]
                varbytepos = varbyte.position
                asm.code.add_ins("mov", "%si", self.memories[program["acmem"]].with_prefix())  # TODO: Change to support other memories
                if varbytepos: asm.code.add_ins("add", "%si", varbytepos)
                asm.code.add_ins("mov", f"byte [%si]", byte)
        elif token.verify_type("string"):
            if var.type == "str":
                chars = [*token.token_string]
                for byte_index, byte in enumerate(varbytes):
                    bytepos = byte.position
                    if not byte_index < len(chars): break
                    asm.code.add_ins("mov", "%si", self.memories[program["acmem"]].with_prefix())  # TODO: Change to support other memories
                    if bytepos: asm.code.add_ins("add", "%si", bytepos)
                    char = chars[byte_index]
                    asm.code.add_ins("mov", f"byte [%si]", min(max(0, ord(char)), 255))
            elif var.type == "chr":
                char = token.token_string
                if len(char) != 1:
                    self.raise_exception(self.TokenToAddress, "Char values must have 1 character of lenght.")
                asm.code.add_ins("mov", "%si", self.memories[program["acmem"]].with_prefix())  # TODO: Change to support other memories
                bytepos = varbytes[0].position
                if bytepos: asm.code.add_ins("add", "%si", bytepos)
                asm.code.add_ins("mov", f"byte [%si]", min(max(0, ord(char)), 255))
        # TODO: Do more token types.
        elif token.verify_type("address"):
            addr_size = 8
            if asm.architecture == "x86": addr_size = 4
            addr_operator = "qword" if addr_size == 8 else "dword"
            if address_redirect:
                if size is None: size = 1
                asm.code.add_ins("mov", f"%ax", token.token_string)
                for i in range(size):
                    varbyte = varbytes[i]
                    varbytepos = varbyte.position
                    asm.code.add_ins("mov", "%si", self.memories[program["acmem"]].with_prefix())  # TODO: Change to support other memories
                    if varbytepos: asm.code.add_ins("add", "%si", varbytepos)
                    asm.code.add_ins("mov", "al", "byte [%ax]")
                    asm.code.add_ins("mov", "byte [%si]", "al")
            else:
                asm.code.add_ins("mov", f"{addr_operator} [%si]", token.token_string)
        else:
            self.raise_exception(self.TokenToAddress, "Invalid token type.")
    
    def generate_assembly(self, filename:str, program:str=None):
        if not program: program = self.main_program
        program["asm"].save_to_file(filename)