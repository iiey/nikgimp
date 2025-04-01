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
2. Copy [nikplugin.py](nikplugin.py) into the folder and ensure that the script is *executable*
    ```sh
    GIMP_INSTALLATION_PATH/lib/gimp/3.0/plug-ins/nikplugin/nikplugin.py
    ```
3. (Re)start GIMP, the plugin should appear under the menu `Filters > NikCollection`

**Note**: For details see [Wiki - Installation](https://github.com/iiey/nikgimp/wiki/install)<br>
**Note**: see also [Troubleshooting](#custom-installation-path) if Nik is installed in a non-default location.

### Update
- Replace the script with the [latest version][releases] `nikplugin.py` in this repository and restart GIMP

### Uninstall
- Remove the folder `nikplugin/` from your `plugin-ins` directory

## Usage

After installation, you can access the Nik Collection filters from GIMP's Filters menu.

The plugin sends the current image to the selected Nik Collection program, and after processing, will return the result to GIMP.

## License

This code revises the original `shellout.py` script to make it compatible with the API in GIMP `v3.x`.
It maintains the same functionality but updates the implementation to work with the [GIMP Python API v3.0][api30].

This plugin has the same license `GNU GPLv3` as the original [shellout.py][gimp2_shellout] script it's based on.


# Troubleshooting

## Custom installation path

<details>

Specify path in the variable `NIK_BASE_PATH` of the script to match your machine configuration,
If you have installed Nik Collection in a non-default location.<br>
Following paths are considered default:
- Linux with Wine: `$HOME/.wine/drive_c/Program Files`
- macOS: `/Application`
- Win: `C:/Program Files`

</details>

## Plugin doesn't show up in the menu

<details>

Please verify with these following checks.<br>
In most case a new reinstallation of [latest GIMP3 version](https://www.gimp.org/downloads/) resolves the issues.<br>
After all, you could find posts, ask [gimp-forum.net][gimp_forum] or file an [issue report][issue_report]
with details.

### 1. Verify GIMP installation

Ensure GIMP3 is properly installed with Python support:

1. Add official demo plugin `GIMP_INSTALL/lib/gimp/3.0/plug-ins/test-dialog/`[test-dialog.py][test_dialog]
2. Restart GIMP and check if the test plugin appears under `Filters > Development > Demos`
3. If the `Test dialog...` plugin isn't there either, then is not an issue with this plugin
but general GIMP problem, a reinstallation may help.

### 2. Check plugin location

In GIMP, go to `Edit > Preferences > Folders > Plug-ins`, ensure that we placed plugin folder in one of the listed directories there. This may differ between machine-wide and user installations.

### 3. Test Python module availability

1. Open `GIMP > Filters > Development > Python-Fu > Python Console`
2. Input [these imports][loc_libs] into the interpreter and press `Enter`:
```python
import gi
gi.require_version("Gimp", "3.0")
gi.require_version("GimpUi", "3.0")
gi.require_version("Gegl", "0.4")
from gi.repository import GLib
from gi.repository import GObject
from gi.repository import Gegl
from gi.repository import Gimp
from gi.repository import GimpUi
from gi.repository import Gio
from gi.repository import Gtk
```

Any error indicates that the necessary Python module is missing and it's a GIMP issue that reinstallation may help.

### 4. Check file & permissions

- Ensure you downloaded the latest version of the plugin and the *file content is intact*, as Python is sensitive to indentation.
- Under Unix-like, the script must has *executable* permission: `chmod +x nikplugin.py`

### 5. Check for error messages

Run GIMP console in verbose mode from command-line:
```
GIMP_INSTALL/bin/gimp-console-3.0.exe --verbose
```

If error occurs, gimp reinstallation may resolve issue or file a report.

</details>

## *HDR Efex Pro 2* warning

<details>

If you encounter the warning message `Plugin cannot identify 'Documents' path on your system`,<br>
you need to manually add your additional `Documents` path in your local script at [this location][loc_doc]<br>.
To determine the path by `right-click` on the folder and select `Documents Properties > Location`.

Explanation: The HDR program in this version doesn't override the input image when you click the "Save" button.<br>
Instead, it saves the output at its default location: `Documents/INPUT_FILENAME_HDR.ext`.<br>
Since the GIMP Python does not have the `win32com.client` module installed, it cannot determine the resolved "Documents" path.
Therefore, you need to specify it manually if it is configured differently from the default.

</details>


<!--references-->
[api30]: https://developer.gimp.org/api/3.0
[download_link]: https://www.techspot.com/downloads/6809-google-nik-collection.html
[gimp2_shellout]: https://github.com/iiey/nikgimp/blob/main/gimp2x/shellout.py
[gimp_forum]: https://www.gimp-forum.net/Forum-Gimp-2-99-Gimp-3-0
[issue_report]: https://github.com/iiey/nikGimp/issues
[loc_doc]: https://github.com/iiey/nikGimp/blob/29260dfe52e2e4afbd3f2bacf26f9fce0234369b/nikplugin.py#L154
[loc_libs]: https://github.com/iiey/nikGimp/blob/9c1e5f927679043a5f9697b31e055647cbd3f3a2/nikplugin.py#L18-L32
[releases]: https://github.com/iiey/nikgimp/blob/main/CHANGELOG.md
[test_dialog]: https://gitlab.gnome.org/GNOME/gimp/-/blob/master/plug-ins/python/test-dialog.py