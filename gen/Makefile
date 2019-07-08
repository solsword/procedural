seed:
	head -c 3 /dev/urandom | hexdump -e '"%u"' > $@

.PHONY: reseed
reseed:
	rm seed
	make seed

.DEFAULT_GOAL := run
.PHONY: run
run: *.lp seed
	clingo --outf=3 --seed=`cat seed` run.lp || true

.PHONY: fresh
fresh: reseed run

.PRECIOUS: puzzles.json
puzzles.json: *.lp seed
	clingo --outf=3 --seed=`cat seed` run.lp > $@ || true
