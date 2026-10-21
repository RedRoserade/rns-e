# Android Auto — findings and integration options

Status: **research only, nothing tried on hardware yet.** Read 2026-10-03
from shallow clones of the repos below; re-check before relying on details.

## The landscape

Google publishes no head-unit SDK. Every open implementation sits on
**aasdk** (C++). Projects, all GPL-3.0, under
[opencardev](https://github.com/opencardev):

| Project | What it is |
|---|---|
| `aasdk` | The Android Auto protocol library. Maintained (updated 2026-06). |
| `openauto` | The original Qt5-era all-in-one head unit app on aasdk. Updated 2026-02. |
| `crankshaft` | The OS image. Its current generation is **not** based on OpenAuto: it's built from the two below. Updated 2026-07. |
| **`crankshaft-core`** | Headless Qt6 C++ service: Android Auto (aasdk), Bluetooth (BlueZ), audio routing (PipeWire/Pulse), profiles. Exposes a **local WebSocket API**. |
| **`crankshaft-ui-slim`** | Qt6/QML client of crankshaft-core: shows the projection, forwards touch/keys. |

Also relevant: [openDsh/dash](https://github.com/openDsh/dash) — a Qt
infotainment UI that embeds OpenAuto. Useful as a reference for one app with
AA inside it.

## crankshaft-core's API (what matters to us)

Topics seen in the source (`src/services/websocket/`):

- Status: `android-auto/status/{connected,disconnected,device-found,state-changed,channel-status,error}`
- Control: `android-auto/{launch,disconnect,reconnect,terminate,renegotiate}`
- Input to the phone: `android-auto/touch`, **`android-auto/key`**
- Display: `android-auto/display/resolution` (touch scaling only), `android-auto/display/fps`
- Media: `android-auto/media/video-frame`, `android-auto/media/audio-chunk`
- WebRTC signalling: `android-auto/webrtc/{offer,ice-candidate}`
- Also `bluetooth/*`, `audio/{route_changed,volume_changed}`, `media/playback_started`, `system/config_updated`

Video transport is set per profile (`/etc/crankshaft/profiles/host_profiles.json`,
device setting `video.transport_mode`): **`websocket-jpeg`** (default and
fallback) or **`webrtc`**. Core decodes H.264 with GStreamer; the stream is
negotiated at 1920x1080 by default (configurable — we'd want 800x480).
The WebSocket is local and unauthenticated.

## Integration options for our UI

1. **Our UI as a crankshaft-core client (one app).** PySide6 opens the
   WebSocket, subscribes to status + video frames, shows them in a QML
   `Image` (via a `QQuickImageProvider`) when AA is the active function, and
   sends panel input as `android-auto/key` (rotary knob → AA's native
   rotary navigation). No C++, no GPL code linked.
   *Risks:* JPEG frames over a socket through Python — the decode is Qt's C++,
   Python only moves bytes, but measure CPU on the Pi. Lowering the AA stream to
   800x480 helps a lot. The WebSocket message format needs reading from
   `CoreClient.cpp` / `WebSocketServer.cpp`.
2. **Two apps.** crankshaft-ui-slim and our UI both fullscreen under a small
   Wayland compositor (cage / labwc); a function button raises one or the
   other. Simple and robust, but switching is visible and two UIs must share
   panel input.
3. **Fork crankshaft-ui-slim** and restyle it. Fastest to AA, but you'd be
   learning their codebase (C++/QML, GPL) instead of building your own.

Leaning: try **1**, fall back to **2**. Decide in M3 (see `../PLAN.md`).

## First spike checklist (M3)

- [ ] Stock crankshaft image or core + ui-slim from source on the Pi; phone connects
- [ ] Note which transport is active and CPU use of core + ui-slim
- [ ] Read `CoreClient.cpp` for the WebSocket message format (hello, subscribe, frame payload)
- [ ] Python script: connect, subscribe, print status messages
- [ ] Python script: save one video frame to disk
- [ ] Send one `android-auto/key` and watch the phone react
