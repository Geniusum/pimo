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
PARAGRAPH = "§"
SEMICOLON = ";"
PERCENTAGE = "%"

# Two chars
DOUBLE_HASHTAG = "##"
DOUBLE_SLASH = "//"
SLASH_STAR = "/*"
STAR_SLASH = "*/"

# Operators
OPERATORS = [HASHTAG, DOUBLE_HASHTAG, TILDE, PERCENTAGE]

# Delimiter
DELIMITERS = [SEMICOLON, OPEN_HOOK, CLOSED_HOOK]

# Alphabet
AL_LETTERS = "abcdefghijklmnopqrstuvwxyz"
AL_LETTERS_UPPER = AL_LETTERS.upper()

# Digits
DIGITS = "012345689"
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
        if is_a_valid_name(self.token_string):
            return "name"
        if is_a_integer(self.token_string):
            return "integer"
        if is_a_decimal(self.token_string):
            return "decimal"
        if is_a_delimiter(self.token_string):
            return "delimiter"
        if is_a_operator(self.token_string):
            return "operator"
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

def get_stack_used_size(stack:dict) -> int:
    used_size = 0
    for element in stack["elements"]:
        used_size += element["size"]
    return used_size

def how_much_bytes_decimal(nb: float) -> int:
    try:
        struct.pack('f', nb)
        return 4
    except OverflowError: return 8