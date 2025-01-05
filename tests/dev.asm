format ELF64 executable 3
segment readable executable
	; Ini instruction
	; Add to memory 'mem_C30FEEC6' the element 'var' of type u8<1>
	mov rsi, mem_C30FEEC6
	mov byte [rsi], 6
	add rsi, 1
	; Exit instruction
	mov rax, 60
	mov rsi, mem_C30FEEC6
	mov al, byte [rsi]
	mov byte [rdi], al
	syscall 
segment readable writeable
	mem_C30FEEC6 rb 512
