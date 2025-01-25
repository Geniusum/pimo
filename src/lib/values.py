import llvmlite.ir as ir
import lib.lang as lang
import lib.stack as stack
import lib.names as names

class LiteralValue():
    class InvalidElementType(BaseException): ...
    class InvalidLiteralValueType(BaseException): ...
    class InvalidOperator(BaseException): ...
    class InvalidArgumentSyntax(BaseException): ...

    def __init__(self, compiler, token:lang.Token, builder:ir.IRBuilder, scope:names.Name):
        self.compiler = compiler
        self.token = token
        if lang.is_a_token(self.token): self.token_string = token.token_string
        self.builder = builder
        self.scope = scope
        self.size:int
        self.type:ir.Type
        self.value_ptr:ir.Value
        self.value:any
        self.proc()

    def proc(self):
        if lang.is_a_token(self.token):
            if self.token.verify_type("integer"):
                integer = int(self.token_string)
                self.size = lang.how_much_bytes(integer)
                self.type = ir.IntType(self.size * 8)
                try: self.type = self.token.type
                except: pass
                self.value = ir.Constant(self.type, integer)
            elif self.token.verify_type("decimal"):
                decimal = float(self.token_string)
                self.size = lang.how_much_bytes_decimal(decimal)
                self.type = lang.FLOAT_32 if self.size == 4 else lang.FLOAT_64
                try: self.type = self.token.type
                except: pass
                self.value = ir.Constant(self.type, decimal)
            elif self.token.verify_type("boolean"):
                boolean = 1 if self.token_string.lower() == "true" else 0
                self.size = 1
                self.type = lang.BOOLEAN
                try: self.type = self.token.type
                except: pass
                self.value = ir.Constant(self.type, boolean)
            elif self.token.verify_type("string"):
                string = self.token_string
                self.size = len(string)
                self.type = ir.ArrayType(lang.CHAR, self.size)
                try: self.type = self.token.type
                except: pass
                char_constants = [ir.Constant(lang.CHAR, ord(c)) for c in string]
                self.value = ir.Constant(self.type, char_constants)

                self.value_ptr = self.builder.alloca(self.type, name=f"string_{self.compiler.generate_id()}")
                for i, char_value in enumerate(char_constants):
                    ptr = self.builder.gep(self.value_ptr, [ir.Constant(ir.IntType(32), 0), ir.Constant(ir.IntType(32), i)])
                    self.builder.store(char_value, ptr)
                return
            elif self.token.verify_type("name"):
                path = self.token_string
                found:names.Variable = self.scope.get_from_path(path)
                if not isinstance(found, names.Variable):
                    options = None
                    try: options = self.token.options
                    except: pass
                    if isinstance(found, names.Function) and not options is None:
                        arguments = []
                        found:names.Function
                        for element in lang.split_tokens(options.elements, "delimiter", lang.COMMA):
                            if len(element) != 1:
                                self.compiler.raise_exception(self.InvalidArgumentSyntax)
                            element = element[0]
                            if not self.compiler.verify_literal_value_type(element):
                                self.compiler.raise_exception(self.InvalidElementType)
                            arguments.append(LiteralValue(self.compiler, element, self.builder, self.scope).value)
                        self.value = self.builder.call(found.func, arguments)
                        self.type = found.func.function_type.return_type
                    else:
                        self.compiler.raise_exception(self.InvalidElementType, "Need to be a variable or a function with arguments.")
                else:
                    try: self.type = self.token.type
                    except: self.type = found.type
                    self.value = found.get_value(self.builder, self.type)
            else:
                self.compiler.raise_exception(self.InvalidLiteralValueType)
            self.value_ptr = self.builder.alloca(self.type)
            self.builder.store(self.value, self.value_ptr)
        elif lang.is_a_stack(self.token):
            self.size = 128  # Default
            try: self.size = self.token.size
            except: pass
            self.stack = stack.Stack(self.builder, self.size, self.compiler.generate_id())
            for element in self.token.elements:
                if self.compiler.verify_literal_value_type(element):
                    value = LiteralValue(self.compiler, element, self.builder, self.scope)
                    self.stack.push(value.value)
                elif lang.is_a_token(element) and element.verify_type("operator"):
                    if element.verify("operator", lang.DOT_PERCENTAGE):
                        self.stack.push_top_ptr()
                    elif element.verify("operator", lang.DOT_DOT_PERCENTAGE):
                        self.stack.push_base_ptr()
                    elif element.verify("operator", lang.BANG):
                        self.stack.push_size()
                    elif element.verify("operator", lang.PERCENTAGE):
                        self.stack.push(self.stack.pop_val())
                    elif element.verify("operator", "dup"):
                        to_dup = self.stack.pop_val()
                        self.stack.push(to_dup)
                        self.stack.push(to_dup)
                    elif element.verify("operator", lang.STAR):
                        ptr = self.stack.pop()
                        ptr_ptr = self.builder.alloca(ptr.type)
                        self.builder.store(ptr, ptr_ptr)
                        self.stack.push(ptr_ptr)
                    elif element.verify("operator", lang.PLUS):
                        value_b = self.stack.pop_val()
                        value_a = self.stack.pop_val()
                        self.stack.push(self.builder.add(value_a, value_b))
                    else:
                        self.compiler.raise_exception(self.InvalidOperator)
                else:
                    self.compiler.raise_exception(self.InvalidLiteralValueType)
            conv_type = lang.UNSIGNED_8.as_pointer()
            try: conv_type = self.token.type.as_pointer()
            except: pass
            result = self.stack.pop()
            typed_result = self.builder.bitcast(result, conv_type)
            self.value = self.builder.load(typed_result)
        else:
            self.compiler.raise_exception(self.InvalidElementType)