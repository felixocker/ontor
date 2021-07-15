## all			: Create all onto files.
.PHONY : all
all : example.py 
	python $<

## clean		: Remove all generated files.
.PHONY : clean
clean:
	rm -f *.owl
	rm -f *.nt
	rm -f *.log
	rm -rf __pycache__/
	find ../ontor -name __pycache__ -exec rm -rf {} \;

## help			: Return help info.
.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<

