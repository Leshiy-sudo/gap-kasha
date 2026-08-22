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
import androidx.compose.runtime.remember
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import com.gapkassa.R
import com.gapkassa.data.db.PaymentEntity
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.ui.components.AppCard
import com.gapkassa.ui.components.AppNavButton
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.components.BackIconButton
import com.gapkassa.ui.components.HomeIconButton
import com.gapkassa.ui.components.StatusChip
import com.gapkassa.ui.theme.FintechColors
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.MemberUi
import com.gapkassa.viewmodel.RoomViewModel

@Composable
fun RoomScreen(
    roomId: String,
    viewModel: RoomViewModel,
    onOpenCalendar: () -> Unit,
    onOpenStats: () -> Unit,
    onOpenSchedule: () -> Unit,
    onPaymentClick: (String) -> Unit,
    onBack: () -> Unit,
    onHome: () -> Unit
) {
    LaunchedEffect(roomId) { viewModel.setRoom(roomId) }
    val room by viewModel.roomUiState.collectAsState()
    val members by viewModel.members.collectAsState()
    val payments by viewModel.payments.collectAsState()
    val memberNames = remember(members) { members.associate { it.userId to it.name } }

    Scaffold(
        topBar = {
            AppTopBar(
                title = room.roomName.ifBlank { stringResource(R.string.rooms_title) },
                navigationIcon = { BackIconButton(onClick = onBack) },
                actions = { HomeIconButton(onClick = onHome) }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(FintechSpacing.lg),
                horizontalArrangement = Arrangement.spacedBy(FintechSpacing.sm)
            ) {
                StatusChip(
                    text = stringResource(R.string.label_amount_value, room.amount),
                    background = FintechColors.PrimaryBlueSoft,
                    contentColor = FintechColors.PrimaryBlue
                )
                StatusChip(
                    text = stringResource(R.string.label_payment_day, room.paymentDay),
                    background = FintechColors.SurfaceSecondary,
                    contentColor = FintechColors.TextSecondary
                )
                StatusChip(
                    text = stringResource(R.string.label_members_count, room.memberCount),
                    background = FintechColors.SurfaceSecondary,
                    contentColor = FintechColors.TextSecondary
                )
            }

            Column(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = FintechSpacing.lg),
                verticalArrangement = Arrangement.spacedBy(FintechSpacing.sm)
            ) {
                AppNavButton(
                    text = stringResource(R.string.action_calendar),
                    modifier = Modifier.fillMaxWidth(),
                    onClick = onOpenCalendar
                )
                AppNavButton(
                    text = stringResource(R.string.action_stats),
                    modifier = Modifier.fillMaxWidth(),
                    onClick = onOpenStats
                )
                AppNavButton(
                    text = stringResource(R.string.action_edit_schedule),
                    modifier = Modifier.fillMaxWidth(),
                    onClick = onOpenSchedule
                )
            }

            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))

            if (payments.isEmpty()) {
                Text(
                    text = stringResource(R.string.empty_payments),
                    modifier = Modifier.padding(FintechSpacing.lg),
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = FintechSpacing.lg, vertical = FintechSpacing.sm),
                    verticalArrangement = Arrangement.spacedBy(FintechSpacing.sm)
                ) {
                    items(payments, key = { it.id }) { payment ->
                        PaymentRow(
                            payment = payment,
                            payerName = memberNames[payment.payerId] ?: payment.payerId,
                            receiverName = memberNames[payment.receiverId] ?: payment.receiverId,
                            onClick = { onPaymentClick(payment.id) }
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun PaymentRow(
    payment: PaymentEntity,
    payerName: String,
    receiverName: String,
    onClick: () -> Unit
) {
    AppCard(modifier = Modifier.fillMaxWidth(), onClick = onClick) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(FintechSpacing.lg),
            horizontalArrangement = Arrangement.SpaceBetween
        ) {
            Column {
                Text(
                    text = stringResource(R.string.label_payer, payerName),
                    style = MaterialTheme.typography.bodyMedium
                )
                Text(
                    text = stringResource(R.string.label_receiver, receiverName),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = stringResource(R.string.label_amount_value, payment.amount),
                    style = MaterialTheme.typography.bodySmall
                )
            }
            paymentStatusChip(payment.status)
        }
    }
}

@Composable
private fun paymentStatusChip(status: PaymentStatus) {
    val (textRes, background, content) = when (status) {
        PaymentStatus.PAID -> Triple(R.string.status_paid, FintechColors.SuccessSoft, FintechColors.Success)
        PaymentStatus.SKIPPED -> Triple(R.string.status_skipped, FintechColors.WarningSoft, FintechColors.Warning)
        PaymentStatus.OVERDUE -> Triple(R.string.status_overdue, FintechColors.ErrorSoft, FintechColors.Error)
        PaymentStatus.EXPECTED -> Triple(R.string.status_expected, FintechColors.InfoSoft, FintechColors.Info)
    }
    StatusChip(text = stringResource(textRes), background = background, contentColor = content)
}
