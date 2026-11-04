package com.jarvis.assistant

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test
import java.security.interfaces.ECPublicKey
import java.util.Base64

/** A pairing link can come from any web page: only one the app can really connect with is kept (a bad one crashed it at
 *  every start). And a PC that went offline doesn't leave "Working on it…" up for good. */
class PairingTest {
    private val b64 = Base64.getUrlEncoder().withoutPadding()
    private val key = b64.encodeToString(Crypto.raw(Crypto.fresh().public as ECPublicKey))

    private fun link(relay: String, pc: String = "a".repeat(43), k: String = key, p: String = "s3cret") = "jarvis://pair#" +
        b64.encodeToString(JSONObject().put("v", 1).put("r", relay).put("s", pc).put("k", k).put("p", p).toString().toByteArray())

    @Test
    fun readsTheCodeThePcShows() {
        assertEquals("wss://relay.example.workers.dev", Pairing.parse(link("wss://relay.example.workers.dev"))?.relay)
        assertEquals("ws://localhost:8787", Pairing.parse(link("ws://localhost:8787"))?.relay)  // (wrangler dev)
    }

    @Test
    fun refusesWhatTheAppCantConnectWith() {
        for (bad in listOf(link("x"), link(""), link("https://relay.example"), link("wss://relay .example"),
                           link("wss://r.example", pc = "short"), link("wss://r.example", k = "AAAA"), link("wss://r.example", p = ""),
                           "jarvis://pair#not-json"))
            assertNull(bad, Pairing.parse(bad))
    }

    @Test
    fun letsGoOfWhatAnOfflinePcWontAnswer() {
        val waiting = mutableMapOf(1 to true)
        assertFalse(dropWaiting(State.ONLINE, waiting))
        assertEquals(1, waiting.size)
        assertTrue(dropWaiting(State.PC_OFFLINE, waiting))
        assertTrue(waiting.isEmpty())
        assertFalse(dropWaiting(State.PC_OFFLINE, waiting))  // (nothing waiting: no note)
    }
}
