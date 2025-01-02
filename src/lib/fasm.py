# The FASM Python API

from lib.lang import REGISTERS

class CodePart():
    def __init__(self):
        self.fm: str

    def get_formatted(self, replace_list: dict) -> str:
        formatted = self.fm
        for to_replace, replace in replace_list.items():
            formatted = formatted.replace(f"%{to_replace}%", replace)
        return formatted

class CodeSegment(CodePart):
    def __init__(self):
        super().__init__()
        self.instructions = []
        self.fm = "segment %specs%\n%instructions%\n"
        self.executable = True
        self.writeable = False
    
    def add_instruction(self, instruction: str):
        """Adds an assembly instruction to the segment."""
        self.instructions.append(instruction)
        return len(self.instructions) - 1
    
    def get_specs(self, executable:bool = False, writeable:bool = False) -> str:
        """Returns the specifications for the segment."""
        r = "readable"
        if executable: r += " executable"
        if writeable: r += " writeable"
        return r

    def get_formatted(self, replace_list: dict = None) -> str:
        """Formats the segment with its specifications and instructions."""
        if len(self.instructions):
            replace_list = replace_list or {}
            replace_list.update({
                "specs": self.get_specs(self.executable, self.writeable),  # Example: always executable
                "instructions": "\n".join(self.instructions),
            })
            return super().get_formatted(replace_list)
        else:
            return ""

class Program():
    def __init__(self, architecture: str = "x64"):
        self.architecture = architecture
        self.register_prefix = "e" if self.architecture == "x86" else "r"
        self.segments = []
        self.data_segment = CodeSegment()
        self.data_segment.executable = False
        self.data_segment.writeable = True
        self.code_segment = CodeSegment()
        self.segments.append(self.code_segment)
        self.segments.append(self.data_segment)
    
    def get_register(self, suffix:str):
        return f"{self.register_prefix}{suffix}"

    def pass_to_indent(self, s:str):
        return "\t" + s.replace("\t", "")
        
    def args_to_string(self, args: list) -> list[str]:
        return [str(item) for item in args]

    def __add_to_data_segment(self, data: str):
        """Adds data to the data segment."""
        return self.data_segment.add_instruction(self.pass_to_indent(data))
    
    def add_to_data_segment(self, name:str, type:str, *args:list[str]):
        return self.__add_to_data_segment(" ".join([name.strip(), type.strip().lower(), ", ".join(self.args_to_string(args))]))

    def __add_to_code_segment(self, instruction: str):
        """Adds an instruction to the code segment."""
        return self.code_segment.add_instruction(self.format_registers(self.pass_to_indent(instruction)))

    def add_to_code_segment(self, instruction:str, *args:list[str]):
        return self.__add_to_code_segment(" ".join([instruction.strip().lower(), ", ".join(self.args_to_string(args))]))

    def generate_source(self) -> str:
        """Generates the full FASM source code."""
        return "format ELF64 executable 3\n" + "".join(segment.get_formatted() for segment in self.segments)

    def save_to_file(self, filename: str):
        """Saves the generated FASM source code to a file."""
        with open(filename, "w") as f:
            f.write(self.generate_source())
    
    def format_registers(self, s: str) -> str:
        for register in REGISTERS:
            s.replace(f"%{register}", self.register_prefix + register)
        return s

# Testing
"""if __name__ == "__main__":
    instance = Program()
    # Adding data to the data segment
    instance.add_to_data_segment("my_data", "db", "'Hello, world!'", 0)

    # Adding instructions to the code segment
    instance.add_to_code_segment(f"mov", instance.get_register("ax"), 1)
    instance.add_to_code_segment(f"mov", instance.get_register("di"), 1)
    instance.add_to_code_segment(f"mov", instance.get_register("si"), "my_data")
    instance.add_to_code_segment(f"mov", instance.get_register("dx"), 13)
    instance.add_to_code_segment(f"syscall")
    instance.add_to_code_segment(f"mov", instance.get_register("ax"), 60)
    instance.add_to_code_segment(f"xor", instance.get_register("di"), instance.get_register("di"))
    instance.add_to_code_segment(f"syscall")

    # Generate and display the source
    source_code = instance.generate_source()
    print(source_code)

    # Save to a file
    instance.save_to_file("program.asm")"""