package com.gapkassa.data.remote

import com.squareup.moshi.Json

/** Payloads and responses for the local backend. */
data class PhoneAuthStartRequest(
    val phone: String
)

data class PhoneAuthVerifyRequest(
    val phone: String,
    val code: String
)

data class RefreshRequest(
    @Json(name = "refresh_token") val refreshToken: String
)

data class LogoutRequest(
    @Json(name = "refresh_token") val refreshToken: String?
)

data class DeviceTokenRequest(
    val token: String,
    val platform: String = "android"
)

data class ClientErrorReportRequest(
    val kind: String,
    @Json(name = "report_id") val reportId: String,
    @Json(name = "occurred_at") val occurredAt: String,
    @Json(name = "exception_type") val exceptionType: String?,
    val message: String,
    val stacktrace: String?,
    @Json(name = "thread_name") val threadName: String?,
    @Json(name = "app_version") val appVersion: String,
    @Json(name = "build_type") val buildType: String,
    @Json(name = "package_name") val packageName: String,
    @Json(name = "api_base_url") val apiBaseUrl: String,
    @Json(name = "device_model") val deviceModel: String,
    @Json(name = "android_version") val androidVersion: String,
    @Json(name = "user_id") val userId: String?,
    @Json(name = "user_phone") val userPhone: String?
)

data class MessageResponse(
    val message: String
)


data class UserDto(
    val id: String,
    val phone: String,
    val name: String?,
    @Json(name = "last_name") val lastName: String?,
    val patronymic: String?,
    @Json(name = "photo_url") val photoUrl: String?
)

data class AuthResponse(
    @Json(name = "access_token") val accessToken: String,
    @Json(name = "refresh_token") val refreshToken: String,
    val user: UserDto
)

data class ProfileUpdateRequest(
    val name: String?,
    @Json(name = "last_name") val lastName: String?,
    val patronymic: String?,
    val phone: String?,
    @Json(name = "photo_url") val photoUrl: String?
)

data class RoomCreateRequest(
    val name: String,
    val description: String?,
    @Json(name = "monthly_amount") val monthlyAmount: Long,
    @Json(name = "payment_day") val paymentDay: Int,
    @Json(name = "cycle_length_months") val cycleLengthMonths: Int,
    @Json(name = "auto_rotate") val autoRotate: Boolean,
    val members: List<MemberCreateRequest>
)

data class RoomUpdateRequest(
    val name: String?,
    val description: String?,
    @Json(name = "monthly_amount") val monthlyAmount: Long?,
    @Json(name = "payment_day") val paymentDay: Int?,
    @Json(name = "cycle_length_months") val cycleLengthMonths: Int?,
    @Json(name = "auto_rotate") val autoRotate: Boolean?,
    @Json(name = "member_count") val memberCount: Int?
)

data class RoomDto(
    val id: String,
    val name: String,
    val description: String?,
    @Json(name = "monthly_amount") val monthlyAmount: Long?,
    @Json(name = "payment_day") val paymentDay: Int?,
    @Json(name = "cycle_length_months") val cycleLengthMonths: Int?,
    @Json(name = "auto_rotate") val autoRotate: Boolean?,
    @Json(name = "member_count") val memberCount: Int?,
    @Json(name = "created_at") val createdAt: String?
)

data class MemberCreateRequest(
    val phone: String,
    val name: String?,
    val role: String?,
    @Json(name = "order_index") val orderIndex: Int?
)

data class MemberDto(
    @Json(name = "user_id") val userId: String,
    val phone: String,
    val name: String?,
    val role: String,
    @Json(name = "order_index") val orderIndex: Int
)

data class PaymentDto(
    val id: String,
    @Json(name = "room_id") val roomId: String,
    @Json(name = "payer_id") val payerId: String,
    @Json(name = "receiver_id") val receiverId: String,
    val amount: Long,
    val month: String,
    val status: String,
    @Json(name = "updated_at") val updatedAt: String
)

data class RoomBundleDto(
    val room: RoomDto,
    val members: List<MemberDto>,
    val payments: List<PaymentDto>
)

data class PaymentStatusUpdateRequest(
    val status: String
)

data class ScheduleItemRequest(
    val month: String,
    @Json(name = "receiver_id") val receiverId: String
)

data class ScheduleUpdateRequest(
    val items: List<ScheduleItemRequest>
)
