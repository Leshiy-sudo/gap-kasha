package com.gapkassa.utils

import android.util.Patterns

/**
 * Common validation helpers for auth, profile, and room forms.
 */
object Validators {
    fun isEmailValid(email: String): Boolean =
        email.isNotBlank() && email.length <= 30 && Patterns.EMAIL_ADDRESS.matcher(email).matches()

    fun isPasswordValid(password: String): Boolean = password.length in 8..30

    fun isRoomNameValid(name: String): Boolean = name.trim().length in 3..30

    fun isNameValid(name: String): Boolean = name.trim().length in 2..30

    fun isPhoneValid(phone: String): Boolean =
        phone.trim().length in 7..15 && phone.all { it.isDigit() || it == '+' || it == ' ' || it == '-' }
}
