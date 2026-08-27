package com.gapkassa.utils

/**
 * Common validation helpers for auth, profile, and room forms.
 */
object Validators {
    fun isRoomNameValid(name: String): Boolean = name.trim().length in 3..30

    fun isNameValid(name: String): Boolean = name.trim().length in 2..30

    fun isPhoneValid(phone: String): Boolean =
        phone.trim().length in 7..15 && phone.all { it.isDigit() || it == '+' || it == ' ' || it == '-' }
}
