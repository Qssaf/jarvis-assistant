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
    property bool needsSetup: false  // the first run: the setup screen covers the window until it's done or skipped
    readonly property bool maximized: visibility === Window.Maximized
    width: 1220
    height: 800
    minimumWidth: 900
    minimumHeight: 600
    visible: startShown
    title: "Jarvis"
    color: "transparent"
    flags: Qt.Window | Qt.FramelessWindowHint
    LayoutMirroring.enabled: Backend.rtl  // (Arabic first: the whole window reads right to left)
    LayoutMirroring.childrenInherit: true

    function present() { show(); raise(); requestActivate() }
    function go(key) { page = key }
    Component.onCompleted: Api.get("/api/settings", d => { win.needsSetup = !d.settings.setup_done; Theme.scale = d.settings.text_size || 1 })

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

    onPageChanged: pageIn.restart()

    Item {
        id: frame
        anchors.fill: parent
        readonly property real radius: win.maximized ? 0 : Theme.radiusWindow
        property color glow: Theme.stateColor(Backend.state)
        Behavior on glow { ColorAnimation { duration: 600; easing.type: Easing.OutCubic } }

        // the canvas: a deep navy gradient, light in Jarvis's colour of the moment from the top right, a warm hint below
        Shape {
            id: canvas
            anchors.fill: parent
            preferredRendererType: Shape.CurveRenderer
            readonly property real big: Math.max(width, height)
            ShapePath {
                strokeWidth: -1
                fillGradient: LinearGradient {
                    x1: 0; y1: 0; x2: 0; y2: frame.height
                    GradientStop { position: 0; color: Theme.bgTop }
                    GradientStop { position: 1; color: Theme.bgBottom }
                }
                PathRectangle { width: frame.width; height: frame.height; radius: frame.radius }
            }
            ShapePath {
                strokeWidth: -1
                fillGradient: RadialGradient {
                    centerX: frame.width * 0.9; centerY: -frame.height * 0.08; focalX: centerX; focalY: centerY
                    centerRadius: canvas.big * 0.8
                    GradientStop { position: 0; color: Theme.alpha(frame.glow, 0.13) }
                    GradientStop { position: 0.45; color: Theme.alpha(frame.glow, 0.045) }
                    GradientStop { position: 1; color: Theme.alpha(frame.glow, 0) }
                }
                PathRectangle { width: frame.width; height: frame.height; radius: frame.radius }
            }
            ShapePath {
                strokeWidth: -1
                fillGradient: RadialGradient {
                    centerX: frame.width * 0.08; centerY: frame.height * 1.05; focalX: centerX; focalY: centerY
                    centerRadius: canvas.big * 0.75
                    GradientStop { position: 0; color: Theme.alpha(Theme.warm, 0.04) }
                    GradientStop { position: 1; color: Theme.alpha(Theme.warm, 0) }
                }
                PathRectangle { width: frame.width; height: frame.height; radius: frame.radius }
            }
        }

        // ---- the rail, floating over the canvas
        Glass {
            id: rail
            floating: true
            anchors { left: parent.left; top: parent.top; bottom: parent.bottom; margins: 12 }
            width: 76
            radius: 26

            DragHandler { target: null; onActiveChanged: if (active) win.startSystemMove() }

            ColumnLayout {
                anchors { fill: parent; topMargin: 14; bottomMargin: 6 }
                spacing: 2

                Orb {
                    Layout.alignment: Qt.AlignHCenter
                    Layout.preferredWidth: 48; Layout.preferredHeight: 48
                    mode: Backend.state
                    level: Backend.level
                    rings: false
                    TapHandler { onTapped: Backend.talk() }
                    HoverHandler { cursorShape: Qt.PointingHandCursor }
                }
                Rectangle { Layout.alignment: Qt.AlignHCenter; Layout.preferredWidth: 28; Layout.preferredHeight: 1
                            Layout.topMargin: 10; Layout.bottomMargin: 10; color: Theme.stroke }

                Repeater {
                    model: [["home", qsTr("Home"), "home"], ["chats", qsTr("Chats"), "chats"], ["activity", qsTr("Activity"), "activity"],
                            ["accounts", qsTr("Accounts"), "accounts"], ["plugins", qsTr("Plugins"), "plugins"], ["models", qsTr("Models"), "cpu"],
                            ["memory", qsTr("Memory"), "memory"], ["health", qsTr("Health"), "pulse"]]
                    RailButton { required property var modelData; key: modelData[0]; label: modelData[1]; symbol: modelData[2] }
                }
                Item { Layout.fillHeight: true }
                RailButton { key: "settings"; label: qsTr("Settings"); symbol: "settings" }
            }
        }

        // ---- the page
        Item {
            anchors { left: rail.right; right: parent.right; top: parent.top; bottom: parent.bottom }

            Item {
                id: pages
                anchors.fill: parent
                transform: Translate { id: rise }
                ParallelAnimation {
                    id: pageIn
                    NumberAnimation { target: pages; property: "opacity"; from: 0; to: 1; duration: 200; easing.type: Easing.OutCubic }
                    NumberAnimation { target: rise; property: "y"; from: 8; to: 0; duration: 200; easing.type: Easing.OutCubic }
                }
                StackLayout {
                    anchors.fill: parent
                    currentIndex: ["home", "chats", "activity", "accounts", "plugins", "models", "memory", "settings", "health"].indexOf(win.page)
                    HomePage { id: home }
                    Loader { active: win.page === "chats" || item; sourceComponent: ChatsPage { onOpened: { home.reload(); win.go("home") } } }
                    Loader { active: win.page === "activity" || item; sourceComponent: ActivityPage {} }
                    Loader { active: win.page === "accounts" || item; sourceComponent: AccountsPage {} }
                    Loader { active: win.page === "plugins" || item; sourceComponent: PluginsPage {} }
                    Loader { active: win.page === "models" || item; sourceComponent: ModelsPage {} }
                    Loader { active: win.page === "memory" || item; sourceComponent: MemoryPage {} }
                    Loader { active: win.page === "settings" || item; sourceComponent: SettingsPage { onSetupAgain: win.needsSetup = true } }
                    Loader { active: win.page === "health" || item; sourceComponent: HealthPage { onGoTo: key => win.go(key) } }
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

        Item {  // the top strip: drag to move, window buttons on the right (over the setup screen too)
            id: top
            anchors { left: rail.right; right: parent.right; top: parent.top }
            height: 46
            z: 5.5
            DragHandler { target: null; onActiveChanged: if (active) win.startSystemMove() }
            TapHandler { onDoubleTapped: win.maximized ? win.showNormal() : win.showMaximized() }
            Row {
                anchors { right: parent.right; rightMargin: 12; top: parent.top; topMargin: 12 }
                spacing: 4
                WinButton { symbol: "min"; tip: qsTr("Minimise"); onClicked: win.showMinimized() }
                WinButton { symbol: win.maximized ? "restore" : "max"; tip: win.maximized ? qsTr("Restore") : qsTr("Maximise")
                            onClicked: win.maximized ? win.showNormal() : win.showMaximized() }
                WinButton { symbol: "close"; danger: true; tip: qsTr("Close (Jarvis keeps running in the tray)"); onClicked: win.hide() }
            }
        }


        Loader {
            anchors.fill: parent
            active: win.needsSetup
            z: 5
            sourceComponent: SetupWizard { onFinished: goTo => { win.needsSetup = false; if (goTo) win.go(goTo) } }
        }

        Toast { id: toast; z: 6; anchors.horizontalCenter: parent.horizontalCenter; anchors.bottom: parent.bottom; anchors.bottomMargin: 28 }

        Rectangle {  // the window's edge, over everything
            anchors.fill: parent
            z: 7
            visible: !win.maximized
            radius: frame.radius
            color: "transparent"
            border.width: 1
            border.color: Theme.strokeStrong
        }
    }

    component RailButton: AbstractButton {
        id: rb
        property string key
        property string label
        property string symbol
        readonly property bool current: win.page === key
        Layout.alignment: Qt.AlignHCenter
        Layout.preferredWidth: 64
        Layout.preferredHeight: 56
        Layout.maximumHeight: 56
        Layout.minimumHeight: 44
        Layout.fillHeight: true  // (so it can shrink in a short window)
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        onClicked: win.go(key)
        background: Rectangle {
            radius: 16
            color: rb.current ? Theme.accentSoft : rb.hovered ? Theme.glassHover : "transparent"
            Behavior on color { ColorAnimation { duration: Theme.fast } }
        }
        contentItem: Item {
            Column {
                anchors.centerIn: parent
                spacing: 4
                Icon { anchors.horizontalCenter: parent.horizontalCenter; name: rb.symbol; size: 20
                       color: rb.current ? Theme.accent : rb.hovered ? Theme.text : Theme.text2 }
                Text { anchors.horizontalCenter: parent.horizontalCenter; text: rb.label; font.family: Theme.font; font.pixelSize: Theme.px(11)
                       width: 70; horizontalAlignment: Text.AlignHCenter; fontSizeMode: Text.HorizontalFit; minimumPixelSize: Theme.px(8)  // (long words shrink)
                       font.variableAxes: { "wght": rb.current ? 600 : 500 }; color: rb.current ? Theme.text : rb.hovered ? Theme.text : Theme.text2 }
            }
        }
        scale: down ? 0.97 : 1
        Behavior on scale { NumberAnimation { duration: Theme.fast; easing.type: Easing.OutCubic } }
    }

    component WinButton: AbstractButton {
        id: wb
        property string symbol
        property string tip
        property bool danger: false
        implicitWidth: 30; implicitHeight: 30
        hoverEnabled: true
        focusPolicy: Qt.NoFocus
        Tip { text: wb.tip; visible: wb.hovered }
        background: Rectangle {
            radius: 15
            color: !wb.hovered ? "transparent" : wb.danger ? Theme.alpha(Theme.red, 0.8) : Theme.glassHover
            Behavior on color { ColorAnimation { duration: Theme.fast } }
        }
        contentItem: Item {
            Icon { anchors.centerIn: parent; name: wb.symbol; size: 16; color: wb.hovered ? (wb.danger ? "white" : Theme.text) : Theme.text3 }
        }
    }
}
