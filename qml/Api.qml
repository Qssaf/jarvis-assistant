pragma Singleton
import QtQuick
import Jarvis

// Calls into Jarvis without blocking the window: Api.get("/api/x", done), Api.post("/api/x", {...}, done, failed).
QtObject {
    id: api
    property int next: 0
    property var waiting: ({})

    function call(path, data, done, failed) {
        const rid = "r" + (++next)
        waiting[rid] = [done, failed]
        Backend.request(rid, path, data === undefined ? "" : JSON.stringify(data))
    }
    function get(path, done, failed) { call(path, undefined, done, failed) }
    function post(path, data, done, failed) { call(path, data || {}, done, failed) }
    // A model provider as the user knows it ("aistudio" is the API's word for their Gemini key); others by their name.
    function provider(id) { return id === "aistudio" ? qsTr("Gemini API key") : id === "antigravity" ? qsTr("Google sign-in") : id }

    readonly property Connections replies: Connections {
        target: Backend
        function onReply(rid, body, ok) {
            const cb = api.waiting[rid]
            delete api.waiting[rid]
            if (!cb) return
            const value = JSON.parse(body)
            if (ok && cb[0]) cb[0](value)
            else if (!ok) (cb[1] || function (e) { Backend.toast(e.error || qsTr("Something went wrong"), true) })(value)
        }
    }
}
