class StackByte():
    def __init__(self, position:int):
        self.position = position

class StackElement():
    def __init__(self, size:int, token_type:str):
        self.size = size
        self.token_type = token_type
        self.bytes:list[StackByte] = []

class Stack():
    def __init__(self, size:int, id:str):
        self.size = size
        self.id = id
        self.elements:list[StackElement] = []

    def enough_size(self, size:int) -> bool:
        return not len(self.get_free_positions()) < size

    def push(self, *args):
        self.elements.append(StackElement(*args))
        for i in range(self.elements[-1].size):
            self.elements[-1].bytes.append(StackByte(self.get_free_positions()[-1]))
        return self.elements[-1]

    def pop(self):
        return self.elements.pop()
    
    def get_used_positions(self) -> list[int]:
        used_positions = []
        used_bytes = self.get_used_bytes()
        for byte in used_bytes: used_positions.append(byte.position)
        return used_positions
    
    def get_free_positions(self) -> list[int]:
        free_positions = []
        free_bytes = self.get_free_bytes()
        for byte in free_bytes: free_positions.append(byte.position)
        return free_positions
    
    def with_prefix(self) -> str: return "stack_" + self.id