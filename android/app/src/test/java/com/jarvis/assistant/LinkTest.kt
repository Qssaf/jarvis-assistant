package com.jarvis.assistant

import okhttp3.Dns
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.net.InetAddress
import java.net.UnknownHostException

/** On a real phone the private DNS timed out for minutes while the relay's address stayed the same, and the app sat on
 *  "Relay unreachable": a lookup that fails gives the last answer that worked. */
class LinkTest {
    @Test
    fun keptDns() {
        val relay = listOf(InetAddress.getByAddress(byteArrayOf(188.toByte(), 114, 96, 3)))
        var up = true
        val dns = KeptDns(object : Dns {
            override fun lookup(hostname: String) = if (up) relay else throw UnknownHostException(hostname)
        })
        assertEquals(relay, dns.lookup("relay.example.workers.dev"))
        up = false
        assertEquals(relay, dns.lookup("relay.example.workers.dev"))
        assertThrows(UnknownHostException::class.java) { dns.lookup("never.example.com") }  // (never answered: nothing to fall back on)
    }
}
