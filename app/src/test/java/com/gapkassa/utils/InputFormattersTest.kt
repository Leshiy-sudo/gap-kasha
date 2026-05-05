package com.gapkassa.utils

import org.junit.Assert.assertEquals
import org.junit.Test

class InputFormattersTest {
    @Test
    fun formatPersonName_trimsLeadingWhitespaceAndCapitalizesFirstLetter() {
        assertEquals("Ivan", InputFormatters.formatPersonName("   ivan"))
    }

    @Test
    fun formatPersonName_returnsEmptyStringForBlankInput() {
        assertEquals("", InputFormatters.formatPersonName("   "))
    }
}
