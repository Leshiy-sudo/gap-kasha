package com.gapkassa.notifications

import android.util.Log
import com.gapkassa.GapKassaApp
import com.gapkassa.BuildConfig
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch

/**
 * Receives FCM tokens and messages (stub logging for now).
 */
class GapKassaFirebaseMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        if (BuildConfig.DEBUG) {
            Log.d("GapKassaFCM", "New token: $token")
        }
        val app = application as? GapKassaApp ?: return
        if (!app.authRepository.hasStoredSession) return
        CoroutineScope(Dispatchers.IO).launch {
            runCatching { app.notificationRepository.registerFcmToken(token) }
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        if (BuildConfig.DEBUG) {
            Log.d("GapKassaFCM", "Message: ${message.data}")
        }
        val title = message.notification?.title ?: message.data["title"] ?: "GapKassa"
        val body = message.notification?.body ?: message.data["body"] ?: return
        GapKassaNotifications.showRemoteMessage(applicationContext, title, body)
    }
}
