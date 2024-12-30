format ELF64 executable 3
segment readable executable
	mov rax, stack_E629DAD82AC43EB86049C4F8
	mov byte [rax], 3
	mov rax, stack_E629DAD82AC43EB86049C4F8
	add rax, 1
	mov byte [rax], 4
	mov rax, 60
	mov rdi, 0
	syscall 
segment readable writeable
	stack_F4409996DAB822573DC0CDD5 rb 128
	stack_E629DAD82AC43EB86049C4F8 rb 128
	mem_FEB9E81F870255EF25B65737 rb 512
