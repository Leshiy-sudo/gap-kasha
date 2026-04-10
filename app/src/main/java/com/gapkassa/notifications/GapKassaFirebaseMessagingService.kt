package com.gapkassa.notifications

import android.util.Log
import com.gapkassa.BuildConfig
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage

/**
 * Receives FCM tokens and messages (stub logging for now).
 */
class GapKassaFirebaseMessagingService : FirebaseMessagingService() {
    override fun onNewToken(token: String) {
        super.onNewToken(token)
        if (BuildConfig.DEBUG) {
            Log.d("GapKassaFCM", "New token: $token")
        }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        if (BuildConfig.DEBUG) {
            Log.d("GapKassaFCM", "Message: ${message.data}")
        }
    }
}
