macro ALLOC_RAND size {
    mov rax, 9
    xor rdi, rdi
    mov rsi, size
    mov rdx, 3
    mov r10, 34
    xor r8, r8
    xor r9, r9
    syscall
}

macro ALLOC addr, size {
    mov rax, 9
    mov rdi, addr
    mov rsi, size
    mov rdx, 3
    mov r10, 34
    xor r8, r8
    xor r9, r9
    syscall
}