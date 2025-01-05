format ELF64 executable 3
segment readable executable
	; Exit instruction
	mov rsi, stack_DF255AD4
	; Started stack 'stack_DF255AD4' of size 128
	mov byte [rsi], 1
	add rsi, 1
	mov byte [rsi], 2
	add rsi, 1
	; Add stack operator
	mov rbx, stack_DF255AD4
	mov rcx, stack_DF255AD4
	sub rsi, 1
	mov al, byte [rsi]
	mov byte [rbx], al
	mov byte [rbx + 1], 0
	mov byte [rbx + 2], 0
	mov byte [rbx + 3], 0
	mov byte [rbx + 4], 0
	mov byte [rbx + 5], 0
	mov byte [rbx + 6], 0
	mov byte [rbx + 7], 0
	sub rsi, 1
	mov al, byte [rsi]
	mov byte [rcx], al
	mov byte [rcx + 1], 0
	mov byte [rcx + 2], 0
	mov byte [rcx + 3], 0
	mov byte [rcx + 4], 0
	mov byte [rcx + 5], 0
	mov byte [rcx + 6], 0
	mov byte [rcx + 7], 0
	add rbx, rcx
	mov al, byte [rbx]
	mov byte [rsi], al
	add rsi, 1
	; End add stack operator
	mov rax, 60
	mov rsi, stack_DF255AD4
	movzx rdi, byte [rsi]
	syscall 
	mov rsi, stack_DF255AD4
segment readable writeable
	mem_FE17CF44 rb 512
	stack_DF255AD4 rb 128
