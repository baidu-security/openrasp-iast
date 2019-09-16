name="openrasp/iast-test-env"

default: build run

build:
	docker build -t $(name) .

run: build
	docker run --rm -it $(name) /bin/bash
