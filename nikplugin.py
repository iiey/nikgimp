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
For bug fixes & updates: https://iiey.github.io/nikgimp
Issues and contributing: https://github.com/iiey/nikgimp
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
DATE = "2025-04-01"
VERSION = "3.1.0"


def find_nik_install() -> Path:
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
        text=f"{PROC_NAME} installation path not found",
        message="Please specify the correct installation path 'NIK_BASE_PATH' in the script.",
    )

    return Path("")


def get_prog_details(prog_dir: Path) -> Optional[Tuple[str, Path]]:
    """Return pair (prog_name, exec_path) from the given directory"""

    bit64_dirs = [
        d for d in prog_dir.iterdir() if d.is_dir() and "64-bit" in d.name.lower()
    ]
    # prefer 64-bit version then fall back to default binary
    if bit64_dirs:
        exec_file = next(bit64_dirs[0].glob("*.exe"), None)
    if exec_file is None:
        exec_file = next(prog_dir.glob("*.exe"), None)
    if exec_file:
        return prog_dir.name, exec_file
    return None


def list_progs(idx: Optional[int] = None) -> Union[List[str], Tuple[str, Path]]:
    """
    Build a list of Nik programs installed on the system
    Args:
        idx: Optional index of the program to return details for
    Returns:
        If idx is None, returns a list of program names
        Otherwise, returns [prog_name, prog_filepath] for the specified program
    """

    if not (base_path := find_nik_install()).is_dir():
        return []

    progs_lst = []
    # on mac, programs located directly under installation folder
    if sys.platform == "darwin":
        for prog_item in base_path.iterdir():
            if prog_item.is_dir() and prog_item.suffix == ".app":
                progs_lst.append((prog_item.stem, prog_item))
    # on win or linx+wine
    else:
        sub_dirs = [d for d in base_path.iterdir() if d.is_dir()]
        for prog_dir in sub_dirs:
            if prog_detail := get_prog_details(prog_dir):
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


def prepare_data(
    image: Gimp.Image,
    visible: str,
    prog_name: str,
    is_hdr: bool,
) -> Tuple[Gimp.Layer, List[Gimp.Image]]:
    """Prepare target layer(s) and create tmp image filepath(s)
    Returns:
        target_layer: where the final result will be written to
        tm_image(s): list of temporary images created from the selected layers
    """

    # Clear current selection to avoid wrongly pasting the processed image
    if not Gimp.Selection.is_empty(image):
        Gimp.Selection.none(image)

    selected_layers: List[Gimp.Layer] = image.get_selected_layers()

    # Determine target and source layers based on visibility setting
    if visible == LayerSource.CURRENT_LAYER:
        target_layer = selected_layers[0]
        source_layers = [target_layer]
    else:
        # Prepare a new layer from all the visible layers
        target_layer = Gimp.Layer.new_from_visible(image, image, prog_name)
        image.insert_layer(target_layer, None, 0)
        # For hdr program, we use all the user selected layers as inputs
        source_layers = [target_layer] if not is_hdr else selected_layers

    # Create temporary images from source layers
    tmp_images: List[Gimp.Image] = []
    for layer in source_layers:
        buffer = Gimp.edit_named_copy([layer], "ShellOutTemp")
        tmp_img = Gimp.edit_named_paste_as_new_image(buffer)
        if not tmp_img:
            raise RuntimeError(f"Failed creating tmp image from: {layer.get_name()}")
        Gimp.Image.undo_disable(tmp_img)
        tmp_images.append(tmp_img)

    Gimp.buffer_delete(buffer)
    return target_layer, tmp_images


def process_result(
    target_layer: Gimp.Layer,
    tmp_img: Gimp.Image,
    tmp_filepath: str,
) -> None:
    """Process the result image and integrate it back into GIMP"""

    # Integrate image back into gimp
    # 1. Load image file as layer into tmp image
    filtered: Gimp.Layer = Gimp.file_load_layer(
        run_mode=Gimp.RunMode.NONINTERACTIVE,
        image=tmp_img,
        file=Gio.File.new_for_path(tmp_filepath),
    )
    # 2. the returned layer needs to be added to the image
    tmp_img.insert_layer(filtered, None, 0)

    buffer = Gimp.edit_named_copy([filtered], "ShellOutTemp")

    # Align size and position
    target_layer.resize(filtered.get_width(), filtered.get_height(), 0, 0)
    sel = Gimp.edit_named_paste(target_layer, buffer, True)
    Gimp.Item.transform_translate(
        target_layer,
        (tmp_img.get_width() - filtered.get_width()) / 2,
        (tmp_img.get_height() - filtered.get_height()) / 2,
    )

    target_layer.edit_clear()
    Gimp.buffer_delete(buffer)
    Gimp.floating_sel_anchor(sel)


