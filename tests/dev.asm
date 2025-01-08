format ELF64 executable 3
segment readable executable
	; Write instruction
	mov rsi, stack_CB52E064
	; Started stack 'stack_CB52E064' of size 128
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
	mov byte [rsi], 44
	add rsi, 1
	mov byte [rsi], 32
	add rsi, 1
	mov byte [rsi], 87
	add rsi, 1
	mov byte [rsi], 111
	add rsi, 1
	mov byte [rsi], 114
	add rsi, 1
	mov byte [rsi], 108
	add rsi, 1
	mov byte [rsi], 100
	add rsi, 1
	mov byte [rsi], 33
	add rsi, 1
	mov rax, 1
	mov rdi, 1
	mov rsi, stack_CB52E064
	mov rdx, 128
	syscall 
	; Exit instruction
	mov rax, 60
	mov rdi, 0
	syscall 
	mov rsi, stack_CB52E064
segment readable writeable
	mem_DA94C72B rb 512
	stack_CB52E064 rb 128
