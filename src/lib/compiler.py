import llvmlite as llvm
import llvmlite.ir as llvm_ir
import llvmlite.binding as llvm_bindings
import lib.logger as logger
import lib.lang as lang
import lib.utils as utils
import lib.program as program
import lib.memory as memory
import lib.stack as stack
import lib.info as info
import random, os, platform

class Compiler():
    class InvalidInstructionSyntax(BaseException): ...
    class EmptySegment(BaseException): ...
    class InvalidInstructionContext(BaseException): ...
    class InvalidInstruction(BaseException): ...

    def __init__(self, pimo_instance):
        self.pimo_instance = pimo_instance
        self.logger:logger.Logger = self.pimo_instance.logger
        self.error_logger:logger.ErrorLogger = self.pimo_instance.error_logger
        self.ids = []
        self.running_programs:list[program.Program] = []
        self.programs:list[program.Program] = [program.Program(pimo_instance.sourcecode_path, pimo_instance.sourcecode, self.generate_id())]
        self.main_program = self.programs[0]
        self.memories:list[memory.Memory] = []
        self.stacks:list[stack.Stack] = []
        self.macros = {}
    
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
        if line is None: line = self.running_programs[-1].line
        prog = self.running_programs[-1].relpath
        self.pimo_instance.raise_exception(exception, f"{prog}:{line}", "\t" + self.running_programs[-1].content.splitlines()[line - 1].strip(), *args)
    
    def get_target_triple(self):
        sys_platform = platform.system().lower()
        arch = platform.architecture()[0]

        if sys_platform == 'linux':
            if arch == '64bit': return 'x86_64-linux-gnu'
            else: return 'i386-linux-gnu'
        elif sys_platform == 'darwin':
            if arch == '64bit': return 'x86_64-apple-darwin'
            else: return 'i386-apple-darwin'
        elif sys_platform == 'windows':
            if arch == '64bit': return 'x86_64-pc-windows-msvc'
            else: return 'i386-pc-windows-msvc'
        else:
            self.error_logger.log(f"Unsupported platform : '{sys_platform}'.", "error")
    
    def check_pp_static_commands(self, segments:list):
        program = self.running_programs[-1]

        for line in segments:
            tokens:list[lang.Token] = line["tokens"]

            if not tokens: continue
            
            if tokens[0].verify("operator", lang.HASHTAG):
                if not len(tokens) >= 2:
                    self.raise_exception(self.InvalidPreprocessorCommand, "At least 2 tokens.")
                
                ppcommand = tokens[1]
                """if ppcommand.verify("pposcommand", "mem"):
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
                        self.raise_exception(self.InvalidPreprocessorCommand, "The identified memory doesn't exists.")"""
                if ppcommand.verify("pposcommand", "define"):
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
                    if macro_name not in self.macros.keys():
                        if pass_not_defined:
                            continue
                        else:
                            self.raise_exception(element.line, self.InvalidMacro, f"Macro '{macro_name}' not defined.")
                    
                    macro_tokens = self.macros[macro_name]
                    updated_blocks.extend(macro_tokens)
                else:
                    updated_blocks.append(element)

            blocks = updated_blocks

        return blocks
    
    def check_instructions(self, blocks:list, inner:any=None):
        program = self.running_programs[-1]
        module:llvm_ir.Module = program.module

        instructions = lang.split_tokens(blocks, "delimiter", lang.SEMICOLON)

        inner_is_block = isinstance(inner, llvm_ir.Block)

        if inner_is_block:
            if not len(utils.remove_empty_on_list_list(instructions)):
                self.raise_exception(self.EmptySegment)
            function:llvm_ir.Function = inner.function

        for instruction_ in instructions:
            tokens:list[lang.Token] = instruction_
            if not tokens: continue

            for token in tokens:
                if isinstance(token, lang.Block): continue
                try: program.set_line(token.line)
                except: continue
                else: break
            
            arguments = lang.split_tokens(tokens[1:], "delimiter", lang.COMMA)
            s_arguments = tokens[1:]
            instruction = tokens[0]

            if instruction.verify("instruction", "func"):
                type_token = lang.pres_token(s_arguments, 0)
                name_token = lang.pres_token(s_arguments, 1)
                args_block = lang.pres_block(s_arguments, 2)
                segment_block = lang.pres_block(s_arguments, 3)
                if not (
                    lang.are_tokens([type_token, name_token]) and
                    lang.verify_tokens_types({
                        type_token: "type",
                        name_token: "name",
                    }) and
                    lang.is_options(args_block) and
                    lang.is_a_segment(segment_block) and
                    len(s_arguments) == 4
                ) and not (
                    lang.are_tokens([type_token, name_token]) and
                    lang.verify_tokens_types({
                        type_token: "type",
                        name_token: "name",
                    }) and
                    lang.is_options(args_block) and
                    len(s_arguments) == 3
                ):
                    self.raise_exception(self.InvalidInstructionSyntax, "Syntax : func <type> <name> (<args>, ...) {<function code>; ...};")
                func_ret_type = lang.get_type_from_token(type_token)
                func_name = name_token.token_string
                args_parts = lang.split_tokens(args_block.elements, "delimiter", lang.COMMA)
                arguments = {}
                for tokens in args_parts:
                    arg_type_token = lang.pres_token(tokens, 0)
                    arg_name_token = lang.pres_token(tokens, 1)
                    if not (
                        lang.are_tokens([arg_type_token, arg_name_token]) and
                        lang.verify_tokens_types({
                            arg_type_token: "type",
                            arg_name_token: "name"
                        }) and
                        len(tokens) == 2
                    ):
                        self.raise_exception(self.InvalidInstructionSyntax, "Arguments syntax : <type> <name>")
                    arguments[arg_name_token] = lang.get_type_from_token(arg_type_token)
                has_segment = lang.is_a_segment(segment_block)
                func_type = llvm_ir.FunctionType(func_ret_type, arguments.values())
                func = llvm_ir.Function(module, func_type, func_name)
                if has_segment:
                    entry = func.append_basic_block("entry")
                    self.check_instructions(segment_block.elements, entry)
            elif instruction.verify("instruction", "return"):
                if not inner_is_block:
                    self.raise_exception(self.InvalidInstructionContext, "Only in functions.")
                if not len(s_arguments):
                    if str(function.function_type.return_type) != "void":
                        self.raise_exception(self.InvalidInstructionContext, "The function don't returns a void value.")
                    builder = llvm_ir.IRBuilder(inner)
                    builder.ret_void()
                    continue
                # TODO: Expression, replace stack
            else:
                self.raise_exception(self.InvalidInstruction)
    
    def compile(self, segments:list[lang.Token], blocks:list[lang.Block], program:program.Program=None):
        if not program: program = self.main_program
        module:llvm_ir.Module = program.module

        module.triple = self.get_target_triple()  # TODO: Changeable

        """di_file = module.add_debug_info("DIFile", {
            "filename": os.path.basename(program.relpath),
            "directory": os.path.dirname(program.relpath),
        })
        di_compile_unit = module.add_debug_info("DICompileUnit", {
            "language": llvm_ir.DIToken("DW_LANG_Pimo"),
            "file": di_file,
            "producer": f"Pimo {info.PIMO_VERSION} by {info.PIMO_PRODUCER}",
            "runtimeVersion": 2,
            "isOptimized": False,
        }, is_distinct=True)"""

        """module.add_metadata("Generated with LLVMLite, from the Pimo compiler.")
        module.add_metadata(f"Pimo {info.PIMO_VERSION} by {info.PIMO_PRODUCER}")
        module.add_metadata(f"https://mazegroup.org/projects/pimo/index.php")"""

        self.running_programs.append(program)

        self.check_pp_static_commands(segments)

        blocks = self.check_macros(blocks, False)

        self.check_instructions(blocks)

        ...  # TODO

    def get_llvm_module(self) -> llvm_ir.Module: return self.running_programs[-1].module