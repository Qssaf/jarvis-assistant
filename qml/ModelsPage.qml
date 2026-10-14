import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// Which model does which job, and the providers and keys they come from. Changes save at once.
ScrollPage {
    id: page
    title: "Models"
    hint: "Pick the models for each job. Each list is tried top to bottom: when one is busy or down, the next takes over."
    property var info: ({ providers: [], ollama: null })
    property var avail: ({ backends: [], live: [] })  // what each provider offers (asked for separately: it's slower)
    property var jobs: []
    property bool looking: false

    function load() {
        Api.get("/api/models", d => info = d)
        Api.get("/api/models/jobs", d => jobs = d)
        lookUp()
    }
    function lookUp() {
        looking = true
        Api.get("/api/models/available", d => { avail = d; looking = false }, e => { looking = false; Backend.toast(e.error, true) })
    }
    function save(job, list) {
        const change = {}
        change[job + "_models"] = list
        Api.post("/api/settings", change, () => Api.get("/api/models/jobs", d => jobs = d), e => { Backend.toast(e.error, true); load() })
    }
    function options(list, current) {  // [{value, label}] for a Select, keeping the current choice even if it isn't listed
        const all = current && list.indexOf(current) < 0 ? [current].concat(list) : list
        return all.map(v => ({ value: v, label: v }))
    }
    function modelsOf(name) { const b = page.avail.backends.find(b => b.name === name); return b ? b.models : [] }
    function usableBackends() { return page.avail.backends.filter(b => !b.error || b.models.length).map(b => b.name) }
    readonly property string status: looking ? "Looking up the models you can use…" : avail.backends
        .filter(b => b.models.length || (b.error && !/no API key|unknown backend/.test(b.error)))
        .map(b => b.models.length ? `${b.name}: ${b.models.length} models` : `${b.name}: ${b.error}`).join(" · ")
    Component.onCompleted: load()

    Section {
        title: "What each job uses"
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Txt { kind: "small"; text: page.status; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
            Pill { text: "Refresh"; symbol: "refresh"; enabled: !page.looking; onClicked: page.lookUp() }
        }
        Repeater {
            model: page.jobs
            ColumnLayout {
                id: job
                required property var modelData
                Layout.fillWidth: true
                Layout.topMargin: 6
                spacing: 6
                RowLayout {
                    Layout.fillWidth: true
                    ColumnLayout {
                        Layout.fillWidth: true
                        spacing: 2
                        Txt { text: job.modelData.label; font.weight: Font.DemiBold }
                        Txt { kind: "small"; text: job.modelData.hint + (job.modelData.custom ? "" : " (Jarvis's choice)"); Layout.fillWidth: true }
                    }
                    Pill { visible: job.modelData.custom && job.modelData.job !== "agent"; text: "Use Jarvis's choice"
                           onClicked: page.save(job.modelData.job, []) }
                }
                ModelList { job: job.modelData.job; entries: job.modelData.models }
            }
        }
    }

    Section {
        title: "Providers and keys"
        Txt { kind: "small"; Layout.fillWidth: true; text: "Keys are kept in " + (page.info.storage || "your keychain") + ", never in the settings file." }
        Repeater {
            model: page.info.providers
            RowLayout {
                required property var modelData
                Layout.fillWidth: true
                spacing: 12
                Rectangle { Layout.preferredWidth: 8; Layout.preferredHeight: 8; radius: 4
                            color: modelData.key || modelData.local ? Theme.green : Theme.faint }
                ColumnLayout {
                    Layout.preferredWidth: 250
                    spacing: 0
                    Txt { text: modelData.name; font.weight: Font.DemiBold }
                    Txt { kind: "small"; text: modelData.url; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                }
                Field {
                    Layout.fillWidth: true
                    visible: !modelData.local
                    echoMode: TextInput.Password
                    placeholderText: modelData.key ? "Key saved · paste a new one to replace it" : "Paste an API key"
                    onAccepted: if (text) Api.post(`/api/keys/${modelData.name}`, { key: text }, d => { page.info = d; text = ""; Backend.toast("Key saved", false); page.lookUp() })
                }
                Txt { kind: "small"; visible: !!modelData.local; Layout.fillWidth: true
                      text: page.info.ollama === null ? "Ollama isn't running" : (page.info.ollama.length ? page.info.ollama.join(", ") : "No models downloaded yet") }
                IconButton { visible: !!modelData.custom; symbol: "trash"; tip: "Remove this provider"
                             onClicked: Api.post(`/api/providers/${modelData.name}/delete`, {}, d => { page.info = d; page.lookUp() }) }
            }
        }
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            Field { id: pname; Layout.preferredWidth: 160; placeholderText: "new provider name" }
            Field { id: purl; Layout.fillWidth: true; placeholderText: "https://host/v1 (any OpenAI-compatible service)" }
            Pill { text: "Add"; symbol: "plus"; enabled: pname.text && purl.text
                   onClicked: Api.post("/api/providers", { name: pname.text, url: purl.text }, d => { page.info = d; pname.text = purl.text = ""; page.lookUp() }) }
        }
    }
    Item { Layout.preferredHeight: 24 }

    // one job's models: rows of provider, model and thinking, in the order they're tried
    component ModelList: ColumnLayout {
        id: list
        property string job
        property var entries: []
        readonly property var thinking: job === "image" ? ["none"] : ["minimal", "low", "medium", "high"]
        function update(i, parts) { const all = entries.slice(); all[i] = parts.join(" "); page.save(job, all) }
        function move(i) { const all = entries.slice(); all.splice(i - 1, 0, all.splice(i, 1)[0]); page.save(job, all) }
        function remove(i) { const all = entries.slice(); all.splice(i, 1); page.save(job, all) }
        function add() {
            const name = page.usableBackends()[0] || "aistudio"
            page.save(job, entries.concat([[name, page.modelsOf(name)[0] || "gemini-3.8-flash", list.thinking[Math.min(1, list.thinking.length - 1)]].join(" ")]))
        }
        Layout.fillWidth: true
        spacing: 8
        Repeater {
            model: list.entries
            RowLayout {
                id: row
                required property string modelData
                required property int index
                readonly property var parts: modelData.split(/\s+/)
                Layout.fillWidth: true
                spacing: 8
                Txt { text: (row.index + 1) + "."; color: Theme.dim; Layout.preferredWidth: 20 }
                Select { Layout.preferredWidth: 150; model: page.options(page.usableBackends(), row.parts[0]); value: row.parts[0]
                         onPicked: v => list.update(row.index, [v, page.modelsOf(v)[0] || row.parts[1], row.parts[2]]) }
                Select { Layout.fillWidth: true; visible: page.modelsOf(row.parts[0]).length > 0
                         model: page.options(page.modelsOf(row.parts[0]), row.parts[1]); value: row.parts[1]
                         onPicked: v => list.update(row.index, [row.parts[0], v, row.parts[2]]) }
                Field { Layout.fillWidth: true; visible: !page.modelsOf(row.parts[0]).length; text: row.parts[1]; placeholderText: "model name"
                        onEditingFinished: if (text && text !== row.parts[1]) list.update(row.index, [row.parts[0], text.trim(), row.parts[2]]) }
                Select { Layout.preferredWidth: 120; model: page.options(list.thinking, row.parts[2]); value: row.parts[2]
                         onPicked: v => list.update(row.index, [row.parts[0], row.parts[1], v]) }
                IconButton { symbol: "chevron"; rotation: 180; tip: "Try this one sooner"; enabled: row.index > 0; opacity: enabled ? 1 : 0.3
                             onClicked: list.move(row.index) }
                IconButton { symbol: "trash"; tip: "Remove"; enabled: list.job !== "agent" || list.entries.length > 1; opacity: enabled ? 1 : 0.3
                             onClicked: list.remove(row.index) }
            }
        }
        Pill { text: "Add a model"; symbol: "plus"; onClicked: list.add() }
    }
    component Section: Card {
        property string title
        default property alias body: col.data
        Layout.fillWidth: true
        padding: 22
        ColumnLayout {
            id: col
            width: parent.width
            spacing: 14
            Txt { kind: "heading"; text: title }
        }
    }
}
