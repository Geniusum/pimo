format ELF64 executable 3
segment readable executable
	; Ini instruction
	; Add to memory 'mem_E81373C5' the element 'x' of type str<90>
	mov rsi, mem_E81373C5
	mov byte [rsi], 72
	mov rsi, mem_E81373C5
	add rsi, 1
	mov byte [rsi], 101
	mov rsi, mem_E81373C5
	add rsi, 2
	mov byte [rsi], 108
	mov rsi, mem_E81373C5
	add rsi, 3
	mov byte [rsi], 108
	mov rsi, mem_E81373C5
	add rsi, 4
	mov byte [rsi], 111
	mov rsi, mem_E81373C5
	add rsi, 5
	mov byte [rsi], 44
	mov rsi, mem_E81373C5
	add rsi, 6
	mov byte [rsi], 32
	mov rsi, mem_E81373C5
	add rsi, 7
	mov byte [rsi], 87
	mov rsi, mem_E81373C5
	add rsi, 8
	mov byte [rsi], 111
	mov rsi, mem_E81373C5
	add rsi, 9
	mov byte [rsi], 114
	mov rsi, mem_E81373C5
	add rsi, 10
	mov byte [rsi], 108
	mov rsi, mem_E81373C5
	add rsi, 11
	mov byte [rsi], 100
	mov rsi, mem_E81373C5
	add rsi, 12
	mov byte [rsi], 33
	; Write instruction
	mov rsi, stack_DB07F0B8
	; Started stack 'stack_DB07F0B8' of size 128
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
	mov rsi, stack_DB07F0B8
	mov rdx, 128
	syscall 
	mov rsi, stack_DB07F0B8
	; Default exit
	mov rax, 60
	mov rdi, 0
	syscall 
segment readable writeable
	mem_E81373C5 rb 512
	stack_DB07F0B8 rb 128
