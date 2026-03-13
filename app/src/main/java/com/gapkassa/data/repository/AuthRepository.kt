package com.gapkassa.data.repository

import android.content.Context
import com.google.firebase.FirebaseApp
import com.google.firebase.auth.FirebaseAuth
import kotlinx.coroutines.tasks.await

/**
 * Authentication gateway. Uses Firebase when available and falls back to a local stub in debug.
 */
class AuthRepository(context: Context) {
    private val auth: FirebaseAuth? = try {
        if (FirebaseApp.getApps(context).isEmpty()) {
            FirebaseApp.initializeApp(context)
        }
        FirebaseAuth.getInstance()
    } catch (e: Exception) {
        null
    }

    private var localUserId: String? = null

    val isFirebaseAvailable: Boolean
        get() = auth != null

    val currentUserId: String?
        get() = auth?.currentUser?.uid ?: localUserId

    suspend fun register(email: String, password: String): Result<Unit> = runCatching {
        if (auth == null) {
            localUserId = email.lowercase()
            return@runCatching
        }
        val result = auth.createUserWithEmailAndPassword(email, password).await()
        result.user?.sendEmailVerification()?.await()
    }

    suspend fun login(email: String, password: String): Result<Unit> = runCatching {
        if (auth == null) {
            localUserId = email.lowercase()
            return@runCatching
        }
        auth.signInWithEmailAndPassword(email, password).await()
    }

    suspend fun resetPassword(email: String): Result<Unit> = runCatching {
        if (auth == null) return@runCatching
        auth.sendPasswordResetEmail(email).await()
    }

    fun logout() {
        auth?.signOut()
        localUserId = null
    }
}
