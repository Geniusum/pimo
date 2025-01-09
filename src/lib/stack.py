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
        return not self.get_free_nb() < size

    def push(self, *args):
        self.elements.append(StackElement(*args))
        for i in range(self.elements[-1].size):
            self.elements[-1].bytes.append(StackByte(self.get_free_positions()[0]))
        return self.elements[-1]

    def pop(self):
        return self.elements.pop()
    
    def get_used_bytes(self) -> list[StackByte]:
        used_bytes = []
        for element in self.elements: used_bytes += element.bytes
        return used_bytes
    
    def get_used_nb(self) -> int:
        used_nb = 0
        for element in self.elements: used_nb += len(element.bytes)
        return used_nb
    
    def get_used_positions(self) -> list[int]:
        used_positions = []
        used_bytes = self.get_used_bytes()
        for byte in used_bytes: used_positions.append(byte.position)
        return used_positions

    def get_free_bytes(self) -> list[StackByte]:
        free_bytes = []
        used_positions = self.get_used_positions()
        for byte_position in range(self.size):
            if not byte_position in used_positions: free_bytes.append(StackByte(byte_position))
        return free_bytes
    
    def get_free_positions(self) -> list[int]:
        free_positions = []
        free_bytes = self.get_free_bytes()
        for byte in free_bytes: free_positions.append(byte.position)
        return free_positions
    
    def get_free_nb(self) -> int: return self.size - self.get_used_nb()
    
    def with_prefix(self) -> str: return "stack_" + self.id