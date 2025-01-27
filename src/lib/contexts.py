import llvmlite.ir as ir

class Context():
    """
    The base class for contexts.
    """

    builder:ir.builder
    final_block:ir.Block

    def __init__(self, builder:ir.builder, final_block:ir.Block):
        self.builder = builder
        self.final_block = final_block
    