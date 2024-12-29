format ELF64 executable 3
segment readable executable
	mov rax, 1
	mov rdi, 1
	mov rsi, my_data
	mov rdx, 13
	syscall 
	mov rax, 60
	xor rdi, rdi
	syscall 
segment readable
	my_data db 'Hello, world!', 0
