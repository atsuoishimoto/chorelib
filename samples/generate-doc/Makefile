DOC = DOC.txt
SRCFILES = a.txt b.txt c.txt
COMMON = inc1.txt inc2.txt

$(DOC): $(SRCFILES) $(COMMON)
	cat $^ > $@

.PHONY: clean
clean:
	rm -f $(DOC)
