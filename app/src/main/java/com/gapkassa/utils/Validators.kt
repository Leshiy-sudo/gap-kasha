package com.gapkassa.utils

import android.util.Patterns

/**
 * Common validation helpers for auth, profile, and room forms.
 */
object Validators {
    fun isEmailValid(email: String): Boolean =
        email.isNotBlank() && Patterns.EMAIL_ADDRESS.matcher(email).matches()

    fun isPasswordValid(password: String): Boolean = password.length >= 8

    fun isRoomNameValid(name: String): Boolean = name.trim().length >= 3

    fun isNameValid(name: String): Boolean = name.trim().length >= 2

    fun isPhoneValid(phone: String): Boolean =
        phone.trim().length in 7..15 && phone.all { it.isDigit() || it == '+' || it == ' ' || it == '-' }
}
