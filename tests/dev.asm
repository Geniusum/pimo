format ELF64 executable 3
segment readable executable
	; Ini instruction
	; Added to memory 'mem_A4DB78F3' the element 'x' of type u8<1>
	mov rsi, stack_F72A9A75
	; Started stack 'stack_F72A9A75' of size 128
	mov byte [rsi], 4
	add rsi, 1
	mov rsi, mem_A4DB78F3
	mov rax, stack_F72A9A75
	mov al, byte [rax]
	mov byte [rsi], al
	add rsi, 1
	; Exit instruction
	mov rsi, stack_AF9B0D13
	; Started stack 'stack_AF9B0D13' of size 128
	mov rax, mem_A4DB78F3
	mov al, byte [rax]
	mov byte [rsi], al
	add rsi, 1
	mov rax, mem_A4DB78F3
	mov al, byte [rax]
	mov byte [rsi], al
	add rsi, 1
	; Add stack operator
	mov rbx, stack_AF9B0D13
	mov rcx, stack_AF9B0D13
	sub rsi, 1
	movzx rbx, byte [rsi]
	sub rsi, 1
	movzx rcx, byte [rsi]
	add rbx, rcx
	mov byte [rsi], bl
	add rsi, 1
	mov byte [rsi], 4
	add rsi, 1
	mov byte [rsi], 8
	add rsi, 1
	; Add stack operator
	mov rbx, stack_AF9B0D13
	mov rcx, stack_AF9B0D13
	sub rsi, 1
	movzx rbx, byte [rsi]
	sub rsi, 1
	movzx rcx, byte [rsi]
	add rbx, rcx
	mov byte [rsi], bl
	add rsi, 1
	; Add stack operator
	mov rbx, stack_AF9B0D13
	mov rcx, stack_AF9B0D13
	sub rsi, 1
	movzx rbx, byte [rsi]
	sub rsi, 1
	movzx rcx, byte [rsi]
	add rbx, rcx
	mov byte [rsi], bl
	add rsi, 1
	mov rax, 60
	mov rsi, stack_AF9B0D13
	movzx rdi, byte [rsi]
	syscall 
	mov rsi, stack_F72A9A75
	mov rsi, stack_AF9B0D13
segment readable writeable
	mem_A4DB78F3 rb 512
	stack_F72A9A75 rb 128
	stack_AF9B0D13 rb 128
