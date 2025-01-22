from llvmlite import ir, binding

# Création du module LLVM
module = ir.Module(name="example_module")

# Création d'un type entier 32 bits
int_type = ir.IntType(32)

# Création d'une fonction qui prend un pointeur en argument
func_type = ir.FunctionType(int_type, [ir.PointerType(int_type)])
function = ir.Function(module, func_type, name="dereference_pointer")

# Création d'un bloc de base
block = function.append_basic_block(name="entry")
builder = ir.IRBuilder(block)

# Allocation d'une variable de type int et initialisation
alloca = builder.alloca(int_type, name="a")
builder.store(ir.Constant(int_type, 42), alloca)  # Stocke la valeur 42 dans 'a'

# Chargement de la valeur à l'adresse de 'alloca'
load = builder.load(alloca)

# Retourner la valeur
builder.ret(load)

# Afficher le code LLVM généré
print(module)
