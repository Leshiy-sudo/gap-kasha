package com.gapkassa.ui.theme

import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.ui.graphics.Color

object FintechColors {
    // Light
    val PrimaryBlue = Color(0xFF1D4ED8)
    val PrimaryBluePressed = Color(0xFF1E40AF)
    val PrimaryBlueSoft = Color(0xFFDBEAFE)

    val AccentNavy = Color(0xFF0F172A)
    val AccentSlate = Color(0xFF334155)

    val Background = Color(0xFFF8FAFC)
    val Surface = Color(0xFFFFFFFF)
    val SurfaceSecondary = Color(0xFFF1F5F9)
    val SurfaceMuted = Color(0xFFE2E8F0)

    val TextPrimary = Color(0xFF0F172A)
    val TextSecondary = Color(0xFF475569)
    val TextTertiary = Color(0xFF64748B)
    val TextDisabled = Color(0xFF94A3B8)

    val BorderDefault = Color(0xFFCBD5E1)
    val BorderFocus = Color(0xFF1D4ED8)
    val Divider = Color(0xFFE2E8F0)

    val Success = Color(0xFF16A34A)
    val SuccessSoft = Color(0xFFDCFCE7)
    val Warning = Color(0xFFD97706)
    val WarningSoft = Color(0xFFFEF3C7)
    val Error = Color(0xFFDC2626)
    val ErrorSoft = Color(0xFFFEE2E2)
    val Info = Color(0xFF0284C7)
    val InfoSoft = Color(0xFFE0F2FE)

    val IconDefault = Color(0xFF475569)
    val IconActive = Color(0xFF1D4ED8)
    val DisabledBackground = Color(0xFFE2E8F0)

    // Dark
    val BackgroundDark = Color(0xFF020617)
    val SurfaceDark = Color(0xFF0F172A)
    val SurfaceDarkSecondary = Color(0xFF111827)
    val SurfaceDarkTertiary = Color(0xFF1E293B)

    val TextPrimaryDark = Color(0xFFF8FAFC)
    val TextSecondaryDark = Color(0xFFCBD5E1)
    val TextTertiaryDark = Color(0xFF94A3B8)
    val TextDisabledDark = Color(0xFF64748B)

    val BorderDefaultDark = Color(0xFF334155)
    val BorderFocusDark = Color(0xFF60A5FA)
    val DividerDark = Color(0xFF1E293B)

    val PrimaryBlueDark = Color(0xFF3B82F6)
    val PrimaryBluePressedDark = Color(0xFF2563EB)
    val PrimaryBlueSoftDark = Color(0xFF1E3A8A)

    val SuccessDark = Color(0xFF22C55E)
    val SuccessSoftDark = Color(0xFF052E16)
    val WarningDark = Color(0xFFF59E0B)
    val WarningSoftDark = Color(0xFF451A03)
    val ErrorDark = Color(0xFFEF4444)
    val ErrorSoftDark = Color(0xFF450A0A)
    val InfoDark = Color(0xFF38BDF8)
    val InfoSoftDark = Color(0xFF082F49)
}

val FintechLightColors = lightColorScheme(
    primary = FintechColors.PrimaryBlue,
    onPrimary = Color.White,
    primaryContainer = FintechColors.PrimaryBlueSoft,
    onPrimaryContainer = FintechColors.AccentNavy,
    secondary = FintechColors.AccentSlate,
    onSecondary = Color.White,
    tertiary = FintechColors.Info,
    onTertiary = Color.White,
    background = FintechColors.Background,
    onBackground = FintechColors.TextPrimary,
    surface = FintechColors.Surface,
    onSurface = FintechColors.TextPrimary,
    surfaceVariant = FintechColors.SurfaceSecondary,
    onSurfaceVariant = FintechColors.TextSecondary,
    outline = FintechColors.BorderDefault,
    outlineVariant = FintechColors.Divider,
    error = FintechColors.Error,
    onError = Color.White,
    errorContainer = FintechColors.ErrorSoft,
    onErrorContainer = FintechColors.Error
)

val FintechDarkColors = darkColorScheme(
    primary = FintechColors.PrimaryBlueDark,
    onPrimary = FintechColors.TextPrimaryDark,
    primaryContainer = FintechColors.PrimaryBlueSoftDark,
    onPrimaryContainer = FintechColors.TextPrimaryDark,
    secondary = FintechColors.SurfaceDarkTertiary,
    onSecondary = FintechColors.TextPrimaryDark,
    tertiary = FintechColors.InfoDark,
    onTertiary = FintechColors.TextPrimaryDark,
    background = FintechColors.BackgroundDark,
    onBackground = FintechColors.TextPrimaryDark,
    surface = FintechColors.SurfaceDark,
    onSurface = FintechColors.TextPrimaryDark,
    surfaceVariant = FintechColors.SurfaceDarkSecondary,
    onSurfaceVariant = FintechColors.TextSecondaryDark,
    outline = FintechColors.BorderDefaultDark,
    outlineVariant = FintechColors.DividerDark,
    error = FintechColors.ErrorDark,
    onError = FintechColors.TextPrimaryDark,
    errorContainer = FintechColors.ErrorSoftDark,
    onErrorContainer = FintechColors.TextPrimaryDark
)
