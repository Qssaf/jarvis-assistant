import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// What Jarvis remembers about you (a row per note, or all of it as text), and what it does for you: reminders and
// scheduled tasks, routines and the checks it keeps on things. Each row's pencil opens its editor in place, one at a time.
ScrollPage {
    id: page
    objectName: "memoryPage"
    title: qsTr("Memory")
    hint: qsTr("Jarvis reads this before every conversation. Tell it “remember…” or edit it here.")
    property var reminders: []
    property var routines: []
    property var checks: []
    property int checksEvery: 60
    property var checksLast: null  // how the last background look went: {at, answered, ok, found, next}
    property var tried: ({})  // Try now, by check: {busy} while it looks, then {answer} or {error}
    property string saved: ""  // the notes as last loaded or saved: what an edit in the box was made on
    property bool loaded: false  // (no "Nothing yet" before the notes have come)
    property string editing: ""  // the row whose editor is open ("reminder <id>", "routine new", "note 0 - Likes tea"...)
    property bool asText: false  // all the notes in one box, for many changes at once ("Edit as text")
    property string draft: ""  // what the open note's editor holds (kept when a change elsewhere redraws the rows)
    readonly property bool noteOpen: editing.startsWith("note ")
    readonly property var noteRows: parse(saved)
    readonly property int filterFrom: 10  // more notes than this, and a filter shows above them
    readonly property var words: noteRows.length > filterFrom && !asText ? noteFilter.text.toLowerCase().split(/\s+/).filter(w => w) : []
    readonly property var shownRows: noteRows.filter(n => words.every(w => n.line.toLowerCase().includes(w)))  // ("lesson" finds lessons)

    function load() {
        readNotes()
        lists()
    }
    // (unsaved edits stay, and so does what they were made on: Save adds what Jarvis learnt since; an open note too)
    function readNotes() {
        Api.get("/api/memory", d => { if (notes.text === saved && !noteOpen) { show(d.memory); saved = d.memory } loaded = true })
    }
    function show(text) {  // new notes in the box, the cursor where it was
        if (notes.text === text) return
        const at = notes.cursorPosition
        notes.text = text
        notes.cursorPosition = Math.min(at, notes.length)
    }
    // Sends the text it was made on (was): notes Jarvis added meanwhile are kept under the edit, never written over.
    function saveNotes(then) {
        const sent = notes.text
        Api.post("/api/memory", { memory: sent, was: saved }, d => {
            if (notes.text === sent) { show(d.memory); saved = d.memory }
            else saved = sent  // (typed on while it saved: the next Save adds Jarvis's notes again)
            Backend.toast(d.merged ? qsTr("Kept %n note(s) Jarvis added while you were editing", "", d.merged) : qsTr("Memory saved"), false)
            if (then) then()
        })
    }
    // The notes as rows: a line's bullet and kind ("Lesson:", "How to:") are kept apart, so an edit changes only its words.
    // Blank lines and the rest stay in the file as they are, unshown.
    function parse(text) {
        const out = [], seen = {}
        text.split("\n").forEach(line => {
            const m = /^(\s*(?:[-*•]\s*)?)((?:lesson|how to)\s*:\s*)?(.*)$/i.exec(line)
            const body = m[3].trim()
            if (!body) return
            seen[line] = (seen[line] || 0) + 1
            out.push({ line: line, nth: seen[line], lead: m[1], prefix: m[2] || "", text: body,
                       kind: !m[2] ? "fact" : /^lesson/i.test(m[2]) ? "lesson" : "howto" })
        })
        return out
    }
    function shown(text) { return text.charAt(0).toUpperCase() + text.slice(1) }
    // A row's change: that line alone is sent, and changed on the memory as it is now (what Jarvis learnt or forgot while
    // the page was open stays so); a note that's gone meanwhile is said, and the rows show what's there.
    function noteLine(line, said, close) {
        Api.post("/api/memory", { line: line }, d => {
            const clean = notes.text === saved
            saved = d.memory
            if (clean) show(d.memory)
            if (close) closeNote()
            if (said) Backend.toast(said, false)
        }, e => { Backend.toast(e.error, true); if (close) closeNote(); else readNotes() })
    }
    function openNote(n, key) { draft = n.text; editing = key }
    function closeNote() { editing = ""; draft = ""; readNotes() }
    function saveNote(n) {
        const text = draft.trim()
        if (text === n.text) closeNote()
        else if (text) noteLine({ old: n.line, new: n.lead + n.prefix + text }, "", true)
    }
    function addNote() {
        const text = newNote.text.trim()
        if (!text) return
        noteLine({ new: "- " + { fact: "", lesson: "Lesson: ", howto: "How to: " }[newKind.value] + text }, qsTr("Note added"), false)
        newNote.text = ""
    }
    function editAsText() {
        if (noteOpen) closeNote()
        asText = true
        notes.forceActiveFocus()
    }
    function doneAsText() {  // (an edit not saved yet is saved first: the rows show what's in the file)
        if (notes.text === saved) { asText = false; readNotes() }
        else saveNotes(() => asText = false)
    }
    function lists() {  // (not the notes: they may have unsaved edits)
        Api.get("/api/reminders", d => reminders = d)
        Api.get("/api/routines", d => routines = d)
        Api.get("/api/checks", d => { checks = d.checks; checksEvery = d.every; checksLast = d.last })
    }
    function tryCheck(text) {  // one check at once: what it finds shows under it (never said, never kept)
        const put = v => { const t = Object.assign({}, tried); t[text] = v; tried = t }
        put({ busy: true })
        Api.post("/api/checks/test", { text: text }, put, e => put({ error: e.error }))
    }
    function stamp(t) {  // a time today, else the day too
        const d = new Date(t * 1000)
        return Qt.formatDateTime(d, d.toDateString() === new Date().toDateString() ? "HH:mm" : "ddd HH:mm")
    }
    // From an editor: closes it once saved; a refused one stays open with what you typed.
    function save(path, body) { Api.post(path, body, () => { editing = ""; lists() }, e => Backend.toast(e.error, true)) }
    // A switch, a delete or the interval: leaves an open editor alone.
    function change(path, body) { Api.post(path, body, lists, e => { Backend.toast(e.error, true); lists() }) }
    Component.onCompleted: load()
    onVisibleChanged: if (visible) load()
    Timer {  // what Jarvis learns while the page is open shows up, unless the box has an edit not saved yet (or a note has)
        interval: 30000; repeat: true; running: page.visible && notes.text === page.saved && !page.noteOpen
        onTriggered: page.readNotes()
    }

    actions: [
        Pill {
            visible: !page.asText
            text: qsTr("Edit as text"); kind: "ghost"; symbol: "edit"
            onClicked: page.editAsText()
        },
        RowLayout {  // a quiet status while nothing is unsaved; the button only when there's something to save
            visible: page.asText && notes.text === page.saved
            height: 40
            spacing: 6
            Icon { name: "check"; size: 14; color: Theme.text3; Layout.preferredWidth: 14; Layout.preferredHeight: 14 }
            Txt { kind: "small"; text: qsTr("Saved"); color: Theme.text3; wrapMode: Text.NoWrap }
        },
        Pill {
            visible: page.asText && notes.text !== page.saved
            text: qsTr("Save"); kind: "primary"; symbol: "check"
            onClicked: page.saveNotes()
        },
        Pill {
            visible: page.asText
            text: qsTr("Done"); kind: "ghost"
            onClicked: page.doneAsText()
        }
    ]

    Section {
        title: qsTr("What Jarvis knows about you")
        description: page.asText ? qsTr("Plain notes, one per line. Jarvis adds to them as you talk.")
                     : page.loaded && !page.noteRows.length ? qsTr("Nothing yet. Say “remember that I'm vegetarian”, or add a note below.")
                     : qsTr("Jarvis adds to these as you talk. Hover over a note to change or delete it.")
        Field {
            id: noteFilter
            Layout.fillWidth: true
            visible: page.noteRows.length > page.filterFrom && !page.asText
            placeholderText: qsTr("Filter notes")
            Keys.onShortcutOverride: e => e.accepted = e.key === Qt.Key_Escape && text !== ""  // (Esc clears it rather than stopping Jarvis)
            Keys.onEscapePressed: clear()
        }
        Txt {
            kind: "small"; Layout.fillWidth: true
            visible: !page.asText && page.noteRows.length > 0 && !page.shownRows.length
            text: qsTr("No notes match “%1”.").arg(noteFilter.text.trim())
        }
        NoteGroup { kind: "fact" }
        NoteGroup { kind: "lesson"; title: qsTr("Lessons"); hint: qsTr("How you corrected the way Jarvis does things.") }
        NoteGroup { kind: "howto"; title: qsTr("Ways that worked"); hint: qsTr("How Jarvis got something tricky done, kept for next time.") }
        RowLayout {  // a new note goes at the end, as one Jarvis remembers would
            visible: !page.asText
            Layout.fillWidth: true
            spacing: 10
            Field { id: newNote; Layout.fillWidth: true; placeholderText: qsTr("Add a note"); onAccepted: page.addNote() }
            Select {
                id: newKind
                Layout.preferredWidth: 190
                Accessible.name: qsTr("Kind of note")
                value: "fact"
                model: [{ value: "fact", label: qsTr("About you") }, { value: "lesson", label: qsTr("Lesson") },
                        { value: "howto", label: qsTr("Way that worked") }]
            }
            Pill { text: qsTr("Add"); symbol: "plus"; enabled: newNote.text.trim() !== ""; onClicked: page.addNote() }
        }
        Rectangle {
            visible: page.asText
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
                        Toggle { visible: !!modelData.repeat; checked: !modelData.off; Layout.preferredWidth: 44; Accessible.name: modelData.text
                                 onToggled: page.change("/api/reminders", { id: modelData.id, text: modelData.text, at: modelData.edit_at, was: modelData.edit_at,
                                                      repeat: modelData.repeat, task: !!modelData.task, on: checked }) }
                        Edit { onClicked: page.editing = "reminder " + modelData.id }
                        Remove { label: qsTr("Cancel"); again: qsTr("Click again to cancel it")
                                 onConfirmed: page.change(`/api/reminders/${modelData.id}/cancel`, {}) }
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
                        Remove { label: qsTr("Delete")
                                 onConfirmed: page.change("/api/routines/delete", { name: modelData.name }) }
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
                        id: checkRow
                        readonly property var trial: page.tried[modelData.text]
                        detail: !modelData.on ? qsTr("Paused") : !trial ? "" : trial.busy ? qsTr("Looking now…")
                                : trial.error ? trial.error : trial.answer
                        IconButton { symbol: "play"; tip: qsTr("Try it now"); size: 32; glyph: 18; color: Theme.text3
                                     enabled: !(checkRow.trial && checkRow.trial.busy); onClicked: page.tryCheck(modelData.text) }
                        Toggle { checked: modelData.on; Layout.preferredWidth: 44; Accessible.name: modelData.text
                                 onToggled: page.change("/api/checks", { text: modelData.text, old: modelData.text, on: checked }) }
                        Edit { onClicked: page.editing = "check " + modelData.text }
                        Remove { label: qsTr("Delete"); onConfirmed: page.change("/api/checks", { text: "", old: modelData.text }) }
                    }
                    CheckForm { r: modelData; key: "check " + modelData.text }
                }
            }
        }
        Txt {  // (a quiet check is no longer a guess: it looked and found nothing, or it couldn't look)
            kind: "small"; color: page.checksLast && !page.checksLast.ok && !page.checksLast.looking ? Theme.warm : Theme.text3
            Layout.fillWidth: true
            visible: page.checks.length > 0 && !!page.checksLast
            text: !page.checksLast ? "" : page.checksLast.looking ? qsTr("Looking now…")
                  : (!page.checksLast.ok ? qsTr("Couldn't look at %1.").arg(page.stamp(page.checksLast.at))
                     : page.checksLast.found ? qsTr("Last looked at %1 and told you: %2").arg(page.stamp(page.checksLast.at)).arg(page.checksLast.found)
                     : qsTr("Last looked at %1: nothing needed you.").arg(page.stamp(page.checksLast.at)))
                    + " " + qsTr("Next look at %1.").arg(page.stamp(page.checksLast.next))
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
    // One kind of note (facts, lessons, ways that worked): its heading, then a row per note; hidden with none to show.
    component NoteGroup: ColumnLayout {
        id: group
        property string kind
        property string title
        property string hint
        readonly property var rows: page.asText ? [] : page.shownRows.filter(n => n.kind === kind)
        visible: rows.length > 0
        Layout.fillWidth: true
        spacing: 0
        Txt { text: group.title; weight: 600; visible: text !== ""; Layout.fillWidth: true }
        Txt { kind: "small"; text: group.hint; visible: text !== ""; Layout.fillWidth: true; Layout.topMargin: 2; Layout.bottomMargin: 4 }
        Repeater { model: group.rows; NoteRow {} }
    }
    // A note: its words (wrapped), and its pencil and delete, shown on hover or when Tab reaches them. The pencil turns
    // the row into a field: Enter or Save keeps the change, Esc or Cancel leaves it.
    component NoteRow: ColumnLayout {
        id: row
        required property var modelData
        required property int index
        readonly property string key: "note " + modelData.nth + " " + modelData.line
        readonly property bool open: page.editing === key
        readonly property bool lit: hover.hovered || pen.activeFocus || bin.activeFocus || bin.armed
        Layout.fillWidth: true
        spacing: 0
        onOpenChanged: if (open) { box.text = page.draft; box.forceActiveFocus() }
        Component.onCompleted: if (open) box.text = page.draft  // (redrawn while open: what was typed is still there)
        HoverHandler { id: hover }
        Rectangle { Layout.fillWidth: true; Layout.preferredHeight: 1; color: Theme.stroke; visible: row.index > 0 }
        RowLayout {
            visible: !row.open
            Layout.fillWidth: true
            Layout.minimumHeight: 32
            Layout.topMargin: 6; Layout.bottomMargin: 6
            spacing: 12
            Txt { text: page.shown(row.modelData.text); Layout.fillWidth: true }
            RowLayout {
                spacing: 2
                Layout.alignment: Qt.AlignTop
                opacity: row.lit ? 1 : 0
                Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                Edit { id: pen; Accessible.description: row.modelData.text; onClicked: page.openNote(row.modelData, row.key) }
                Remove { id: bin; Accessible.description: row.modelData.text; onConfirmed: page.noteLine({ old: row.modelData.line }, qsTr("Note deleted"), false) }
            }
        }
        RowLayout {
            visible: row.open
            Layout.fillWidth: true
            Layout.topMargin: 6; Layout.bottomMargin: 6
            spacing: 10
            Field {
                id: box
                Layout.fillWidth: true
                placeholderText: qsTr("Write the note")
                onTextEdited: page.draft = text
                onAccepted: page.saveNote(row.modelData)
                Keys.onShortcutOverride: e => e.accepted = e.key === Qt.Key_Escape  // (Esc leaves the edit rather than stopping Jarvis)
                Keys.onEscapePressed: page.closeNote()
            }
            Pill { text: qsTr("Cancel"); kind: "ghost"; onClicked: page.closeNote() }
            Pill { text: qsTr("Save"); kind: "primary"; symbol: "check"; enabled: box.text.trim() !== ""; onClicked: page.saveNote(row.modelData) }
        }
    }
    component List: ColumnLayout {  // the rows of a list card
        Layout.fillWidth: true
        Layout.topMargin: -6; Layout.bottomMargin: -8
        spacing: 0
    }
    component Remove: ConfirmButton { glyph: 18 }
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
