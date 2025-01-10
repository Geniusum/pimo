import lib.fasm as fasm
import os

SCRIPT = os.path.abspath(__file__)
SRC_DIR = os.path.dirname(SCRIPT)
MODS_DIR = os.path.join(SRC_DIR, "modules")

class Module():
    class ModuleNotFound(BaseException): ...

    def __init__(self, segment:fasm.Segment, name:str):
        self.segment = segment
        self.name = name.strip().lower()
        self.path = os.path.join(MODS_DIR, f"{self.name}.py")
        if not os.path.exists(self.path):
            raise ModuleNotFoundError(self.path)
        self.included = False

    def include(self):
        if not self.included:
            self.segment.add_line(f"include '{self.path}'")