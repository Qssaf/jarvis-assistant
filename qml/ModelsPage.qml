import QtQuick
import QtQuick.Controls
import QtQuick.Layouts
import Jarvis

// Which model does which job, and the providers and keys they come from. Changes save at once.
ScrollPage {
    id: page
    title: qsTr("Models")
    hint: qsTr("Pick the models for each job. Each list is tried top to bottom: when one is busy or down, the next takes over.")
    property var info: ({ providers: [], ollama: null })
    property var avail: ({ backends: [], live: [] })  // what each provider offers (asked for separately: it's slower)
    property var jobs: []
    property bool looking: false
    property string adding: ""  // a provider whose key is being pasted
    property bool custom: false  // the add-a-provider row is open

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
    function pretty(m) {  // "gemini-3.8-flash" -> "Gemini 3.8 Flash"
        return m.split("/").pop().replace(/(\d)-(\d)/g, "$1.$2").split(/[-_]/).filter(w => w)
                .map(w => /^(gpt|glm|ai)$/i.test(w) ? w.toUpperCase() : w[0].toUpperCase() + w.slice(1)).join(" ")
    }
    function modelsOf(name) { const b = page.avail.backends.find(b => b.name === name); return b ? b.models : [] }
    function modelsFor(name, job) { return modelsOf(name).filter(m => /tts|piper/i.test(m) === (job === "speak")) }  // (text-to-speech: Speaking only)
    // OpenAI's speaking voices: the third word of another service's Speaking line (Gemini's speak in Jarvis's voice from Settings)
    readonly property var voices: ["alloy", "ash", "ballad", "coral", "echo", "fable", "nova", "onyx", "sage", "shimmer", "verse"]
    function ownLocal() { return page.info.providers.some(p => p.name === "local" && p.custom) }
    function usableBackends(job) {  // (the local backend only hears and speaks; a provider of the user's own called "local" does it all)
        return page.avail.backends.filter(b => (!b.error || b.models.length) && (page.ownLocal() || b.name !== "local" || job === "hear" || job === "speak")).map(b => b.name)
    }
    readonly property string status: looking ? qsTr("Looking up the models you can use…") : avail.backends
        .filter(b => b.models.length || (b.error && !/no API key|unknown backend|not signed in|not installed/.test(b.error)))
        .map(b => b.models.length ? qsTr("%1: %n model(s)", "", b.models.length).arg(b.name) : `${b.name}: ${b.error}`).join(" · ")
    Component.onCompleted: load()
    Timer {  // while a Google sign-in waits in the browser: notice when it's done
        interval: 2000; repeat: true; running: !!page.info.google_signing
        onTriggered: Api.get("/api/models", d => { const was = page.info.google_signing; page.info = d; if (was && !d.google_signing) page.lookUp() })
    }

    actions: Pill { text: qsTr("Refresh"); symbol: "refresh"; enabled: !page.looking; onClicked: page.lookUp() }

    Section {
        title: qsTr("What each job uses")
        spacing: 12
        RowLayout {
            Layout.fillWidth: true
            spacing: 10
            StatusDot { status: page.looking ? "working" : page.avail.backends.some(b => b.models.length) ? "ok" : "off" }
            Txt { kind: "small"; text: page.status; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: page.jobs
                ColumnLayout {
                    id: job
                    required property var modelData
                    property bool open: false
                    readonly property var first: (modelData.models[0] || "").split(/\s+/)
                    readonly property int more: modelData.models.length - 1
                    Layout.fillWidth: true
                    spacing: 0
                    Divider {}
                    Item {  // the job at a glance: click it to open its full list
                        Layout.fillWidth: true
                        implicitHeight: head.implicitHeight + 24
                        Rectangle {
                            anchors { fill: parent; topMargin: 4; bottomMargin: 4; leftMargin: -10; rightMargin: -10 }
                            radius: Theme.radiusControl
                            color: Theme.glassHover
                            opacity: hit.containsMouse ? 1 : 0
                            Behavior on opacity { NumberAnimation { duration: Theme.fast } }
                        }
                        MouseArea { id: hit; anchors.fill: parent; hoverEnabled: true; cursorShape: Qt.PointingHandCursor; onClicked: job.open = !job.open }
                        RowLayout {
                            id: head
                            anchors { left: parent.left; right: parent.right; verticalCenter: parent.verticalCenter }
                            spacing: 12
                            ColumnLayout {
                                Layout.fillWidth: true
                                spacing: 2
                                Item {  // the title, then a small tag when Jarvis picked the models
                                    Layout.fillWidth: true
                                    implicitHeight: name.implicitHeight
                                    Txt { id: name; text: job.modelData.label; weight: 600; elide: Text.ElideRight; wrapMode: Text.NoWrap
                                          anchors.left: parent.left; width: Math.min(implicitWidth, parent.width - (tag.visible ? tag.implicitWidth + 8 : 0)) }
                                    Txt { id: tag; kind: "label"; visible: !job.modelData.custom; color: Theme.text3; text: qsTr("Jarvis's choice"); wrapMode: Text.NoWrap
                                          anchors { left: name.right; leftMargin: 8; baseline: name.baseline } }
                                }
                                Txt { kind: "small"; text: job.modelData.hint; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                            }
                            Pill { visible: job.open && job.modelData.custom && job.modelData.job !== "agent"; text: qsTr("Use Jarvis's choice"); kind: "ghost"
                                   symbol: "restore"; implicitHeight: 32; onClicked: page.save(job.modelData.job, []) }
                            RowLayout {  // a fixed width, so the pills line up from job to job
                                visible: !job.open
                                Layout.fillWidth: false
                                Layout.preferredWidth: 340
                                spacing: 12
                                Chip { visible: job.first[0] !== ""; active: true; text: page.pretty(job.first[1] || ""); onClicked: job.open = true }
                                Txt { kind: "small"; color: Theme.text3; wrapMode: Text.NoWrap; elide: Text.ElideRight; Layout.fillWidth: true
                                      text: job.more > 0 ? qsTr("%1 · +%n fallback(s)", "", job.more).arg(job.first[0]) : job.first[0] }
                            }
                            Icon { name: "chevron-right"; size: 18; color: hit.containsMouse ? Theme.text : Theme.text3
                                   Layout.preferredWidth: 18; Layout.preferredHeight: 18
                                   rotation: job.open ? (LayoutMirroring.enabled ? -90 : 90) : 0; Behavior on rotation { NumberAnimation { duration: Theme.fast } } }
                        }
                    }
                    ModelList { visible: job.open; Layout.bottomMargin: 16; job: job.modelData.job; entries: job.modelData.models }
                }
            }
        }
    }

    Section {
        title: qsTr("Providers and keys")
        spacing: 12
        RowLayout {  // (instead of the description: the path goes in a tip)
            Layout.fillWidth: true
            Layout.topMargin: -12
            spacing: 4
            Txt { kind: "small"
                  text: (/keychain/.test(page.info.storage || "keychain") ? qsTr("Keys stay in your system keychain, never in the settings file.")
                        : qsTr("Keys stay in a private file on this PC, never in the settings file.")) }
            IconButton { symbol: "info"; size: 28; glyph: 16; color: Theme.text3; tip: page.info.storage ? qsTr("Kept in %1").arg(page.info.storage) : qsTr("Kept in your keychain") }
            Item { Layout.fillWidth: true }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            Repeater {
                model: page.info.providers.filter(p => p.key || p.local || p.name === page.adding)
                ColumnLayout {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    spacing: 0
                    Divider {}
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 64
                        spacing: 12
                        StatusDot { status: modelData.local ? (page.info.ollama === null ? "off" : page.info.ollama.length ? "ok" : "working")
                                                            : (modelData.key ? "ok" : "off") }
                        ColumnLayout {
                            Layout.fillWidth: true
                            spacing: 2
                            Txt { text: modelData.name; weight: 600 }
                            Txt { kind: "small"; text: modelData.url; elide: Text.ElideRight; wrapMode: Text.NoWrap; Layout.fillWidth: true }
                        }
                        Field {
                            Layout.preferredWidth: 320
                            visible: !modelData.local
                            echoMode: TextInput.Password
                            placeholderText: modelData.key ? qsTr("Key saved · paste a new one to replace it") : qsTr("Paste an API key")
                            onAccepted: if (text) Api.post(`/api/keys/${modelData.name}`, { key: text }, d => { page.info = d; page.adding = ""; text = ""; Backend.toast(qsTr("Key saved"), false); page.lookUp() })
                            onActiveFocusChanged: if (!activeFocus && !text && page.adding === modelData.name) page.adding = ""
                            Component.onCompleted: if (page.adding === modelData.name) forceActiveFocus()
                        }
                        Txt { kind: "small"; visible: !!modelData.local; Layout.preferredWidth: 320; horizontalAlignment: Text.AlignRight
                              color: page.info.ollama && page.info.ollama.length ? Theme.text2 : Theme.text3; elide: Text.ElideRight; wrapMode: Text.NoWrap
                              text: page.info.ollama === null ? qsTr("Ollama isn't running") : (page.info.ollama.length ? page.info.ollama.join(", ") : qsTr("No models downloaded yet")) }
                        IconButton { visible: !!modelData.custom; symbol: "trash"; color: Theme.text3; tip: qsTr("Remove this provider"); Layout.rightMargin: -8
                                     onClicked: Api.post(`/api/providers/${modelData.name}/delete`, {}, d => { page.info = d; page.lookUp() }) }
                    }
                }
            }
            Divider {}
        }
        Txt { kind: "label"; text: qsTr("More providers"); Layout.topMargin: 4 }
        Flow {
            Layout.fillWidth: true
            spacing: 8
            Repeater {
                model: page.info.providers.filter(p => !(p.key || p.local || p.name === page.adding))
                Chip { id: chip; required property var modelData; symbol: "plus"; text: modelData.name; onClicked: page.adding = modelData.name
                       Tip { text: chip.modelData.url; visible: chip.hovered } }
            }
            Chip { symbol: "link"; text: qsTr("Another service"); checked: page.custom; onClicked: page.custom = !page.custom }
        }
        RowLayout {
            Layout.fillWidth: true
            visible: page.custom
            spacing: 12
            Field { id: pname; Layout.preferredWidth: 180; placeholderText: qsTr("name") }
            Field { id: purl; Layout.fillWidth: true; placeholderText: "https://host/v1 (any OpenAI-compatible service)" }
            Pill { text: qsTr("Add"); symbol: "plus"; implicitHeight: 44; enabled: pname.text && purl.text; kind: enabled ? "primary" : ""
                   onClicked: Api.post("/api/providers", { name: pname.text, url: purl.text }, d => { page.info = d; pname.text = purl.text = ""; page.custom = false; page.lookUp() }) }
        }
    }

    Section {
        title: qsTr("Your Google account")
        description: qsTr("Sign in with Google for Gemini (and Claude) through your account's Antigravity quota, much more than a free "
                     + "AI Studio key.")
        Rectangle {
            Layout.fillWidth: true
            implicitHeight: warn.implicitHeight + 24
            radius: Theme.radiusControl
            color: Theme.warmSoft
            border.width: 1
            border.color: Theme.alpha(Theme.warm, 0.25)
            RowLayout {
                id: warn
                anchors { left: parent.left; right: parent.right; top: parent.top; margins: 12 }
                spacing: 12
                Icon { name: "shield"; size: 18; color: Theme.warm; Layout.preferredWidth: 18; Layout.preferredHeight: 18; Layout.alignment: Qt.AlignTop }
                Txt { kind: "small"; color: Theme.text; Layout.fillWidth: true; Layout.maximumWidth: 640
                      text: qsTr("It signs in the way Google's Antigravity app does, which Google doesn't offer to other apps: "
                            + "Google may limit or suspend accounts used like this. Use an account you can afford to lose.") }
            }
        }
        ColumnLayout {
            Layout.fillWidth: true
            spacing: 0
            visible: (page.info.google || []).length > 0
            Repeater {
                model: page.info.google || []
                ColumnLayout {
                    required property var modelData
                    required property int index
                    Layout.fillWidth: true
                    spacing: 0
                    Divider { visible: index > 0 }
                    RowLayout {
                        Layout.fillWidth: true
                        Layout.preferredHeight: 56
                        spacing: 12
                        Rectangle {
                            Layout.preferredWidth: 36; Layout.preferredHeight: 36; radius: 18
                            color: Theme.accentSoft
                            Txt { anchors.centerIn: parent; text: (modelData.email || "G")[0].toUpperCase(); weight: 600; color: Theme.accent }
                        }
                        Txt { text: modelData.email || qsTr("Google account"); weight: 500; Layout.fillWidth: true; elide: Text.ElideRight; wrapMode: Text.NoWrap }
                        Txt { kind: "small"; color: Theme.text3; visible: modelData.source === "opencode"; text: qsTr("from opencode") }
                        IconButton { visible: modelData.source === "jarvis"; symbol: "trash"; color: Theme.text3; tip: qsTr("Sign out"); Layout.rightMargin: -8
                                     onClicked: Api.post("/api/google/signout", { email: modelData.email }, d => { page.info = d; page.lookUp() }) }
                    }
                }
            }
            Divider {}
        }
        Txt { kind: "small"; Layout.fillWidth: true; visible: page.info.google_client === false; color: Theme.warm
              text: qsTr("First install the opencode-antigravity-auth plugin (github:Qssaf/opencode-antigravity-auth-desktop): Jarvis signs in "
                    + "with its details. Or put ANTIGRAVITY_CLIENT_ID and ANTIGRAVITY_CLIENT_SECRET in Jarvis's env file.") }
        Pill { visible: page.info.google_client !== false
               text: page.info.google_signing ? qsTr("Waiting for the browser…") : (page.info.google || []).length ? qsTr("Add another account") : qsTr("Sign in with Google")
               symbol: (page.info.google || []).length ? "plus" : ""
               kind: (page.info.google || []).length || page.info.google_signing ? "" : "primary"; enabled: !page.info.google_signing
               onClicked: Api.post("/api/google/signin", {}, d => page.info = d, e => Backend.toast(e.error, true)) }
    }

    component Divider: Rectangle { Layout.fillWidth: true; implicitHeight: 1; color: Theme.stroke }

    // one job's models: rows of provider, model and thinking, in the order they're tried
    component ModelList: ColumnLayout {
        id: list
        property string job
        property var entries: []
        // (Whisper-style hearing models think none; a speaking model's third word is its voice, none for Jarvis's own)
        readonly property var thinking: job === "image" ? ["none"] : (job === "hear" ? ["none"] : []).concat(["minimal", "low", "medium", "high"])
        function levels(backend) { return list.job !== "speak" ? list.thinking : /^(aistudio|antigravity)$/.test(backend) || backend === "local" && !page.ownLocal() ? ["none"] : page.voices }
        function update(i, parts) { const all = entries.slice(); all[i] = parts.join(" "); page.save(job, all) }
        function move(i) { const all = entries.slice(); all.splice(i - 1, 0, all.splice(i, 1)[0]); page.save(job, all) }
        function remove(i) { const all = entries.slice(); all.splice(i, 1); page.save(job, all) }
        function add() {
            const name = page.usableBackends(job)[0] || "aistudio", levels = list.levels(name)
            page.save(job, entries.concat([[name, page.modelsFor(name, job)[0] || "gemini-3.8-flash", levels[job === "speak" ? 0 : Math.min(1, levels.length - 1)]].join(" ")]))
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
                Rectangle {  // its place in the order
                    Layout.preferredWidth: 24; Layout.preferredHeight: 24; Layout.rightMargin: 4; radius: 12
                    color: row.index === 0 ? Theme.accentSoft : Theme.glass
                    border.width: 1; border.color: row.index === 0 ? Theme.alpha(Theme.accent, 0.25) : Theme.stroke
                    Txt { anchors.centerIn: parent; text: row.index + 1; kind: "label"; color: row.index === 0 ? Theme.accent : Theme.text3
                          font.features: { "tnum": 1 } }
                }
                Select { Layout.preferredWidth: 150; model: page.options(page.usableBackends(list.job), row.parts[0]); value: row.parts[0]
                         onPicked: v => list.update(row.index, [v, page.modelsFor(v, list.job)[0] || row.parts[1],
                                                                 list.levels(v).includes(row.parts[2]) || list.job !== "speak" ? row.parts[2] : list.levels(v)[0]]) }
                Select { Layout.fillWidth: true; visible: page.modelsFor(row.parts[0], list.job).length > 0
                         model: page.options(page.modelsFor(row.parts[0], list.job), row.parts[1]); value: row.parts[1]
                         onPicked: v => list.update(row.index, [row.parts[0], v, row.parts[2]]) }
                Field { Layout.fillWidth: true; visible: !page.modelsFor(row.parts[0], list.job).length; text: row.parts[1]; placeholderText: qsTr("model name")
                        onEditingFinished: if (text && text !== row.parts[1]) list.update(row.index, [row.parts[0], text.trim(), row.parts[2]]) }
                Select { Layout.preferredWidth: 120; model: page.options(list.levels(row.parts[0]), row.parts[2]); value: row.parts[2]
                         onPicked: v => list.update(row.index, [row.parts[0], row.parts[1], v]) }
                IconButton { symbol: "chevron"; rotation: 180; size: 32; glyph: 16; color: Theme.text3; tip: qsTr("Try this one sooner")
                             enabled: row.index > 0; opacity: enabled ? 1 : 0.3; onClicked: list.move(row.index) }
                IconButton { symbol: "trash"; size: 32; glyph: 16; color: Theme.text3; tip: qsTr("Remove")
                             enabled: list.job !== "agent" || list.entries.length > 1; opacity: enabled ? 1 : 0.3; onClicked: list.remove(row.index) }
            }
        }
        Pill { text: qsTr("Add a model"); symbol: "plus"; kind: "ghost"; implicitHeight: 32; Layout.leftMargin: 20; onClicked: list.add() }
    }
}
