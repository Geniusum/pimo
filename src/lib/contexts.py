import llvmlite.ir as ir
import lib.lang as lang
import lib.values as values

class Context():
    """
    The base class for contexts.
    """

    builder:ir.IRBuilder
    final_block:ir.Block

    def __init__(self, builder:ir.IRBuilder):
        self.builder = builder

class IfContext(Context):
    def __init__(self, builder):
        super().__init__(builder)
        self.final_block = self.builder.append_basic_block("final")
        self.interms:list[ir.Block] = []
        self.elif_blocks:list[ir.Block] = []
        self.if_block:ir.Block = self.builder.append_basic_block("if")
        self.else_block:ir.Block = self.builder.append_basic_block("else")
        self.if_builder:ir.IRBuilder = self.get_builder(self.if_block)
        self.else_builder:ir.IRBuilder = self.get_builder(self.else_block)
        self.else_made = False

    def get_active_interm(self) -> ir.Block: return self.interms[-1]
    
    def get_active_elif_block(self) -> ir.Block: return self.elif_blocks[-1]
    
    def create_interm(self) -> tuple[ir.Block, ir.IRBuilder]:
        interm = self.builder.append_basic_block("interm")
        interm_builder = ir.IRBuilder(interm)
        self.interms.append(interm)
        return interm, interm_builder
    
    def create_elif(self) -> tuple[ir.Block, ir.IRBuilder]:
        elif_block = self.builder.append_basic_block("elif")
        elif_builder = ir.IRBuilder(elif_block)
        self.elif_blocks.append(elif_block)
        return elif_block, elif_builder
    
    def get_builder(self, block:ir.Block) -> ir.IRBuilder: return ir.IRBuilder(block)

    def position_at_final(self):
        if not self.else_made:
            self.make_else()
        self.builder.position_at_end(self.final_block)

    def make_if(self, condition:ir.Value, interm_after:bool=False):
        if not interm_after:
            self.builder.cbranch(condition, self.if_block, self.else_block)
        else:
            elif_block, elif_builder = self.create_elif()
            interm, interm_builder = self.create_interm()
            self.builder.cbranch(condition, self.if_block, interm)
        if not self.if_block.is_terminated:
            self.if_builder.branch(self.final_block)
        if interm_after: return interm, interm_builder
    
    def make_elif(self, condition:ir.Value, interm_after:bool=False):
        interm = self.get_active_interm()
        interm_builder = self.get_builder(interm)
        elif_block = self.get_active_elif_block()
        elif_builder = self.get_builder(elif_block)
        if not interm_after:
            interm_builder.cbranch(condition, elif_block, self.else_block)
        else:
            new_interm, new_interm_builder = self.create_interm()
            interm_builder.cbranch(condition, elif_block, new_interm)
        if not elif_block.is_terminated:
            elif_builder.branch(self.final_block)

    def make_else(self):#, act_builder:ir.IRBuilder):
        self.else_made = True
        if not self.else_block.is_terminated:
            self.else_builder.branch(self.final_block)

class WhileContext(Context):
    def __init__(self, builder):
        super().__init__(builder)
        self.final_block = self.builder.append_basic_block("final")
        self.while_block = self.builder.append_basic_block("while")
        self.while_builder = self.get_builder(self.while_block)
    
    def make_while(self, cond_value_1:values.LiteralValue, cond_value_2:values.LiteralValue, act_builder:ir.IRBuilder):
        cond_1 = self.builder.icmp_unsigned("!=", cond_value_1.value, lang.FALSE)
        self.builder.cbranch(cond_1, self.while_block, self.final_block)

        if not self.while_block.is_terminated:
            self.while_builder.position_at_end(self.while_block)
            cond_2 = self.while_builder.icmp_unsigned("!=", cond_value_2.value, lang.FALSE)
            self.while_builder.cbranch(cond_2, self.while_block, self.final_block)
        else:
            self.while_builder.position_at_end(act_builder.block)
            cond_2 = act_builder.icmp_unsigned("!=", cond_value_2.value, lang.FALSE)
            act_builder.cbranch(cond_2, self.while_block, self.final_block)

    def position_at_final(self):
        self.builder.position_at_end(self.final_block)
    
    def get_builder(self, block:ir.Block) -> ir.IRBuilder: return ir.IRBuilder(block)