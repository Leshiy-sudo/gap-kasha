package com.gapkassa.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import com.gapkassa.data.repository.ThemeMode

private val LegacyLightColors = lightColorScheme(
    primary = Primary,
    secondary = Secondary,
    tertiary = Accent,
    error = ErrorColor,
    background = Color.White,
    surface = Color.White,
    onBackground = Color.Black,
    onSurface = Color.Black,
    onPrimary = Color.White,
    onSecondary = Color.White,
    onTertiary = Color.White,
    onError = Color.White,
    surfaceVariant = Color(0xFFF2F3F5),
    onSurfaceVariant = Color.Black
)

private val LegacyDarkColors = darkColorScheme(
    primary = Primary,
    secondary = Secondary,
    tertiary = Accent,
    error = ErrorColor,
    background = Color.Black,
    surface = Color.Black,
    onBackground = Color(0xFFF5F5F5),
    onSurface = Color(0xFFF5F5F5),
    onPrimary = Color(0xFFF5F5F5),
    onSecondary = Color(0xFFF5F5F5),
    onTertiary = Color(0xFFF5F5F5),
    onError = Color(0xFFF5F5F5),
    surfaceVariant = Color(0xFF101010),
    onSurfaceVariant = Color(0xFFF5F5F5)
)

/**
 * App theme wrapper with explicit light/dark palettes and edge-to-edge setup.
 */
@Composable
fun GapKassaTheme(themeMode: ThemeMode, content: @Composable () -> Unit) {
    val view = LocalView.current
    SideEffect {
        val window = (view.context as android.app.Activity).window
        WindowCompat.setDecorFitsSystemWindows(window, false)
    }
    val isDark = when (themeMode) {
        ThemeMode.DARK -> true
        ThemeMode.LIGHT -> false
    }
    val useFintech = UiConfig.useCleanFintechRedesign
    MaterialTheme(
        colorScheme = when {
            useFintech && isDark -> FintechDarkColors
            useFintech && !isDark -> FintechLightColors
            !useFintech && isDark -> LegacyDarkColors
            else -> LegacyLightColors
        },
        typography = if (useFintech) FintechTypography else LegacyTypography,
        shapes = if (useFintech) FintechShapes else LegacyShapes,
        content = content
    )
}
