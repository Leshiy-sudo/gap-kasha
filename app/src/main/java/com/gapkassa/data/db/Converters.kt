package com.gapkassa.data.db

import androidx.room.TypeConverter
import java.time.LocalDate

/**
 * Type converters for Room to persist java.time values.
 */
class Converters {
    @TypeConverter
    fun fromLocalDate(value: LocalDate?): String? = value?.toString()

    @TypeConverter
    fun toLocalDate(value: String?): LocalDate? = value?.let { LocalDate.parse(it) }
}
