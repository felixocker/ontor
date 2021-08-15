## all			: Create all onto files.
.PHONY : all
all : example.py 
	python $<

## clean		: Remove all generated files.
.PHONY : clean
clean:
	rm -f *.owl
	rm -f *.nt
	find ../ -name "*.log" -type f -delete
	rm -f *.xml
	rm -f *.html
	rm -rf __pycache__/
	find ../ontor -name "__pycache__" -exec rm -rf {} \;
	rm -rf ../docs/build

## help			: Return help info.
.PHONY : help
help : Makefile
	@sed -n 's/^##//p' $<

