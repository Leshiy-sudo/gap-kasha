package com.gapkassa.ui.screens
import androidx.compose.foundation.layout.height

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.gapkassa.R
import com.gapkassa.ui.components.AppCard
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.components.BackIconButton
import com.gapkassa.ui.components.HomeIconButton
import com.gapkassa.ui.components.PaymentStatusChip
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.CalendarViewModel

@Composable
fun CalendarScreen(
    roomId: String,
    viewModel: CalendarViewModel,
    onBack: () -> Unit,
    onHome: () -> Unit
) {
    LaunchedEffect(roomId) { viewModel.setRoom(roomId) }
    val calendarItems by viewModel.calendarItems.collectAsState()
    val usersMap by viewModel.usersMap.collectAsState()
    val months = calendarItems.entries.sortedBy { it.key }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.calendar_title),
                navigationIcon = { BackIconButton(onClick = onBack) },
                actions = { HomeIconButton(onClick = onHome) }
            )
        }
    ) { padding ->
        if (months.isEmpty()) {
            Text(
                text = stringResource(R.string.empty_payments),
                modifier = Modifier.padding(padding).padding(FintechSpacing.lg),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            return@Scaffold
        }
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(padding),
            contentPadding = PaddingValues(FintechSpacing.lg),
            verticalArrangement = Arrangement.spacedBy(FintechSpacing.md)
        ) {
            items(months, key = { it.key.toString() }) { entry ->
                Text(
                    text = entry.key.toString(),
                    style = MaterialTheme.typography.titleSmall,
                    modifier = Modifier.padding(vertical = FintechSpacing.xs)
                )
                Column(verticalArrangement = Arrangement.spacedBy(FintechSpacing.xs)) {
                    entry.value.forEach { payment ->
                        val payer = usersMap[payment.payerId]?.name ?: payment.payerId
                        val receiver = usersMap[payment.receiverId]?.name ?: payment.receiverId
                        AppCard(modifier = Modifier.fillMaxWidth()) {
                            Row(
                                modifier = Modifier.fillMaxWidth().padding(FintechSpacing.md),
                                horizontalArrangement = Arrangement.SpaceBetween,
                                verticalAlignment = Alignment.CenterVertically
                            ) {
                                Text(
                                    text = stringResource(R.string.label_payer, payer) + " → " +
                                        stringResource(R.string.label_receiver, receiver),
                                    style = MaterialTheme.typography.bodySmall,
                                    modifier = Modifier.weight(1f).padding(end = FintechSpacing.sm)
                                )
                                PaymentStatusChip(status = payment.status)
                            }
                        }
                    }
                }
            }
        }
    }
}
