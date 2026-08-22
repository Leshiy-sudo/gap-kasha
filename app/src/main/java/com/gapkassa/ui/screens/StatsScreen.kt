package com.gapkassa.ui.screens
import androidx.compose.foundation.layout.height

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import com.gapkassa.R
import com.gapkassa.ui.components.AppCard
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.components.BackIconButton
import com.gapkassa.ui.components.HomeIconButton
import com.gapkassa.ui.components.SecondaryButton
import com.gapkassa.ui.theme.FintechColors
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.StatsViewModel

@Composable
fun StatsScreen(
    roomId: String,
    viewModel: StatsViewModel,
    onBack: () -> Unit,
    onHome: () -> Unit
) {
    LaunchedEffect(roomId) { viewModel.setRoom(roomId) }
    val stats by viewModel.stats.collectAsState()
    val payments by viewModel.payments.collectAsState()
    var exportMessage by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.stats_title),
                navigationIcon = { BackIconButton(onClick = onBack) },
                actions = { HomeIconButton(onClick = onHome) }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(FintechSpacing.lg),
            verticalArrangement = Arrangement.spacedBy(FintechSpacing.md)
        ) {
            Row(horizontalArrangement = Arrangement.spacedBy(FintechSpacing.md)) {
                MetricCard(
                    label = stringResource(R.string.stats_total_paid_label),
                    value = stats.totalPaid.toString(),
                    modifier = Modifier.weight(1f)
                )
                MetricCard(
                    label = stringResource(R.string.stats_total_received_label),
                    value = stats.totalReceived.toString(),
                    modifier = Modifier.weight(1f)
                )
            }
            Row(horizontalArrangement = Arrangement.spacedBy(FintechSpacing.md)) {
                MetricCard(
                    label = stringResource(R.string.stats_skipped_label),
                    value = stats.skippedCount.toString(),
                    modifier = Modifier.weight(1f)
                )
                MetricCard(
                    label = stringResource(R.string.stats_discipline_label),
                    value = "${stats.discipline}%",
                    modifier = Modifier.weight(1f)
                )
            }

            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
            SecondaryButton(
                text = stringResource(R.string.action_export_csv),
                onClick = {
                    val file = viewModel.exportCsv(roomId, payments)
                    exportMessage = file.absolutePath
                }
            )
            exportMessage?.let {
                Text(
                    text = it,
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

@Composable
private fun MetricCard(label: String, value: String, modifier: Modifier = Modifier) {
    AppCard(modifier = modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(FintechSpacing.lg)) {
            Text(text = label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xs))
            Text(
                text = value,
                style = MaterialTheme.typography.headlineSmall,
                fontWeight = FontWeight.Bold,
                color = FintechColors.PrimaryBlue
            )
        }
    }
}
