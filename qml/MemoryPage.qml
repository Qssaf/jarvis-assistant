import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// What Jarvis remembers about you (edit it freely), and what it does for you: reminders and scheduled tasks, routines
// and the checks it keeps on things. Each row's pencil opens its editor in place, one at a time.
ScrollPage {
    id: page
    title: qsTr("Memory")
    hint: qsTr("Jarvis reads this before every conversation. Tell it “remember…” or edit it here.")
    property var reminders: []
    property var routines: []
    property var checks: []
    property int checksEvery: 60
    property string saved: ""
    property string editing: ""  // the row whose editor is open ("reminder <id>", "routine new"...)

    function load() {
        Api.get("/api/memory", d => { notes.text = d.memory; saved = d.memory })
        lists()
    }
    function lists() {  // (not the notes: they may have unsaved edits)
        Api.get("/api/reminders", d => reminders = d)
        Api.get("/api/routines", d => routines = d)
        Api.get("/api/checks", d => { checks = d.checks; checksEvery = d.every })
    }
    // From an editor: closes it once saved; a refused one stays open with what you typed.
    function save(path, body) { Api.post(path, body, () => { editing = ""; lists() }, e => Backend.toast(e.error, true)) }
    // A switch, a delete or the interval: leaves an open editor alone.
    function change(path, body) { Api.post(path, body, lists, e => { Backend.toast(e.error, true); lists() }) }
    Component.onCompleted: load()
    onVisibleChanged: if (visible) load()

    actions: [
        RowLayout {  // a quiet status while nothing is unsaved; the button only when there's something to save
            visible: notes.text === page.saved
            height: 40
            spacing: 6
            Icon { name: "check"; size: 14; color: Theme.text3; Layout.preferredWidth: 14; Layout.preferredHeight: 14 }
            Txt { kind: "small"; text: qsTr("Saved"); color: Theme.text3; wrapMode: Text.NoWrap }
        },
        Pill {
            visible: notes.text !== page.saved
            text: qsTr("Save"); kind: "primary"; symbol: "check"
            onClicked: Api.post("/api/memory", { memory: notes.text }, () => { page.saved = notes.text; Backend.toast(qsTr("Memory saved"), false) })
        }
    ]

    Section {
        title: qsTr("What Jarvis knows about you")
        description: qsTr("Plain notes, one per line. Jarvis adds to them as you talk.")
        Rectangle {
            Layout.fillWidth: true
            Layout.preferredHeight: Math.min(Math.max(notes.implicitHeight + 2, 140), 420)  // (grows with the notes, then scrolls)
            radius: Theme.radiusControl
            color: "transparent"  // (a second glass fill inside the card reads as a stock text box)
            border.width: 1
            border.color: notes.activeFocus ? Theme.accent : Theme.stroke
            Behavior on border.color { ColorAnimation { duration: Theme.fast } }
            Focus { visible: notes.activeFocus }
            ScrollView {
                anchors.fill: parent
                anchors.margins: 1
                clip: true
                TextArea {
                    id: notes
                    placeholderText: qsTr("- Prefers to be called …\n- Studies …")
                    placeholderTextColor: Theme.text3
                    color: Theme.text
                    font.family: Theme.font
                    font.pixelSize: Theme.px(14)
                    wrapMode: TextEdit.Wrap
                    selectionColor: Theme.alpha(Theme.accent, 0.4)
                    selectedTextColor: Theme.text
                    background: null
                    padding: 20
                }
            }
        }
    }

    Section {
        title: qsTr("Reminders and scheduled tasks")
        description: qsTr("%1 Say “remind me at 5 to call home”, or have Jarvis do something then: “every weekday at 8, check my inbox”.")
                     .arg(page.reminders.length ? qsTr("%n coming up.", "", page.reminders.length) : qsTr("None yet."))
        List {
            visible: page.reminders.length > 0
            Repeater {
                model: page.reminders
                ColumnLayout {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    spacing: 0
                    Entry {
                        first: index === 0
                        off: !!modelData.off
                        symbol: modelData.task ? "sparkle" : "bell"
                        title: modelData.text
                        detail: modelData.task ? qsTr("%1 · Jarvis does it").arg(modelData.when) : modelData.when
                        Toggle { visible: !!modelData.repeat; checked: !modelData.off; Layout.preferredWidth: 44
                                 onToggled: page.change("/api/reminders", { id: modelData.id, text: modelData.text, at: modelData.edit_at, was: modelData.edit_at,
                                                      repeat: modelData.repeat, task: !!modelData.task, on: checked }) }
                        Edit { onClicked: page.editing = "reminder " + modelData.id }
                        Remove { tip: qsTr("Cancel")
                                 onClicked: page.change(`/api/reminders/${modelData.id}/cancel`, {}) }
                    }
                    ReminderForm { r: modelData; key: "reminder " + modelData.id }
                }
            }
        }
        ReminderForm { r: ({}); key: "reminder new" }
        Add { key: "reminder new"; text: qsTr("Add a reminder or task") }
    }

    Section {
        title: qsTr("Routines")
        description: page.routines.length ? qsTr("Say a routine's name and Jarvis runs its steps.")
                     : qsTr("None yet. Say “when I say study mode, close Discord, open my notes and set a 50-minute timer”.")
        List {
            visible: page.routines.length > 0
            Repeater {
                model: page.routines
                ColumnLayout {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    spacing: 0
                    Entry {
                        first: index === 0
                        symbol: "bolt"
                        title: modelData.name.charAt(0).toUpperCase() + modelData.name.slice(1)
                        detail: modelData.steps
                        Edit { onClicked: page.editing = "routine " + modelData.name }
                        Remove { tip: qsTr("Delete")
                                 onClicked: page.change("/api/routines/delete", { name: modelData.name }) }
                    }
                    RoutineForm { r: modelData; key: "routine " + modelData.name }
                }
            }
        }
        RoutineForm { r: ({}); key: "routine new" }
        Add { key: "routine new"; text: qsTr("Add a routine") }
    }

    Section {
        title: qsTr("Keep an eye on")
        description: page.checks.length ? qsTr("Jarvis looks into these with your accounts and the web, and tells you only when something needs you.")
                     : qsTr("Nothing yet. Say “tell me if a payment fails”, or add one here.")
        List {
            visible: page.checks.length > 0
            Repeater {
                model: page.checks
                ColumnLayout {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    spacing: 0
                    Entry {
                        first: index === 0
                        off: !modelData.on
                        symbol: "search"
                        title: modelData.text
                        detail: modelData.on ? "" : qsTr("Paused")
                        Toggle { checked: modelData.on; Layout.preferredWidth: 44
                                 onToggled: page.change("/api/checks", { text: modelData.text, old: modelData.text, on: checked }) }
                        Edit { onClicked: page.editing = "check " + modelData.text }
                        Remove { tip: qsTr("Delete"); onClicked: page.change("/api/checks", { text: "", old: modelData.text }) }
                    }
                    CheckForm { r: modelData; key: "check " + modelData.text }
                }
            }
        }
        CheckForm { r: ({ on: true }); key: "check new" }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Add { key: "check new"; text: qsTr("Add a check") }
            Item { Layout.fillWidth: true }
            Txt { kind: "small"; text: qsTr("Look every"); wrapMode: Text.NoWrap }
            Select { Layout.preferredWidth: 160; value: String(page.checksEvery)
                     model: [{ value: "30", label: qsTr("30 minutes") }, { value: "60", label: qsTr("Hour") }, { value: "180", label: qsTr("3 hours") },
                             { value: "720", label: qsTr("12 hours") }]
                     onPicked: v => page.change("/api/settings", { checks_every: v }) }
        }
    }

    // A row in a list card: an icon in a soft well, a title and a line under it, then its buttons; a hairline above
    // all but the first.
    component Entry: ColumnLayout {
        property bool first
        property bool off  // paused: drawn faded
        property string symbol
        property string title
        property string detail
        default property alias trailing: tail.data
        Layout.fillWidth: true
        spacing: 0
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke; visible: !first }
        RowLayout {
            Layout.fillWidth: true
            Layout.minimumHeight: 40  // (56 with the margins)
            Layout.topMargin: 8; Layout.bottomMargin: 8
            spacing: 14
            Rectangle {
                Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18
                opacity: off ? 0.45 : 1
                color: Theme.accentSoft
                Icon { anchors.centerIn: parent; name: symbol; size: 18; color: Theme.accent }
            }
            ColumnLayout {
                Layout.fillWidth: true
                opacity: off ? 0.55 : 1
                spacing: 2
                Txt { text: title; weight: 500; Layout.fillWidth: true }
                Txt { kind: "small"; text: detail; visible: text !== ""; Layout.fillWidth: true }
            }
            RowLayout { id: tail; spacing: 10 }
        }
    }
    component List: ColumnLayout {  // the rows of a list card
        Layout.fillWidth: true
        Layout.topMargin: -6; Layout.bottomMargin: -8
        spacing: 0
    }
    component Remove: IconButton { symbol: "trash"; size: 32; glyph: 18; color: Theme.text3; iconColor: hovered ? Theme.red : color }
    component Edit: IconButton { symbol: "edit"; tip: qsTr("Edit"); size: 32; glyph: 18; color: Theme.text3 }
    component Add: Pill {  // opens the editor for a new one, which takes the button's place
        property string key
        kind: "ghost"; symbol: "plus"; Layout.leftMargin: -12
        visible: page.editing !== key
        onClicked: page.editing = key
    }

    // An editor under its row (or under the list, for a new one): its fields, then Cancel and Save. Enter in a field saves.
    component Form: ColumnLayout {
        id: form
        property var r
        property string key
        readonly property bool open: page.editing === key
        default property alias fields: box.data
        signal reset()
        signal save()
        visible: open
        onOpenChanged: if (open) reset()
        Layout.fillWidth: true
        Layout.topMargin: 2; Layout.bottomMargin: 14
        spacing: 12
        ColumnLayout { id: box; Layout.fillWidth: true; spacing: 10 }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Item { Layout.fillWidth: true }
            Pill { text: qsTr("Cancel"); kind: "ghost"; onClicked: { page.editing = ""; page.lists() } }  // (its row may be gone)
            Pill { text: qsTr("Save"); kind: "primary"; symbol: "check"; onClicked: form.save() }
        }
    }
    component ReminderForm: Form {
        id: rf
        onReset: { rText.text = r.text || ""; rWhen.text = r.edit_at || ""; rRepeat.value = r.repeat || ""
                   rKind.value = r.task ? "task" : "say"; rText.forceActiveFocus() }
        onSave: page.save("/api/reminders", { id: r.id || "", text: rText.text, at: rWhen.text, was: r.edit_at || "", repeat: rRepeat.value,
                                              task: rKind.value === "task", on: !r.off })
        Field { id: rText; Layout.fillWidth: true; placeholderText: qsTr("What to remind you of, or what Jarvis should do"); onAccepted: rf.save() }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            uniformCellSizes: true
            Field { id: rWhen; Layout.fillWidth: true; placeholderText: qsTr("When: 18:30 or 2026-11-02 08:00"); onAccepted: rf.save() }
            Select { id: rRepeat; Layout.fillWidth: true
                     model: [{ value: "", label: qsTr("Once") }, { value: "daily", label: qsTr("Every day") }, { value: "weekdays", label: qsTr("Weekdays") },
                             { value: "weekly", label: qsTr("Every week") }] }
            Select { id: rKind; Layout.fillWidth: true
                     model: [{ value: "say", label: qsTr("Jarvis reminds you") }, { value: "task", label: qsTr("Jarvis does it") }] }
        }
    }
    component RoutineForm: Form {
        id: tf
        onReset: { tName.text = r.name || ""; tSteps.text = r.steps || ""; tName.forceActiveFocus() }
        onSave: page.save("/api/routines", { name: tName.text, steps: tSteps.text, old: r.name || "", new: !r.name })
        Field { id: tName; Layout.fillWidth: true; placeholderText: qsTr("What you say to start it, e.g. study mode"); onAccepted: tf.save() }
        Field { id: tSteps; Layout.fillWidth: true; placeholderText: qsTr("Its steps, e.g. close Discord, open my notes, set a 50-minute timer")
                onAccepted: tf.save() }
    }
    component CheckForm: Form {
        id: cf
        onReset: { cText.text = r.text || ""; cText.forceActiveFocus() }
        onSave: page.save("/api/checks", { text: cText.text, old: r.text || "", on: r.on })
        Field { id: cText; Layout.fillWidth: true; placeholderText: qsTr("e.g. Tell me if a payment fails or my professor emails"); onAccepted: cf.save() }
    }
}
