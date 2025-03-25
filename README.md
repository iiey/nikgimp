# nikGimp

A Python GIMP plugin for processing images using **external** Nik Collection programs.

## Compatibility

- GIMP version `>= 3.0.0`
- Windows 10, 11

**Prerequisites:** Make sure the Nik Collection Software is installed on your system before proceeding.

## Installation

1. Create a folder named `nikplugin/` under the *plug-ins folder of your GIMP installation*,
2. Copy `nikplugin.py` into the folder and ensure that the script is executable
    ```sh
    GIMP_INSTALLATION_PATH/lib/gimp/3.0/plug-ins/nikplugin/nikplugin.py
    ```
3. Open the script and adapt the *Nik Collection installation path* to match your system configuration
4. (Re)start GIMP, the plugin should appear under the menu `Filters > NikCollection`

## Usage

After installation, you can access the Nik Collection filters from GIMP's Filters menu.

The plugin sends the current image to the selected Nik Collection program, and after processing, will return the result to GIMP.

## Notes

This code revises the original `shellout.py` script to make it compatible with the API in GIMP `v3.x`.
It maintains the same functionality but updates the implementation to work with the [GIMP Python API v3.0](https://developer.gimp.org/api/3.0).

## License

This plugin has the same license as the original [shellout.py](gimp2x/shellout.py) script it's based on.
