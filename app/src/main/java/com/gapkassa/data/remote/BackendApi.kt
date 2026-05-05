package com.gapkassa.data.remote

import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface BackendApi {
    @GET("app/config")
    suspend fun appConfig(@Query("lang") language: String): AppConfigResponse

    @POST("auth/request-otp")
    suspend fun requestRegisterOtp(@Body request: RegisterRequest): MessageResponse

    @POST("auth/verify-otp")
    suspend fun verifyRegisterOtp(@Body request: RegisterVerifyRequest): AuthResponse

    @POST("auth/login")
    suspend fun login(@Body request: LoginRequest): AuthResponse

    @POST("auth/google")
    suspend fun googleAuth(@Body request: GoogleAuthRequest): AuthResponse

    @POST("auth/refresh")
    suspend fun refresh(@Body request: RefreshRequest): AuthResponse

    @POST("auth/logout")
    suspend fun logout(@Body request: LogoutRequest): MessageResponse

    @POST("devices/fcm-token")
    suspend fun registerDeviceToken(@Body request: DeviceTokenRequest): MessageResponse

    @POST("client-errors")
    suspend fun reportClientError(@Body request: ClientErrorReportRequest): MessageResponse

    @GET("me")
    suspend fun me(): UserDto

    @DELETE("me")
    suspend fun deleteMe(): MessageResponse

    @PATCH("me")
    suspend fun updateMe(@Body request: ProfileUpdateRequest): UserDto

    @POST("rooms")
    suspend fun createRoom(@Body request: RoomCreateRequest): RoomBundleDto

    @DELETE("rooms/{id}")
    suspend fun deleteRoom(@Path("id") roomId: String): MessageResponse

    @PATCH("rooms/{id}")
    suspend fun updateRoom(@Path("id") roomId: String, @Body request: RoomUpdateRequest): RoomDto

    @GET("rooms")
    suspend fun rooms(): List<RoomDto>

    @GET("rooms/{id}")
    suspend fun room(@Path("id") roomId: String): RoomBundleDto

    @GET("rooms/{id}/members")
    suspend fun roomMembers(@Path("id") roomId: String): List<MemberDto>

    @GET("rooms/{id}/payments")
    suspend fun roomPayments(@Path("id") roomId: String): List<PaymentDto>

    @PATCH("payments/{id}")
    suspend fun updatePaymentStatus(
        @Path("id") paymentId: String,
        @Body request: PaymentStatusUpdateRequest
    ): PaymentDto

    @PATCH("rooms/{id}/schedule")
    suspend fun updateSchedule(
        @Path("id") roomId: String,
        @Body request: ScheduleUpdateRequest
    ): MessageResponse
}
