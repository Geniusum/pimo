class Segment():
    def __init__(self):
        self.lines = []
        self.sections = []
    
    def add_line(self, content:str, indent:bool=False):
        line = "\t" if indent else ""
        line += content
        self.lines.append(line)
    
    def add_ins(self, instruction:str, *args:list[str]):
        self.add_line(" ".join([instruction.strip().lower(), ", ".join(self.args_to_string(args))]))
    
    def add_def(self, name:str, type:str, *args:list[str]):
        " ".join([name.strip(), type.strip().lower(), ", ".join(self.args_to_string(args))])
    
    def args_to_string(self, args: list) -> list[str]:
        return [str(item) for item in args]

    def __str__(self) -> str:
        return "\n".join(self.lines)

class Section():
    def __init__(self, segment:Segment, label:str):
        self.segment = segment
        self.label = label
        
        self.segment.add_line(f".{self.label}")
        self.index = len(self.segment.lines) - 1
    
    def add_line(self, content:str):
        self.segment.lines.insert(self.index, f"\t{content}")
        self.index + 1

class Program():
    def __init__(self):
        self.segments = []
        self.code = Segment()
        self.code.add_line("segment readable executable")
        self.segments.append(self.code)
        self.data = Segment()
        self.data.add_line("segment readable writeable")
        self.segments.append(self.data)