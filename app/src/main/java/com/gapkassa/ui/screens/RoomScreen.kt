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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AttachMoney
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Group
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import com.gapkassa.data.db.PaymentEntity
import com.gapkassa.ui.components.AppCard
import com.gapkassa.ui.components.AppNavButton
import com.gapkassa.ui.components.AppOutlinedTextField
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.components.BackIconButton
import com.gapkassa.ui.components.HomeIconButton
import com.gapkassa.ui.components.PaymentStatusChip
import com.gapkassa.ui.components.StatusChip
import com.gapkassa.ui.theme.FintechColors
import com.gapkassa.ui.theme.FintechSpacing
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
    val isAdmin = remember(members, viewModel.currentUserId) { viewModel.isAdmin() }
    var showRenameDialog by remember { mutableStateOf(false) }
    var renameError by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            AppTopBar(
                title = room.roomName.ifBlank { stringResource(R.string.rooms_title) },
                navigationIcon = { BackIconButton(onClick = onBack) },
                actions = {
                    if (isAdmin) {
                        IconButton(onClick = { showRenameDialog = true }) {
                            Icon(Icons.Default.Edit, contentDescription = stringResource(R.string.action_rename_room))
                        }
                    }
                    HomeIconButton(onClick = onHome)
                }
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
                    contentColor = FintechColors.PrimaryBlue,
                    icon = Icons.Default.AttachMoney
                )
                StatusChip(
                    text = stringResource(R.string.label_payment_day, room.paymentDay),
                    background = FintechColors.SurfaceSecondary,
                    contentColor = FintechColors.TextSecondary,
                    icon = Icons.Default.CalendarToday
                )
                StatusChip(
                    text = stringResource(R.string.label_members_count, room.memberCount),
                    background = FintechColors.SurfaceSecondary,
                    contentColor = FintechColors.TextSecondary,
                    icon = Icons.Default.Group
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

    if (showRenameDialog) {
        var newName by remember { mutableStateOf(room.roomName) }
        AlertDialog(
            onDismissRequest = { showRenameDialog = false },
            title = { Text(stringResource(R.string.rename_room_title)) },
            text = {
                AppOutlinedTextField(
                    value = newName,
                    onValueChange = { newName = it },
                    label = stringResource(R.string.field_room_name_new),
                    modifier = Modifier.fillMaxWidth()
                )
            },
            confirmButton = {
                TextButton(onClick = {
                    val trimmed = newName.trim()
                    if (trimmed.isNotBlank()) {
                        viewModel.renameRoom(
                            name = trimmed,
                            onSaved = { showRenameDialog = false },
                            onError = { renameError = it.message }
                        )
                    }
                }) {
                    Text(stringResource(R.string.action_save))
                }
            },
            dismissButton = {
                TextButton(onClick = { showRenameDialog = false }) {
                    Text(stringResource(R.string.action_cancel))
                }
            }
        )
    }

    renameError?.let { message ->
        AlertDialog(
            onDismissRequest = { renameError = null },
            title = { Text(stringResource(R.string.delete_room_failed_title)) },
            text = { Text(message.ifBlank { stringResource(R.string.rename_room_error) }) },
            confirmButton = {
                TextButton(onClick = { renameError = null }) {
                    Text(stringResource(R.string.action_ok))
                }
            }
        )
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
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Text(
                    text = stringResource(R.string.label_receiver, receiverName),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Text(
                    text = stringResource(R.string.label_amount_value, payment.amount),
                    style = MaterialTheme.typography.bodyMedium,
                    fontWeight = FontWeight.Bold,
                    color = FintechColors.PrimaryBlue
                )
            }
            PaymentStatusChip(status = payment.status)
        }
    }
}
