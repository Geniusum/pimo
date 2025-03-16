import llvmlite.ir as ir
import lib.logger as logger
import lib.lang as lang
import lib.utils as utils
import lib.program as program
import lib.stack as stack
import lib.info as info
import lib.values as values
import lib.names as names
import lib.contexts as contexts
import random, os, platform

class Compiler():
    class InvalidInstructionSyntax(BaseException): ...
    class InvalidMacro(BaseException): ...
    class EmptySegment(BaseException): ...
    class InvalidInstructionContext(BaseException): ...
    class InvalidPreprocessorCommand(BaseException): ...
    class InvalidInstruction(BaseException): ...
    class InvalidNameCase(BaseException): ...

    def __init__(self, pimo_instance):
        self.pimo_instance = pimo_instance
        self.logger:logger.Logger = self.pimo_instance.logger
        self.error_logger:logger.ErrorLogger = self.pimo_instance.error_logger
        self.ids = []
        self.running_programs:list[program.Program] = []
        self.programs:list[program.Program] = [program.Program(pimo_instance.sourcecode_path, pimo_instance.sourcecode, self.generate_id())]
        self.main_program = self.programs[0]
        self.macros = {}
        self.scope = names.GlobalScope(self, self.main_program.module)
    
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
            line_nb = line["line"]

            if not tokens: continue

            program.set_line(line_nb)

            for token in tokens:
                if isinstance(token, lang.Block): continue
                try: program.set_line(token.line)
                except: pass
                else: break
            
            if tokens[0].verify("operator", lang.HASHTAG):
                if not len(tokens) >= 2:
                    self.raise_exception(self.InvalidPreprocessorCommand, "At least 2 tokens.")
                
                ppcommand = tokens[1]
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

                    self.scopes[program["id"]]["macros"][macro_name.token_string] = macro_tokens  # TODO: Use new scopes
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
    
    def check_inner_function(self, inner_is_block:bool):
        if not inner_is_block:
            self.raise_exception(self.InvalidInstructionContext, "Not in a function.")

    def check_instructions(self, blocks:list, scope:names.Name, inner:any=None, context:contexts.Context=None):
        program = self.running_programs[-1]
        module:ir.Module = program.module

        instructions = lang.split_tokens(blocks, "delimiter", lang.SEMICOLON)

        inner_is_block = isinstance(inner, ir.Block)

        if inner_is_block:
            if not len(utils.remove_empty_on_list_list(instructions)):
                self.raise_exception(self.EmptySegment)
            function:ir.Function = inner.function
            builder = ir.IRBuilder(inner)

        for instruction_ in instructions:
            tokens:list[lang.Token] = instruction_
            if not tokens: continue

            for token in tokens:
                try: program.set_line(token.line)
                except: continue
                else: break
            
            arguments = lang.split_tokens(tokens[1:], "delimiter", lang.COMMA)
            s_arguments = tokens[1:]
            instruction = tokens[0]

            instoken = lang.is_a_token(instruction)

            if inner_is_block: builder.comment(f"Line {program.line}")

            if instoken and instruction.verify("instruction", "func"):
                type_token = lang.pres_token(s_arguments, 0)
                name_token = lang.pres_token(s_arguments, 1)
                args_block = None
                try: args_block = name_token.options
                except: pass
                segment_block = lang.pres_block(s_arguments, 2)
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
                if not lang.is_a_lower_name(func_name):
                    self.raise_exception(self.InvalidInstructionSyntax, "Function names must be in lowercase.")
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
                func_type = ir.FunctionType(func_ret_type, arguments.values())
                func_class:names.Function = self.scope.append(func_name, names.Function, func_type, genargs=False)
                func:ir.Function = func_class.func
                for argument_index, argument in enumerate(func.args):
                    argument.name = list(arguments.keys())[argument_index].token_string
                if has_segment:
                    func_class.gen_args()
                    try: entry = func.entry_basic_block
                    except: entry = func.append_basic_block("entry")
                    self.check_instructions(segment_block.elements, func_class, entry)
            elif instoken and instruction.verify("instruction", "proc"):
                name_token = lang.pres_token(s_arguments, 0)
                try: args_block = name_token.options
                except: pass
                else:
                    self.raise_exception(self.InvalidInstructionSyntax)
                segment_block = lang.pres_block(s_arguments, 1)
                if not (
                    name_token.verify_type("name") and
                    lang.is_a_segment(segment_block)
                ):
                    self.raise_exception(self.InvalidInstructionSyntax)

                func_type = ir.FunctionType(lang.VOID, [])
                func_name = name_token.token_string
                if not lang.is_a_lower_name(func_name):
                    self.raise_exception(self.InvalidInstructionSyntax, "Function names must be in lowercase.")

                func_class:names.Function = self.scope.append(func_name, names.Function, func_type)
                func:ir.Function = func_class.func
                try: entry = func.entry_basic_block
                except: entry = func.append_basic_block("entry")
                self.check_instructions(segment_block.elements, func_class, entry)
                if not entry.is_terminated:
                    entry_builder = ir.IRBuilder(entry)
                    entry_builder.ret_void()
            elif instoken and instruction.verify("instruction", "return"):
                if not inner_is_block:
                    self.raise_exception(self.InvalidInstructionContext, "Not in a function.")
                if inner.is_terminated:
                    self.raise_exception(self.InvalidInstructionContext, "Block already returned.")
                rtype = inner.function.function_type.return_type
                if len(s_arguments) == 1:
                    value_token = s_arguments[0]
                    if not self.verify_literal_value_type(value_token):
                        self.raise_exception(self.InvalidInstructionSyntax, "Not a valid literal value type.")
                    value = values.LiteralValue(self, value_token, builder, scope, type_context=rtype)
                    builder.ret(value.value)
                elif not len(s_arguments):
                    if rtype == lang.VOID:
                        builder.ret_void()
                    else:
                        builder.ret(ir.Constant(rtype, None))
                    return
                else:
                    self.raise_exception(self.InvalidInstructionSyntax, "Too many arguments.")
            elif instoken and instruction.verify("instruction", "if"):
                if not inner_is_block:
                    self.raise_exception(self.InvalidInstructionContext, "Not in a function.")
                if not len(tokens) >= 3:
                    self.raise_exception(self.InvalidInstructionSyntax)
                state = 0
                ifblocks = {}
                for token in tokens:
                    if state == 0:
                        if not lang.is_a_token(token):
                            self.raise_exception(self.InvalidInstructionSyntax)
                        if not (token.verify("instruction", "if") or token.verify("instruction", "elif") or token.verify("instruction", "else")):
                            self.raise_exception(self.InvalidInstructionSyntax)
                        inst = token.token_string.lower()
                        if inst == "elif":
                            inst = self.generate_id()
                        if inst in list(ifblocks.keys()):
                            self.raise_exception(self.InvalidInstructionSyntax)
                        ifblocks[inst] = {
                            "condition": None,
                            "block": None
                        }
                        state = 2 if inst == "else" else 1
                    elif state == 1:
                        if not self.verify_literal_value_type(token):
                            self.raise_exception(self.InvalidInstructionSyntax)
                        user_condition = values.LiteralValue(self, token, builder, scope)
                        condition = builder.icmp_unsigned("!=", user_condition.value, lang.FALSE)
                        ifblocks[list(ifblocks.keys())[-1]]["condition"] = condition
                        state = 2
                    elif state == 2:
                        if not lang.is_a_segment(token):
                            self.raise_exception(self.InvalidInstructionSyntax)
                        ifblocks[list(ifblocks.keys())[-1]]["block"] = token
                        state = 0
                
                context = contexts.IfContext(builder)

                for inst_index, (inst_name, block_data) in enumerate(ifblocks.items()):
                    condition = block_data["condition"]
                    segment = block_data["block"]
                    
                    next_name = None
                    try: next_name = list(ifblocks.keys())[inst_index + 1]
                    except: pass

                    interm_after = next_name != "else"
                    if not inst_name in ["if", "else"] and next_name is None:
                        interm_after = False

                    if inst_name == "if":
                        inner = self.check_instructions(segment.elements, scope, context.if_block)
                        builder = ir.IRBuilder(inner)
                        context.make_if(condition, builder, interm_after=interm_after)
                    elif inst_name == "else":
                        inner = self.check_instructions(segment.elements, scope, context.else_block)
                        builder = ir.IRBuilder(inner)
                        context.make_else(builder)
                    else:
                        elif_block = context.get_active_elif_block()
                        inner = self.check_instructions(segment.elements, scope, elif_block)
                        context.make_elif(condition, builder, interm_after=interm_after)
                
                inner = context.final_block
                builder = ir.IRBuilder(inner)
                context.position_at_final()
            elif instoken and instruction.verify("instruction", "while"):
                if not inner_is_block:
                    self.raise_exception(self.InvalidInstructionContext, "Not in a function.")
                if not len(s_arguments) == 2:
                    self.raise_exception(self.InvalidInstructionSyntax)
                cond_token = s_arguments[0]
                segment_token = s_arguments[1]
                if not (
                    self.verify_literal_value_type(cond_token) and
                    lang.is_a_segment(segment_token)
                ):
                    self.raise_exception(self.InvalidInstructionSyntax)

                context = contexts.WhileContext(builder)

                inner = self.check_instructions(segment_token.elements, scope, context.while_block)

                cond_value_1 = values.LiteralValue(self, cond_token, builder, scope)
                cond_value_2 = values.LiteralValue(self, cond_token, context.while_builder, scope)
                builder = ir.IRBuilder(inner)
                context.make_while(cond_value_1, cond_value_2, builder)

                inner = context.final_block
                builder = ir.IRBuilder(inner)
                context.position_at_final()
            elif instoken and (instruction.verify("instruction", "elif") or instruction.verify("instruction", "else")):
                self.raise_exception(self.InvalidInstructionSyntax, "If instruction needed.")
            elif instoken and (instruction.verify_type("type") or instruction.verify_type("name")):
                self.check_inner_function(inner_is_block)
                if instruction.verify_type("type") or isinstance(scope.get_from_path(instruction.token_string, error=False), names.Structure):
                    d_arguments = lang.split_tokens(tokens, "operator", lang.EQUAL)
                    vartype_token = lang.pres_token(d_arguments[0], 0)
                    varname_token = lang.pres_token(d_arguments[0], 1)
                    varvalue_token = None
                    if len(d_arguments) == 2:
                        if len(d_arguments[1]) > 1:
                            self.raise_exception(self.InvalidInstructionSyntax)
                        varvalue_token = lang.pres_token(d_arguments[1], 0)
                        if not self.verify_literal_value_type(varvalue_token):
                            self.raise_exception(self.InvalidInstructionSyntax)
                    elif len(d_arguments) > 2:
                        self.raise_exception(self.InvalidInstructionSyntax)
                    if not (
                        lang.are_tokens([vartype_token, varname_token]) and
                        varname_token.verify_type("name")
                    ):
                        self.raise_exception(self.InvalidInstructionSyntax)
                    varname = varname_token.token_string
                    if not lang.is_a_lower_name(varname):
                        self.raise_exception(self.InvalidNameCase, "Variable names must be in lowercase.")
                    vartype = values.TypeValue(self, vartype_token, builder, scope).type
                    varvalue = None
                    if not varvalue_token is None:
                        varvalue = values.LiteralValue(self, varvalue_token, builder, scope, type_context=vartype).value
                        varvalue_ptr = builder.alloca(vartype)
                        builder.store(varvalue, varvalue_ptr)
                    var:names.Variable = scope.append(varname, names.Variable, vartype)
                    if len(d_arguments) == 2: var.assign_value(builder, varvalue_ptr)
                    # TODO : Structure definition at declaration
                elif instruction.verify_type("name") and isinstance(scope.get_from_path(instruction.token_string, error=False), names.Function):
                    self.check_inner_function(inner_is_block)
                    if len(s_arguments):
                        self.raise_exception(self.InvalidInstructionSyntax, "Too many arguments.")
                    value = values.LiteralValue(self, instruction, builder, scope)
                else:
                    self.check_inner_function(inner_is_block)
                    d_arguments = lang.split_tokens(tokens, "operator", lang.EQUAL)
                    if not len(d_arguments) == 2:
                        self.raise_exception(self.InvalidInstructionSyntax)
                    if not len(d_arguments[0]) == 1:
                        self.raise_exception(self.InvalidInstructionSyntax)
                    if not len(d_arguments[1]) == 1:
                        self.raise_exception(self.InvalidInstructionSyntax)
                    varname_token = lang.pres_token(d_arguments[0], 0)
                    varvalue_token = lang.pres_token(d_arguments[1], 0)
                    if not self.verify_literal_value_type(varvalue_token):
                        self.raise_exception(self.InvalidInstructionSyntax)
                    varname = varname_token.token_string
                    found = scope.get_from_path(varname)
                    if not isinstance(found, names.Variable):
                        self.raise_exception(self.InvalidInstructionSyntax, "Need to be a variable.")
                    found:names.Variable
                    vartype = found.type
                    varvalue = values.LiteralValue(self, varvalue_token, builder, scope, type_context=vartype).value
                    varvalue_ptr = builder.alloca(vartype)
                    builder.store(varvalue, varvalue_ptr)
                    found.assign_value(builder, varvalue_ptr)
            elif instoken and instruction.verify("instruction", "ops"):
                self.check_inner_function(inner_is_block)
                if not len(arguments):
                    self.raise_exception(self.InvalidInstructionSyntax, "Need operations.")
                operations = arguments[0]
                for operation in operations:
                    if not lang.is_options(operation):
                        self.raise_exception(self.InvalidInstructionSyntax)
                    operation = operation.elements
                    if not len(operation) >= 2:
                        self.raise_exception(self.InvalidInstructionSyntax)
                    operator = operation[0]
                    if not (lang.is_a_token(operator) and (
                            operator.verify_type("operator") or
                            operator.verify_type("name")
                        )):
                        self.raise_exception(self.InvalidInstructionSyntax)
                    values_tokens = operation[1:]
                    for value in values_tokens:
                        if not self.verify_literal_value_type(value):
                            self.raise_exception(self.InvalidInstructionSyntax)
                    dest_value_token = values_tokens[0]
                    if not (lang.is_a_token(dest_value_token) and dest_value_token.verify_type("name")):
                        self.raise_exception(self.InvalidInstructionSyntax)
                    dest_name:names.Variable = scope.get_from_path(dest_value_token.token_string)
                    if not isinstance(dest_name, names.Variable):
                        self.raise_exception(self.InvalidInstructionSyntax)
                    values_ = []
                    for value_token in values_tokens:
                        values_.append(values.LiteralValue(self, value_token, builder, scope, dest_name.type).value)
                    for value in values_:
                        final_value:ir.Value
                        
                        dest_value = values.LiteralValue(self, dest_value_token, builder, scope).value

                        if operator.verify("name", "add"):
                            final_value = builder.add(dest_value, value)
                        elif operator.verify("name", "sub"):
                            final_value = builder.sub(dest_value, value)
                        else:
                            self.raise_exception(self.InvalidInstructionSyntax)

                        final_value_ptr = builder.alloca(dest_name.type)
                        builder.store(final_value, final_value_ptr)
                            
                        dest_name.assign_value(builder, final_value_ptr)
            elif self.verify_literal_value_type(instruction):
                self.check_inner_function(inner_is_block)
                if len(s_arguments):
                    self.raise_exception(self.InvalidInstructionSyntax, "Too many arguments.")
                value = values.LiteralValue(self, instruction, builder, scope)
            else:
                self.raise_exception(self.InvalidInstruction)
        
        return inner
    
    def compile(self, segments:list[lang.Token], blocks:list[lang.Block], program:program.Program=None):
        if not program: program = self.main_program
        module:ir.Module = program.module

        module.triple = self.get_target_triple()  # TODO: Changeable

        """di_file = module.add_debug_info("DIFile", {
            "filename": os.path.basename(program.relpath),
            "directory": os.path.dirname(program.relpath),
        })
        di_compile_unit = module.add_debug_info("DICompileUnit", {
            "language": ir.DIToken("DW_LANG_Pimo"),
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

        self.check_instructions(blocks, self.scope)

        ...  # TODO
    
    def verify_literal_value_type(self, token:lang.Token):
        return lang.is_a_stack(token) or lang.is_a_segment(token) or (lang.is_a_token(token) and token.token_type.lower() in lang.LITERAL_TOKEN_TYPES)

    def get_llvm_module(self) -> ir.Module: return self.running_programs[-1].module