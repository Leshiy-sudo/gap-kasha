package com.gapkassa.ui.screens
import androidx.compose.foundation.layout.height

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.AlertDialog
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
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import com.gapkassa.R
import com.gapkassa.data.model.UserProfile
import com.gapkassa.ui.TestTags
import com.gapkassa.ui.components.AppOutlinedTextField
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.components.BackIconButton
import com.gapkassa.ui.components.DestructiveButton
import com.gapkassa.ui.components.HomeIconButton
import com.gapkassa.ui.components.PrimaryButton
import com.gapkassa.ui.components.SecondaryButton
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.ProfileViewModel

@Composable
fun ProfileScreen(
    viewModel: ProfileViewModel,
    onLogout: () -> Unit,
    onBack: () -> Unit,
    onHome: () -> Unit
) {
    val profile by viewModel.profile.collectAsState()
    var name by remember(profile) { mutableStateOf(profile.name) }
    var lastName by remember(profile) { mutableStateOf(profile.lastName) }
    var patronymic by remember(profile) { mutableStateOf(profile.patronymic) }
    var showDeleteConfirm by remember { mutableStateOf(false) }
    var deleteError by remember { mutableStateOf<String?>(null) }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.profile_title),
                navigationIcon = { BackIconButton(onClick = onBack) },
                actions = { HomeIconButton(onClick = onHome) }
            )
        }
    ) { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(FintechSpacing.lg),
            verticalArrangement = Arrangement.spacedBy(FintechSpacing.fieldSpacing)
        ) {
            Text(text = stringResource(R.string.section_personal), style = MaterialTheme.typography.titleSmall)
            AppOutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = stringResource(R.string.field_name),
                modifier = Modifier.fillMaxWidth()
            )
            AppOutlinedTextField(
                value = lastName,
                onValueChange = { lastName = it },
                label = stringResource(R.string.field_last_name),
                modifier = Modifier.fillMaxWidth()
            )
            AppOutlinedTextField(
                value = patronymic,
                onValueChange = { patronymic = it },
                label = stringResource(R.string.field_patronymic),
                modifier = Modifier.fillMaxWidth()
            )

            Text(text = stringResource(R.string.section_contacts), style = MaterialTheme.typography.titleSmall)
            AppOutlinedTextField(
                value = profile.phone,
                onValueChange = {},
                label = stringResource(R.string.field_phone),
                readOnly = true,
                modifier = Modifier.fillMaxWidth()
            )

            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
            PrimaryButton(
                text = stringResource(R.string.action_save),
                onClick = {
                    viewModel.saveProfile(
                        profile.copy(name = name, lastName = lastName, patronymic = patronymic),
                        onDone = {}
                    )
                }
            )

            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xxl))
            SecondaryButton(
                text = stringResource(R.string.action_logout),
                fullWidth = true,
                modifier = Modifier.testTag(TestTags.ProfileLogout),
                onClick = { viewModel.logout(onLogout) }
            )
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.sm))
            DestructiveButton(
                text = stringResource(R.string.action_delete_account),
                fullWidth = true,
                modifier = Modifier.testTag(TestTags.ProfileDeleteAccount),
                onClick = { showDeleteConfirm = true }
            )
        }
    }

    if (showDeleteConfirm) {
        AlertDialog(
            onDismissRequest = { showDeleteConfirm = false },
            title = { Text(stringResource(R.string.delete_account_title)) },
            text = { Text(stringResource(R.string.delete_account_message)) },
            confirmButton = {
                TextButton(
                    onClick = {
                        showDeleteConfirm = false
                        viewModel.deleteAccount(
                            onDone = onLogout,
                            onError = { message -> deleteError = message }
                        )
                    },
                    modifier = Modifier.testTag(TestTags.ProfileDeleteConfirm)
                ) {
                    Text(stringResource(R.string.action_delete_account))
                }
            },
            dismissButton = {
                TextButton(onClick = { showDeleteConfirm = false }) {
                    Text(stringResource(R.string.action_cancel))
                }
            }
        )
    }

    deleteError?.let { message ->
        AlertDialog(
            onDismissRequest = { deleteError = null },
            title = { Text(stringResource(R.string.delete_room_failed_title)) },
            text = { Text(message) },
            confirmButton = {
                TextButton(onClick = { deleteError = null }) {
                    Text(stringResource(R.string.action_ok))
                }
            }
        )
    }
}
