format ELF64 executable 3
include '/home/genius_um/Developpement/pimo/src/modules/memalloc.asm'
include '/home/genius_um/Developpement/pimo/src/modules/mem.asm'

segment readable executable
    ALLOC_RAND 5
    mov byte [rax], 64
    mov rsi, rax
    mov rax, 1
    mov rdi, 1
    mov rdx, 5
    syscall
    mov rax, 60
    mov rdi, 0
    syscall
segment readable writeable
    hello db "Hello", 10