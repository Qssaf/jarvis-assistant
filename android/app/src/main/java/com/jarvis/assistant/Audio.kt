package com.jarvis.assistant

import android.annotation.SuppressLint
import android.media.AudioAttributes
import android.media.AudioFormat
import android.media.AudioManager
import android.media.AudioRecord
import android.media.AudioTrack
import android.media.MediaRecorder
import android.media.ToneGenerator
import android.os.SystemClock
import java.util.concurrent.LinkedBlockingQueue
import kotlin.concurrent.thread

/** Debug builds only: what the app did (connection, voice, microphone; never what was said), for
 *  `adb shell run-as com.jarvis.assistant cat files/trace.log`: some phones (Honor) encrypt logcat. */
object Trace {
    private var file: java.io.File? = null
    fun start(dir: java.io.File) { if (BuildConfig.DEBUG) file = java.io.File(dir, "trace.log") }
    @Synchronized fun log(what: String) {
        val f = file ?: return
        if (f.length() > 500_000) f.delete()
        runCatching { f.appendText("${java.text.SimpleDateFormat("HH:mm:ss.SSS", java.util.Locale.ROOT).format(java.util.Date())} $what\n") }
    }
}

/** The microphone as 80 ms frames of 16 kHz PCM: what the wake word and Jarvis both take. [onFrame] runs on its thread. */
class Mic(private val onFrame: (ShortArray) -> Unit) {
    @Volatile private var running = false
    val on get() = running

    @SuppressLint("MissingPermission")  // (whoever starts it has asked for RECORD_AUDIO)
    fun start(): Boolean {
        if (running) return true
        val size = maxOf(AudioRecord.getMinBufferSize(16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT), Wake.FRAME * 4)
        val record = try {
            AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION, 16000, AudioFormat.CHANNEL_IN_MONO, AudioFormat.ENCODING_PCM_16BIT, size)
        } catch (e: Exception) {
            Trace.log("mic: couldn't open ($e)")
            return false
        }
        if (record.state != AudioRecord.STATE_INITIALIZED) {
            Trace.log("mic: not initialised")
            record.release()
            return false
        }
        Trace.log("mic: on")
        running = true
        thread(name = "mic") {
            try {
                record.startRecording()
                val frame = ShortArray(Wake.FRAME)
                while (running) {
                    var n = 0
                    while (running && n < frame.size) {
                        val read = record.read(frame, n, frame.size - n)
                        if (read <= 0) running = false.also { Trace.log("mic: read gave $read") } else n += read
                    }
                    if (n == frame.size) onFrame(frame.copyOf())
                }
            } catch (e: Exception) {  // the microphone was taken away: start() is asked again when it's next needed
                Trace.log("mic: $e")
            } finally {
                Trace.log("mic: off")
                running = false
                runCatching { record.stop() }
                record.release()
            }
        }
        return true
    }

    fun stop() {
        running = false
    }
}

/** Plays Jarvis's voice (24 kHz PCM) as it streams in, and knows roughly when it will have finished. */
class Player {
    private val queue = LinkedBlockingQueue<ByteArray>()
    @Volatile private var until = 0L  // when what's queued will have played
    private val track by lazy {
        AudioTrack.Builder()
            .setAudioAttributes(AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_ASSISTANT).setContentType(AudioAttributes.CONTENT_TYPE_SPEECH).build())
            .setAudioFormat(AudioFormat.Builder().setSampleRate(24000).setEncoding(AudioFormat.ENCODING_PCM_16BIT).setChannelMask(AudioFormat.CHANNEL_OUT_MONO).build())
            .setBufferSizeInBytes(maxOf(AudioTrack.getMinBufferSize(24000, AudioFormat.CHANNEL_OUT_MONO, AudioFormat.ENCODING_PCM_16BIT), 24000))
            .setTransferMode(AudioTrack.MODE_STREAM).build()
    }
    private val tone by lazy { runCatching { ToneGenerator(AudioManager.STREAM_MUSIC, 55) }.getOrNull() }

    init {
        thread(isDaemon = true, name = "player") {
            while (true) {
                val pcm = queue.take()
                try {
                    if (track.playState != AudioTrack.PLAYSTATE_PLAYING) track.play()
                    track.write(pcm, 0, pcm.size)
                } catch (e: Exception) {  // (stopped mid-reply: the next one starts it again)
                }
            }
        }
    }

    /** Jarvis is talking (and for a moment after: the microphone would hear the end of it). */
    val busy get() = SystemClock.elapsedRealtime() < until + 400

    fun play(pcm: ByteArray) {
        until = maxOf(until, SystemClock.elapsedRealtime()) + pcm.size / 48  // (24 kHz, 2 bytes a sample: 48 bytes a millisecond)
        queue.put(pcm)
    }

    fun hush() {
        queue.clear()
        until = 0
        runCatching {
            track.pause()
            track.flush()
        }
    }

    /** The short sound that says "I heard the wake word". */
    fun chime() {
        tone?.startTone(ToneGenerator.TONE_PROP_BEEP, 120)
    }
}
