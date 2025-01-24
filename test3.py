import llvmlite.ir as ir
import llvmlite.binding as llvm
import ctypes

# Initialisation de LLVM pour la génération de code
llvm.initialize()
llvm.initialize_native_target()
llvm.initialize_native_asmprinter()

# Création du module LLVM
module = ir.Module(name="printf_example")

# Déclaration de printf
printf_type = ir.FunctionType(ir.IntType(32), [ir.PointerType(ir.IntType(8))], var_arg=True)
printf_func = ir.Function(module, printf_type, name="printf")

# Fonction principale
main_type = ir.FunctionType(ir.IntType(32), [])
main_func = ir.Function(module, main_type, name="main")

# Bloc d'entrée de la fonction main
entry_block = main_func.append_basic_block(name="entry")
builder = ir.IRBuilder(entry_block)

# Définir une chaîne de caractères à afficher avec printf
format_str = builder.alloca(ir.ArrayType(ir.IntType(8), 14))  # 14 caractères pour "Hello, world!\n"
builder.store(ir.Constant(ir.ArrayType(ir.IntType(8), 14), bytearray(b"Hello, world!\n")), format_str)

# Appeler printf
builder.call(printf_func, [builder.bitcast(format_str, ir.PointerType(ir.IntType(8)))])

# Retourner 0
builder.ret(ir.Constant(ir.IntType(32), 0))

# Vérification du module
print(module)