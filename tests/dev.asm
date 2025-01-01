format ELF64 executable 3
segment readable executable
	mov rsi, stack_C66FCDE292A8929EA88B98FF
	mov tword [rsi], 25698721928398612464
	add rsi, 10
	mov rax, 60
	mov rsi, stack_C66FCDE292A8929EA88B98FF
	movzx rdi, byte [rsi]
	syscall 
segment readable writeable
	stack_C66FCDE292A8929EA88B98FF rb 32
	mem_MAIN rb 512
