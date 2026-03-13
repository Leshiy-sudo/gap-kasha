package com.gapkassa.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Column
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.MaterialTheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.luminance
import androidx.compose.ui.unit.dp
import com.gapkassa.ui.theme.FintechRadius
import com.gapkassa.ui.theme.UiConfig

@Composable
fun AppCard(
    modifier: Modifier = Modifier,
    onClick: (() -> Unit)? = null,
    content: @Composable () -> Unit
) {
    val isDark = MaterialTheme.colorScheme.background.luminance() < 0.5f
    val shape = androidx.compose.foundation.shape.RoundedCornerShape(FintechRadius.large)
    val baseModifier = if (onClick != null) modifier.clickable { onClick() } else modifier
    Card(
        modifier = baseModifier,
        shape = shape,
        colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
        elevation = if (UiConfig.useCleanFintechRedesign && !isDark) CardDefaults.cardElevation(6.dp) else CardDefaults.cardElevation(0.dp),
        border = if (UiConfig.useCleanFintechRedesign && isDark) BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant) else null
    ) {
        Column { content() }
    }
}
