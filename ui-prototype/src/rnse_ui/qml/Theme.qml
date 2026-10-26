pragma Singleton
import QtQuick

// Colours, fonts and sizes in one place. Registered as a singleton by the
// qmldir next to this file, so any QML in this directory can say Theme.accent.
//
// Accent colours are eyeballed from the manual's screenshots; see
// docs/DESIGN.md for which ones are confirmed.
QtObject {

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

    // Audi Sans (fonts/, converted from the manual's embedded CFFs). Each
    // face carries its own family name, so regular and bold are separate
    // families. If a file is missing or fails to load we fall back to the
    // generic sans-serif and ask Qt to synthesise the bold instead.
    readonly property FontLoader _roman: FontLoader {
        source: "fonts/AudiSans-Roman.ttf"
    }
    readonly property FontLoader _bold: FontLoader {
        source: "fonts/AudiSans-Bold.ttf"
    }
    readonly property string _fallbackFamily: "Sans Serif"

    readonly property string fontFamily: _roman.status === FontLoader.Ready ? _roman.name : _fallbackFamily
    readonly property string fontFamilyBold: _bold.status === FontLoader.Ready ? _bold.name : _fallbackFamily
    // Set `font.bold` to this next to fontFamilyBold.
    readonly property bool fontBoldSynthetic: _bold.status !== FontLoader.Ready

    readonly property int animMs: 160

    // Typography
    readonly property int fontSizeTitle: 24
    readonly property int fontSizeCorner: 20

    readonly property int fontSizeSubtitle: 24
    readonly property int fontSizeBody: 20
}
