format ELF64 executable 3
segment readable executable
; Write instruction
mov rsi, stack_B3897BE3
; Started stack 'stack_B3897BE3' of size 128
mov byte [rsi], 72
add rsi, 1
mov byte [rsi], 101
add rsi, 1
mov byte [rsi], 108
add rsi, 1
mov byte [rsi], 108
add rsi, 1
mov byte [rsi], 111
add rsi, 1
mov rax, 1
mov rdi, 1
mov rsi, stack_B3897BE3
mov rdx, 128
syscall 
; Exit instruction
mov rax, 60
mov rdi, 0
syscall 
mov rsi, stack_B3897BE3
segment readable writeable
mem_CDF12BFD rb 512
stack_B3897BE3 rb 128