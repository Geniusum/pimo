# Problems with Pimo

## Problem #1

**Statut :** in progress

All stacks, memories and other are closely followed by the compiler. If we want be example use a stack in a loop, the stack operations couldn't be followed by the compiler because the loop will be made in the assembly program.

For correct this design error, we need to prepare some functions in the assembly program (with fasm stuffs) who operate with stacks, memories directly in the assembly. Theses functions will don't appear on the output if they aren't used (for optimisations).

We need to know if it's possible to reserve bytes dynamically. We need to change ALL.