import lib.fasm as fasm
import lib.logger as logger

class Compiler():
    def __init__(self, pimo_instance, architecture:str="x64"):
        self.pimo_instance = pimo_instance
        self.logger:logger.Logger = self.pimo_instance.logger
        self.error_logger:logger.ErrorLogger = self.pimo_instance.error_logger
        self.programs = {
            "main": fasm.Program(architecture)
        }
        self.main_program = self.programs["main"]
    
    def compile(self, segments:list):
        self.logger.log(str(segments))