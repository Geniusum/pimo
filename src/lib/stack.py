import llvmlite as llvm
import llvmlite.ir as ir
import lib.lang as lang

class Stack():
    def __init__(self, block:ir.Block, size:int, id:str):
        self.size = size
        self.id = id
        self.element_type = ir.ArrayType(lang.UNSIGNED_64, 2)
        self.type = ir.global_context.get_identified_type("Stack")
        self.type.set_body(
            ir.ArrayType(self.type, self.size),
            lang.UNSIGNED_32,
            lang.UNSIGNED_32
        )
        self.block = block
        self.module = self.block.module

        self.define_push()
        self.define_pop()

    def define_push(self):
        push_func_type = ir.FunctionType(ir.VoidType(), [self.stack_type.as_pointer(), lang.VOID_PTR])
        push_func = ir.Function(self.module, push_func_type, name=f"push_{id}")

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
        pop_func = ir.Function(self.module, pop_func_type, name="pop")

        pop_block = pop_func.append_basic_block(name="entry")
        pop_builder = ir.IRBuilder(pop_block)

        stack_ptr = pop_func.args[0]

        top_ptr = pop_builder.gep(stack_ptr, [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 1)], name="top_ptr")
        top = pop_builder.load(top_ptr, name="top")

        is_empty = pop_builder.icmp_unsigned("==", top, ir.Constant(lang.UNSIGNED_32, 0), name="is_empty")
        with pop_builder.if_else(is_empty) as (then, otherwise):
            with then:
                pop_builder.ret(lang.VOID_PTR.null())

            with otherwise:
                new_top = pop_builder.sub(top, ir.Constant(lang.UNSIGNED_32, 1), name="new_top")
                pop_builder.store(new_top, top_ptr)

                element_ptr = pop_builder.gep(stack_ptr, [ir.Constant(lang.UNSIGNED_32, 0), ir.Constant(lang.UNSIGNED_32, 0), new_top], name="element_ptr")
                element_ptr = pop_builder.bitcast(element_ptr, lang.VOID_PTR.as_pointer(), name="cast_element_ptr")

                pop_builder.ret(element_ptr)

        return pop_func