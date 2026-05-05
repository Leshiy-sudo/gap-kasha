package com.gapkassa.auth

import android.app.Activity
import android.content.Context
import android.content.ContextWrapper
import android.util.Base64
import androidx.credentials.ClearCredentialStateRequest
import androidx.credentials.CredentialManager
import androidx.credentials.CustomCredential
import androidx.credentials.GetCredentialRequest
import androidx.credentials.exceptions.GetCredentialCancellationException
import com.gapkassa.BuildConfig
import com.google.android.libraries.identity.googleid.GetSignInWithGoogleOption
import com.google.android.libraries.identity.googleid.GoogleIdTokenCredential
import com.google.android.libraries.identity.googleid.GoogleIdTokenParsingException
import org.json.JSONObject
import java.security.SecureRandom

data class GoogleAuthToken(
    val idToken: String,
    val nonce: String?
)

class GoogleAuthException(
    val code: String,
    cause: Throwable? = null
) : Exception(code, cause)

class GoogleAuthManager(context: Context) {
    private val credentialManager = CredentialManager.create(context)
    private val secureRandom = SecureRandom()

    val isConfigured: Boolean
        get() = BuildConfig.GOOGLE_WEB_CLIENT_ID.isNotBlank()

    val isMockAvailable: Boolean
        get() = BuildConfig.DEBUG && BuildConfig.GOOGLE_AUTH_ALLOW_MOCK

    suspend fun requestGoogleToken(activity: Activity): GoogleAuthToken {
        if (!isConfigured) {
            throw GoogleAuthException("google_auth_not_configured")
        }

        val nonce = generateNonce()
        val request = GetCredentialRequest.Builder()
            .addCredentialOption(
                GetSignInWithGoogleOption.Builder(BuildConfig.GOOGLE_WEB_CLIENT_ID)
                    .setNonce(nonce)
                    .build()
            )
            .build()

        val credential = try {
            credentialManager.getCredential(activity, request).credential
        } catch (error: GetCredentialCancellationException) {
            throw GoogleAuthException("google_auth_cancelled", error)
        } catch (error: Exception) {
            throw GoogleAuthException("google_auth_failed", error)
        }

        if (credential !is CustomCredential ||
            credential.type != GoogleIdTokenCredential.TYPE_GOOGLE_ID_TOKEN_CREDENTIAL
        ) {
            throw GoogleAuthException("google_auth_invalid_response")
        }

        val googleCredential = try {
            GoogleIdTokenCredential.createFrom(credential.data)
        } catch (error: GoogleIdTokenParsingException) {
            throw GoogleAuthException("google_auth_invalid_response", error)
        }

        return GoogleAuthToken(
            idToken = googleCredential.idToken,
            nonce = nonce,
        )
    }

    fun buildMockGoogleToken(): GoogleAuthToken {
        if (!isMockAvailable) {
            throw GoogleAuthException("google_auth_mock_disabled")
        }
        val payload = JSONObject(
            mapOf(
                "email" to BuildConfig.GOOGLE_AUTH_MOCK_EMAIL,
                "sub" to BuildConfig.GOOGLE_AUTH_MOCK_SUBJECT,
                "name" to BuildConfig.GOOGLE_AUTH_MOCK_NAME,
                "given_name" to BuildConfig.GOOGLE_AUTH_MOCK_NAME,
                "family_name" to "",
                "email_verified" to true,
            )
        ).toString()
        return GoogleAuthToken(idToken = "mock-google:$payload", nonce = null)
    }

    suspend fun clearCredentialState() {
        runCatching {
            credentialManager.clearCredentialState(ClearCredentialStateRequest())
        }
    }

    private fun generateNonce(): String {
        val bytes = ByteArray(32)
        secureRandom.nextBytes(bytes)
        return Base64.encodeToString(
            bytes,
            Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
        )
    }
}

fun Context.findActivity(): Activity? = when (this) {
    is Activity -> this
    is ContextWrapper -> baseContext.findActivity()
    else -> null
}
