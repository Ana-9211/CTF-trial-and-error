# Reproducible build for the Aurora License VM challenge.
# 1. regenerate bytecode from the flag, 2. splice into vm.c, 3. compile+strip.
all: vm

bytecode.inc: build_bytecode.py
	python3 build_bytecode.py

vm_built.c: vm.c bytecode.inc
	python3 -c "vm=open('vm.c').read(); bc=open('bytecode.inc').read(); open('vm_built.c','w').write(vm.replace('/*BYTECODE*/', bc.rstrip()))"

vm: vm_built.c
	gcc -O2 -o vm vm_built.c
	strip vm

clean:
	rm -f vm vm_built.c

.PHONY: all clean
