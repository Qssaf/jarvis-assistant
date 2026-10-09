import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import QtQuick.Shapes
import Jarvis

// Jarvis's window: a rail of pages on the left, the page on the right, the notch at the top of the screen.
Window {
    id: win
    property bool startShown: true
    property string page: "home"
    readonly property bool maximized: visibility === Window.Maximized
    width: 1220
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    visible: startShown
    title: "Jarvis"
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint

    function present() { show(); raise(); requestActivate() }
    function go(key) { page = key }

    Connections {
        target: Backend
        function onShowRequested() { win.present() }
        function onToastRequested(text, bad) { toast.show(text, bad) }
    }

    Shortcut { sequence: "Ctrl+N"; onActivated: { Api.post("/api/new", {}, () => home.reload()); win.go("home") } }
    Shortcut { sequence: "Ctrl+1"; onActivated: win.go("home") }
    Shortcut { sequence: "Ctrl+2"; onActivated: win.go("chats") }
    Shortcut { sequence: "Ctrl+,"; onActivated: win.go("settings") }
    Shortcut { sequence: "Escape"; enabled: Backend.state !== "idle"; onActivated: Backend.stop() }

    Rectangle {
        id: frame
        anchors.fill: parent
        radius: win.maximized ? 0 : 18
        color: Theme.bg
        border.width: win.maximized ? 0 : 1
        border.color: Theme.lineStrong
        clip: true

        // a soft glow in the corner, in Jarvis's colour of the moment
        Shape {
            width: 900; height: 900
            x: parent.width - 560; y: -560
            preferredRendererType: Shape.CurveRenderer
            ShapePath {
                strokeWidth: 0
                fillGradient: RadialGradient {
                    centerX: 450; centerY: 450; centerRadius: 450; focalX: 450; focalY: 450
                    GradientStop { position: 0; color: Theme.alpha(Theme.stateColor(Backend.state), 0.16) }
                    GradientStop { position: 1; color: Theme.alpha(Theme.stateColor(Backend.state), 0) }
                }
                PathAngleArc { centerX: 450; centerY: 450; radiusX: 450; radiusY: 450; sweepAngle: 360 }
            }
        }

        RowLayout {
            anchors.fill: parent
            anchors.margins: 1
            spacing: 0

            // ---- the rail
            Rectangle {
                Layout.fillHeight: true
                Layout.preferredWidth: 84
                color: Theme.alpha(Theme.panel, 0.85)
                topLeftRadius: frame.radius
                bottomLeftRadius: frame.radius

                DragHandler { target: null; onActiveChanged: if (active) win.startSystemMove() }

                ColumnLayout {
                    anchors.fill: parent
                    anchors.topMargin: 18
                    anchors.bottomMargin: 16
                    spacing: 4

                    Orb {
                        Layout.alignment: Qt.AlignHCenter
                        Layout.preferredWidth: 46; Layout.preferredHeight: 46
                        mode: Backend.state
                        level: Backend.level
                        rings: false
                        TapHandler { onTapped: Backend.talk() }
                        HoverHandler { cursorShape: Qt.PointingHandCursor }
                    }
                    Item { Layout.preferredHeight: 14 }

                    Repeater {
                        model: [["home", "Home", "home"], ["chats", "Chats", "chats"], ["activity", "Activity", "activity"],
                                ["accounts", "Accounts", "accounts"], ["plugins", "Plugins", "plugins"], ["memory", "Memory", "memory"]]
                        RailButton { required property var modelData; key: modelData[0]; label: modelData[1]; symbol: modelData[2] }
                    }
                    Item { Layout.fillHeight: true }
                    RailButton { key: "settings"; label: "Settings"; symbol: "settings" }
                }
            }
            Rectangle { Layout.fillHeight: true; Layout.preferredWidth: 1; color: Theme.line }

            // ---- the page
            Item {
                Layout.fillWidth: true
                Layout.fillHeight: true

                Item {  // the top strip: drag to move, window buttons on the right
                    id: top
                    anchors { left: parent.left; right: parent.right; top: parent.top }
                    height: 46
                    z: 2
                    DragHandler { target: null; onActiveChanged: if (active) win.startSystemMove() }
                    TapHandler { onDoubleTapped: win.maximized ? win.showNormal() : win.showMaximized() }
                    Row {
                        anchors { right: parent.right; rightMargin: 10; verticalCenter: parent.verticalCenter }
                        spacing: 2
                        IconButton { symbol: "min"; size: 32; glyph: 16; tip: "Minimise"; onClicked: win.showMinimized() }
                        IconButton { symbol: "max"; size: 32; glyph: 15; tip: win.maximized ? "Restore" : "Maximise"
                                     onClicked: win.maximized ? win.showNormal() : win.showMaximized() }
                        IconButton { symbol: "close"; size: 32; glyph: 16; tip: "Close (Jarvis keeps running in the tray)"; onClicked: win.hide() }
                    }
                }

                StackLayout {
                    anchors.fill: parent
                    currentIndex: ["home", "chats", "activity", "accounts", "plugins", "memory", "settings"].indexOf(win.page)
                    HomePage { id: home }
                    Loader { active: win.page === "chats" || item; sourceComponent: ChatsPage { onOpened: { home.reload(); win.go("home") } } }
                    Loader { active: win.page === "activity" || item; sourceComponent: ActivityPage {} }
                    Loader { active: win.page === "accounts" || item; sourceComponent: AccountsPage {} }
                    Loader { active: win.page === "plugins" || item; sourceComponent: PluginsPage {} }
                    Loader { active: win.page === "memory" || item; sourceComponent: MemoryPage {} }
                    Loader { active: win.page === "settings" || item; sourceComponent: SettingsPage {} }
                }
            }
        }

        // resize from the edges and corners
        Repeater {
            model: [[Qt.LeftEdge, 0, 6, 0, 0], [Qt.RightEdge, 0, 6, 1, 0], [Qt.TopEdge, 1, 6, 0, 0], [Qt.BottomEdge, 1, 6, 0, 1],
                    [Qt.LeftEdge | Qt.TopEdge, 2, 12, 0, 0], [Qt.RightEdge | Qt.TopEdge, 2, 12, 1, 0],
                    [Qt.LeftEdge | Qt.BottomEdge, 2, 12, 0, 1], [Qt.RightEdge | Qt.BottomEdge, 2, 12, 1, 1]]
            MouseArea {
                required property var modelData
                visible: !win.maximized
                readonly property int kind: modelData[1]
                x: kind === 1 ? 12 : modelData[3] ? parent.width - width : 0
                y: kind === 0 ? 12 : modelData[4] ? parent.height - height : 0
                width: kind === 1 ? parent.width - 24 : modelData[2]
                height: kind === 0 ? parent.height - 24 : modelData[2]
                cursorShape: kind === 0 ? Qt.SizeHorCursor : kind === 1 ? Qt.SizeVerCursor
                           : (modelData[3] === modelData[4]) ? Qt.SizeFDiagCursor : Qt.SizeBDiagCursor
                onPressed: win.startSystemResize(modelData[0])
            }
        }

        Toast { id: toast; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 26 }
    }

    component RailButton: AbstractButton {
        id: rb
        property string key
        property string label
        property string symbol
        readonly property bool current: win.page === key
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: 68
        Layout.preferredHeight: 58
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        onClicked: win.go(key)
        background: Rectangle {
            radius: 14
            color: rb.current ? Theme.alpha(Theme.accent, 0.16) : rb.hovered ? Theme.card : "transparent"
            Behavior on color { ColorAnimation { duration: 140 } }
            Rectangle {
                visible: rb.current
                width: 3; height: 22; radius: 2
                anchors.verticalCenter: parent.verticalCenter
                x: -8
                color: Theme.accent
            }
        }
        contentItem: Column {
            spacing: 4
            topPadding: 8
            Icon { anchors.horizontalCenter: parent.horizontalCenter; name: rb.symbol; size: 21
                   color: rb.current ? Theme.accent : rb.hovered ? Theme.text : Theme.dim }
            Text { anchors.horizontalCenter: parent.horizontalCenter; text: rb.label; font.family: Theme.font; font.pixelSize: 11
                   font.weight: rb.current ? Font.DemiBold : Font.Medium; color: rb.current ? Theme.text : Theme.dim }
        }
    }
}
