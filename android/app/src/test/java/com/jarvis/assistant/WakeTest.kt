package com.jarvis.assistant

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertTrue
import org.junit.Assume.assumeTrue
import org.junit.Test
import java.io.File
import kotlin.math.abs

/** Wake.kt against openWakeWord itself: the same made-up signal through the same three models must give the numbers
 *  evals/wake_vector.py wrote (wake.json). The models aren't in the repository: WAKE_MODELS names the folder holding
 *  melspectrogram.onnx, embedding_model.onnx and hey_jarvis_v0.1.onnx (the PC's
 *  .venv, under site-packages/openwakeword/resources/models; tests.yml downloads them). Skipped without it. */
class WakeTest {
    private val models = System.getenv("WAKE_MODELS")?.let(::File)

    private fun wake(): Wake {
        assumeTrue("WAKE_MODELS isn't set", models?.resolve("hey_jarvis_v0.1.onnx")?.exists() == true)
        return Wake(models!!.resolve("melspectrogram.onnx"), models.resolve("embedding_model.onnx"), models.resolve("hey_jarvis_v0.1.onnx"))
    }

    private var x = 12345L
    private fun frame() = ShortArray(Wake.FRAME) {
        x = (x * 1103515245 + 12345) and 0x7fffffff
        ((x shr 8) % 6001 - 3000).toShort()
    }

    @Test
    fun hearsWhatThePcHears() {
        val want = JSONObject(javaClass.getResource("/wake.json")!!.readText())
        wake().use { wake ->
            val scores = (0 until want.getInt("frames")).map { wake.score(frame()) }
            val feature = want.getJSONArray("feature")
            assertEquals(feature.length(), wake.feature.size)
            for (i in 0 until feature.length()) assertEquals("embedding $i", feature.getDouble(i), wake.feature[i].toDouble(), 0.01)
            val last = want.getJSONArray("scores")
            for (i in 0 until last.length()) assertEquals("score $i", last.getDouble(i), scores[scores.size - last.length() + i].toDouble(), 1e-4)
        }
    }

    /** A quiet room doesn't run the models; sound does, starting with the frames just before it. */
    @Test
    fun restsWhileItsQuiet() {
        wake().use { wake ->
            val gate = WakeGate(wake)
            repeat(WakeGate.TAIL + 30) { gate.score(ShortArray(Wake.FRAME)) }
            val before = wake.feature
            gate.score(ShortArray(Wake.FRAME))
            assertTrue(before === wake.feature)  // (still resting)
            gate.score(frame())
            assertTrue(before !== wake.feature && abs(wake.feature[0]) > 0f)
        }
    }

    /** The real thing, on this PC only: WAKE_CLIP names a 16 kHz mono 16-bit WAV of someone saying the wake word. */
    @Test
    fun wakesToTheRealWord() {
        val clip = System.getenv("WAKE_CLIP")?.let(::File)
        assumeTrue("WAKE_CLIP isn't set", clip?.exists() == true)
        wake().use { wake ->
            val pcm = clip!!.readBytes().drop(44)
            val samples = ShortArray(pcm.size / 2) { ((pcm[2 * it + 1].toInt() shl 8) or (pcm[2 * it].toInt() and 0xff)).toShort() }
            val gate = WakeGate(wake)
            val padded = ShortArray(16000) + samples + ShortArray(16000)  // (a second of quiet each side, as a room has)
            val best = (0 until padded.size / Wake.FRAME).maxOf { gate.score(padded.copyOfRange(it * Wake.FRAME, (it + 1) * Wake.FRAME)) }
            assertTrue("the wake word scored $best", best >= WakeGate.BAR)
        }
    }
}
