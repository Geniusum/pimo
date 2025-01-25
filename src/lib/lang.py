import llvmlite as llvm
import llvmlite.ir as ir
import lib.utils as utils
from lib.enum import *
import struct

#########################
#  LEXICAL DEFINITIONS  #
#########################

# One char
HASHTAG = '#'
TILDE = "~"
DASH = "-"
UNDERSCORE = "_"
DOT = "."
AMPERSAND = "&"
SPACE = " "
OPEN_HOOK = "["
CLOSE_HOOK = "]"
OPEN_CURLY_BRACE = "{"
CLOSE_CURLY_BRACE = "}"
OPEN_BRACKET = "("
CLOSE_BRACKET = ")"
LESS_THAN = "<"
GREATER_THAN = ">"
PARAGRAPH = "§"
SEMICOLON = ";"
COMMA = ","
PERCENTAGE = "%"
COLON = ":"
EQUAL = "="
PLUS = "+"
CARET = "^"
BANG = "!"
STAR = "*"

# Two chars
DOUBLE_HASHTAG = "##"
DOUBLE_SLASH = "//"
SLASH_STAR = "/*"
STAR_SLASH = "*/"
DOUBLE_COLON = "::"
DOT_PERCENTAGE = ".%"

# Three chars
DOT_DOT_PERCENTAGE = "..%"

# Operators
OPERATORS = [
             HASHTAG, DOUBLE_HASHTAG, TILDE, COLON, PERCENTAGE, EQUAL, CARET, DOT,
             PLUS, DOT_PERCENTAGE, DOT_DOT_PERCENTAGE, BANG, PERCENTAGE, "dup", STAR  # Stack operators
            ]

# Delimiters
DELIMITERS = [SEMICOLON, COMMA, OPEN_HOOK, CLOSE_HOOK, OPEN_CURLY_BRACE, CLOSE_CURLY_BRACE, OPEN_BRACKET, CLOSE_BRACKET]

# Registers
REGISTERS = ["ax", "bx", "cx", "dx", "si", "di", "bp", "sp"]

# Instructions
INSTRUCTIONS = ["func", "return"]

# Types
UNSIGNED_8 = ir.IntType(8)
UNSIGNED_16 = ir.IntType(16)
UNSIGNED_24 = ir.IntType(24)
UNSIGNED_32 = ir.IntType(32)
UNSIGNED_64 = ir.IntType(64)
UNSIGNED_128 = ir.IntType(128)
UNSIGNED_256 = ir.IntType(256)
FLOAT_32 = ir.FloatType()
FLOAT_64 = ir.DoubleType()
CHAR = ir.IntType(8)
BOOLEAN = ir.IntType(1)
VOID = ir.VoidType()
VOID_PTR = ir.IntType(8).as_pointer()
NULL_PTR = ir.Constant(VOID_PTR, None)

TYPES_WITH_LLTYPES = {
    "u8": UNSIGNED_8,
    "u16": UNSIGNED_16,
    "u24": UNSIGNED_24,
    "u32": UNSIGNED_32,
    "u64": UNSIGNED_64,
    "u128": UNSIGNED_128,
    "u256": UNSIGNED_256,
    "f32": FLOAT_32,
    "f64": FLOAT_64,
    "chr": CHAR,
    "bool": BOOLEAN,
    "void": VOID,
    # Aliases :
    "int": UNSIGNED_32,
    "dec": FLOAT_64,
    "byte": UNSIGNED_8
}

TYPES = list(TYPES_WITH_LLTYPES.keys())

# Alphabet
AL_LETTERS = "abcdefghijklmnopqrstuvwxyz"
AL_LETTERS_UPPER = AL_LETTERS.upper()

# Digits
DIGITS = "0123456789"
DECIMAL_CHARS = DIGITS + DOT
HEX_DIGITS = "0123456789abcdef"

# Name chars
NM_CHARS = AL_LETTERS + AL_LETTERS_UPPER + DIGITS + UNDERSCORE