def cleanup(tmp_filepath: Optional[str], tmp_images: List[Gimp.Image]) -> None:
    """Clean up temporary resources"""

    if tmp_filepath and os.path.exists(tmp_filepath):
        os.remove(tmp_filepath)

    for tmp_img in tmp_images:
        tmp_img.delete()


def run_nik(prog_idx: int, images: List[Gimp.Image]) -> Optional[str]:
    """Invoke external Nik program"""

    prog_name, prog_filepath = list_progs(prog_idx)
    is_hdr = "hdr efex pro 2" in prog_name.lower()
    # all other programs work with one input i.e. always idx=0 and saves the result to the same file
    # except hdr program could accept multiple input images
    temp_files: List[str] = []

    try:
        # Save all temporary images to disk
        for i, img in enumerate(images):
            temp_path = os.path.join(tempfile.gettempdir(), f"tmpNik_{i}.jpg")
            temp_files.append(temp_path)

            Gimp.progress_init(f"Saving image {i+1}/{len(images)}")
            Gimp.file_save(
                run_mode=Gimp.RunMode.NONINTERACTIVE,
                image=img,
                file=Gio.File.new_for_path(temp_path),
                options=None,
            )

        # Track modification time of first file to detect changes
        time_before = os.path.getmtime(temp_files[0])

        # Run the external program
        if sys.platform == "darwin":
            prog_caller = ["open", "-a"]
        elif sys.platform == "linux":
            prog_caller = ["wine"]
        else:  # windows
            prog_caller = []
        cmd = prog_caller + [str(prog_filepath)] + temp_files
        Gimp.progress_init(f"Calling {prog_name}...")
        Gimp.progress_pulse()
        subprocess.check_call(cmd)

        # location of the processed image
        result_path = temp_files[0]

        # handle troublesome hdr program
        # it cannot save image correctly, so find & move its output to the designed location
        hdr_path = find_hdr_output(prog_name, Path(temp_files[0]))
        if is_hdr and hdr_path:
            shutil.move(hdr_path, result_path)

        # Check if the file was modified
        time_after = os.path.getmtime(result_path)
        return None if time_before == time_after else result_path

    finally:
        # Clean up temporary files except the first one (potential result)
        for i, temp_file in enumerate(temp_files):
            try:
                # Don't delete first file yet since it might be the result
                if i > 0 and os.path.exists(temp_file):
                    os.remove(temp_file)
            except Exception:
                pass  # Ignore errors in cleanup


def plugin_main(
    procedure: Gimp.Procedure,
    run_mode: Gimp.RunMode,
    image: Gimp.Image,
    drawables: List[Gimp.Drawable],  # pylint: disable=W0613
    config: Gimp.ProcedureConfig,
    run_data: Any,  # pylint: disable=W0613
) -> Gimp.ValueArray:
    """Main function executed by the plugin"""

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
        visible = str(config.get_property("visible"))
        prog_idx = int(config.get_property("command"))
        prog_name: str = list_progs(prog_idx)[0]
        is_hdr: bool = "hdr efex pro" in prog_name.lower()

        # Start an undo_group
        Gimp.context_push()
        image.undo_group_start()

        # Prepare layers and create temporary images
        target_layer, tmp_images = prepare_data(
            image,
            visible,
            prog_name,
            is_hdr,
        )

        # Execute external program
        tmp_filepath = run_nik(prog_idx, tmp_images)

        # If no changes detected, clean up and return
        if tmp_filepath is None:
            cleanup(None, tmp_images)

            # Remove the target layer if it was newly created and not modified
            if visible == LayerSource.FROM_VISIBLES:
                image.remove_layer(target_layer)

            return procedure.new_return_values(
                Gimp.PDBStatusType.SUCCESS,
                GLib.Error(message="No changes detected"),
            )

        # load the nik result from file into gimp
        process_result(target_layer, tmp_images[0], tmp_filepath)
        cleanup(tmp_filepath, tmp_images)
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
