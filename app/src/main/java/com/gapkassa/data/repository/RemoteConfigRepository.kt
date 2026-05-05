package com.gapkassa.data.repository

import com.gapkassa.data.preferences.AppConfigStore
import com.gapkassa.data.remote.AdConfigDto
import com.gapkassa.data.remote.AppConfigResponse
import com.gapkassa.data.remote.BackendApi
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow

class RemoteConfigRepository(
    private val backendApi: BackendApi,
    private val cache: AppConfigStore
) {
    private val fallback = cache.read() ?: AppConfigResponse(
        generatedAt = "",
        ads = AdConfigDto(
            enabled = true,
            badge = "AD",
            title = "Тестовая интеграция",
            body = "GapPay: скидка 20% на комиссии до 30 апреля. Подключение за 5 минут.",
            cta = "Подключить",
            targetUrl = ""
        ),
        texts = mapOf(
            "helper_register_otp" to "Мы отправим код подтверждения на указанный email.",
            "verification_hint" to "Можно вставить ссылку из письма — приложение извлечёт код.",
            "message_verification_sent" to "Письмо с кодом отправлено. Проверьте почту."
        )
    )

    private val _config = MutableStateFlow(fallback)
    val configFlow: StateFlow<AppConfigResponse> = _config.asStateFlow()

    suspend fun refresh(language: String) {
        runCatching { backendApi.appConfig(language) }
            .onSuccess {
                cache.write(it)
                _config.value = it
            }
    }

    fun text(key: String): String? = _config.value.texts[key]
}
