package com.gapkassa.data.repository

import com.gapkassa.data.remote.BackendApi
import com.gapkassa.data.remote.DeviceTokenRequest

class NotificationRepository(
    private val api: BackendApi
) {
    suspend fun registerFcmToken(token: String) {
        if (token.isBlank()) return
        api.registerDeviceToken(DeviceTokenRequest(token = token))
    }
}