PPCommands = { # Pre-processor commands
    "define", "mem", "acmem"
}
PPOSCommands = { # Pre-processor only static commands
    "mem", "define"
}
L_PPCommands = list(PPCommands)
L_PPOSCommands = list(PPOSCommands)

DefaultTokens = {
    "unknown", "name"
}
L_DefaultTokens = list(DefaultTokens)

LITERAL_TOKEN_TYPES = ["integer", "decimal", "boolean", "string", "name"]


#####################
#  GRAMMAR METHODS  #
#####################

def is_a_valid_name(presumed_name: str):
    if not presumed_name or presumed_name[0] in DIGITS:
        return False
    return all(char in NM_CHARS for char in presumed_name)

def is_an_upper_name(presumed_upper_name:str): return presumed_upper_name == presumed_upper_name.upper()

def is_a_lower_name(presumed_lower_name:str): return presumed_lower_name == presumed_lower_name.lower()

def is_an_integer(presumed_integer:str):
    if not len(presumed_integer): return False
    for char in presumed_integer:
        if not char in DIGITS: return False
    return True

def is_a_decimal(presumed_decimal:str):
    if not len(presumed_decimal): return False
    parts = presumed_decimal.split(DOT)
    if not len(parts) == 2: return False
    for part in parts:
        if not is_an_integer(part): return False
    return True

def is_a_boolean(presumed_boolean:str):
    if presumed_boolean.lower() in ["true", "false"]: return True
    return False

def is_an_operator(presumed_operator:str):
    if presumed_operator.lower() in OPERATORS: return True
    return False

def is_a_delimiter(presumed_delimiter:str):
    if presumed_delimiter.lower() in DELIMITERS: return True
    return False

def is_a_register(presumed_register:str):
    if presumed_register in REGISTERS: return True
    return False

def is_an_instruction(presumed_instruction:str):
    if presumed_instruction.lower() in INSTRUCTIONS: return True
    return False

def is_a_type(presumed_type:str):
    if presumed_type in TYPES: return True
    return False


#############
#  CLASSES  #
#############

class Token():
    def __init__(self, token_string: str, token_type: str = None):
        self.token_string = token_string
        self.token_type = token_type or self.get_type()

    def get_type(self):
        if self.token_string.lower() in PPCommands:
            if self.token_string.lower() in PPOSCommands:
                return "pposcommand"
            return "ppcommand"
        if is_a_boolean(self.token_string):
            return "boolean"
        if is_an_integer(self.token_string):
            return "integer"
        if is_a_decimal(self.token_string):
            return "decimal"
        if is_a_delimiter(self.token_string):
            return "delimiter"
        if is_an_operator(self.token_string):
            return "operator"
        if is_an_instruction(self.token_string):
            return "instruction"
        if is_a_register(self.token_string):
            return "register"
        if is_a_type(self.token_string):
            return "type"
        if is_a_valid_name(self.token_string):
            return "name"
        
        return "unknown"

    def __str__(self):
        return f"Token: '{self.token_string}', {self.token_type}"

    def verify(self, presumed_type:str, presumed_string:str):
        return self.verify_type(presumed_type) and presumed_string.lower() == self.token_string.lower()

    def verify_type(self, presumed_type:str):
        return presumed_type.lower() == self.token_type.lower()

class Block():
    def __init__(self, kind:str, parent:any=None, start_token:Token=None):
        self.kind = kind
        self.parent:Block = parent
        self.start_token:Token = start_token
        self.elements:list[Token, Block] = []
    
    def __str__(self):
        return f"Block: of kind '{self.kind}' from [{self.start_token}] with :\n{utils.dump(self.elements)}"

###################
#  OTHER METHODS  #
###################

