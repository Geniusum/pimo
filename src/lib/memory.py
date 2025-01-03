import lib.lang as lang

class MemoryByte():
    def __init__(self, position:int):
        self.position = position

class MemoryElement():
    def __init__(self, name:str, size:int, lenght:int, type:str=None, token_type:str=None, redirect:bool=True):
        self.name = name
        self.size = size
        self.lenght = lenght
        self.type = type
        self.token_type = token_type
        self.redirect = redirect
        self.bytes:list[MemoryByte] = []
    
    def get_memory_size(self) -> int: return self.size * self.lenght

class Memory():
    def __init__(self, size:int, id:str):
        self.size = size
        self.id = id
        self.elements:list[MemoryElement] = []
    
    def get_used_bytes(self) -> list[MemoryByte]:
        used_bytes = []
        for element in self.elements: used_bytes += element.bytes
        return used_bytes
    
    def get_used_positions(self) -> list[int]:
        used_positions = []
        used_bytes = self.get_used_bytes()
        for byte in used_bytes: used_positions.append(byte.position)
        return used_positions

    def get_free_bytes(self) -> list[MemoryByte]:
        free_bytes = []
        used_positions = self.get_used_positions()
        for byte_position in range(self.size):
            if not byte_position in used_positions: free_bytes.append(MemoryByte(byte_position))
        return free_bytes
    
    def get_free_positions(self) -> list[int]:
        free_positions = []
        free_bytes = self.get_free_bytes()
        for byte in free_bytes: free_positions.append(byte.position)
        return free_positions

    def get_bytes(self) -> list[MemoryByte]:
        bytes = self.get_free_bytes() + self.get_used_bytes()

    def get_positions(self) -> list[int]:
        bytes = self.get_free_positions() + self.get_used_positions()

    def get_names(self) -> list[str]:
        names = []
        for element in self.elements: names.append(element.name)
        return names

    def get_element(self, name:str) -> MemoryElement:
        for element in self.elements:
            if element.name == name: return element

    def name_exists(self, name:str) -> bool:
        return name in self.get_names()
    
    def byte_exists(self, byte:MemoryByte) -> bool:
        return byte in self.get_used_bytes()
    
    def position_exists(self, position:int) -> bool:
        return position in self.get_used_positions()
    
    def valid_position(self, position:int) -> bool:
        return 0 < position < self.size

    def valid_name(self, name:str) -> bool:
        return lang.is_a_valid_name(name) and lang.is_a_lower_name(name)
    
    def with_prefix(self) -> str: return "mem_" + self.id

def find_memory_index(memories:list[Memory], id:str):
    id = id.upper()
    for memory_index, memory in enumerate(memories):
        if memory.id == id: return memory_index