from lib.enum import *

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

# Two chars
DOUBLE_HASHTAG = "##"
DOUBLE_SLASH = "//"
SLASH_STAR = "/*"
STAR_SLASH = "*/"

# Operators
OPERATORS = [HASHTAG, DOUBLE_HASHTAG]

# Alphabet
AL_LETTERS = "abcdefghijklmnopqrstuvwxyz"
AL_LETTERS_UPPER = AL_LETTERS.upper()

# Digits
DIGITS = "012345689"
DECIMAL_CHARS = DIGITS + DOT

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
        if is_a_operator(self.token_string):
            return "operator"
        return "unknown"

    def __str__(self):
        return f"Token: '{self.token_string}', {self.token_type}"
