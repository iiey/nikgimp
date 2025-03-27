#!/usr/bin/env python3

"""
VERSION:
3.0.1 Create program list dynamically
3.0.0 Make plugin compatible with Gimp 3.x
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
import subprocess
import sys
import tempfile
import traceback

# NOTE: Update this base path to match your installation
NIK_BASE_PATH = "C:/Program Files/Google/Nik Collection"

# Define plug-in metadata
PROC_NAME = "NikCollection"
HELP = "Call an external program"
DOC = "Call an external program passing the active layer as a temp file"
AUTHOR = "nemo"
COPYRIGHT = "GNU General Public License v3"
DATE = "2025-03-25"
VERSION = "3.0.1"


def list_progs(idx: Optional[int] = None) -> Union[List[str], Tuple[str, Path, str]]:
    """
    Build a list of Nik programs installed on the system
    Args:
        idx: Optional index of the program to return details for
    Returns:
        If idx is None, returns a list of program names
        Otherwise, returns [prog_name, prog_filepath, output_ext] for the specified program
    """

    def get_exec(prog_dir: Path) -> Optional[Path]:
        """Check for executable in the given directory"""
        if executables := list(prog_dir.glob("*.exe")):
            return executables[0]
        else:
            return None

    progs_lst = []
    base_path = Path(NIK_BASE_PATH)
    if base_path.is_dir():
        sub_dirs = [d for d in base_path.iterdir() if d.is_dir()]
        for prog_dir in sub_dirs:
            # prefer looking for 64-bit first
            bit64_dirs = [
                d
                for d in prog_dir.iterdir()
                if d.is_dir() and "64-bit" in d.name.lower()
            ]
            exec_file = get_exec(bit64_dirs[0]) if bit64_dirs else None
            # fallback to default version if not found
            if exec_file is None:
                exec_file = get_exec(prog_dir)
            # only append to final list if one found
            if exec_file:
                prog_detail = (prog_dir.name, exec_file, "jpg")
                progs_lst.append(prog_detail)
    progs_lst.sort(key=lambda x: x[0].lower())  # sort alphabetically

    if idx is None:
        return [prog[0] for prog in progs_lst]
    elif 0 <= idx < len(progs_lst):
        return progs_lst[idx]
    else:
        return []  # invalid index


def run_nik(prog_idx: int, gimp_img: Gimp.Image) -> Optional[str]:

    def check_issue_prog(prog_name: str) -> None:
        if "hdr" in prog_name.lower():
            msg = (
                "'Save' button does not work in this program.\n"
                "Use 'File > Save Image as...' with the following path\n"
                "to manually replace intermediate processed image instead!\n"
                f"{img_path}"
            )
            show_alert(prog_name, msg)

    prog_name, prog_filepath, img_ext = list_progs(prog_idx)
    img_path = os.path.join(tempfile.gettempdir(), f"TmpNik.{img_ext}")

    # Save gimp image to disk
    Gimp.progress_init("Saving a copy")
    Gimp.file_save(
        run_mode=Gimp.RunMode.NONINTERACTIVE,
        image=gimp_img,
        file=Gio.File.new_for_path(img_path),
        options=None,
    )

    # NOTE: silly workaround for troublesome program
    check_issue_prog(prog_name)

    # Invoke external command
    time_before = os.path.getmtime(img_path)
    Gimp.progress_init(f"Calling {prog_name}...")
    Gimp.progress_pulse()
    cmd = [str(prog_filepath), img_path]
    subprocess.check_call(cmd)
    time_after = os.path.getmtime(img_path)

    return None if time_before == time_after else img_path


def show_alert(text: str, message: str, parent=None) -> None:

    dialog = Gtk.MessageDialog(
        transient_for=parent,
        flags=0,
        message_type=Gtk.MessageType.ERROR,
        buttons=Gtk.ButtonsType.CLOSE,
        text=text,
    )
    dialog.format_secondary_text(message)
    dialog.set_title(f"{PROC_NAME} v{VERSION}")
    dialog.run()
    dialog.destroy()


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
      - Start an undo group (let user undo all operations as a single step)
      - Copy and save the layer to a temporary file based on the "visible" setting
      - Call the chosen external Nik Collection program
      - Load the modified result into 'image'
      - End the undo group and finalize
    """

    try:
        # Open dialog to get config parameters
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

        # Start an undo group
        Gimp.context_push()
        image.undo_group_start()

        # Clear current selection to avoid wrongly pasting the processed image
        if not Gimp.Selection.is_empty(image):
            Gimp.Selection.none(image)

        # Prepare the layer to be processed
        active_layer: Gimp.Layer = image.get_layers()[0]
        if visible == LayerSource.CURRENT_LAYER:
            target_layer = active_layer
        else:
            # prepare a new layer in 'image' from all the visibles
            prog_name: str = list_progs(prog_idx)[0]
            target_layer = Gimp.Layer.new_from_visible(image, image, prog_name)
            image.insert_layer(target_layer, None, 0)

        # Intermediate storage enables exporting content to image then save to disk
        buffer: str = Gimp.edit_named_copy([target_layer], "ShellOutTemp")
        tmp_img: Gimp.Image = Gimp.edit_named_paste_as_new_image(buffer)
        if not tmp_img:
            raise Exception("Failed to create temporary image from buffer")

        Gimp.Image.undo_disable(tmp_img)

        # Execute external program
        tmp_filepath = run_nik(prog_idx, tmp_img)
        if tmp_filepath is None:
            if visible == LayerSource.FROM_VISIBLES:
                image.remove_layer(target_layer)

            tmp_img.delete()
            return procedure.new_return_values(
                Gimp.PDBStatusType.SUCCESS,
                GLib.Error(message="No changes detected"),
            )

        # Put it as a new layer in the opened image
        filtered: Gimp.Layer = Gimp.file_load_layer(
            run_mode=Gimp.RunMode.NONINTERACTIVE,
            image=tmp_img,
            file=Gio.File.new_for_path(tmp_filepath),
        )

        tmp_img.insert_layer(filtered, None, -1)
        buffer: str = Gimp.edit_named_copy([filtered], "ShellOutTemp")

        # Align size and position
        target = active_layer if visible == LayerSource.CURRENT_LAYER else target_layer
        target.resize(filtered.get_width(), filtered.get_height(), 0, 0)
        sel = Gimp.edit_named_paste(target, buffer, True)
        Gimp.Item.transform_translate(
            target,
            (tmp_img.get_width() - filtered.get_width()) / 2,
            (tmp_img.get_height() - filtered.get_height()) / 2,
        )

        target.edit_clear()
        Gimp.buffer_delete(buffer)
        Gimp.floating_sel_anchor(sel)

        # Cleanup temporary file & image
        os.remove(tmp_filepath)
        tmp_img.delete()

        return procedure.new_return_values(Gimp.PDBStatusType.SUCCESS, GLib.Error())
    except Exception as e:
        show_alert(text=str(e), message=traceback.format_exc())
        return procedure.new_return_values(
            Gimp.PDBStatusType.EXECUTION_ERROR,
            GLib.Error(message=f"{str(e)}\n\n{traceback.format_exc()}"),
        )
    finally:
        image.undo_group_end()
        Gimp.context_pop()
        Gimp.displays_flush()


class LayerSource(str, Enum):
    FROM_VISIBLES = "new_from_visibles"
    CURRENT_LAYER = "use_current_layer"

    @classmethod
    def create_choice(cls) -> Gimp.Choice:
        choice = Gimp.Choice.new()
        choice.add(
            nick=cls.FROM_VISIBLES,
            id=1,
            label="new from visible",
            help="Apply filter on new layer created from the visibles",
        )
        choice.add(
            nick=cls.CURRENT_LAYER,
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
            value=LayerSource.FROM_VISIBLES,
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
