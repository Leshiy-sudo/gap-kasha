package com.gapkassa.ui.components

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import com.gapkassa.ui.theme.FintechRadius

@Composable
fun StatusChip(
    text: String,
    background: Color,
    contentColor: Color,
    modifier: Modifier = Modifier
) {
    Row(
        modifier = modifier
            .background(background, RoundedCornerShape(FintechRadius.small))
            .padding(PaddingValues(horizontal = 10.dp, vertical = 6.dp))
    ) {
        Text(text = text, color = contentColor, style = MaterialTheme.typography.labelSmall)
    }
}
