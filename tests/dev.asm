format ELF64 executable 3
segment readable executable
	; Ini instruction
	; Added to memory 'mem_E8664B30' the element 'x' of type u8<1>
	mov rsi, stack_DD7D40D2
	; Started stack 'stack_DD7D40D2' of size 128
	mov byte [rsi], 4
	add rsi, 1
	mov rsi, mem_E8664B30
	mov rax, stack_DD7D40D2
	mov al, byte [rax]
	mov byte [rsi], al
	add rsi, 1
	; Exit instruction
	mov rsi, stack_FD70A203
	; Started stack 'stack_FD70A203' of size 128
	mov rax, mem_E8664B30
	mov al, byte [rax]
	mov byte [rsi], al
	add rsi, 1
	mov rax, mem_E8664B30
	mov al, byte [rax]
	mov byte [rsi], al
	add rsi, 1
	; Add stack operator
	mov rbx, stack_FD70A203
	mov rcx, stack_FD70A203
	sub rsi, 1
	movzx rbx, byte [rsi]
	sub rsi, 1
	movzx rcx, byte [rsi]
	add rbx, rcx
	mov byte [rsi], bl
	mov byte [rsi], 4
	add rsi, 1
	; Add stack operator
	mov rbx, stack_FD70A203
	mov rcx, stack_FD70A203
	sub rsi, 1
	movzx rbx, byte [rsi]
	sub rsi, 1
	movzx rcx, byte [rsi]
	add rbx, rcx
	mov byte [rsi], bl
	mov rax, 60
	mov rsi, stack_FD70A203
	movzx rdi, byte [rsi]
	syscall 
	mov rsi, stack_DD7D40D2
	mov rsi, stack_FD70A203
segment readable writeable
	mem_E8664B30 rb 512
	stack_DD7D40D2 rb 128
	stack_FD70A203 rb 128
