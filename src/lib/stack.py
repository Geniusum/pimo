import llvmlite.ir as ir
import lib.lang as lang

# TODO: Use shared push & pop functions

class Stack():
    def __init__(self, builder:ir.IRBuilder, size:int, id:str):
        self.size = size
        self.id = id
        self.element_type = ir.ArrayType(lang.UNSIGNED_64, 2)
        self.type = ir.global_context.get_identified_type(f"stacktype_{id}")
        self.type.set_body(
            ir.ArrayType(lang.VOID_PTR, self.size),
            lang.UNSIGNED_32,  # Top
            lang.UNSIGNED_32   # Size
        )
        self.builder = builder
        self.block = self.builder.block
        self.module = self.block.module

        self.push_function = self.define_push()
        self.pop_function = self.define_pop()

        self.stack = self.builder.alloca(self.type, self.size, f"stack_{id}")

        self.top_ptr = self.builder.gep(
            self.stack,
            [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 1)],
            name=f"stacktop_{id}"
        )
        self.builder.store(ir.Constant(lang.UNSIGNED_32, 0), self.top_ptr)
        
        self.size_ptr = self.builder.gep(
            self.stack,
            [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 2)],
            name=f"stacksize_{id}"
        )
        self.builder.store(ir.Constant(lang.UNSIGNED_32, self.size), self.size_ptr)

        self.base_ptr = self.builder.gep(
            self.stack,
            [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 0)],
            name=f"stackbase_{self.id}"
        )
    
    def push(self, value:ir.Value):
        if not value.type.is_pointer:
            alloca = self.builder.alloca(value.type)
            self.builder.store(value, alloca)
            value = alloca
        cast_value = self.builder.bitcast(value, lang.VOID_PTR)
        return self.builder.call(self.push_function, [self.stack, cast_value])

    def push_top_ptr(self):  # TODO: Fix
        self.push(self.top_ptr)

    def push_base_ptr(self):  # TODO: Fix
        self.push(self.base_ptr)
    
    def push_size(self):
        self.push(self.builder.load(self.size_ptr))

    def pop(self):
        return self.builder.call(self.pop_function, [self.stack])

    def pop_val(self):
        return self.builder.load(self.pop())

    def define_push(self):
        push_func_type = ir.FunctionType(ir.VoidType(), [self.type.as_pointer(), lang.VOID_PTR])
        push_func = ir.Function(self.module, push_func_type, name=f"push_{self.id}")

        push_block = push_func.append_basic_block(name="entry")
        push_builder = ir.IRBuilder(push_block)

        stack_ptr, value_ptr = push_func.args

        top_ptr = push_builder.gep(stack_ptr, [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 1)], name="top_ptr")
        size_ptr = push_builder.gep(stack_ptr, [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 2)], name="size_ptr")

        top = push_builder.load(top_ptr, name="top")
        size = push_builder.load(size_ptr, name="size")

        is_full = push_builder.icmp_unsigned("==", top, size, name="is_full")
        with push_builder.if_else(is_full) as (then, otherwise):
            with then:
                push_builder.ret_void()

            with otherwise:
                element_ptr = push_builder.gep(stack_ptr, [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 0), top], name="element_ptr")
                element_ptr = push_builder.bitcast(element_ptr, lang.VOID_PTR.as_pointer(), name="cast_element_ptr")

                push_builder.store(value_ptr, element_ptr)

                new_top = push_builder.add(top, ir.Constant(lang.UNSIGNED_32, 1), name="new_top")
                push_builder.store(new_top, top_ptr)

        push_builder.ret_void()

        return push_func

    def define_pop(self):
        pop_func_type = ir.FunctionType(lang.VOID_PTR, [self.type.as_pointer()])
        pop_func = ir.Function(self.module, pop_func_type, name=f"pop_{self.id}")

        pop_block = pop_func.append_basic_block(name="entry")
        pop_builder = ir.IRBuilder(pop_block)

        stack_ptr = pop_func.args[0]

        top_ptr = pop_builder.gep(stack_ptr, [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 1)], name="top_ptr")
        top = pop_builder.load(top_ptr, name="top")

        is_empty = pop_builder.icmp_unsigned("==", top, ir.Constant(lang.UNSIGNED_32, 0), name="is_empty")
        with pop_builder.if_else(is_empty) as (then, otherwise):
            with then:
                pop_builder.ret(lang.NULL_PTR)

            with otherwise:
                new_top = pop_builder.sub(top, ir.Constant(lang.UNSIGNED_32, 1), name="new_top")
                pop_builder.store(new_top, top_ptr)

                element_ptr = pop_builder.gep(
                    stack_ptr,
                    [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 0), new_top],
                    name="element_ptr"
                )

                element_ptr = pop_builder.load(element_ptr)

                pop_builder.ret(element_ptr)
        
        pop_builder.ret(lang.NULL_PTR)

        return pop_func