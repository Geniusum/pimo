import llvmlite as llvm
import llvmlite.ir as ir
import lib.stack as stack
import lib.sourcecode as sourcecode
import lib.names as names
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
        self.ended = False
    
    def set_line(self, new_line:int):
        self.line = new_line
    
    def terminate(self):
        self.ended = True