def format_tokens(sf:str, tokens:list[Token], overload:bool=False) -> bool:
    ftypes = []
    for format in sf.split():
        if format == "%ppc": ftypes.append("ppcommand")
        elif format == "%pposc": ftypes.append("pposcommand")
        elif format == "%b": ftypes.append("boolean")
        elif format == "%n": ftypes.append("name")
        elif format == "%i": ftypes.append("integer")
        elif format == "%d": ftypes.append("decimal")
        elif format == "%o": ftypes.append("operator")
        elif format == "%dl": ftypes.append("delimiter")
        elif format == "%a": ftypes.append("address")
        elif format == "%in": ftypes.append("instruction")
        elif format == "%t": ftypes.append("type")
    
    if not overload:
        if len(tokens) != len(ftypes): return False
    else:
        if len(tokens) < len(ftypes): return False
    
    for i, type in enumerate(ftypes):
        token = tokens[i]
        if not token.token_type == type: return False
    
    return True

def how_much_bytes(nb: int) -> int:    
    num_bits = nb.bit_length()
    num_bytes = (num_bits + 7) // 8
    return max(1, num_bytes)

def how_much_bytes_decimal(nb: float) -> int:
    try:
        struct.pack('f', nb)
        return 4
    except OverflowError: return 8

def int_to_bytes(nb: int) -> list[int]:
    num_bytes = how_much_bytes(nb)
    byte_array = nb.to_bytes(num_bytes, byteorder='big', signed=True)
    return list(byte_array)

def decimal_to_bytes(nb: float) -> list[int]:
    num_bytes = how_much_bytes_decimal(nb)
    if num_bytes == 4: byte_array = struct.pack('f', nb)
    else: byte_array = struct.pack('d', nb)
    return list(byte_array)

def bytes_to_operator(size:int):
    if size == 1: operator = "byte"
    elif size == 2: operator = "word"
    elif size <= 4: operator = "dword"
    elif size <= 6: operator = "fword"
    elif size <= 8: operator = "qword"
    elif size <= 10: operator = "tword"
    elif size <= 16: operator = "dqword"
    elif size <= 32: operator = "qqword"
    elif size <= 64: operator = "dqqword"
    else:
        return None
    return operator

def operator_to_bytes(operator:str):
    op = {
        "byte": 1, "word": 2, "dword": 4, "fword": 6, "qword": 8,
        "tword": 10, "dqword": 16, "qqword": 32, "dqqword": 64
    }
    try:
        return op[operator.lower()]
    except: return None

def split_tokens(blocks:list, token_type:str=None, token_string:str=None) -> list[list[Token, Block]]:
    groups = [[]]
    for element in blocks:
        if not isinstance(element, Block):
            if token_string is None and not token_type is None:
                if element.verify_type(token_type): groups.append([])
                else: groups[-1].append(element)
            else:
                if element.verify(token_type, token_string): groups.append([])
                else: groups[-1].append(element)
        else:
            groups[-1].append(element)
    if groups == [[]]: groups = []
    return groups

def is_a_stack(token:any) -> bool:
    return isinstance(token, Block) and token.kind == "stack"

def is_a_segment(token:any) -> bool:
    return isinstance(token, Block) and token.kind == "segment"

def is_options(token:any) -> bool:
    return isinstance(token, Block) and token.kind == "options"

def is_a_token(token:any) -> bool:
    return isinstance(token, Token)

def are_tokens(tokens:list) -> bool:
    for token in tokens:
        if not is_a_token(token): return False
    return True

def verify_tokens_types(pairs:dict[Token, str]):
    for token, type in pairs.items():
        if not token.verify_type(type): return False
    return True

def verify_blocks_types(pairs:dict[Block, str]):
    for block, kind in pairs.items():
        if block.kind != kind: return False
    return True

def pres_token(tokens:list[Token], index:int) -> Token: return utils.get_item(tokens, index, Token("", "unknown"))

def pres_block(blocks:list[Token], index:int) -> Block: return utils.get_item(blocks, index, Block(""))

def get_type_from_token(token:Token) -> ir.Type:
    return TYPES_WITH_LLTYPES[token.token_string]