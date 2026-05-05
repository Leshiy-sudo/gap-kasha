package com.gapkassa.data.remote

import android.util.Log
import com.gapkassa.BuildConfig
import com.gapkassa.data.preferences.TokenStore
import com.squareup.moshi.Moshi
import com.squareup.moshi.kotlin.reflect.KotlinJsonAdapterFactory
import okhttp3.Authenticator
import okhttp3.Interceptor
import okhttp3.OkHttpClient
import okhttp3.Response
import okhttp3.Route
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import retrofit2.Call
import retrofit2.converter.moshi.MoshiConverterFactory

class ApiClient(tokenStore: TokenStore) {
    private val moshi = Moshi.Builder()
        .addLast(KotlinJsonAdapterFactory())
        .build()

    private val authInterceptor = Interceptor { chain ->
        val original = chain.request()
        val token = tokenStore.accessToken
        if (BuildConfig.DEBUG) {
            Log.d(
                "ApiClient",
                "request=${original.method} ${original.url} token=${if (token.isNullOrBlank()) "missing" else "present"}"
            )
        }
        val builder = original.newBuilder()
            .header("Accept", "application/json")
        if (!token.isNullOrBlank()) {
            builder.header("Authorization", "Bearer $token")
        }
        chain.proceed(builder.build())
    }

    private val loggingInterceptor = HttpLoggingInterceptor().apply {
        level = if (BuildConfig.DEBUG) HttpLoggingInterceptor.Level.BASIC else HttpLoggingInterceptor.Level.NONE
    }

    private interface RefreshApi {
        @retrofit2.http.POST("auth/refresh")
        fun refresh(@retrofit2.http.Body request: RefreshRequest): Call<AuthResponse>
    }

    private val refreshClient = OkHttpClient.Builder()
        .addInterceptor(loggingInterceptor)
        .build()

    private val refreshApi: RefreshApi by lazy {
        Retrofit.Builder()
            .baseUrl(BuildConfig.API_BASE_URL)
            .addConverterFactory(MoshiConverterFactory.create(moshi))
            .client(refreshClient)
            .build()
            .create(RefreshApi::class.java)
    }

    private val refreshLock = Any()

    private val authenticator = Authenticator { _: Route?, response: Response ->
        if (responseCount(response) >= 2) return@Authenticator null
        val refreshToken = tokenStore.refreshToken ?: run {
            tokenStore.clear()
            return@Authenticator null
        }
        synchronized(refreshLock) {
            val requestToken = response.request.header("Authorization")?.removePrefix("Bearer ")?.trim()
            val latestToken = tokenStore.accessToken
            if (!latestToken.isNullOrBlank() && latestToken != requestToken) {
                return@Authenticator response.request.newBuilder()
                    .header("Authorization", "Bearer $latestToken")
                    .build()
            }
            val refreshResponse = runCatching {
                refreshApi.refresh(RefreshRequest(refreshToken)).execute()
            }.getOrNull() ?: return@Authenticator null
            if (!refreshResponse.isSuccessful) {
                if (refreshResponse.code() == 401 || refreshResponse.code() == 403) {
                    tokenStore.clear()
                }
                return@Authenticator null
            }
            val body = refreshResponse.body() ?: return@Authenticator null
            tokenStore.saveSession(
                accessToken = body.accessToken,
                refreshToken = body.refreshToken,
                userId = body.user.id,
                userEmail = body.user.email
            )
            response.request.newBuilder()
                .header("Authorization", "Bearer ${body.accessToken}")
                .build()
        }
    }

    private val client = OkHttpClient.Builder()
        .addInterceptor(authInterceptor)
        .addInterceptor(loggingInterceptor)
        .authenticator(authenticator)
        .build()

    private val retrofit = Retrofit.Builder()
        .baseUrl(BuildConfig.API_BASE_URL)
        .addConverterFactory(MoshiConverterFactory.create(moshi))
        .client(client)
        .build()

    val backendApi: BackendApi = retrofit.create(BackendApi::class.java)

    private fun responseCount(response: Response): Int {
        var count = 1
        var prior = response.priorResponse
        while (prior != null) {
            count++
            prior = prior.priorResponse
        }
        return count
    }
}
