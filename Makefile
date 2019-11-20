default: build

build-test-env:
	@echo "Build test enviroment..."
	@root_path=$$(pwd); \
	make -C "$${root_path}/docker/test-env"  build

test:
	@echo "Run test cases..."
	@root_path=$$(pwd); \
	docker run --rm -v "$${root_path}:/code" openrasp/iast-test-env

clean:
	rm -rf log
	cd openrasp_iast && rm -rf log build dist .coverage .coverage.* htmlcov .pytest_cache 
	find ./openrasp_iast -name __pycache__ | xargs rm -rf
	find ./openrasp_iast -name '*.pyc' | xargs rm -rf
	rm -rf build dist *.egg-info

build:
	cd openrasp_iast && \
	pip3 install -r requirements.txt && \
	pyinstaller main.spec
