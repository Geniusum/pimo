import lib.colors as colors

class Logger():
    def __init__(self, enabled:bool, uncolored:bool):
        self.enabled = enabled
        self.uncolored = uncolored
        self.colors = colors.Colors(not self.uncolored)
        self.kinds = {
            "info": f"{self.colors.get('yellow', 'bold')}[INFO]{self.colors.get()}",
            "work": f"{self.colors.get('cyan', 'bold')}[WORK]{self.colors.get()}",
            "cmd": f"{self.colors.get('blue', 'bold')}[CMD]{self.colors.get(style='underline')}",
            "out": f"{self.colors.get('blue', 'bold')}[OUT]{self.colors.get(style='underline')}",
            "success": f"{self.colors.get('green', 'bold')}[SUCCESS]{self.colors.get()}"
        }
        self.start = "》"
    
    def log(self, message:str, kinds:any=[]):
        if self.enabled:
            print(self.start, end="")
            if isinstance(kinds, str):
                print(self.kinds[kinds], end=" ")
            else:
                for kind in kinds:
                    print(self.kinds[kind], end=" ")
            message = message.strip()
            print(message)
            print(self.colors.get(), end="")

class ErrorLogger(Logger):
    def __init__(self, uncolored):
        super().__init__(True, uncolored)
        self.kinds = {
            "warn": f"{self.colors.get('purple', 'bold')}[WARN]{self.colors.get()}",
            "error": f"{self.colors.get('red', 'bold')}[ERROR]{self.colors.get()}"
        }