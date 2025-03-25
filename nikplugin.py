#!/usr/bin/env python3

"""
VERSION:
3.0 Make plugin compatible with Gimp 3.x
    - Revise the code using v3.x API
    - Refactor code and format with black
previous versions: see gimp2x/shellout.py

LICENSE:
This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.
This program is licensed under the GNU General Public License v3 (GPLv3).

CONTRIBUTING:
For updates, raising issues and contributing, visit <https://github.com/iiey/nikGimp>.
"""

import gi

gi.require_version("Gimp", "3.0")
gi.require_version("GimpUi", "3.0")
gi.require_version("Gegl", "0.4")

from gi.repository import (
    GLib,
    GObject,
    Gegl,
    Gimp,
    GimpUi,
    Gio,
    Gtk,
)

from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Tuple, Union

import os
import shlex
import subprocess
import sys
import tempfile
import traceback

# NOTE: Update this base path to match your installation
NIK_BASE_PATH = Path("C:/Program Files/Google/Nik Collection")

# Define plug-in metadata
PROC_NAME = "NikCollection"
HELP = "Call an external program"
DOC = "Call an external program passing the active layer as a temp file"
AUTHOR = "nemo"
COPYRIGHT = "GNU General Public License v3"
DATE = "2025-03-25"


def list_progs(idx: Optional[int] = None) -> Union[List[str], Tuple[str, Path, str]]:
    """
    Build a list of Nik programs installed on the system

    Args:
        idx: Optional index of the program to return details for

    Returns:
        If idx is None, returns a list of program names
        Otherwise, returns [prog_name, prog_filepath, output_ext] for the specified program
    """

    # Assume all nik programs are installed in the same base directory
    # Define program details as: (program_name, executable_filename, file_extension)
    progs_info = [
        ("Analog Efex Pro 2", "Analog Efex Pro 2.exe", "jpg"),
        ("Color Efex Pro 4", "Color Efex Pro 4.exe", "jpg"),
        ("DFine 2", "Dfine2.exe", "png"),
        ("HDR Efex Pro 2", "HDR Efex Pro 2.exe", "jpg"),
        ("Sharpener Pro 3", "SHP3OS.exe", "png"),
        ("Silver Efex Pro 2", "Silver Efex Pro 2.exe", "jpg"),
        ("Viveza 2", "Viveza 2.exe", "png"),
    ]

    # Build the list of existing programs
    progs_lst = []
    for prog, exe, ext in progs_info:
        fullpath = NIK_BASE_PATH / prog / exe
        if fullpath.exists():
            progs_lst.append((prog, fullpath, ext))

    if idx is None:
        return [prog[0] for prog in progs_lst]
    else:
        return progs_lst[idx]


