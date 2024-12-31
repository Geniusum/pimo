import sys, argparse, os, time, subprocess

SCRIPT = os.path.abspath(__file__)
SRC_DIR = os.path.dirname(SCRIPT)
LIB_DIR = os.path.join(SRC_DIR, "lib")

sys.path += [SRC_DIR, LIB_DIR]

import lib.sourcecode as sourcecode
import lib.compiler as compiler
import lib.logger as logger
import lib.parser as parser
import lib.utils as utils

class Main():
    class FileNotFound(BaseException): ...
    class InvalidFileExtension(BaseException): ...
    class ExistantAssemblyOutput(BaseException): ...
    class ExistantOutput(BaseException): ...
    class ExecuteWithoutChangeMod(BaseException): ...

    def __init__(self, argv:list[str]) -> None:
        self.arg_parser = argparse.ArgumentParser(prog="pimo", description="Compile .pim programs.")
        self.arg_parser.add_argument("-t", "--timer", action="store_true")  # For get compile time
        self.arg_parser.add_argument("-o", "--output", type=str)  # For choose a specific output path
        self.arg_parser.add_argument("-a", "--architecture", type=str)  # For choose a specific output path
        self.arg_parser.add_argument("-p", "--parsed", action="store_true")  # For return the parser result
        self.arg_parser.add_argument("-d", "--direct", action="store_true")  # For no assembly, it will create an assembly but it will delete it after
        self.arg_parser.add_argument("-b", "--bum", action="store_true")  # For no compile
        self.arg_parser.add_argument("-s", "--silent", action="store_true")  # For no logs
        self.arg_parser.add_argument("-r", "--replace", action="store_true")  # For replace an existant output file and an existant assembly file
        self.arg_parser.add_argument("-ul", "--uncolored-logs", action="store_true")  # For uncolored logs
        self.arg_parser.add_argument("-ue", "--uncolored-errors", action="store_true")  # For uncolored error
        self.arg_parser.add_argument("-c", "--chmod", "--change-mod", action="store_true")  # For change mod of the output
        self.arg_parser.add_argument("-e", "--execute", action="store_true")  # For execute the output after compiling
        self.arg_parser.add_argument("sourcecode", type=str)
        self.args = vars(self.arg_parser.parse_args(argv))

        self.silent:bool = self.args["silent"]
        self.timer:bool = self.args["timer"]
        self.output:str = self.args["output"]
        self.architecture:str = self.args["architecture"]
        self.parsed:bool = self.args["parsed"]
        self.direct:bool = self.args["direct"]
        self.bum:bool = self.args["bum"]
        self.replace:bool = self.args["replace"]
        self.uncolored_logs:bool = self.args["uncolored_logs"]
        self.uncolored_errors:bool = self.args["uncolored_errors"]
        self.change_mod:bool = self.args["chmod"]
        self.execute:bool = self.args["execute"]

        self.sourcecode:str = self.args["sourcecode"]
        
        if not self.output:
            self.output = os.path.join(os.path.dirname(self.sourcecode), os.path.splitext(os.path.basename(self.sourcecode))[0])

        self.assembly_output = f"{self.output}.asm"

        self.logger = logger.Logger(not self.silent, self.uncolored_logs)
        self.error_logger = logger.ErrorLogger(self.uncolored_errors)

        self.parser = parser.Parser(self)
        
        self.compiler = compiler.Compiler(self, self.architecture)

    def raise_exception(self, exception:BaseException, *args):
        error_args = f"\n{self.error_logger.start}      ↳ ".join(args)
        exception_name = f'{exception=}'.replace("=", "").split(".")[-1].replace("'>", "")
        self.error_logger.log(f"{exception_name}: {error_args}", "error")
        self.end()
        sys.exit(1)
    
    def execute_command(self, command:str):
        command = command.strip()
        self.logger.log(command, "cmd")
        output = subprocess.check_output(command, shell=True).decode("utf-8")
        output_lines = output.splitlines()
        to_log = "-"
        if len(output_lines):
            to_log = f"\n{self.logger.start}    ↳ ".join(output_lines)
        self.logger.log(to_log, "out")
    
    def show_parsed(self, segments:list):
        to_show = f"Parsed segments:\n\n{utils.dump(segments)}"

        self.logger.log(f"\n{self.logger.start}    ↳ ".join(to_show.splitlines()), "out")

    def start(self):
        # Logger and ErrorLogger testing :
        # self.logger.log("Hello, World!")
        # self.logger.log("It's a information.", "info")
        # self.logger.log("I'm working! Brrr...", "work")
        # self.logger.log("Deleting your files...", "cmd")
        # self.logger.log("Hello, World!", "out")
        # self.logger.log("How it's possible to don't have any errors?", "success")
        # self.error_logger.log("Your code is terribly fragile!", "warn")
        # self.error_logger.log("Never think about it! A division by 0, you're fucking stupid bro...", "error")

        if self.timer:
            self.start_time = time.time()
            self.logger.log("Timer started.", "work")
        
        if self.execute and not self.output:
            self.raise_exception(self.ExecuteWithoutChangeMod, "You need to add the `-c` change mod option for execute the output.")

        if not os.path.exists(self.sourcecode):
            self.raise_exception(self.FileNotFound, self.sourcecode)

        if os.path.splitext(os.path.basename(self.sourcecode))[1].lower() != ".pim":
            self.raise_exception(self.InvalidFileExtension, os.path.basename(self.sourcecode))

        if os.path.exists(self.assembly_output):
            if self.replace:
                os.remove(self.assembly_output)
                self.logger.log(f"The file `{self.assembly_output}` was deleted due to the `-r` replace option.", "info")
            else:
                self.raise_exception(self.ExistantAssemblyOutput, self.assembly_output, "Use the `-r` replace option to replace the assembly output.")

        if os.path.exists(self.output):
            if self.replace:
                os.remove(self.output)
                self.logger.log(f"The file `{self.output}` was deleted due to the `-r` replace option.", "info")
            else:
                self.raise_exception(self.ExistantOutput, self.output, "Use the `-r` replace option to replace the output.")
        
        if not self.direct:
            self.logger.log(f"Here's the output files who will be created after compilation : {self.output}, {self.assembly_output}", "info")
        else:
            self.logger.log(f"Here's the output file who will be created after compilation : {self.output}", "info")

        self.logger.log("Reading the source code content...", "work")
        sourcecode_content:str = open(self.sourcecode, "r", encoding="utf-8").read().strip()
        self.sourcecode = sourcecode.SourceCode(sourcecode_content)
        self.logger.log("Source code content ready to be used.", "success")

        self.logger.log("Starting parsing...", "work")
        self.segments = self.parser.parse(self.sourcecode.content)
        self.logger.log("Parsed.", "success")

        if self.parsed:
            self.show_parsed(self.segments)
        
        self.logger.log("Starting compiling...", "work")
        self.compiler.compile(self.segments)
        self.logger.log("Compiled.", "success")

        self.logger.log("Generating assembly and saving the file...", "work")
        self.compiler.generate_assembly(self.assembly_output)
        self.logger.log(f"The file `{self.assembly_output}` now contains the assembly code.", "success")

        self.logger.log(f"Creating binary from the file `{self.assembly_output}` with FASM.", "work")
        try: self.execute_command(f"fasm \"{self.assembly_output}\" \"{self.output}\"")
        except: pass
        if os.path.exists(self.output):
            self.logger.log(f"Binary generated at the path `{self.output}`.", "success")
        else:
            self.error_logger.log(f"Binary not found, maybe due to a FASM compilation error.", "error")
            self.end()

        if self.change_mod:
            self.logger.log(f"Changing mod due to the `-c` change mod option.", "info")
            self.execute_command(f"chmod +x {self.output}")

        self.logger.log(f"Executing the output...", "work")
        try: self.execute_command(f"./{self.output}")
        except Exception as e:
            self.error_logger.log(f"Exception during the output execution : {e}", "error")
            self.end()
        else:
            self.logger.log(f"Output executed.", "success")

    def end(self):
        if self.direct:
            if os.path.exists(self.assembly_output):
                os.remove(self.assembly_output)
                self.logger.log(f"The assembly output file `{self.assembly_output}` was deleted due to the `-d` direct option.", "info")
            else:
                self.error_logger.log("Trying to delete the assembly output but it doesn't exists. From the `-d` direct option.", "warn")

        if self.timer:
            self.end_time = time.time()
            self.logger.log(f"Process time : {self.end_time - self.start_time}s", "info")
        
        sys.exit()

if __name__ == "__main__":
    instance = Main(sys.argv[1:])
    instance.start()
    instance.end()
