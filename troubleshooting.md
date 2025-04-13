# Troubleshooting

## Custom installation path

<details>

Specify path in the variable `NIK_BASE_PATH` of the script to the location of your Nik Collection installation,<br>
if you have installed the software in a non-default location.<br>

Following paths are considered *default* if the software is here, you don't need to adapt above path.:
- Linux with Wine: `$HOME/.wine/drive_c/Program Files/Google/Nik Collection`
- macOS: `/Application/Nik Collection`
- Win: `C:/Program Files/Google/Nik Collection`

</details>

## Plugin doesn't show up in the menu

<details>

Please verify with these following checks.<br>
In most case a new reinstallation of [latest GIMP3 version](https://www.gimp.org/downloads/) resolves the issues.<br>
After all, you could find posts, ask [gimp-forum.net][gimp_forum] or file an [issue report][issue_report]
with details.

### 1. Check `plugin-ins` location

In GIMP, go to `Edit > Preferences > Folders > Plug-ins`, ensure that we placed plugin folder in one of the listed directories there. This may differ between machine-wide and user installations.

### 2. Script folder
In GIMP3, the plugin script must be placed in a plugin folder with the same name as the script under `plugin-ins` location.<br>
I.e.: `<PLUGIN_LOCATION>/nikplugin/nikplugin.py` and not `<PLUGIN_LOCATION>/nikplugin.py`.

### 3. Verify GIMP installation

Ensure GIMP3 is properly installed with Python support:

1. Add official demo plugin `GIMP_INSTALL/lib/gimp/3.0/plug-ins/test-dialog/`[test-dialog.py][test_dialog]
2. Restart GIMP and check if the test plugin appears under `Filters > Development > Demos`
3. If the `Test dialog...` plugin isn't there either, then is not an issue with this plugin
but general GIMP problem, a reinstallation may help.

### 4. Check file & permissions

- Ensure you downloaded the latest version of the plugin and the *file content is intact*, as Python is sensitive to indentation.
- Under Unix-like (linux & mac), the downloaded script must have *executable* permission: `chmod +x nikplugin.py`

### 5. Test Python module availability

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

### 6. Check for error messages

Run GIMP console in verbose mode from command-line:
```
GIMP_INSTALL/bin/gimp-console-3.0.exe --verbose
```

If error occurs, gimp reinstallation may resolve issue or file a report.

</details>

## *HDR Efex Pro 2* issues

<details>

### Documents Folder Not Found

warning message:
```md
**HDR Efex Pro 2: Folder not found**
Plugin cannot identify 'Documents' on your system
```

**Solution**:
- Modify the [candidate_paths][loc_doc] list in the `find_hdr_output()` function of your `nikplugin.py` script to include your Documents folder location if you specified it differently from the default.
- To determine your *Documents* folder location, *right-click* on your 'Documents' folder and select `Properties > Location` (win).

- Background information:
*HDR Efex Pro 2* doesn't override the input image when you click "Save". Instead, it saves the output at `Documents/INPUT_FILENAME_HDR.ext` (win).
Since GIMP Python cannot use additional lib (i.e. `win32com.client`) to query the exact Documents path, it relies on common default locations.

### Output File Not Found

warning message:
```md
**HDR Efex Pro 2: File not found**
Plugin cannot find the output [filename] in 'Documents'
```

1. The plugin found Documents folder
2. But the expected output file wasn't there after HDR Efex Pro 2 completed

This typically happens when:
- HDR Efex Pro 2 saved the file to a different location
- HDR Efex Pro 2 failed to save the file
- The file was saved with a different naming pattern than expected

**Solution**: When GIMP plugin starts the filter program, go to `SETTINGS > IMAGE OUTPUT SETTINGS > Image Output Format > JPG`. It's the default image format that the plugin expects.

</details>


<!--references -->
[gimp_forum]: https://www.gimp-forum.net/Forum-Gimp-2-99-Gimp-3-0
[issue_report]: https://github.com/iiey/nikGimp/issues
[loc_doc]: https://github.com/iiey/nikGimp/blob/29260dfe52e2e4afbd3f2bacf26f9fce0234369b/nikplugin.py#L154
[loc_libs]: https://github.com/iiey/nikGimp/blob/9c1e5f927679043a5f9697b31e055647cbd3f3a2/nikplugin.py#L18-L32
[test_dialog]: https://gitlab.gnome.org/GNOME/gimp/-/blob/master/plug-ins/python/test-dialog.py