def plugin_main(
    procedure: Gimp.Procedure,
    run_mode: Gimp.RunMode,
    image: Gimp.Image,
    drawables: List[Gimp.Drawable],
    config: Gimp.ProcedureConfig,
    data: Any,
) -> Gimp.ValueArray:
    """
    Main function executed by the plugin. Call an external Nik Collection program on the active layer
    It supports two modes:
      - When visible == 0, operates on the active drawable (current layer).
      - When visible != 0, creates a new layer from the composite of all visible layers

    Workflow:
      - Show dialog in interactive mode for setting parameters (layer source and external program)
      - Start an undo group (let user undo all operations as a single step)
      - Copy and save the layer to a temporary file based on the "visible" setting
      - Call the chosen external Nik Collection program
      - Load the modified result as a new layer and paste it
      - Restore any saved selection and clean up temporary resources
      - End the undo group and finalize
    """

    try:
        # Show dialog in interactive mode
        if run_mode == Gimp.RunMode.INTERACTIVE:
            GimpUi.init(PROC_NAME)
            Gegl.init(None)
            dialog = GimpUi.ProcedureDialog(procedure=procedure, config=config)
            dialog.fill(None)
            if not dialog.run():
                dialog.destroy()
                return procedure.new_return_values(
                    Gimp.PDBStatusType.CANCEL,
                    GLib.Error(message="No dialog response"),
                )
            dialog.destroy()

        # Get parameters
        visible = config.get_property("visible")
        prog_idx = int(config.get_property("command"))

        # Get the program to run and filetype
        prog_name, prog_filepath, img_ext = list_progs(prog_idx)

        # Check if drawables is empty
        if not drawables or len(drawables) == 0:
            return procedure.new_return_values(
                Gimp.PDBStatusType.CALLING_ERROR,
                GLib.Error().new_literal(
                    Gimp.PlugIn.error_quark(), "No drawable provided", 0
                ),
            )
        drawable: Gimp.Drawable = drawables[0]

        # Start an undo group
        Gimp.context_push()
        image.undo_group_start()

        # Copy so the save operations doesn't affect the original
        if visible == LayerSource.USE_CURRENT_LAYER:
            # Use the active drawable
            temp = drawable
        else:
            # Get the current visible
            temp = Gimp.Layer.new_from_visible(image, image, prog_name)
            image.insert_layer(temp, None, 0)

        # Copy the layer content into the named buffer
        buffer: str = Gimp.edit_named_copy([temp], "ShellOutTemp")

        # Save selection if one exists
        hassel = not Gimp.Selection.is_empty(image)
        if hassel:
            savedsel = Gimp.Selection.save(image)

        # Create a new image with the copied content
        tmp_img: Gimp.Image = Gimp.edit_named_paste_as_new_image(buffer)
        if not tmp_img:
            image.undo_group_end()
            Gimp.context_pop()
            return procedure.new_return_values(
                Gimp.PDBStatusType.EXECUTION_ERROR,
                GLib.Error(message="Failed to create temporary image form buffer"),
            )

        Gimp.Image.undo_disable(tmp_img)

        # Get the active layer from the temp image
        tmp_drawable: Gimp.Drawable = tmp_img.get_selected_drawables()[0]

        # Use temp file names from gimp, it reflects the user's choices in gimp.rc
        # change as indicated if you always want to use the same temp file name
        tmp_filepath = os.path.join(tempfile.gettempdir(), f"TmpNik.{img_ext}")

        Gimp.progress_init("Saving a copy")
        Gimp.file_save(
            run_mode=Gimp.RunMode.NONINTERACTIVE,
            image=tmp_img,
            file=Gio.File.new_for_path(tmp_filepath),
            options=None,
        )

        # Invoke external command
        Gimp.progress_init("Calling " + prog_name + "...")
        Gimp.progress_pulse()
        cmd = [str(prog_filepath), str(tmp_filepath)]
        subprocess.Popen(cmd, shell=False).communicate()

        # Put it as a new layer in the opened image
        filtered: Gimp.Layer = Gimp.file_load_layer(
            run_mode=Gimp.RunMode.NONINTERACTIVE,
            image=tmp_img,
            file=Gio.File.new_for_path(tmp_filepath),
        )

        tmp_img.insert_layer(filtered, None, -1)
        buffer: str = Gimp.edit_named_copy([filtered], "ShellOutTemp")

        if visible == LayerSource.USE_CURRENT_LAYER:
            drawable.resize(filtered.get_width(), filtered.get_height(), 0, 0)
            sel: Gimp.Layer = Gimp.edit_named_paste(drawable, buffer, True)
            Gimp.Item.transform_translate(
                drawable,
                (tmp_drawable.get_width() - filtered.get_width()) / 2,
                (tmp_drawable.get_height() - filtered.get_height()) / 2,
            )
        else:
            temp.resize(filtered.get_width(), filtered.get_height(), 0, 0)
            sel: Gimp.Layer = Gimp.edit_named_paste(temp, buffer, True)
            Gimp.Item.transform_translate(
                temp,
                (tmp_drawable.get_width() - filtered.get_width()) / 2,
                (tmp_drawable.get_height() - filtered.get_height()) / 2,
            )

        temp.edit_clear()
        Gimp.buffer_delete(buffer)
        Gimp.floating_sel_anchor(sel)

        # Load up old selection
        if hassel:
            Gimp.Selection.load(savedsel)
            image.remove_channel(savedsel)

        # Cleanup temporary file & image
        os.remove(tmp_filepath)
        tmp_img.delete()

        # End the undo group
        image.undo_group_end()
        Gimp.displays_flush()
        Gimp.context_pop()
    except Exception as e:
        image.undo_group_end()
        Gimp.context_pop()
        show_alert(text=str(e), message=traceback.format_exc())
        return procedure.new_return_values(
            Gimp.PDBStatusType.EXECUTION_ERROR,
            GLib.Error(message=f"{str(e)}\n\n{traceback.format_exc()}"),
        )

    return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())


def show_alert(text: str, message: str, parent=None) -> None:
    """Create a popup dialog to show an error message"""

    dialog = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CLOSE,
        text=text,
    )
    dialog.format_secondary_text(message)
    dialog.set_title(f"{PROC_NAME} - Error")
    dialog.run()
    dialog.destroy()


class LayerSource(str, Enum):
    NEW_FROM_VISIBLE = "new_from_visible"
    USE_CURRENT_LAYER = "use_current_layer"

    @classmethod
    def create_choice(cls) -> Gimp.Choice:
        choice = Gimp.Choice.new()
        choice.add(
            nick=cls.NEW_FROM_VISIBLE,
            id=1,
            label="new from visible",
            help="Apply filter on new layer created from the visibles",
        )
        choice.add(
            nick=cls.USE_CURRENT_LAYER,
            id=0,
            label="use current layer",
            help="Apply filter directly on the active layer",
        )
        return choice


class NikPlugin(Gimp.PlugIn):

    def do_query_procedures(self):
        return [PROC_NAME]

    def do_create_procedure(self, name):
        procedure = Gimp.ImageProcedure.new(
            self,
            name,
            Gimp.PDBProcType.PLUGIN,
            plugin_main,
            None,
        )

        procedure.set_image_types("RGB*, GRAY*")
        procedure.set_attribution(AUTHOR, COPYRIGHT, DATE)
        procedure.set_documentation(HELP, DOC, None)
        procedure.set_menu_label(PROC_NAME)
        procedure.add_menu_path("<Image>/Filters/")

        # Replace PF_RADIO choice
        visible_choice = LayerSource.create_choice()
        procedure.add_choice_argument(
            name="visible",
            nick="Layer:",
            blurb="Select the layer source",
            choice=visible_choice,
            value=LayerSource.NEW_FROM_VISIBLE,
            flags=GObject.ParamFlags.READWRITE,
        )

        # Dropdown selection list of programs
        command_choice = Gimp.Choice.new()
        programs = list_progs()
        for idx, prog in enumerate(programs):
            # the get_property(choice_name) will return 'nick' not 'id' so str(id) to get the index later
            command_choice.add(str(idx), idx, prog, prog)
        procedure.add_choice_argument(
            "command",
            "Program:",
            "Select external program to run",
            command_choice,
            str(idx),
            GObject.ParamFlags.READWRITE,
        )
        return procedure


Gimp.main(NikPlugin.__gtype__, sys.argv)
