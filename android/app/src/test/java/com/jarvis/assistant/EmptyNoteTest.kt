package com.jarvis.assistant

import org.junit.Assert.assertEquals
import org.junit.Test

/** An empty Today or PC page says nothing is there only once the PC has answered: out of reach, it said "No reminders
 *  set." and "Nothing is playing." without having asked. */
class EmptyNoteTest {
    @Test
    fun saysWhyItsEmpty() {
        assertEquals("No reminders set.", emptyNote(Ui(state = State.ONLINE, loaded = true), "No reminders set."))
        assertEquals("Asking your PC…", emptyNote(Ui(state = State.ONLINE), "No reminders set."))
        assertEquals("Asking your PC…", emptyNote(Ui(state = State.CONNECTING), "Nothing is playing."))
        for (state in listOf(State.PC_OFFLINE, State.NO_RELAY, State.UNPAIRED))
            assertEquals("Your PC is out of reach.", emptyNote(Ui(state = state), "Nothing is playing."))
    }
}
