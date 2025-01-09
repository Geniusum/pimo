format ELF64 executable 3
segment readable executable
	; Write instruction
	mov rsi, stack_D415D4C8
	; Started stack 'stack_D415D4C8' of size 128
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
	mov rsi, stack_D415D4C8
	mov rdx, 128
	syscall 
	; Exit instruction
	mov rax, 60
	mov rdi, 0
	syscall 
	mov rsi, stack_D415D4C8
segment readable writeable
	mem_F645B7C5 rb 512
	stack_D415D4C8 rb 128
