package com.gapkassa.utils

import java.util.Locale

/**
 * Lightweight text normalizers used by forms before validation and persistence.
 */
object InputFormatters {
    fun formatPersonName(value: String): String {
        val trimmedStart = value.trimStart()
        if (trimmedStart.isEmpty()) return ""
        return trimmedStart.replaceFirstChar { char ->
            if (char.isLowerCase()) {
                char.titlecase(Locale.getDefault())
            } else {
                char.toString()
            }
        }
    }
}
