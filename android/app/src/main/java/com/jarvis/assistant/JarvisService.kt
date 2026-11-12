package com.jarvis.assistant

import android.Manifest
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder

/** Keeps Jarvis going while the app is closed: the link to the PC (reminders and finished tasks arrive as
 *  notifications) and, with the microphone, the wake word. Android only lets a service use the microphone if it was
 *  started while the app was on screen, so after a restart of the phone the wake word waits for the app to be opened. */
class JarvisService : Service() {
    override fun onBind(intent: Intent?): IBinder? = null

    override fun onCreate() {
        super.onCreate()
        Jarvis.init(this)
        Jarvis.hold()
        running = true
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        if (!Jarvis.serviceWanted) {
            stopSelf()
            return START_NOT_STICKY
        }
        val mic = Jarvis.micWanted && intent?.getBooleanExtra("boot", false) != true && intent != null  // (null: restarted by Android, in the background)
        if (!show(mic) && !(mic && show(false))) stopSelf()
        return START_STICKY
    }

    /** Becomes a foreground service of this kind; false if Android refuses (the microphone, from the background). */
    private fun show(mic: Boolean): Boolean = try {
        val manager = getSystemService(NotificationManager::class.java)
        manager.createNotificationChannel(NotificationChannel("status", "Jarvis is on", NotificationManager.IMPORTANCE_LOW))
        val open = PendingIntent.getActivity(this, 0, Intent(this, MainActivity::class.java), PendingIntent.FLAG_IMMUTABLE)
        val notification = Notification.Builder(this, "status").setSmallIcon(R.drawable.ic_launcher_monochrome)
            .setContentTitle(if (mic) "Listening for “${Jarvis.ui.wakePhrase}”" else "In touch with your PC")
            .setContentText(if (mic) "Say it, or tap to open Jarvis" else "Reminders and finished tasks arrive here")
            .setContentIntent(open).setOngoing(true).build()
        val type = when {
            Build.VERSION.SDK_INT >= 34 -> ServiceInfo.FOREGROUND_SERVICE_TYPE_SPECIAL_USE or (if (mic) ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE else 0)
            Build.VERSION.SDK_INT >= 30 -> if (mic) ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE else ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC
            else -> 0
        }
        if (Build.VERSION.SDK_INT >= 29) startForeground(1, notification, type) else startForeground(1, notification)
        Jarvis.serviceIs(true, mic && checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED)
        true
    } catch (e: Exception) {
        false
    }

    override fun onDestroy() {
        running = false
        Jarvis.serviceIs(false, false)
        Jarvis.release()
        super.onDestroy()
    }

    companion object {
        @Volatile var running = false
            private set
    }
}

/** The phone restarted: back in touch with the PC (the wake word needs the app opened once, see JarvisService). */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        Jarvis.init(context)
        if (Jarvis.serviceWanted) runCatching { context.startForegroundService(Intent(context, JarvisService::class.java).putExtra("boot", true)) }
    }
}
