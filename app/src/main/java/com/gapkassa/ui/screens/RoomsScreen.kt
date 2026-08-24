package com.gapkassa.ui.screens

import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AttachMoney
import androidx.compose.material.icons.filled.CalendarToday
import androidx.compose.material.icons.filled.Group
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Person
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.gapkassa.R
import com.gapkassa.data.repository.RoomDeleteError
import com.gapkassa.ui.TestTags
import com.gapkassa.ui.components.AdSlot
import com.gapkassa.ui.components.AppCard
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.theme.FintechColors
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.RoomItem
import com.gapkassa.viewmodel.RoomsViewModel

@Composable
fun RoomsScreen(
    viewModel: RoomsViewModel,
    onCreateRoom: () -> Unit,
    onRoomClick: (String) -> Unit,
    onProfile: () -> Unit
) {
    val rooms by viewModel.rooms.collectAsState()
    var pendingDelete by remember { mutableStateOf<RoomItem?>(null) }
    var deleteError by remember { mutableStateOf<RoomDeleteError?>(null) }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.rooms_title),
                titleModifier = Modifier.testTag(TestTags.RoomsTitle),
                actions = {
                    IconButton(
                        onClick = onProfile,
                        modifier = Modifier.testTag(TestTags.RoomsProfileButton)
                    ) {
                        Icon(Icons.Default.Person, contentDescription = stringResource(R.string.profile_title))
                    }
                }
            )
        },
        floatingActionButton = {
            FloatingActionButton(
                onClick = onCreateRoom,
                modifier = Modifier.testTag(TestTags.RoomsCreateFab)
            ) {
                Icon(Icons.Default.Add, contentDescription = stringResource(R.string.action_create))
            }
        }
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            AdSlot(modifier = Modifier.fillMaxWidth())
            if (rooms.isEmpty()) {
                EmptyRoomsState()
            } else {
                LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(FintechSpacing.lg),
                    verticalArrangement = Arrangement.spacedBy(FintechSpacing.md)
                ) {
                    items(rooms, key = { it.id }) { room ->
                        RoomRow(
                            room = room,
                            onClick = { onRoomClick(room.id) },
                            onDeleteRequested = { pendingDelete = room }
                        )
                    }
                }
            }
        }
    }

    pendingDelete?.let { room ->
        AlertDialog(
            onDismissRequest = { pendingDelete = null },
            title = { Text(stringResource(R.string.delete_room_title)) },
            text = { Text(stringResource(R.string.delete_room_message)) },
            confirmButton = {
                androidx.compose.material3.TextButton(
                    onClick = {
                        viewModel.deleteRoom(
                            roomId = room.id,
                            onDeleted = { pendingDelete = null },
                            onError = { error ->
                                pendingDelete = null
                                deleteError = error
                            }
                        )
                    },
                    modifier = Modifier.testTag(TestTags.RoomDeleteConfirm)
                ) {
                    Text(stringResource(R.string.action_delete_room))
                }
            },
            dismissButton = {
                androidx.compose.material3.TextButton(onClick = { pendingDelete = null }) {
                    Text(stringResource(R.string.action_cancel))
                }
            }
        )
    }

    deleteError?.let { error ->
        val messageRes = when (error) {
            RoomDeleteError.PAID_EXISTS -> R.string.error_room_delete_paid
            RoomDeleteError.FORBIDDEN -> R.string.error_room_delete_forbidden
            RoomDeleteError.NOT_FOUND -> R.string.error_room_delete_not_found
            RoomDeleteError.UNKNOWN -> R.string.error_room_delete_unknown
        }
        AlertDialog(
            onDismissRequest = { deleteError = null },
            title = { Text(stringResource(R.string.delete_room_failed_title)) },
            text = { Text(stringResource(messageRes)) },
            confirmButton = {
                androidx.compose.material3.TextButton(onClick = { deleteError = null }) {
                    Text(stringResource(R.string.action_ok))
                }
            }
        )
    }
}

@Composable
private fun EmptyRoomsState() {
    Column(
        modifier = Modifier
            .fillMaxSize()
            .padding(FintechSpacing.xxxl),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center
    ) {
        Icon(
            imageVector = Icons.Default.Group,
            contentDescription = null,
            modifier = Modifier.size(48.dp),
            tint = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Spacer(Modifier.height(FintechSpacing.md))
        Text(
            text = stringResource(R.string.empty_rooms_title),
            style = MaterialTheme.typography.titleMedium,
            textAlign = TextAlign.Center
        )
        Spacer(Modifier.height(FintechSpacing.xs))
        Text(
            text = stringResource(R.string.empty_rooms_body),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant,
            textAlign = TextAlign.Center
        )
    }
}

@Composable
private fun RoomRow(
    room: RoomItem,
    onClick: () -> Unit,
    onDeleteRequested: () -> Unit
) {
    var menuExpanded by remember { mutableStateOf(false) }

    AppCard(
        modifier = Modifier
            .fillMaxWidth()
            .testTag(TestTags.roomCard(room.name)),
        onClick = onClick
    ) {
        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(FintechSpacing.lg),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically
        ) {
            Column(modifier = Modifier.weight(1f)) {
                Text(
                    text = room.name,
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                Spacer(Modifier.height(FintechSpacing.xs))
                MetaRow(icon = Icons.Default.AttachMoney, tint = FintechColors.PrimaryBlue) {
                    Text(
                        text = stringResource(R.string.label_monthly_amount, room.amount),
                        style = MaterialTheme.typography.bodyMedium,
                        fontWeight = FontWeight.Bold,
                        color = FintechColors.PrimaryBlue
                    )
                }
                Spacer(Modifier.height(FintechSpacing.xs))
                Row(horizontalArrangement = Arrangement.spacedBy(FintechSpacing.md)) {
                    MetaRow(icon = Icons.Default.CalendarToday) {
                        Text(
                            text = room.paymentDay.toString(),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    MetaRow(icon = Icons.Default.Group) {
                        Text(
                            text = room.memberCount.toString(),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    Text(
                        text = stringResource(R.string.label_cycle_months, room.cycleMonths),
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            Box {
                IconButton(
                    onClick = { menuExpanded = true },
                    modifier = Modifier.testTag(TestTags.roomMenu(room.name))
                ) {
                    Icon(Icons.Default.MoreVert, contentDescription = null)
                }
                DropdownMenu(expanded = menuExpanded, onDismissRequest = { menuExpanded = false }) {
                    DropdownMenuItem(
                        text = { Text(stringResource(R.string.action_delete_room)) },
                        modifier = Modifier.testTag(TestTags.RoomDeleteAction),
                        onClick = {
                            menuExpanded = false
                            onDeleteRequested()
                        }
                    )
                }
            }
        }
    }
}

@Composable
private fun MetaRow(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    tint: androidx.compose.ui.graphics.Color = MaterialTheme.colorScheme.onSurfaceVariant,
    content: @Composable () -> Unit
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(imageVector = icon, contentDescription = null, tint = tint, modifier = Modifier.size(14.dp))
        Spacer(Modifier.width(4.dp))
        content()
    }
}
