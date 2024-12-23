import sys, argparse, os, time

SCRIPT = os.path.abspath(__file__)
SRC_DIR = os.path.dirname(SCRIPT)
LIB_DIR = os.path.join(SRC_DIR, "lib")

sys.path += [SRC_DIR, LIB_DIR]

import lib.sourcecode as sourcecode
import lib.logger as logger

class Main():
    class FileNotFound(BaseException): ...
    class InvalidFileExtension(BaseException): ...
    class ExistantOutput(BaseException): ...

    def __init__(self, argv:list[str]) -> None:
        self.arg_parser = argparse.ArgumentParser(prog="pimo compiler", description="Compile .pim programs.")
        self.arg_parser.add_argument("-t", "--timer", action="store_true")  # For get compile time
        self.arg_parser.add_argument("-o", "--output", type=str)  # For choose a specific output path
        self.arg_parser.add_argument("-p", "--parsed", action="store_true")  # For return the parser result
        self.arg_parser.add_argument("-b", "--bum", action="store_true")  # For no compile
        self.arg_parser.add_argument("-s", "--silent", action="store_true")  # For no logs
        self.arg_parser.add_argument("-r", "--replace", action="store_true")  # For replace an existant output file
        self.arg_parser.add_argument("-ul", "--uncoloredlogs", action="store_true")  # For uncolored logs
        self.arg_parser.add_argument("-ue", "--uncolorederrors", action="store_true")  # For uncolored error
        self.arg_parser.add_argument("sourcecode", type=str)
        self.args = vars(self.arg_parser.parse_args(argv))

        self.silent:bool = self.args["silent"]
        self.timer:bool = self.args["timer"]
        self.output:str = self.args["output"]
        self.parsed:bool = self.args["parsed"]
        self.bum:bool = self.args["bum"]
        self.replace:bool = self.args["replace"]
        self.uncolored_logs:bool = self.args["uncoloredlogs"]
        self.uncolored_errors:bool = self.args["uncolorederrors"]

        self.sourcecode:str = self.args["sourcecode"]
        if not self.output:
            self.output = os.path.join(os.path.dirname(self.sourcecode), os.path.splitext(os.path.basename(self.sourcecode))[0])

        self.logger = logger.Logger(not self.silent, self.uncolored_logs)
        self.error_logger = logger.ErrorLogger(self.uncolored_errors)

    def raise_exception(self, exception:BaseException, *args):
        error_args = f"\n{self.error_logger.start} ↳ ".join(args)
        exception_name = f'{exception=}'.replace("=", "").split(".")[-1].replace("'>", "")
        self.error_logger.log(f"{exception_name}: {error_args}", "error")
        sys.exit(1)

    def start(self):
        # Logger and ErrorLogger testing :
        #
        # self.logger.log("Hello, World!")
        # self.logger.log("It's a information.", "info")
        # self.logger.log("I'm working! Brrr...", "work")
        # self.logger.log("Deleting your files...", "cmd")
        # self.logger.log("How it's possible to don't have any errors?", "sucess")
        # self.error_logger.log("Your code is terribly fragile!", "warn")
        # self.error_logger.log("Never think about it! A division by 0, you're fucking stupid bro...", "error")

        if self.timer:
            self.start_time = time.time()
            self.logger.log("Timer started.", "work")

        if not os.path.exists(self.sourcecode):
            self.raise_exception(self.FileNotFound, self.sourcecode)
        
        if os.path.exists(self.output):
            if self.replace:
                os.remove(self.output)
                self.logger.log(f"The file `{self.output}` was deleted due to the `-r` replace option.", "info")
            else:
                self.raise_exception(self.ExistantOutput, self.output, "Use the `-r` replace option to replace the output.")

        if os.path.splitext(os.path.basename(self.sourcecode))[1].lower() != ".pim":
            self.raise_exception(self.InvalidFileExtension, os.path.basename(self.sourcecode))

        sourcecode_content:str = open(self.sourcecode, "r", encoding="utf-8").read().strip()

        self.sourcecode = sourcecode.SourceCode(sourcecode_content)

    def end(self):
        if self.timer:
            self.end_time = time.time()
            self.logger.log(f"Program running time : {self.end_time - self.start_time}s", "info")
        
        sys.exit()

if __name__ == "__main__":
    instance = Main(sys.argv[1:])
    instance.start()
    instance.end()