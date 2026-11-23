"""Which typeface the UI uses.

Barlow (SIL OFL) is bundled in ``qml/fonts`` and is the default. Audi Sans is
proprietary, so it is never committed or shipped (PLAN.md decision 9): a user
who owns it drops the files into ``qml/fonts`` and the UI prefers it.

Checked here, in Python, so QML never tries to load a file that isn't there
(a FontLoader with a missing source logs a warning on every start).
"""

from pathlib import Path

# The faces Theme.qml loads. Both must be present, or we stay on Barlow
# rather than mix a real Audi Sans roman with a synthesised bold.
AUDI_SANS_FILES = ("AudiSans-Roman.ttf", "AudiSans-Bold.ttf")


def audi_sans_available(fonts_dir: Path) -> bool:
    """True when every Audi Sans face Theme.qml needs is in ``fonts_dir``."""
    return all((fonts_dir / name).is_file() for name in AUDI_SANS_FILES)
