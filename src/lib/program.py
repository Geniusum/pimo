import llvmlite as llvm
import llvmlite.ir as ir
import lib.fasm as fasm
import lib.memory as memory
import lib.stack as stack
import lib.sourcecode as sourcecode
import os

class Program():
    def __init__(self, sourcepath:str, sourcecode:sourcecode.SourceCode, id:str):
        self.sourcepath = sourcepath
        self.sourcecode = sourcecode
        self.content = self.sourcecode.content
        self.relpath = os.path.relpath(self.sourcepath)
        self.module = ir.Module(self.relpath)
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