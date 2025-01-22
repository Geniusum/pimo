; ModuleID = "tests/dev2.pim"
target triple = "x86_64-linux-gnu"
target datalayout = ""

declare i8 @"add"(i8 %".1", i8 %".2")

define i8 @"main"()
{
entry:
  %".2" = alloca i8
  store i8 4, i8* %".2"
  ret i8 4
}
