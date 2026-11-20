package com.jarvis.assistant

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.security.interfaces.ECPublicKey
import java.util.Base64

/** A pairing link can come from any web page: only one the app can really connect with is kept (a bad one crashed it at
 *  every start). (What a PC that went offline was asked: AsksTest.) */
class PairingTest {
    private val b64 = Base64.getUrlEncoder().withoutPadding()
    private val key = b64.encodeToString(Crypto.raw(Crypto.fresh().public as ECPublicKey))

    private fun link(relay: String, pc: String = "a".repeat(43), k: String = key, p: String = "s3cret", d: List<String>? = null) = "jarvis://pair#" +
        b64.encodeToString(JSONObject().put("v", 1).put("r", relay).put("s", pc).put("k", k).put("p", p)
            .apply { if (d != null) put("d", JSONArray(d)) }.toString().toByteArray())

    @Test
    fun readsTheCodeThePcShows() {
        assertEquals("wss://relay.example.workers.dev", Pairing.parse(link("wss://relay.example.workers.dev"))?.relay)
        assertEquals("ws://localhost:8787", Pairing.parse(link("ws://localhost:8787"))?.relay)  // (wrangler dev)
    }

    /** The PC's own addresses (the same Wi-Fi, a VPN) are a way to it too: with them a code needs no relay, and what
     *  isn't an address the app could dial is left out. */
    @Test
    fun readsWhereThePcIsOnItsNetwork() {
        val both = Pairing.parse(link("wss://relay.example.workers.dev", d = listOf("192.168.1.20:47800", "100.64.0.7:47800")))
        assertEquals(listOf("192.168.1.20:47800", "100.64.0.7:47800"), both?.direct)
        assertEquals(listOf("192.168.1.20:47800"), Pairing.parse(link("", d = listOf("192.168.1.20:47800")))?.direct)
        assertEquals(listOf("pc.tailnet.ts.net:47800"),
            Pairing.parse(link("", d = listOf("pc.tailnet.ts.net:47800", "no port", "evil.example/path:80", "1.2.3.4:99999999", "@:1")))?.direct)
        assertNull(Pairing.parse(link("", d = listOf("nothing usable"))))
        assertNull(Pairing.parse(link("", d = emptyList())))
        assertEquals(emptyList<String>(), Pairing.parse(link("wss://relay.example.workers.dev"))?.direct)  // (a code from an older Jarvis)
    }

    @Test
    fun refusesWhatTheAppCantConnectWith() {
        for (bad in listOf(link("x"), link(""), link("https://relay.example"), link("wss://relay .example"),
                           link("wss://r.example", pc = "short"), link("wss://r.example", k = "AAAA"), link("wss://r.example", p = ""),
                           "jarvis://pair#not-json"))
            assertNull(bad, Pairing.parse(bad))
    }
}
