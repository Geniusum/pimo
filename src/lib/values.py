import llvmlite as llvm
import llvmlite.ir as ir
import lib.lang as lang
import lib.stack as stack

class LiteralValue():
    class InvalidElementType(BaseException): ...
    class InvalidLiteralValueType(BaseException): ...
    class InvalidOperator(BaseException): ...

    def __init__(self, compiler, token:lang.Token, builder:ir.IRBuilder):
        self.compiler = compiler
        self.token = token
        if lang.is_a_token(self.token): self.token_string = token.token_string
        self.builder = builder
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
            # TODO: Names
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
                    value = LiteralValue(self.compiler, element, self.builder)
                    self.stack.push(value.value)
                elif lang.is_a_token(element) and element.verify_type("operator"):
                    if element.verify(lang.DOT_PERCENTAGE, "operator"):
                        self.stack.push_top_ptr()
                    elif element.verify(lang.DOT_DOT_PERCENTAGE, "operator"):
                        self.stack.push_base_ptr()
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