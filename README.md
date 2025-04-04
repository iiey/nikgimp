[![ci](https://github.com/iiey/nikgimp/actions/workflows/linting.yml/badge.svg?branch=main)](https://github.com/iiey/nikgimp/actions/workflows/linting.yml)

# nikgimp

A Python GIMP plugin for processing images using **external** Nik Collection programs.

## Compatibility

**Prerequisites:** Make sure the *Google Nik Collection* is installed on your system before proceeding.<br>
It was tested with the `v1.2.11`, you could still find it on the internet<br>
or try this download link [Google Nik Collection v1.2.11][download_link],
which contains both Win & Mac installation.

- GIMP version `>= 3.0.0`
- Windows 10, 11 (tested)
- Unix-like i.e. Linux with Wine & MacOS may need a little further fine-tune

## Installation

1. Create a folder named `nikplugin/` under the *plug-ins folder of your GIMP installation*
2. Copy [nikplugin.py](nikplugin.py) (latest) into the folder and ensure that the script is *executable*
    ```sh
    GIMP_INSTALLATION_PATH/lib/gimp/3.0/plug-ins/nikplugin/nikplugin.py
    ```
3. (Re)start GIMP, the plugin should appear under the menu `Filters > NikCollection`

**Note**: For details see [Wiki - Installation][wiki_install]<br>
**Note**: see also [TROUBLESHOOTING][troubles] if Nik is installed in a *non-default location*.

### Update
- Replace the script with the latest version or [stable releases][releases] `nikplugin.py` in this repository and restart GIMP

### Uninstall
- Remove the folder `nikplugin/` from your `plugin-ins` directory

## Usage

After installation, you can access the Nik Collection filters from GIMP's Filters menu.<br>
The plugin sends the current image to the selected Nik Collection program, and after processing, will return the result to GIMP.<br>
See [demo video][wiki_demo].

## License

This code revises the original `shellout.py` script to make it compatible with the API in GIMP `v3.x`.
It maintains the same functionality but updates the implementation to work with the [GIMP Python API v3.0][api30].

This plugin has the same license `GNU GPLv3` as the original [shellout.py][gimp2_shellout] script it's based on.


<!--references-->
[api30]: https://developer.gimp.org/api/3.0
[download_link]: https://www.techspot.com/downloads/6809-google-nik-collection.html
[gimp2_shellout]: https://github.com/iiey/nikgimp/blob/main/gimp2x/shellout.py
[releases]: https://github.com/iiey/nikgimp/blob/main/CHANGELOG.md
[troubles]: https://github.com/iiey/nikgimp/blob/main/troubleshooting.md
[wiki_install]: https://github.com/iiey/nikgimp/wiki/install
[wiki_demo]: https://github.com/iiey/nikgimp/wiki/demo