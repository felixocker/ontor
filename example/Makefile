## all			: Create all onto files.
.PHONY : all
all : example.py onto-ex.owl onto-ex-add.owl
	python $<

## onto-ex.owl		: Create example onto.
onto-ex.owl : onto_ex.py
	python $^

## onto-ex-add.owl	: Create additional example onto.
onto-ex-add.owl : onto_ex_add.py
	python $^

## clean		: Remove all generated files.
.PHONY : clean
clean:
	rm -f *.owl
	rm -f *.log
	rm -rf __pycache__/

## help			: Return help info.
.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<

