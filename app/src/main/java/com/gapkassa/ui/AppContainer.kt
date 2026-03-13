package com.gapkassa.ui

import androidx.compose.runtime.staticCompositionLocalOf
import com.gapkassa.GapKassaApp

// CompositionLocal to access app-level repositories from composables.
val LocalAppContainer = staticCompositionLocalOf<GapKassaApp> {
    error("GapKassaApp not provided")
}
