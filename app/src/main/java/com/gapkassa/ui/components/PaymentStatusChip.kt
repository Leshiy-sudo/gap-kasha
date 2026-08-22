package com.gapkassa.ui.components

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.PriorityHigh
import androidx.compose.material.icons.filled.Schedule
import androidx.compose.runtime.Composable
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.gapkassa.R
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.ui.theme.FintechColors

/**
 * Shared status→(text, icon, colors) mapping so every screen renders
 * payment status the same way instead of duplicating the same `when`.
 */
@Composable
fun PaymentStatusChip(status: PaymentStatus, modifier: Modifier = Modifier) {
    val spec = when (status) {
        PaymentStatus.PAID -> Triple(R.string.status_paid, Icons.Default.Check, FintechColors.SuccessSoft to FintechColors.Success)
        PaymentStatus.SKIPPED -> Triple(R.string.status_skipped, Icons.Default.Close, FintechColors.WarningSoft to FintechColors.Warning)
        PaymentStatus.OVERDUE -> Triple(R.string.status_overdue, Icons.Default.PriorityHigh, FintechColors.ErrorSoft to FintechColors.Error)
        PaymentStatus.EXPECTED -> Triple(R.string.status_expected, Icons.Default.Schedule, FintechColors.InfoSoft to FintechColors.Info)
    }
    val (textRes, icon, colors) = spec
    val (background, content) = colors
    StatusChip(
        text = stringResource(textRes),
        background = background,
        contentColor = content,
        icon = icon,
        modifier = modifier
    )
}
