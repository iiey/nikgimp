# nikGimp

A Python GIMP plugin for processing images using **external** Nik Collection programs.

## Compatibility

**Prerequisites:** Make sure the *Google Nik Collection* is installed on your system before proceeding.<br>
It was tested with the `v1.2.11`, you could still it find on the internet or try to download from [here](https://www.techspot.com/downloads/6809-google-nik-collection.html).

- GIMP version `>= 3.0.0`
- Windows 10, 11 (under Unix i.e. Linux/Mac may need a little further fine-tune, not tested).

## Installation

1. Create a folder named `nikplugin/` under the *plug-ins folder of your GIMP installation*,
2. Copy `nikplugin.py` into the folder and ensure that the script is *executable*
    ```sh
    GIMP_INSTALLATION_PATH/lib/gimp/3.0/plug-ins/nikplugin/nikplugin.py
    ```
3. Open the script and adapt the software installation path `NIK_BASE_PATH` to match your system configuration
4. (Re)start GIMP, the plugin should appear under the menu `Filters > NikCollection`

## Usage

After installation, you can access the Nik Collection filters from GIMP's Filters menu.

The plugin sends the current image to the selected Nik Collection program, and after processing, will return the result to GIMP.

## Notes

This code revises the original `shellout.py` script to make it compatible with the API in GIMP `v3.x`.
It maintains the same functionality but updates the implementation to work with the [GIMP Python API v3.0](https://developer.gimp.org/api/3.0).

## License

This plugin has the same license as the original [shellout.py](gimp2x/shellout.py) script it's based on.


# Troubleshooting

## Plugin doesn't show up in the menu

<details>

Please verify with these following checks.<br>
In most case a new reinstallation of [latest GIMP3 version](https://www.gimp.org/downloads/) resolves the issues.<br>
After all, you could find posts, ask [gimp-format.net](https://www.gimp-forum.net/Forum-Gimp-2-99-Gimp-3-0) or file an [issue report](https://github.com/iiey/nikGimp/issues)
with details.

### 1. Verify GIMP installation

Ensure GIMP3 is properly installed with Python support:

1. Add official demo plugin `GIMP_INSTALL/lib/gimp/3.0/plug-ins/test-dialog/`[test-dialog.py](https://gitlab.gnome.org/GNOME/gimp/-/blob/master/plug-ins/python/test-dialog.py)
2. Restart GIMP and check if the test plugin appears under `Filters > Development > Demos`
3. If the `Test dialog...` plugin isn't there either, then is not an issue with this plugin
but general GIMP problem, a reinstallation may help.

### 2. Check plugin location

In GIMP, go to `Edit > Preferences > Folders > Plug-ins`, ensure that we placed plugin folder in one of the listed directories there. This may differ between machine-wide and user installations.

### 3. Test Python module availability

1. Open `GIMP > Filters > Development > Python-Fu > Python Console`
2. Input [these imports](https://github.com/iiey/nikGimp/blob/9c1e5f927679043a5f9697b31e055647cbd3f3a2/nikplugin.py#L18-L32) into the interpreter and press `Enter`:
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

- Ensure you downloaded the latest version of the plugin and the file content is intact, as Python is sensitive to indentation.
- About the permission, the script should be *executable*. Not sure whether it's really necessary, but it may worth to check:
    - Under Unix, `chmod +x nikplugin.py`
    - Under Win, right-click `nikplugin.py` *> Properties > Security* and ensure *Read & Execute* permissions are enabled.

### 5. Check for error messages

Run GIMP console in verbose mode from command-line:
```
GIMP_INSTALL/bin/gimp-console-3.0.exe --verbose
```

If error occurs, gimp reinstallation may resolve issue or file a report.

</details>
