package com.gapkassa.data.remote

import com.squareup.moshi.Json

data class AppConfigResponse(
    @Json(name = "generated_at") val generatedAt: String,
    val ads: AdConfigDto,
    val texts: Map<String, String>
)

data class AdConfigDto(
    val enabled: Boolean,
    val badge: String,
    val title: String,
    val body: String,
    val cta: String,
    @Json(name = "target_url") val targetUrl: String?
)
