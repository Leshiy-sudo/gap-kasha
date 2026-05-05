package com.gapkassa.ui.components

import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.platform.LocalUriHandler
import androidx.compose.ui.unit.dp
import com.gapkassa.ui.LocalAppContainer
import com.gapkassa.ui.theme.FintechSpacing

/**
 * Small ad placeholder card. Replace content with an ad SDK integration when ready.
 */
@Composable
fun AdSlot(
    modifier: Modifier = Modifier,
    onAction: (() -> Unit)? = null
) {
    val app = LocalAppContainer.current
    val config by app.remoteConfigRepository.configFlow.collectAsState()
    val ad = config.ads
    if (!ad.enabled) return
    val uriHandler = LocalUriHandler.current
    val isClickable = onAction != null || !ad.targetUrl.isNullOrBlank()

    Surface(
        modifier = if (isClickable) {
            modifier.clickable {
                onAction?.invoke()
                ad.targetUrl?.takeIf { it.isNotBlank() }?.let(uriHandler::openUri)
            }
        } else {
            modifier
        },
        shape = RoundedCornerShape(0.dp),
        color = MaterialTheme.colorScheme.surface,
        tonalElevation = 0.dp,
        shadowElevation = 0.dp,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    ) {
        Column(
            modifier = Modifier
                .fillMaxWidth()
                .heightIn(min = 56.dp)
                .padding(horizontal = FintechSpacing.md, vertical = FintechSpacing.sm),
            verticalArrangement = Arrangement.spacedBy(4.dp)
        ) {
            Row(
                horizontalArrangement = Arrangement.spacedBy(6.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                Text(
                    text = ad.badge,
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier
                        .clip(RoundedCornerShape(6.dp))
                        .background(MaterialTheme.colorScheme.surfaceVariant)
                        .padding(horizontal = 4.dp, vertical = 1.dp)
                )
                Text(
                    text = ad.title,
                    style = MaterialTheme.typography.labelLarge
                )
            }
            Text(
                text = ad.body,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                maxLines = 2,
                overflow = TextOverflow.Ellipsis
            )
            if (!ad.cta.isNullOrBlank()) {
                Text(
                    text = ad.cta,
                    style = MaterialTheme.typography.labelMedium,
                    color = MaterialTheme.colorScheme.primary,
                    modifier = Modifier
                        .align(Alignment.End)
                        .clip(RoundedCornerShape(8.dp))
                        .background(MaterialTheme.colorScheme.primary.copy(alpha = 0.08f))
                        .padding(horizontal = 8.dp, vertical = 4.dp)
                )
            }
        }
    }
}
