#!/usr/bin/env python3

"""
VERSION:
See CHANGELOG for details

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
import shutil
import subprocess
import sys
import tempfile
import traceback

# NOTE: Specify IF your installation is not in the default location
# e.g. D:/plugins/nikcollection
NIK_BASE_PATH: str = ""


# Define plug-in metadata
PROC_NAME = "NikCollection"
HELP = "Call an external program"
DOC = "Call an external program passing the active layer as a temp file"
AUTHOR = "nemo"
COPYRIGHT = "GNU General Public License v3"
DATE = "2025-03-30"
VERSION = "3.0.4"


def find_nik_installation() -> Path:
    """Detect Nik Collection installation path based on operating system"""

    possible_paths = []
    # Common installation paths
    if sys.platform == "win32":
        possible_paths = [
            Path("C:/Program Files/Google"),
            Path("C:/Program Files (x86)/Google"),
            Path("C:/Program Files/DxO"),
        ]
    elif sys.platform == "darwin":
        possible_paths = [
            Path("/Applications"),
            Path("~/Applications"),
        ]
    elif sys.platform.startswith("linux"):
        possible_paths = [
            Path.home() / ".wine/drive_c/Program Files/Google",
        ]

    possible_paths = [p / "Nik Collection" for p in possible_paths]
    for path in possible_paths:
        if path.is_dir():
            return path

    # Fallback to user-configured path if specified
    if NIK_BASE_PATH and (nik_path := Path(NIK_BASE_PATH)).is_dir():
        return nik_path

    show_alert(
        text=f"{PROC_NAME} installtion path not found",
        message="Please specify the correct installation path 'NIK_BASE_PATH' in the script.",
    )

    return Path("")


def list_progs(idx: Optional[int] = None) -> Union[List[str], Tuple[str, Path]]:
    """
    Build a list of Nik programs installed on the system
    Args:
        idx: Optional index of the program to return details for
    Returns:
        If idx is None, returns a list of program names
        Otherwise, returns [prog_name, prog_filepath] for the specified program
    """

    def get_exec(prog_dir: Path) -> Optional[Path]:
        """Check for executable in the given directory"""
        if executables := list(prog_dir.glob("*.exe")):
            return executables[0]
        return None

    progs_lst = []
    base_path = find_nik_installation()
    if base_path.is_dir():
        # on mac, programs located directly under installation folder
        if sys.platform == "darwin":
            for prog_item in base_path.iterdir():
                if prog_item.is_dir() and prog_item.suffix == ".app":
                    progs_lst.append((prog_item.stem, prog_item))
        else:
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
                # only append to final list if one is found
                if exec_file:
                    prog_detail = (prog_dir.name, exec_file)
                    progs_lst.append(prog_detail)
    progs_lst.sort(key=lambda x: x[0].lower())  # sort alphabetically

    if idx is None:
        return [prog[0] for prog in progs_lst]
    if 0 <= idx < len(progs_lst):
        return progs_lst[idx]
    return []  # invalid index


def find_hdr_output(prog: str, input_path: Path) -> Optional[Path]:
    """
    Guess output file of 'prog' based on OS
    It typically extends original input file with '_HDR' and stores under the Documents folder
    """

    # NOTE: workaround for troublesome program
    if prog != "HDR Efex Pro 2":
        return None

    fname = f"{input_path.stem}_HDR{input_path.suffix}"
    # NOTE: extend paths correspondingly if you custom your documents folder
    if sys.platform in "win32":
        candidate_paths = [
            Path.home() / "Documents",
            Path("D:/Documents"),
        ]
    if sys.platform == "darwin":
        # NOTE: not work, absolute no idea where mac prog saves the output
        candidate_paths = [
            Path.home() / "Documents",
        ]
    elif sys.platform.startswith("linux"):
        wine_user = os.environ.get("USER", os.environ.get("USERNAME", "user"))
        candidate_paths = [
            Path.home() / f".wine/drive_c/users/{wine_user}/My Documents",
        ]

    doc_paths = [p for p in candidate_paths if p.is_dir()]
    for path in doc_paths:
        if (out_path := (path / fname).resolve()).is_file():
            return out_path

    if not doc_paths:
        show_alert(
            text=f"{prog}: Folder not found",
            message="Plugin cannot identify 'Documents' on your system.",
        )
        return None

    show_alert(
        text=f"{prog}: File not found",
        message=f"Plugin cannot find the output {fname} in 'Documents'.",
    )
    return None


def run_nik(prog_idx: int, gimp_img: Gimp.Image) -> Optional[str]:
    """Invoke external Nik program"""

    prog_name, prog_filepath = list_progs(prog_idx)
    img_path = os.path.join(tempfile.gettempdir(), "tmpNik.jpg")

    # Save gimp image to disk
    Gimp.progress_init("Saving a copy")
    Gimp.file_save(
        run_mode=Gimp.RunMode.NONINTERACTIVE,
        image=gimp_img,
        file=Gio.File.new_for_path(img_path),
        options=None,
    )

    # Invoke external command
    time_before = os.path.getmtime(img_path)
    Gimp.progress_init(f"Calling {prog_name}...")
    Gimp.progress_pulse()
    if sys.platform == "darwin":
        prog_caller = ["open", "-a"]
    elif sys.platform == "linux":
        prog_caller = ["wine"]
    else:
        prog_caller = []
    cmd = prog_caller + [str(prog_filepath), img_path]
    subprocess.check_call(cmd)

    # Move output file to the desinged location so gimp can pick it up
    if hdr_path := find_hdr_output(prog_name, Path(img_path)):
        shutil.move(hdr_path, img_path)

    time_after = os.path.getmtime(img_path)

    return None if time_before == time_after else img_path


def show_alert(text: str, message: str, parent=None) -> None:
    """Popup a message dialog with the given text and message"""

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
    drawables: List[Gimp.Drawable],  # pylint: disable=W0613
    config: Gimp.ProcedureConfig,
    run_data: Any,  # pylint: disable=W0613
) -> Gimp.ValueArray:
    """
    Main function executed by the plugin.
    Call an external Nik Collection program on the active layer
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
    except Exception as error:
        show_alert(text=str(error), message=traceback.format_exc())
        return procedure.new_return_values(
            Gimp.PDBStatusType.EXECUTION_ERROR,
            GLib.Error(message=f"{str(error)}\n\n{traceback.format_exc()}"),
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
            # the get_property(choice_name) returns 'nick' not 'id' so str(id) to get idx later
            command_choice.add(str(idx), idx, prog, prog)
        procedure.add_choice_argument(
            "command",
            "Program:",
            "Select external program to run",
            command_choice,
            "0",
            GObject.ParamFlags.READWRITE,
        )
        return procedure


Gimp.main(NikPlugin.__gtype__, sys.argv)
