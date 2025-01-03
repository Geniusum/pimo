format ELF64 executable 3
segment readable executable
	; Ini instruction
	; Added to memory 'mem_F2ADEC51' the element 'x' of type u8<1>
	mov rsi, stack_FD3E5429
	; Started stack 'stack_FD3E5429' of size 128
	mov byte [rsi], 4
	add rsi, 1
	mov rsi, mem_F2ADEC51
	mov rax, stack_FD3E5429
	mov al, byte [rax]
	mov byte [rsi], al
	add rsi, 1
	; Exit instruction
	mov rsi, stack_AF7643F8
	; Started stack 'stack_AF7643F8' of size 128
	mov rax, mem_F2ADEC51
	mov al, byte [rax]
	mov byte [rsi], al
	add rsi, 1
	mov byte [rsi], 1
	add rsi, 1
	; Add stack operator
	mov rbx, 0x0000000000000000
	mov rcx, 0x0000000000000000
	sub rsi, 1
	mov qword [rbx], rsi
	sub rsi, 1
	mov qword [rcx], rsi
	add rbx, rcx
	mov rdi, rbx
	mov al, byte [rdi]
	mov byte [rsi], al
	add rsi, 1
	mov rax, 60
	mov rsi, stack_AF7643F8
	movzx rdi, byte [rsi]
	syscall 
	mov rsi, stack_FD3E5429
	mov rsi, stack_AF7643F8
segment readable writeable
	mem_F2ADEC51 rb 512
	stack_FD3E5429 rb 128
	stack_AF7643F8 rb 128
