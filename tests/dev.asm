format ELF64 executable 3
segment readable executable
	; Exit instruction
	mov rsi, stack_DED7A35C
	; Started stack 'stack_DED7A35C' of size 128
	mov byte [rsi], 4
	add rsi, 1
	mov byte [rsi], 3
	add rsi, 1
	; Add stack operator
	mov rbx, stack_DED7A35C
	mov rcx, stack_DED7A35C
	sub rsi, 1
	movzx rbx, byte [rsi]
	sub rsi, 1
	movzx rcx, byte [rsi]
	add rbx, rcx
	mov byte [rsi], bl
	mov byte [rsi], 5
	add rsi, 1
	; Add stack operator
	mov rbx, stack_DED7A35C
	mov rcx, stack_DED7A35C
	sub rsi, 1
	movzx rbx, byte [rsi]
	sub rsi, 1
	movzx rcx, byte [rsi]
	add rbx, rcx
	mov byte [rsi], bl
	mov rax, 60
	mov rsi, stack_DED7A35C
	movzx rdi, byte [rsi]
	syscall 
	mov rsi, stack_DED7A35C
segment readable writeable
	mem_C8727BCB rb 512
	stack_DED7A35C rb 128
