import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// The people Jarvis knows: who they are to you, what it understood of them from your one-to-one chats, your notes and
// promises. The list on the left (search it), the person picked on the right.
Item {
    id: page
    objectName: "peoplePage"
    signal goTo(string key)  // another page of the window
    property var people: []
    property bool profilesOn: true
    property string selected: ""
    property var working: ({})  // name -> {busy} while its profile is written again, then {text, bad} if it says why
    property string editing: ""  // the note being edited ("new" for one being added), on the person shown
    readonly property var blank: ({ name: "", aka: [], apps: [], last: 0, seen: {}, wrote: {}, notes: [], promises: [], profile: null, forgot: false })
    readonly property var person: people.find(p => p.name === selected) || null
    readonly property var p: person || blank
    readonly property var status: working[p.name] || ({})
    readonly property var terms: fold(search.text.trim()).split(/\s+/).filter(w => w !== "")
    readonly property var shown: !terms.length ? people : people.filter(e => {
        const all = fold([e.name].concat(e.aka, e.notes.map(n => n.text), e.profile ? [e.profile.gist].concat(e.profile.lines) : []).join(" "))
        return terms.every(w => all.indexOf(w) >= 0)
    })

    function load() {
        Api.get("/api/people", d => { people = d.people; profilesOn = d.profiles; keep() })
    }
    function keep() {  // the one shown stays picked while it's in the list; else the first
        if (!shown.some(e => e.name === selected)) pick(shown.length ? shown[0].name : "")
    }
    function pick(name) {
        if (name !== selected) editing = ""
        selected = name
    }
    function step(i) {  // the arrow keys in the list: the person above or below, shown, with the keyboard's ring on it
        if (i < 0 || i >= shown.length) return
        pick(shown[i].name)
        list.positionViewAtIndex(i, ListView.Contain)
        const row = list.itemAtIndex(i)
        if (row) row.forceActiveFocus(Qt.TabFocusReason)
    }
    function fold(text) { return String(text).toLowerCase().normalize("NFD").replace(/[̀-ͯ]/g, "") }  // (é finds e)
    function ago(t) {
        const s = Date.now() / 1000 - t
        return s < 60 ? qsTr("just now") : s < 3600 ? qsTr("%n min ago", "", Math.round(s / 60)) : s < 86400 ? qsTr("%n h ago", "", Math.round(s / 3600))
             : s < 7 * 86400 ? qsTr("%n day(s) ago", "", Math.floor(s / 86400)) : new Date(t * 1000).toLocaleDateString(Qt.locale(), "d MMM")
    }
    function appName(app) { return app === "whatsapp" ? "WhatsApp" : app === "discord" ? "Discord" : app }
    function appIcon(app) { return app === "discord" ? "hash" : "phone" }
    function initial(name) { const c = String(name).codePointAt(0); return c ? String.fromCodePoint(c).toUpperCase() : "" }
    function talked(e, app) {  // "WhatsApp: they wrote 2 h ago, you wrote yesterday"
        const they = e.seen[app], you = e.wrote[app]
        return they && you ? qsTr("%1: they wrote %2, you wrote %3").arg(appName(app)).arg(ago(they)).arg(ago(you))
             : they ? qsTr("%1: they wrote %2").arg(appName(app)).arg(ago(they)) : qsTr("%1: you wrote %2").arg(appName(app)).arg(ago(you))
    }
    function underName(e) {  // the list's second line: the gist, else their newest note, else when you last talked
        return e.profile ? e.profile.gist : e.notes.length ? e.notes[e.notes.length - 1].text
             : e.last ? qsTr("Talked %1").arg(ago(e.last)) : ""
    }
    function day(t) { return Qt.formatDate(new Date(t * 1000), "yyyy-MM-dd") }
    function setWorking(name, value) { const w = Object.assign({}, working); w[name] = value; working = w }
    function refresh(name) {  // a model request: it takes a few seconds
        setWorking(name, { busy: true })
        Api.post("/api/people/refresh", { name: name }, d => {
            setWorking(name, d.outcome === "few" ? { text: qsTr("Not enough messages from them yet to say much. Jarvis tries again once you've talked more.") } : {})
            load()
        }, e => setWorking(name, { text: e.error || qsTr("Something went wrong"), bad: true }))
    }
    function change(path, body, done) {  // a change on the person shown, then the list again
        Api.post(path, Object.assign({ name: p.name }, body), d => { if (done) done(d); load() }, e => { Backend.toast(e.error, true); load() })
    }
    function saveNote(old, text, until) {  // (an editor that's refused stays open, with what you typed)
        Api.post("/api/people/note", { name: p.name, text: text, until: until, old: old }, () => { editing = ""; load() },
                 e => Backend.toast(e.error, true))
    }
    onVisibleChanged: if (visible) load()
    Component.onCompleted: load()
    Shortcut { sequence: "Ctrl+F"; enabled: page.visible; onActivated: { search.forceActiveFocus(Qt.ShortcutFocusReason); search.selectAll() } }

    ColumnLayout {
        anchors { top: parent.top; bottom: parent.bottom; horizontalCenter: parent.horizontalCenter; margins: Theme.margin }
        width: Math.min(parent.width - 2 * Theme.margin, Theme.pageWidth)
        spacing: 24

        PageHeader {
            Layout.fillWidth: true
            Layout.rightMargin: Math.max(0, 112 - (page.width - parent.width) / 2)  // (clear of the window buttons)
            title: qsTr("People")
            hint: qsTr("Who you talk with, what Jarvis understands of them from your chats, and what you've noted or promised.")
        }

        RowLayout {
            Layout.fillWidth: true
            Layout.fillHeight: true
            spacing: Theme.gap

            Card {  // the list
                Layout.preferredWidth: Math.round(Math.min(320, Math.max(260, parent.width * 0.34)))
                Layout.fillHeight: true
                padding: 8
                ColumnLayout {
                    anchors.fill: parent
                    spacing: 8
                    Field {
                        id: search
                        Layout.fillWidth: true
                        Layout.topMargin: 12
                        placeholderText: qsTr("Search people")
                        Accessible.name: qsTr("Search people")
                        leftPadding: LayoutMirroring.enabled ? 14 : 40  // (paddings don't mirror by themselves; the icon's anchors do)
                        rightPadding: LayoutMirroring.enabled ? 40 : 14
                        onTextChanged: page.keep()
                        Keys.onShortcutOverride: e => e.accepted = e.key === Qt.Key_Escape && text !== ""  // (Esc clears it rather than stopping Jarvis)
                        Keys.onEscapePressed: clear()
                        Keys.onDownPressed: page.step(Math.max(0, page.shown.findIndex(e => e.name === page.selected)))
                        Icon { name: "search"; size: 16; color: search.activeFocus ? Theme.accent : Theme.text3
                               anchors { left: parent.left; leftMargin: 14; verticalCenter: parent.verticalCenter } }
                    }
                    ListView {
                        id: list
                        Layout.fillWidth: true
                        Layout.fillHeight: true
                        clip: true
                        model: page.shown
                        boundsBehavior: Flickable.StopAtBounds
                        ScrollBar.vertical: Scroller {}
                        delegate: AbstractButton {
                            id: row
                            required property var modelData
                            required property int index
                            readonly property bool chosen: page.selected === modelData.name
                            readonly property bool nextChosen: index + 1 < page.shown.length && page.shown[index + 1].name === page.selected
                            width: ListView.view.width
                            height: 62
                            hoverEnabled: true
                            // (one Tab stop, the one shown: the arrows move along; kept while it has the focus, which Qt requires)
                            focusPolicy: chosen || activeFocus ? Qt.TabFocus : Qt.NoFocus
                            Keys.onReturnPressed: click()
                            Keys.onEnterPressed: click()
                            Keys.onUpPressed: page.step(index - 1)
                            Keys.onDownPressed: page.step(index + 1)
                            Accessible.name: modelData.name
                            Accessible.description: page.underName(modelData)
                            onClicked: page.pick(modelData.name)
                            background: Item {
                                Rectangle {
                                    anchors.fill: parent
                                    radius: Theme.radiusControl
                                    color: row.chosen ? Theme.accentSoft : row.hovered ? Theme.glassHover : "transparent"
                                    Behavior on color { ColorAnimation { duration: Theme.fast } }
                                    Focus { keyboard: true; anchors.margins: 1; radius: parent.radius - 1; visible: row.visualFocus }
                                }
                                Rectangle {
                                    anchors { left: parent.left; right: parent.right; bottom: parent.bottom; leftMargin: 12; rightMargin: 12 }
                                    height: 1
                                    color: Theme.stroke
                                    visible: row.index < page.shown.length - 1 && !row.chosen && !row.nextChosen && !row.hovered
                                }
                            }
                            contentItem: Item { RowLayout {
                                anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter; leftMargin: 10; rightMargin: 12 }
                                spacing: 10
                                Avatar { name: row.modelData.name; lit: row.chosen; Layout.preferredWidth: 34; Layout.preferredHeight: 34 }
                                ColumnLayout {
                                    Layout.fillWidth: true
                                    spacing: 3
                                    RowLayout {
                                        Layout.fillWidth: true
                                        spacing: 6
                                        Txt { text: row.modelData.name; weight: 500; elide: Text.ElideRight; wrapMode: Text.NoWrap
                                              Layout.fillWidth: true; Layout.maximumWidth: implicitWidth + 1 }
                                        Repeater {
                                            model: row.modelData.apps
                                            Icon { required property string modelData; name: page.appIcon(modelData); size: 13
                                                   Layout.preferredWidth: size; Layout.preferredHeight: size
                                                   color: row.chosen ? Theme.text2 : Theme.text3; Accessible.name: page.appName(modelData) }
                                        }
                                        Item { Layout.fillWidth: true }
                                        Txt { kind: "small"; font.pixelSize: Theme.px(12); color: row.chosen ? Theme.text2 : Theme.text3; wrapMode: Text.NoWrap
                                              visible: row.modelData.last > 0; text: row.modelData.last > 0 ? page.ago(row.modelData.last) : "" }
                                    }
                                    Txt {
                                        Layout.fillWidth: true
                                        kind: "small"; elide: Text.ElideRight; wrapMode: Text.NoWrap
                                        visible: text !== ""
                                        text: page.underName(row.modelData)
                                    }
                                }
                            } }
                        }
                        ColumnLayout {
                            anchors.centerIn: parent
                            width: parent.width - 32
                            visible: !page.shown.length
                            spacing: 10
                            Icon { Layout.alignment: Qt.AlignHCenter; name: search.text ? "search" : "people"; size: 22; color: Theme.text3 }
                            Txt { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; kind: "small"
                                  text: search.text ? qsTr("No one matches that") : qsTr("No one here yet") }
                        }
                    }
                }
            }

            Card {  // the person picked
                Layout.fillWidth: true
                Layout.fillHeight: true
                padding: 0
                Flickable {
                    id: detail
                    anchors.fill: parent
                    visible: page.person !== null
                    clip: true
                    contentWidth: width
                    contentHeight: body.implicitHeight + 2 * Theme.pad
                    boundsBehavior: Flickable.StopAtBounds
                    ScrollBar.vertical: Scroller {}
                    Connections {  // a control Tab reaches that's out of sight is scrolled into view
                        target: page.Window.window
                        function onActiveFocusItemChanged() {
                            const item = page.Window.window.activeFocusItem
                            if (!item || !(item.focusReason === Qt.TabFocusReason || item.focusReason === Qt.BacktabFocusReason)) return
                            for (let up = item.parent; up !== body; up = up.parent)
                                if (!up) return  // (not in here)
                            const y = item.mapToItem(body, 0, 0).y + Theme.pad, top = detail.contentY
                            if (y < top + Theme.pad) detail.contentY = Math.max(0, y - Theme.pad)
                            else if (y + item.height > top + detail.height - Theme.pad) detail.contentY = y + item.height - detail.height + Theme.pad
                        }
                    }

                    ColumnLayout {
                        id: body
                        anchors { left: parent.left; right: parent.right; top: parent.top; margins: Theme.pad }
                        spacing: 20

                        RowLayout {  // who they are, and when you last wrote each other
                            Layout.fillWidth: true
                            spacing: 14
                            Avatar { name: page.p.name; lit: true; Layout.preferredWidth: 48; Layout.preferredHeight: 48; Layout.alignment: Qt.AlignTop }
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 4
                                Txt { kind: "heading"; text: page.p.name; Layout.fillWidth: true; wrapMode: Text.Wrap; textFormat: Text.PlainText }
                                Txt { kind: "small"; visible: page.p.aka.length > 0; Layout.fillWidth: true; textFormat: Text.PlainText
                                      text: qsTr("Also %1").arg(page.p.aka.join(", ")) }
                                Repeater {
                                    model: page.p.apps
                                    RowLayout {
                                        required property string modelData
                                        Layout.fillWidth: true
                                        Layout.topMargin: 2
                                        spacing: 8
                                        Icon { name: page.appIcon(modelData); size: 14; color: Theme.text3; Layout.preferredWidth: size; Layout.preferredHeight: size }
                                        Txt { kind: "small"; text: page.talked(page.p, modelData); Layout.fillWidth: true }
                                    }
                                }
                                Txt { kind: "small"; visible: !page.p.apps.length; Layout.fillWidth: true
                                      text: qsTr("You haven't chatted with them one to one on WhatsApp or Discord since Jarvis was linked.") }
                            }
                        }

                        Line {}
                        ColumnLayout {  // what Jarvis understands of them
                            Layout.fillWidth: true
                            spacing: 10
                            RowLayout {
                                Layout.fillWidth: true
                                spacing: 8
                                Txt { kind: "heading"; text: qsTr("What Jarvis understands"); Layout.fillWidth: true }
                                Pill {
                                    kind: "ghost"; symbol: "refresh"
                                    text: page.status.busy ? qsTr("Reading your chats…") : qsTr("Refresh")
                                    enabled: !page.status.busy
                                    Accessible.description: qsTr("Write it again now from your latest one-to-one messages with them")
                                    onClicked: page.refresh(page.p.name)
                                }
                                ConfirmButton {
                                    visible: !!page.p.profile
                                    label: qsTr("Forget this"); again: qsTr("Click again to forget it")
                                    onConfirmed: page.change("/api/people/profile/forget", {}, () => Backend.toast(qsTr("Profile forgotten"), false))
                                }
                            }
                            Txt {
                                visible: !!page.p.profile
                                Layout.fillWidth: true
                                weight: 500
                                textFormat: Text.PlainText
                                text: page.p.profile ? page.p.profile.gist : ""
                            }
                            Repeater {
                                model: page.p.profile ? page.p.profile.lines : []
                                RowLayout {
                                    required property string modelData
                                    Layout.fillWidth: true
                                    spacing: 10
                                    Rectangle { Layout.alignment: Qt.AlignTop; Layout.topMargin: Math.round(Theme.px(14) * 0.5); width: 4; height: 4; radius: 2; color: Theme.text3 }
                                    Txt { text: modelData; Layout.fillWidth: true; textFormat: Text.PlainText; color: Theme.text2 }
                                }
                            }
                            Txt {
                                kind: "small"; color: Theme.text3; Layout.fillWidth: true
                                visible: !!page.p.profile
                                text: page.p.profile ? qsTr("Updated %1, from %n message(s)", "", page.p.profile.count).arg(page.ago(page.p.profile.at)) : ""
                            }
                            Txt {
                                kind: "small"; Layout.fillWidth: true
                                visible: !page.p.profile
                                text: page.p.forgot ? qsTr("You had Jarvis forget what it understood of them. It won't write it again unless you press Refresh.")
                                      : page.profilesOn ? qsTr("Nothing yet. Every so often Jarvis reads your latest one-to-one messages with someone and writes a short profile of them, once there are enough messages.")
                                      : qsTr("Jarvis doesn't read your chats to understand people: profiles are off.")
                            }
                            RowLayout {  // (off, with or without an old one)
                                visible: !page.profilesOn
                                Layout.fillWidth: true
                                spacing: 6
                                Txt { kind: "small"; visible: !!page.p.profile; text: qsTr("Profiles are off, so this one isn't updated."); wrapMode: Text.NoWrap }
                                LinkButton { text: qsTr("Turn them on in Settings"); onClicked: page.goTo("settings") }
                            }
                            RowLayout {  // what a refresh found (or why it couldn't)
                                visible: !!page.status.busy || !!page.status.text
                                Layout.fillWidth: true
                                spacing: 10
                                StatusDot { status: page.status.busy ? "working" : page.status.bad ? "error" : "off"; Layout.alignment: Qt.AlignTop; Layout.topMargin: 5 }
                                Txt { kind: "small"; Layout.fillWidth: true; textFormat: Text.PlainText; color: page.status.bad ? Theme.red : Theme.text2
                                      text: page.status.busy ? qsTr("Reading your latest messages with %1 and asking your model…").arg(page.p.name) : page.status.text || "" }
                            }
                        }

                        Line {}
                        ColumnLayout {  // your notes about them
                            Layout.fillWidth: true
                            spacing: 6
                            RowLayout {
                                Layout.fillWidth: true
                                Txt { kind: "heading"; text: qsTr("Notes"); Layout.fillWidth: true }
                                Pill { kind: "ghost"; symbol: "plus"; text: qsTr("Add a note"); visible: page.editing !== "new"; onClicked: page.editing = "new" }
                            }
                            Txt { kind: "small"; Layout.fillWidth: true; visible: !page.p.notes.length && page.editing !== "new"
                                  text: qsTr("None yet. Tell Jarvis “Sam is my cousin”, or add one here.") }
                            Repeater {
                                model: page.p.notes
                                ColumnLayout {
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke; visible: index > 0 }
                                    RowLayout {
                                        visible: page.editing !== modelData.text
                                        Layout.fillWidth: true
                                        Layout.minimumHeight: 44
                                        spacing: 8
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 1
                                            Txt { text: modelData.text; Layout.fillWidth: true; textFormat: Text.PlainText }
                                            Txt { kind: "small"; color: Theme.text3; visible: !!modelData.until; Layout.fillWidth: true
                                                  text: modelData.until ? qsTr("Until %1").arg(new Date(modelData.until * 1000).toLocaleDateString(Qt.locale(), "d MMM yyyy")) : "" }
                                        }
                                        IconButton { symbol: "edit"; tip: qsTr("Edit"); size: 32; glyph: 16; color: Theme.text3; onClicked: page.editing = modelData.text }
                                        ConfirmButton { onConfirmed: page.change("/api/people/note/delete", { text: modelData.text }) }
                                    }
                                    NoteForm { open: page.editing === modelData.text; note: modelData }
                                }
                            }
                            NoteForm { open: page.editing === "new"; note: ({ text: "" }) }
                        }

                        Line {}
                        ColumnLayout {  // what you promised them
                            Layout.fillWidth: true
                            spacing: 6
                            Txt { kind: "heading"; text: qsTr("Promises"); Layout.fillWidth: true }
                            Txt { kind: "small"; Layout.fillWidth: true; visible: !page.p.promises.length
                                  text: qsTr("Nothing open. When you write them “I'll send it tomorrow”, Jarvis keeps it here.") }
                            Repeater {
                                model: page.p.promises
                                ColumnLayout {
                                    required property var modelData
                                    required property int index
                                    Layout.fillWidth: true
                                    spacing: 0
                                    Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke; visible: index > 0 }
                                    RowLayout {
                                        Layout.fillWidth: true
                                        Layout.minimumHeight: 48
                                        spacing: 10
                                        ColumnLayout {
                                            Layout.fillWidth: true
                                            spacing: 1
                                            Txt { text: modelData.what; Layout.fillWidth: true; textFormat: Text.PlainText }
                                            Txt { kind: "small"; color: Theme.text3; Layout.fillWidth: true
                                                  text: modelData.due ? qsTr("Due %1").arg(new Date(modelData.due * 1000).toLocaleString(Qt.locale(), "ddd d MMM, HH:mm"))
                                                        : qsTr("No time set: it's on your evening list") }
                                        }
                                        Pill { kind: "ghost"; symbol: "check"; text: qsTr("Done")
                                               Accessible.description: qsTr("Mark this promise as kept")
                                               onClicked: Api.post("/api/promises/done", { to: page.p.name, what: modelData.what }, page.load, e => Backend.toast(e.error, true)) }
                                    }
                                }
                            }
                        }

                        Line {}
                        RowLayout {  // the whole page goes
                            Layout.fillWidth: true
                            Layout.bottomMargin: 4
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Txt { text: qsTr("Forget this person"); Layout.fillWidth: true }
                                Txt { kind: "small"; Layout.fillWidth: true
                                      text: qsTr("Their notes, promises and profile go. If you chat with them again, Jarvis starts a new page.") }
                            }
                            ConfirmButton {
                                label: qsTr("Forget this person"); again: qsTr("Click again to forget them")
                                onConfirmed: { const who = page.p.name
                                               page.change("/api/people/forget", {}, () => Backend.toast(qsTr("Forgot %1").arg(who), false)) }
                            }
                        }
                    }
                }
                ColumnLayout {
                    anchors.centerIn: parent
                    width: parent.width - 64
                    visible: page.person === null
                    spacing: 12
                    Rectangle {
                        Layout.alignment: Qt.AlignHCenter
                        width: 40; height: 40; radius: 20
                        color: Theme.accentSoft
                        Icon { anchors.centerIn: parent; name: "people"; size: 20; color: Theme.accent }
                    }
                    Txt { Layout.fillWidth: true; horizontalAlignment: Text.AlignHCenter; kind: "small"
                          text: page.people.length ? qsTr("Pick someone to see what Jarvis knows about them")
                                : qsTr("People appear here when you chat with someone one to one on WhatsApp or Discord, or when you tell Jarvis about them: “Sam is my cousin”.") }
                }
            }
        }
    }

    // A round initial in a soft well (lit: the one picked).
    component Avatar: Rectangle {
        property string name
        property bool lit
        Accessible.ignored: true  // (the name is said beside it)
        radius: width / 2
        color: lit ? Theme.alpha(Theme.accent, 0.22) : Theme.glassHover
        border.width: 1
        border.color: lit ? Theme.alpha(Theme.accent, 0.35) : Theme.stroke
        Text {
            anchors.centerIn: parent
            text: page.initial(parent.name)
            font.family: Theme.font; font.pixelSize: Math.round(parent.height * 0.42); font.weight: 600; font.variableAxes: { "wght": 600 }
            color: parent.lit ? Theme.accent : Theme.text2
        }
    }
    component Line: Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke }
    // Text that acts like a link: for going somewhere else in the window.
    component LinkButton: AbstractButton {
        id: lb
        hoverEnabled: true
        focusPolicy: Qt.TabFocus
        Keys.onReturnPressed: click()
        Keys.onEnterPressed: click()
        implicitWidth: label.implicitWidth + 8
        implicitHeight: label.implicitHeight + 6
        background: Rectangle { radius: 6; color: "transparent"; Focus { keyboard: true; visible: lb.visualFocus } }
        contentItem: Item {
            Txt { id: label; anchors.centerIn: parent; kind: "small"; text: lb.text; color: Theme.accent; wrapMode: Text.NoWrap; font.underline: lb.hovered }
        }
    }
    // A note's editor, in its row's place (or under the list, for a new one): its words, an optional last day, then
    // Cancel and Save. Enter saves, Escape cancels.
    component NoteForm: ColumnLayout {
        id: form
        property bool open
        property var note
        visible: open
        onOpenChanged: if (open) { noteText.text = note.text || ""; noteUntil.text = note.until ? page.day(note.until) : ""; noteText.forceActiveFocus() }
        Layout.fillWidth: true
        Layout.topMargin: 6; Layout.bottomMargin: 10
        spacing: 10
        function save() { page.saveNote(note.text || "", noteText.text, noteUntil.text.trim()) }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Field { id: noteText; Layout.fillWidth: true; placeholderText: qsTr("e.g. My cousin, studies medicine in Lyon"); onAccepted: form.save()
                    Keys.onShortcutOverride: e => e.accepted = e.key === Qt.Key_Escape  // (Esc closes the editor rather than stopping Jarvis)
                    Keys.onEscapePressed: page.editing = "" }
            Field { id: noteUntil; Layout.preferredWidth: 170; placeholderText: qsTr("Until (optional)"); onAccepted: form.save()
                    Accessible.description: qsTr("The last day it's true, like 2026-12-31")
                    Keys.onShortcutOverride: e => e.accepted = e.key === Qt.Key_Escape
                    Keys.onEscapePressed: page.editing = "" }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Txt { kind: "small"; color: Theme.text3; Layout.fillWidth: true; text: qsTr("A date like 2026-12-31 makes the note go after that day.") }
            Pill { text: qsTr("Cancel"); kind: "ghost"; onClicked: page.editing = "" }
            Pill { text: qsTr("Save"); kind: "primary"; symbol: "check"; onClicked: form.save() }
        }
    }
}
