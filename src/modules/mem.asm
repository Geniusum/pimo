; Requires: memalloc.asm

; 0x2C for comma, 0x3B for semicolon, they aren't authorized in names

ALLOC 0x668A0, 98000  ; from 0x668A0 to 0x7E770 : Memories scope
; The memory scope will had all memory names and their addresses
; name 0x2C addr 0x3B ...

ALLOC 0x7E771, 147000 ; from 0x7E771 to 0xA25A9 : Variables scope
; The memory scope will had all variables names, sizes, lenght, address and parent memory
; name 0x2C mem 0x2C size 0x2C len 0x2C addr 0x3B ...

SCOPE_MEM = 0x668A0
SCOPE_MEM_SIZE = 98000
SCOPE_VAR_END = 0x7E770
SCOPE_VAR = 0x7E771
SCOPE_VAR_SIZE = 147000
SCOPE_VAR_END = 0xA25A9
