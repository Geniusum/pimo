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
CLOSED_HOOK = "]"
LESS_THAN = "<"
GREATER_THAN = ">"
PARAGRAPH = "§"
SEMICOLON = ";"
PERCENTAGE = "%"
COLON = ":"
EQUAL = "="
PLUS = "+"

# Two chars
DOUBLE_HASHTAG = "##"
DOUBLE_SLASH = "//"
SLASH_STAR = "/*"
STAR_SLASH = "*/"

# Operators
OPERATORS = [
             HASHTAG, DOUBLE_HASHTAG, TILDE, PERCENTAGE, COLON, PERCENTAGE, EQUAL,
             PLUS  # Stack operators
            ]

# Delimiters
DELIMITERS = [SEMICOLON, OPEN_HOOK, CLOSED_HOOK]

# Registers
REGISTERS = ["ax", "bx", "cx", "dx", "si", "di", "bp", "sp"]

# Instructions
INSTRUCTIONS = ["exit", "ini"]

# Types
TYPES_SIZES = {
    "u8": [1, "integer"],
    "u16": [2, "integer"],
    "u24": [3, "integer"],
    "u32": [4, "integer"],
    "u64": [8, "integer"],
    "chr": [1, "string"],
    "bool": [1, "boolean"],
    "f32": [4, "decimal"],
    "f64": [8, "decimal"],
    "x86": [4, "address"],
    "x64": [8, "address"]
}
TYPES = list(TYPES_SIZES.keys())

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
    "mem"
}
L_PPCommands = list(PPCommands)
L_PPOSCommands = list(PPOSCommands)

DefaultTokens = {
    "unknown", "name"
}
L_DefaultTokens = list(DefaultTokens)


#####################
#  GRAMMAR METHODS  #
#####################

def is_a_valid_name(presumed_name: str):
    if not presumed_name or presumed_name[0] in DIGITS:
        return False
    return all(char in NM_CHARS for char in presumed_name)

def is_a_upper_name(presumed_upper_name:str): return presumed_upper_name == presumed_upper_name.upper()

def is_a_lower_name(presumed_lower_name:str): return presumed_lower_name == presumed_lower_name.lower()

def is_a_integer(presumed_integer:str):
    if not len(presumed_integer): return False
    for char in presumed_integer:
        if not char in DIGITS: return False
    return True

def is_a_decimal(presumed_decimal:str):
    if not len(presumed_decimal): return False
    parts = presumed_decimal.split(DOT)
    if not len(parts) == 2: return False
    for part in parts:
        if not is_a_integer(part): return False
    return True

def is_a_boolean(presumed_boolean:str):
    if presumed_boolean.lower() in ["true", "false"]: return True
    return False

def is_a_operator(presumed_operator:str):
    if presumed_operator.lower() in OPERATORS: return True
    return False

def is_a_delimiter(presumed_delimiter:str):
    if presumed_delimiter.lower() in DELIMITERS: return True
    return False

def is_a_register(presumed_register:str):
    if presumed_register in REGISTERS: return True
    return False

def is_a_instruction(presumed_instruction:str):
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
        if is_a_integer(self.token_string):
            return "integer"
        if is_a_decimal(self.token_string):
            return "decimal"
        if is_a_delimiter(self.token_string):
            return "delimiter"
        if is_a_operator(self.token_string):
            return "operator"
        if is_a_instruction(self.token_string):
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

"""def get_stack_used_size(stack:dict) -> int:
    used_size = 0
    for element in stack["elements"]:
        used_size += element["size"]
    return used_size

def get_memory_used_size(memory:dict) -> int:
    used_size = 0
    for element in memory["elements"].values():
        used_size += element["size"] * element["lenght"]
    return used_size"""

"""def bytes_to_operator(size:int):
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
        return op[operator]
    except: return None"""