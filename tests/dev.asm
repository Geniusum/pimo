format ELF64 executable 3
segment readable executable
; Write instruction  ; 15
mov rsi, stack_C16273B3  ; 15
; Started stack 'stack_C16273B3' of size 128  ; 15
mov byte [rsi], 72  ; 15
add rsi, 1  ; 15
mov byte [rsi], 101  ; 15
add rsi, 1  ; 15
mov byte [rsi], 108  ; 15
add rsi, 1  ; 15
mov byte [rsi], 108  ; 15
add rsi, 1  ; 15
mov byte [rsi], 111  ; 15
add rsi, 1  ; 15
mov rax, 1  ; 15
mov rdi, 1  ; 15
mov rsi, stack_C16273B3  ; 15
mov rdx, 128  ; 15
syscall   ; 15
; Exit instruction  ; 16
mov rax, 60  ; 16
mov rdi, 0  ; 16
syscall   ; 16
mov rsi, stack_C16273B3  ; 16
segment readable writeable
mem_A1AD6F67 rb 512  ; 16
stack_C16273B3 rb 128  ; 16