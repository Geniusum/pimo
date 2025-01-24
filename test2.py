from llvmlite import ir, binding

# 1. Création du module et du contexte LLVM
module = ir.Module(name="u8_pointer_example")
builder = None

# 2. Déclaration des types nécessaires
i8 = ir.IntType(8)           # Type u8
i8_ptr = i8.as_pointer()     # Type u8*
i8_ptr_ptr = i8_ptr.as_pointer()  # Type u8**

# 3. Fonction pour accéder au u8**
func_type = ir.FunctionType(i8, [i8_ptr_ptr])  # Retourne un u8 à partir d'un u8**
func = ir.Function(module, func_type, name="get_u8_value")

# Création d'un bloc de base
entry_block = func.append_basic_block(name="entry")
builder = ir.IRBuilder(entry_block)

# Récupérer l'argument de la fonction
u8_pp = func.args[0]

# Déréférencement du premier niveau pour obtenir u8*
u8_p = builder.load(u8_pp, name="load_u8_ptr")

# Déréférencement du deuxième niveau pour obtenir u8
u8_value = builder.load(u8_p, name="load_u8_value")

# Retourner la valeur u8
builder.ret(u8_value)

# Afficher le module généré
print(module)

# 4. Initialisation et exécution avec LLVM (binding)
binding.initialize()
binding.initialize_native_target()
binding.initialize_native_asmprinter()

# Compilation et exécution si nécessaire
llvm_ir = str(module)
print("\nLLVM IR Generated:\n", llvm_ir)
