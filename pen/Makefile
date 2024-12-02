.PHONY: all compile upload
compile:
	arduino-cli compile -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 .

upload:
	arduino-cli upload -p /dev/ttyUSB0 --fqbn esp32:esp32:esp32 .

all: compile upload
