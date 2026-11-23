from pathlib import Path

from rnse_ui.fonts import AUDI_SANS_FILES, audi_sans_available

QML_FONTS = Path(__file__).parents[1] / "src" / "rnse_ui" / "qml" / "fonts"


def test_no_fonts_means_barlow(tmp_path):
    assert not audi_sans_available(tmp_path)


def test_all_audi_faces_present(tmp_path):
    for name in AUDI_SANS_FILES:
        (tmp_path / name).touch()
    assert audi_sans_available(tmp_path)


def test_partial_audi_sans_falls_back(tmp_path):
    (tmp_path / AUDI_SANS_FILES[0]).touch()
    assert not audi_sans_available(tmp_path)


def test_barlow_is_bundled():
    # The default must always be there, whatever the user has added.
    for name in (
        "Barlow-Regular.ttf",
        "Barlow-Medium.ttf",
        "Barlow-SemiBold.ttf",
        "Barlow-Bold.ttf",
        "BarlowSemiCondensed-Regular.ttf",
        "BarlowSemiCondensed-Medium.ttf",
        "BarlowSemiCondensed-SemiBold.ttf",
        "OFL-Barlow.txt",
    ):
        assert (QML_FONTS / name).is_file(), name
