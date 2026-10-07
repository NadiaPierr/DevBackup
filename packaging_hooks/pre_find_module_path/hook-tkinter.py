"""Keep tkinter discoverable when PyInstaller's Tcl probe is inconclusive."""


def pre_find_module_path(hook_api):
    # The Python installation used for this project contains tkinter and its
    # Tcl/Tk libraries, although PyInstaller's initialization probe fails.
    # Leaving search_dirs unchanged lets module analysis continue normally.
    return None
