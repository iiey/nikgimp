# ShellOut GIMP Plugin

A GIMP Python plugin that allows you to call external programs (like Nik Collection) passing the active layer as a temporary file.

## Compatibility

- Only compatible with GIMP `version < 2.99.x`
- Works under Windows
- Primarily designed for use with Google Nik Collection filters

## Installation

1. Copy the `shellout.py` script into the GIMP plug-ins folder:
	```sh
	GIMP_INSTALLATION_PATH/lib/gimp/2.0/plug-ins/
	```

	Modify the `programlist` in the script to add your own external programs or update paths if needed.

2. Make sure the script is executable

3. Restart GIMP

## Disclaim

I'm not the original author of this plug-in (see LICENSE and CHANGES embedded in the source code file).