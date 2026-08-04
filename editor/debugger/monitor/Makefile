.PHONY: all format test build debug clean

all: format test build

format:
	clang-format src/* include/* -i

test:
	@echo "Running tests..."
	# Writing tests later ...

build:
	mkdir -p build
	cd build && \
	cmake .. && \
	make

debug:
	mkdir -p build
	cd build && \
	cmake -DCMAKE_BUILD_TYPE=Debug .. && \
	make

clean:
	rm -rf build
