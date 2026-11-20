package com.jarvis.assistant

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Test

/** The link dropped while the PC worked on what the phone asked: the app used to say "ask again", and asking again did
 *  it twice (an event made, a message sent). Now it waits for the answer the PC kept, and lets go only of what the PC
 *  says it doesn't know (it restarted), or can't say (an older Jarvis). */
class AsksTest {
    @Test
    fun waitsForTheAnswerAcrossADrop() {
        val asks = Asks()
        asks.sent(1)
        assertTrue(asks.dropped())   // the app says the answer comes once the link is back...
        assertFalse(asks.dropped())  // ...once (connecting, then the PC offline: not said again)
        assertEquals(listOf(1), asks.hello())  // back: the hello names what it still waits for
        asks.sent(2)                 // (asked once back, before the PC's ready: not the ready's to answer for)
        assertEquals(emptyList<Int>(), asks.back(emptyList()))
        assertTrue(asks.any)         // "Working on it…" stays: the PC is still on it
        asks.answered(1)
        assertTrue(asks.any)
        asks.answered(2)
        assertFalse(asks.any)
        asks.sent(3)
        assertTrue(asks.dropped())   // (a later drop with something new waiting: said again)
    }

    @Test
    fun letsGoOfWhatThePcLost() {
        val asks = Asks()
        asks.sent(1)
        asks.sent(2)
        asks.dropped()
        assertEquals(listOf(1, 2), asks.hello())
        asks.sent(3)
        asks.answered(1)              // (an answer that came between the hello and the ready)
        assertEquals(listOf(2), asks.back(listOf(1, 2, 3)))  // the PC restarted: no answer is coming for 2
        assertTrue(asks.any)          // 3 was asked after the hello
        asks.answered(3)
        assertFalse(asks.any)
        assertEquals(emptyList<Int>(), asks.back(listOf(2)))  // (a ready answers one hello only)
    }

    @Test
    fun anOlderPcCantSay() {
        val asks = Asks()
        asks.sent(1)
        asks.dropped()
        asks.hello()
        asks.sent(2)
        assertEquals(listOf(1), asks.back(null))  // not waited for ("Working on it…" doesn't stay up for good)...
        assertTrue(asks.any)                       // ...but what was asked after the hello is
        assertNull(lost(JSONObject().put("op", "ready")))
        assertEquals(listOf(4, 5), lost(JSONObject().put("op", "ready").put("lost", JSONArray(listOf(4, 5)))))
    }

    @Test
    fun theHelloNamesWhatTheAppWaitsFor() {
        val hello = greeting("t0ken", listOf(7, 9))
        assertEquals("hello", hello.getString("op"))
        assertEquals("t0ken", hello.getString("token"))
        assertEquals(listOf(7, 9), hello.getJSONArray("waiting").let { a -> (0 until a.length()).map { a.getInt(it) } })
    }

    @Test
    fun unpairedForgetsWhatWasAsked() {
        val asks = Asks()
        asks.sent(1)
        asks.clear()
        assertFalse(asks.any)
        assertFalse(asks.dropped())
        assertEquals(emptyList<Int>(), asks.hello())
    }
}
