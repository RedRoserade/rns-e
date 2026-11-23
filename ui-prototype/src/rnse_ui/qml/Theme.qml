pragma Singleton
import QtQuick

// Colours, fonts and sizes in one place. Registered as a singleton by the
// qmldir next to this file, so any QML in this directory can say Theme.accent.
//
// Accent colours are eyeballed from the manual's screenshots; see
// docs/DESIGN.md for which ones are confirmed.
QtObject {
    id: theme

    readonly property int barHeight: 40

    readonly property int panelVerticalPaddingPx: 40
    readonly property int panelHorizontalPaddingPx: 20

    // Per-function accent. Setup has none: it takes its function's (p. 169).
    readonly property var accents: ({
            "radio": "#ff6a13"  // confirmed, p. 56
            ,
            "cd_tv_sd_media": "#ff6a13"  // confirmed, p. 33 (MP3)
            ,
            "nav": "#27b4ec"  // confirmed, p. 27
            ,
            "info": "#27b4ec"  // assumed: shares the NAV/INFO chapter colour
            ,
            "name": "#66ff01"  // fig. 103
            ,
            "tel": "#66ff01"  // assumed
            ,
            "car": "#fc0417"   // assumed: CAR/SETUP chapter colour
        })

    readonly property color accent: accents[ui.function] || "#27b4ec"
    // Darker shade of the accent for fills, arcs at rest and gradients.
    readonly property color accentDim: Qt.darker(accent, 2)
    readonly property color disabled: "#7f7f7f"

    readonly property color background: "#000000"

    readonly property color text: "#ffffff"
    readonly property color textDim: "#8a8a8a"

    readonly property color tabIdle: "#4a4a4a"

    // Fonts (PLAN.md decision 9). Barlow (SIL OFL, fonts/OFL-Barlow.txt) is
    // bundled and is the default. Audi Sans is proprietary and never shipped:
    // if the user has put its files in fonts/, Python sets the `audiSans`
    // context property (see fonts.py) and we prefer it. An empty FontLoader
    // source loads nothing and logs nothing, so machines without Audi Sans
    // start quietly.
    readonly property bool _wantAudiSans: typeof audiSans !== "undefined" && audiSans

    // Audi Sans: each face carries its own family name, so regular and bold
    // are separate families.
    readonly property FontLoader _audiRoman: FontLoader {
        source: theme._wantAudiSans ? "fonts/AudiSans-Roman.ttf" : ""
    }
    readonly property FontLoader _audiBold: FontLoader {
        source: theme._wantAudiSans ? "fonts/AudiSans-Bold.ttf" : ""
    }
    readonly property bool usingAudiSans: _audiRoman.status === FontLoader.Ready
                                          && _audiBold.status === FontLoader.Ready

    // Barlow: four weights of one family "Barlow"; Qt picks the face from
    // font.weight (Font.Normal / Medium / DemiBold / Bold).
    readonly property FontLoader _barlowRegular: FontLoader { source: "fonts/Barlow-Regular.ttf" }
    readonly property FontLoader _barlowMedium: FontLoader { source: "fonts/Barlow-Medium.ttf" }
    readonly property FontLoader _barlowSemiBold: FontLoader { source: "fonts/Barlow-SemiBold.ttf" }
    readonly property FontLoader _barlowBold: FontLoader { source: "fonts/Barlow-Bold.ttf" }
    // Barlow Semi Condensed, for numbers, whichever text font is in use.
    readonly property FontLoader _barlowScRegular: FontLoader { source: "fonts/BarlowSemiCondensed-Regular.ttf" }
    readonly property FontLoader _barlowScMedium: FontLoader { source: "fonts/BarlowSemiCondensed-Medium.ttf" }
    readonly property FontLoader _barlowScSemiBold: FontLoader { source: "fonts/BarlowSemiCondensed-SemiBold.ttf" }

    readonly property string fontFamily: usingAudiSans ? _audiRoman.name : _barlowRegular.name
    // Audi Sans' bold is its own family; Barlow's bold is a weight of "Barlow".
    readonly property string fontFamilyBold: usingAudiSans ? _audiBold.name : _barlowRegular.name
    // Set `font.bold` to this next to fontFamilyBold. True for Barlow, where
    // it selects the real Barlow-Bold face (nothing is synthesised).
    readonly property bool fontBold: !usingAudiSans
    // Frequencies, times, distances (docs/DESIGN_LANGUAGE.md §4).
    readonly property string fontFamilyNumeric: _barlowScRegular.name

    readonly property int animMs: 160

    // Typography
    readonly property int fontSizeTitle: 24
    readonly property int fontSizeCorner: 20

    readonly property int fontSizeSubtitle: 24
    readonly property int fontSizeBody: 20
}
