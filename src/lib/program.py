import lib.fasm as fasm
import lib.memory as memory
import lib.stack as stack
import os

class Program():
    def __init__(self, sourcepath:str, asm:fasm.Program, id:str):
        self.sourcepath = sourcepath
        self.relpath = os.path.relpath(self.sourcepath)
        self.asm = asm
        self.id = id
        self.line = None
        self.actual_memory:memory.Memory = None
        self.actual_stack:stack.Stack = None
        self.ended = False
    
    def set_line(self, new_line:int):
        self.line = new_line
    
    def set_acmem(self, new_mem:memory.Memory):
        self.actual_memory = new_mem
    
    def set_acstack(self, new_stack:stack.Stack):
        self.actual_stack = new_stack

    def terminate(self):
        self.ended = True