package com.jarvis.assistant

import ai.onnxruntime.OnnxTensor
import ai.onnxruntime.OrtEnvironment
import ai.onnxruntime.OrtSession
import java.io.File
import java.nio.FloatBuffer
import kotlin.math.max
import kotlin.math.min
import kotlin.math.sqrt

/** The wake word, heard on the phone the way the PC hears it: openWakeWord's three models (a melspectrogram, Google's
 *  speech embedding, and the word itself), which the PC sends over (the `wake` op), fed 80 ms at a time exactly as
 *  openwakeword/utils.py's AudioFeatures does (WakeTest compares the two, number for number). */
class Wake(mel: File, embedding: File, word: File) : AutoCloseable {
    private val env = OrtEnvironment.getEnvironment()
    private val options = OrtSession.SessionOptions().apply { setIntraOpNumThreads(1); setInterOpNumThreads(1) }
    private val melModel = env.createSession(mel.path, options)
    private val embeddingModel = env.createSession(embedding.path, options)
    private val wordModel = env.createSession(word.path, options)
    private var raw = FloatArray(0)             // the last 80 ms + 30 ms: what one melspectrogram step needs
    private val mels = ArrayDeque<FloatArray>()  // rows of 32, the last 76 (0.76 s): one embedding
    private val features = ArrayDeque<FloatArray>()  // embeddings of 96, the last 16 (1.3 s): what the word model looks at
    var feature = FloatArray(0)  // the latest embedding (for the test)
        private set

    init {
        reset()
    }

    fun reset() {
        raw = FloatArray(0)
        mels.clear()
        repeat(MEL_ROWS) { mels.add(FloatArray(MEL_BINS) { 1f }) }
        features.clear()
    }

    private fun run(session: OrtSession, data: FloatArray, vararg shape: Long): FloatArray =
        OnnxTensor.createTensor(env, FloatBuffer.wrap(data), shape).use { input ->
            session.run(mapOf(session.inputNames.first() to input)).use { out ->
                (out[0] as OnnxTensor).floatBuffer.let { b -> FloatArray(b.remaining()).also(b::get) }
            }
        }

    /** The wake word's score, 0 to 1, after these 1280 samples (80 ms at 16 kHz). */
    fun score(frame: ShortArray): Float {
        require(frame.size == FRAME) { "frames are $FRAME samples" }
        val audio = raw.takeLast(CONTEXT).toFloatArray() + FloatArray(FRAME) { frame[it].toFloat() }
        raw = audio
        val spec = run(melModel, audio, 1, audio.size.toLong())
        for (i in 0 until spec.size / MEL_BINS) mels.add(FloatArray(MEL_BINS) { spec[i * MEL_BINS + it] / 10f + 2f })
        while (mels.size > MEL_ROWS) mels.removeFirst()
        val window = FloatArray(MEL_ROWS * MEL_BINS)
        mels.forEachIndexed { i, row -> row.copyInto(window, i * MEL_BINS) }
        feature = run(embeddingModel, window, 1, MEL_ROWS.toLong(), MEL_BINS.toLong(), 1)
        features.add(feature)
        while (features.size > FEATURES) features.removeFirst()
        if (features.size < FEATURES) return 0f
        val input = FloatArray(FEATURES * feature.size)
        features.forEachIndexed { i, f -> f.copyInto(input, i * f.size) }
        return run(wordModel, input, 1, FEATURES.toLong(), feature.size.toLong())[0]
    }

    override fun close() {
        melModel.close()
        embeddingModel.close()
        wordModel.close()
    }

    companion object {
        const val FRAME = 1280
        private const val CONTEXT = 480
        private const val MEL_ROWS = 76
        private const val MEL_BINS = 32
        private const val FEATURES = 16
    }
}

/** Runs the models only while the microphone hears more than the room's own noise, and for a moment after (the score
 *  peaks once the word has ended): a silent room costs no battery. When sound comes back the models first get the
 *  frames just before it, so a soft "Hey" isn't lost (jarvis.py's WakeGate and MicLevel, on the PC). */
class WakeGate(private val wake: Wake) {
    private var floor = 30f
    private var quiet = 0
    private var skipped = 0
    private val recent = ArrayDeque<ShortArray>()

    @Synchronized  // (the microphone's thread scores; the main thread resets when a conversation ends)
    fun score(frame: ShortArray): Float {
        var sum = 0.0
        for (s in frame) sum += s.toDouble() * s
        val level = sqrt(sum / frame.size).toFloat()
        floor = min(level, floor * 1.002f) + 0.05f
        quiet = if (level > max(2.5f * floor, 8f)) 0 else quiet + 1
        recent.add(frame)
        if (recent.size > PRE_ROLL + 1) recent.removeFirst()
        if (quiet > TAIL) {
            skipped++
            return 0f
        }
        if (skipped > 0) recent.toList().dropLast(1).takeLast(min(skipped, PRE_ROLL)).forEach { wake.score(it) }
        skipped = 0
        return wake.score(frame)
    }

    @Synchronized
    fun reset() {
        wake.reset()
        skipped = 0
    }

    companion object {
        const val TAIL = 19      // frames (1.5 s) the models go on for after the last sound (jarvis.py WAKE_TAIL)
        const val PRE_ROLL = 4   // frames (0.32 s) from before the sound came back (WAKE_PRE_ROLL)
        const val BAR = 0.5f     // the score that counts as the wake word
    }
}
