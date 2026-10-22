package com.jarvis.assistant

import org.json.JSONObject
import org.junit.Assert.assertArrayEquals
import org.junit.Assert.assertEquals
import org.junit.Assert.assertThrows
import org.junit.Test
import java.security.KeyFactory
import java.security.KeyPair
import java.security.interfaces.ECPublicKey
import java.security.spec.PKCS8EncodedKeySpec
import java.util.Base64

/** handshake.json comes from phone.py (test_jarvis.py checks it against phone.py too): the two sides must agree byte for byte. */
class HandshakeTest {
    private val v = JSONObject(javaClass.classLoader!!.getResource("handshake.json").readText())
    private fun bytes(name: String) = Base64.getDecoder().decode(v.getString(name))

    private fun phoneKeys(): KeyPair {
        val private = KeyFactory.getInstance("EC").generatePrivate(PKCS8EncodedKeySpec(bytes("phone_private")))
        return KeyPair(Crypto.point(bytes("phone_public"), Crypto.fresh().public as ECPublicKey), private)
    }

    @Test
    fun opensWhatThePcSealed() {
        val channel = Crypto.finish(phoneKeys(), bytes("pc_public"), bytes("welcome"))
        assertEquals("test-pc", channel.open(bytes("frame")).getString("name"))
        assertArrayEquals(bytes("phone_frame"), channel.seal(JSONObject().put("op", "hello")))  // (and the other way)
    }

    @Test
    fun refusesAnotherPc() {
        val other = Crypto.raw(Crypto.fresh().public as ECPublicKey)
        assertThrows(Exception::class.java) { Crypto.finish(phoneKeys(), other, bytes("welcome")) }
    }

    @Test
    fun rawKeysRoundTrip() {
        val key = Crypto.fresh().public as ECPublicKey
        assertEquals(key.w, Crypto.point(Crypto.raw(key), key).w)
    }
}
