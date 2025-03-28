import llvmlite.ir as ir
import lib.lang as lang

class Name():
    """
    The base class for names.
    """

    class NameNotFound(BaseException): ...
    class NameAlreadyTaken(BaseException): ...
    
    compiler:any
    parent:any
    module:ir.Module
    names:dict

    def get_from_path(self, path:str, error:bool=True):
        path_parts = path.split(".")
        active:Name = self
        for part in path_parts:
            if not part in active.names.keys():
                if part == lang.CARET:
                    active = active.parent
                else:
                    if error:
                        self.compiler.raise_exception(self.NameNotFound)
                    else:
                        active = None
                        break
            else:
                active = active.names[part]
        return active

    def exists(self, name:str) -> bool:
        return name in list(self.names.keys())
    
    def append(self, name:str, nameclass, *args, **kwargs):
        if self.exists(name):
            self.compiler.raise_exception(self.NameAlreadyTaken)
        self.names[name] = nameclass(self, self.compiler, self.module, name, *args, **kwargs)
        return self.names[name]

class GlobalScope(Name):
    def __init__(self, compiler, module, parent=None):
        self.compiler = compiler
        self.module = module
        self.parent = parent
        if self.parent is None: self.parent = self
        self.names = {}

class Variable(Name):
    def __init__(self, parent:Name, compiler:any, module:ir.Module, name:str, type:ir.Type, init_value:ir.Value=None, constant:bool=False):
        self.parent = parent
        self.is_root = self.parent == self.parent.parent
        self.compiler = compiler
        self.id = self.compiler.generate_id()
        self.module = module
        self.name = name
        self.names = {}
        self.type = type
        self.var = ir.GlobalVariable(self.module, self.type.as_pointer(), f"var_{self.id}" if not self.is_root else self.name)
        if init_value:
            self.var.initializer = init_value
        else:
            self.var.initializer = ir.Constant(self.type.as_pointer(), None)
        self.var.global_constant = constant
    
    def get_value(self, builder:ir.IRBuilder, type:ir.Type=None):
        if type is None: type = self.type
        if builder.load(self.var).type != self.type.as_pointer():
            return builder.load(builder.bitcast(builder.load(self.var), self.type.as_pointer()))
        else:
            return builder.load(builder.load(self.var))
    
    def assign_value(self, builder:ir.IRBuilder, value:ir.Value):
        builder.store(value, self.var)

class Function(Name):
    def __init__(self, parent:Name, compiler:any, module:ir.Module, name:str, type:ir.FunctionType, genargs:bool=True, vararg:bool=False):
        self.parent = parent
        self.is_root = self.parent == self.parent.parent
        self.compiler = compiler
        self.id = self.compiler.generate_id()
        self.module = module
        self.name = name
        self.names = {}
        self.type = type
        self.vararg = vararg
        nmid = f"func_{self.id}" if not self.is_root else self.name
        if self.parent.parent == self.parent and self.name == "main":
            nmid = "main"
        self.func = ir.Function(self.module, self.type, nmid)
        if genargs: self.gen_args()

    def gen_args(self):
        if len(self.func.args):
            try: builder = ir.IRBuilder(self.func.entry_basic_block)
            except: builder = ir.IRBuilder(self.func.append_basic_block("entry"))
            for arg in self.func.args:
                arg_ptr = builder.alloca(arg.type)
                builder.store(arg, arg_ptr)
                argvar = self.append(arg.name.replace(".", "_"), Variable, arg.type)
                argvar.assign_value(builder, arg_ptr)

class Structure(Name):
    ...