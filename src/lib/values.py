import llvmlite as llvm
import llvmlite.ir as ir
import lib.lang as lang

class LiteralValue():
    def __init__(self, token:lang.Token, builder:ir.IRBuilder):
        self.token = token
        self.token_string = token.token_string
        self.builder = builder
        self.size:int
        self.type:ir.Type
        self.value_ptr:ir.Value
        self.value:any
        self.proc()

    def proc(self):
        if self.token.verify_type("integer"):
            integer = int(self.token_string)
            self.size = lang.how_much_bytes(integer)
            self.type = ir.IntType(self.size * 8)
            self.value = ir.Constant(self.type, integer)
        elif self.token.verify_type("decimal"):
            decimal = float(self.token_string)
            self.size = lang.how_much_bytes_decimal(decimal)
            self.type = lang.FLOAT_32 if self.size == 4 else lang.FLOAT_64
            self.value = ir.Constant(self.type, decimal)
        elif self.token.verify_type("boolean"):
            boolean = 1 if self.token_string.lower() == "true" else 0
            self.size = 1
            self.type = lang.BOOLEAN
            self.value = ir.Constant(self.type, boolean)
        elif self.token.verify_type("string"):
            string = self.token_string
            self.size = 1
            self.type = ir.ArrayType(lang.CHAR, len(string))
            self.value = ir.Constant(self.type, string)
        # TODO: Names
        self.value_ptr = self.builder.alloca(self.type)
        self.builder.store(self.value, self.value_ptr)