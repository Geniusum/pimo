import sys, argparse, os, time, subprocess

SCRIPT = os.path.abspath(__file__)
SRC_DIR = os.path.dirname(SCRIPT)
LIB_DIR = os.path.join(SRC_DIR, "lib")
PIMO_DIR = os.path.dirname(SRC_DIR)

sys.path += [SRC_DIR, LIB_DIR]

import lib.sourcecode as sourcecode
import lib.compiler as compiler
import lib.logger as logger
import lib.parser as parser
import lib.utils as utils

class Main():
    class FileNotFound(BaseException): ...
    class InvalidFileExtension(BaseException): ...
    class ExistantLLVMOutput(BaseException): ...
    class ExistantObjectOutput(BaseException): ...
    class ExistantAssemblyOutput(BaseException): ...
    class ExistantOutput(BaseException): ...
    class ExecuteWithoutChangeMod(BaseException): ...

    def __init__(self, argv:list[str]) -> None:
        self.arg_parser = argparse.ArgumentParser(prog="pimo", description="Compile .pim programs.")
        self.arg_parser.add_argument("-t", "--timer", action="store_true")  # For get compile time
        self.arg_parser.add_argument("-o", "--output", type=str)  # For choose a specific output path
        #self.arg_parser.add_argument("-a", "--architecture", type=str)  # For choose a specific output path
        self.arg_parser.add_argument("-p", "--parsed", action="store_true")  # For return the parser result
        self.arg_parser.add_argument("-b", "--bum", action="store_true")  # For no compile
        self.arg_parser.add_argument("-sl", "--silent", action="store_true")  # For no logs
        self.arg_parser.add_argument("-s", "--assembly", action="store_true")  # For generate assembly
        self.arg_parser.add_argument("-kll", "--keep-llvm", action="store_true")  # For keep the LLVM file
        self.arg_parser.add_argument("-ko", "--keep-obj", action="store_true")  # For keep the object file
        self.arg_parser.add_argument("-r", "--replace", action="store_true")  # For replace generated files (.o, .ll, .s)
        self.arg_parser.add_argument("-ul", "--uncolored-logs", action="store_true")  # For uncolored logs
        self.arg_parser.add_argument("-ue", "--uncolored-errors", action="store_true")  # For uncolored error
        self.arg_parser.add_argument("-c", "--chmod", "--change-mod", action="store_true")  # For change mod of the output
        self.arg_parser.add_argument("-e", "--execute", action="store_true")  # For execute the output after compiling
        self.arg_parser.add_argument("sourcecode", type=str)
        self.args = vars(self.arg_parser.parse_args(argv))

        self.silent:bool = self.args["silent"]
        self.timer:bool = self.args["timer"]
        self.output:str = self.args["output"]
        #self.architecture:str = self.args["architecture"]
        self.parsed:bool = self.args["parsed"]
        self.bum:bool = self.args["bum"]
        self.assembly:bool = self.args["assembly"]
        self.keep_llvm:bool = self.args["keep_llvm"]
        self.keep_obj:bool = self.args["keep_obj"]
        self.replace:bool = self.args["replace"]
        self.uncolored_logs:bool = self.args["uncolored_logs"]
        self.uncolored_errors:bool = self.args["uncolored_errors"]
        self.change_mod:bool = self.args["chmod"]
        self.execute:bool = self.args["execute"]

        self.sourcecode_path:str = self.args["sourcecode"]
        
        if not self.output:
            self.output = os.path.join(os.path.dirname(self.sourcecode_path), os.path.splitext(os.path.basename(self.sourcecode_path))[0])

        self.llvm_output = f"{self.output}.ll"
        self.obj_output = f"{self.output}.o"
        self.asm_output = f"{self.output}.s"

        self.logger = logger.Logger(not self.silent, self.uncolored_logs)
        self.error_logger = logger.ErrorLogger(self.uncolored_errors)

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
    
    def show_parsed_blocks(self, blocks:list):
        to_show = f"Parsed blocks:\n\n{utils.dump(blocks)}"

        self.logger.log(f"\n{self.logger.start}    ↳ ".join(to_show.splitlines()), "out")

    def start(self):
        if self.timer:
            self.start_time = time.time()
            self.logger.log("Timer started.", "work")
        
        if self.execute and not self.output:
            self.raise_exception(self.ExecuteWithoutChangeMod, "You need to add the `-c` change mod option for execute the output.")

        if not os.path.exists(self.sourcecode_path):
            self.raise_exception(self.FileNotFound, self.sourcecode_path)

        if os.path.splitext(os.path.basename(self.sourcecode_path))[1].lower() != ".pim":
            self.raise_exception(self.InvalidFileExtension, os.path.basename(self.sourcecode_path))

        if os.path.exists(self.llvm_output):
            if self.replace:
                os.remove(self.llvm_output)
                self.logger.log(f"The file `{self.llvm_output}` was deleted due to the `-r` replace option.", "info")
            else:
                self.raise_exception(self.ExistantLLVMOutput, self.llvm_output, "Use the `-r` replace option to replace the LLVM output.")

        if os.path.exists(self.obj_output):
            if self.replace:
                os.remove(self.obj_output)
                self.logger.log(f"The file `{self.obj_output}` was deleted due to the `-r` replace option.", "info")
            else:
                self.raise_exception(self.ExistantObjectOutput, self.obj_output, "Use the `-r` replace option to replace the object output.")

        if os.path.exists(self.asm_output):
            if self.replace:
                os.remove(self.asm_output)
                self.logger.log(f"The file `{self.asm_output}` was deleted due to the `-r` replace option.", "info")
            elif self.assembly:
                self.raise_exception(self.ExistantAssemblyOutput, self.asm_output, "Use the `-r` replace option to replace the assembly output.")

        if os.path.exists(self.output):
            if self.replace:
                os.remove(self.output)
                self.logger.log(f"The file `{self.output}` was deleted due to the `-r` replace option.", "info")
            else:
                self.raise_exception(self.ExistantOutput, self.output, "Use the `-r` replace option to replace the output.")
        
        if not self.bum:
            listed_files = []
            listed_files.append(self.output)
            if self.keep_llvm: listed_files.append(self.llvm_output)
            if self.keep_obj: listed_files.append(self.obj_output)
            if self.assembly: listed_files.append(self.asm_output)

            self.logger.log(f"Here's the output file who will be created after compilation : {', '.join(listed_files)}", "info")

        self.logger.log("Reading the source code content...", "work")
        self.sourcecode_content:str = open(self.sourcecode_path, "r", encoding="utf-8").read().strip()
        self.sourcecode = sourcecode.SourceCode(self.sourcecode_content)
        self.logger.log("Source code content ready to be used.", "success")

        self.parser = parser.Parser(self)

        self.logger.log("Starting parsing...", "work")
        self.segments = self.parser.parse(self.sourcecode.content)
        self.blocks = self.parser.parse_blocks(self.segments)
        self.logger.log("Parsed.", "success")

        if self.parsed:
            self.show_parsed(self.segments)
            self.show_parsed_blocks(self.blocks)

        self.compiler = compiler.Compiler(self)
        
        self.logger.log("Starting compiling...", "work")
        self.compiler.compile(self.segments, self.blocks)
        self.logger.log("Compiled.", "success")

        self.logger.log("Generating LLVM file...", "work")
        llvm_module = self.compiler.get_llvm_module()
        llvm_file = open(self.llvm_output, "w+")
        llvm_file.write(str(llvm_module))
        llvm_file.close()
        self.logger.log(f"The file `{self.llvm_output}` now contains the LLVM module.", "success")

        self.logger.log("Generating object file...", "work")
        try: self.execute_command(f"llc -filetype=obj {self.llvm_output} -o {self.obj_output}")
        except: pass
        if os.path.exists(self.obj_output):
            self.logger.log(f"Object file generated at the path `{self.obj_output}`.", "success")
        else:
            self.error_logger.log(f"Object file not found, maybe due to an error.", "error")
            self.end()

        self.logger.log("Generating binary file...", "work")
        try: self.execute_command(f"clang {self.obj_output} -o {self.output} -Woverride-module")
        except: pass
        if os.path.exists(self.output):
            self.logger.log(f"Binary file generated at the path `{self.obj_output}`.", "success")
        else:
            self.error_logger.log(f"Binary file not found, maybe due to an error.", "error")
            self.end()

        self.logger.log("Generating assembly file...", "work")
        try: self.execute_command(f"clang -S {self.llvm_output} -o {self.asm_output}")
        except: pass
        if os.path.exists(self.asm_output):
            self.logger.log(f"Assembly file generated at the path `{self.asm_output}`.", "success")
        else:
            self.error_logger.log(f"Assembly file not found, maybe due to an error.", "error")
            self.end()
        
        if not self.keep_llvm:
            self.logger.log("Deleting LLVM file...", "work")
            os.remove(self.llvm_output)
            self.logger.log("LLVM file deleted.", "success")
        
        if not self.keep_obj:
            self.logger.log("Deleting object file...", "work")
            os.remove(self.obj_output)
            self.logger.log("Object file deleted.", "success")

        if self.change_mod:
            self.logger.log(f"Changing mod due to the `-c` change mod option.", "info")
            self.execute_command(f"chmod +x {self.output}")

        if self.execute:
            self.logger.log(f"Executing the output...", "work")
            try: self.execute_command(f"./{self.output}")
            except Exception as e:
                self.error_logger.log(f"Exception during the output execution : {e}", "error")
                self.end()
            else:
                self.logger.log(f"Output executed.", "success")

    def end(self):
        if self.timer:
            self.end_time = time.time()
            self.logger.log(f"Process time : {self.end_time - self.start_time}s", "info")
        
        sys.exit()

if __name__ == "__main__":
    instance = Main(sys.argv[1:])
    instance.start()
    instance.end()
