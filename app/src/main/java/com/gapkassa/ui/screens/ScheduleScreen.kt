package com.gapkassa.ui.screens
import androidx.compose.foundation.layout.height

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import com.gapkassa.R
import com.gapkassa.data.model.Role
import com.gapkassa.data.repository.ScheduleAssignment
import com.gapkassa.ui.components.AppCard
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.components.BackIconButton
import com.gapkassa.ui.components.HomeIconButton
import com.gapkassa.ui.components.PrimaryButton
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.RoomViewModel

@Composable
fun ScheduleScreen(
    roomId: String,
    viewModel: RoomViewModel,
    onBack: () -> Unit,
    onHome: () -> Unit
) {
    LaunchedEffect(roomId) { viewModel.setRoom(roomId) }
    val payments by viewModel.payments.collectAsState()
    val members by viewModel.members.collectAsState()
    val isAdmin = remember(members, viewModel.currentUserId) {
        members.any { it.userId == viewModel.currentUserId && it.role == Role.ADMIN }
    }

    val months = remember(payments) {
        payments.groupBy { it.month }.entries.sortedBy { it.key }
            .map { (month, list) -> month to (list.firstOrNull()?.receiverId ?: "") }
    }
    var editing by remember { mutableStateOf(false) }
    val assignments = remember(months) {
        mutableMapOf<java.time.LocalDate, String>().apply {
            months.forEach { (month, receiverId) -> put(month, receiverId) }
        }
    }
    var showConfirm by remember { mutableStateOf(false) }
    var errorMessage by remember { mutableStateOf<Int?>(null) }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.schedule_title),
                navigationIcon = { BackIconButton(onClick = onBack) },
                actions = { HomeIconButton(onClick = onHome) }
            )
        }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            Text(
                text = stringResource(R.string.schedule_subtitle),
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(FintechSpacing.lg)
            )
            if (!isAdmin) {
                Text(
                    text = stringResource(R.string.schedule_admin_only_hint),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    modifier = Modifier.padding(horizontal = FintechSpacing.lg)
                )
            } else {
                Row(modifier = Modifier.padding(horizontal = FintechSpacing.lg)) {
                    TextButton(onClick = { editing = !editing }) {
                        Text(
                            text = if (editing) stringResource(R.string.action_cancel) else stringResource(R.string.action_edit)
                        )
                    }
                }
                if (!editing) {
                    Text(
                        text = stringResource(R.string.schedule_hint),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.padding(horizontal = FintechSpacing.lg)
                    )
                }
            }

            LazyColumn(
                modifier = Modifier.fillMaxSize(),
                contentPadding = PaddingValues(FintechSpacing.lg),
                verticalArrangement = Arrangement.spacedBy(FintechSpacing.sm)
            ) {
                items(months, key = { it.first.toString() }) { (month, receiverId) ->
                    val memberName = members.firstOrNull { it.userId == assignments[month] }?.name ?: receiverId
                    AppCard(modifier = Modifier.fillMaxWidth()) {
                        Row(
                            modifier = Modifier.fillMaxWidth().padding(FintechSpacing.lg),
                            horizontalArrangement = Arrangement.SpaceBetween
                        ) {
                            Text(text = month.toString(), style = MaterialTheme.typography.bodyMedium)
                            if (editing) {
                                var menuOpen by remember { mutableStateOf(false) }
                                Box {
                                    TextButton(onClick = { menuOpen = true }) {
                                        Text(memberName)
                                    }
                                    DropdownMenu(expanded = menuOpen, onDismissRequest = { menuOpen = false }) {
                                        members.forEach { member ->
                                            DropdownMenuItem(
                                                text = { Text(member.name) },
                                                onClick = {
                                                    assignments[month] = member.userId
                                                    menuOpen = false
                                                }
                                            )
                                        }
                                    }
                                }
                            } else {
                                Text(text = memberName, style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                }
            }

            if (editing) {
                PrimaryButton(
                    text = stringResource(R.string.action_save),
                    modifier = Modifier.padding(FintechSpacing.lg),
                    onClick = { showConfirm = true }
                )
            }
        }
    }

    if (showConfirm) {
        AlertDialog(
            onDismissRequest = { showConfirm = false },
            title = { Text(stringResource(R.string.schedule_confirm_title)) },
            text = { Text(stringResource(R.string.schedule_confirm_message)) },
            confirmButton = {
                TextButton(onClick = {
                    showConfirm = false
                    val memberIds = members.map { it.userId }.toSet()
                    if (assignments.values.any { it !in memberIds }) {
                        errorMessage = R.string.schedule_error_invalid_receiver
                        return@TextButton
                    }
                    viewModel.saveSchedule(
                        assignments = assignments.map { (month, receiverId) ->
                            ScheduleAssignment(month, receiverId)
                        },
                        onSaved = { editing = false },
                        onError = { errorMessage = R.string.schedule_error_save }
                    )
                }) {
                    Text(stringResource(R.string.action_save))
                }
            },
            dismissButton = {
                TextButton(onClick = { showConfirm = false }) {
                    Text(stringResource(R.string.action_cancel))
                }
            }
        )
    }

    errorMessage?.let { messageRes ->
        AlertDialog(
            onDismissRequest = { errorMessage = null },
            title = { Text(stringResource(R.string.delete_room_failed_title)) },
            text = { Text(stringResource(messageRes)) },
            confirmButton = {
                TextButton(onClick = { errorMessage = null }) {
                    Text(stringResource(R.string.action_ok))
                }
            }
        )
    }
}
