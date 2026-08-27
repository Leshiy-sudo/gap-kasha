package com.gapkassa.ui.screens
import androidx.compose.foundation.layout.height

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Checkbox
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
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.input.KeyboardType
import com.gapkassa.R
import com.gapkassa.ui.TestTags
import com.gapkassa.ui.components.AppOutlinedTextField
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.components.BackIconButton
import com.gapkassa.ui.components.HomeIconButton
import com.gapkassa.ui.components.PrimaryButton
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.utils.Validators
import com.gapkassa.viewmodel.RoomsViewModel

@Composable
fun CreateRoomScreen(
    viewModel: RoomsViewModel,
    onCreated: () -> Unit,
    onBack: () -> Unit,
    onHome: () -> Unit
) {
    var name by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var amountText by remember { mutableStateOf("") }
    var paymentDayText by remember { mutableStateOf("") }
    var cycleLengthText by remember { mutableStateOf("") }
    var autoRotate by remember { mutableStateOf(true) }
    var participantInput by remember { mutableStateOf("") }
    val participants = remember { mutableStateListOf<String>() }
    var showValidation by remember { mutableStateOf(false) }
    val isCreating by viewModel.isCreating.collectAsState()

    val nameError = showValidation && !Validators.isRoomNameValid(name)
    val descriptionError = showValidation && description.length > 200
    val amount = amountText.toLongOrNull()
    val amountError = showValidation && (amount == null || amount <= 0)
    val paymentDay = paymentDayText.toIntOrNull()
    val paymentDayError = showValidation && (paymentDay == null || paymentDay !in 1..31)
    val cycleLength = cycleLengthText.toIntOrNull()
    val cycleLengthError = showValidation && (cycleLength == null || cycleLength !in 1..60)
    val participantsError = showValidation && participants.size !in 5..20
    val participantsPhoneError = showValidation && participants.any { !Validators.isPhoneValid(it) }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.create_room_title),
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
            Text(text = stringResource(R.string.section_main), style = MaterialTheme.typography.titleSmall)
            AppOutlinedTextField(
                value = name,
                onValueChange = { name = it },
                label = stringResource(R.string.field_room_name),
                isError = nameError,
                supportingText = if (nameError) stringResource(R.string.error_room_name) else null,
                modifier = Modifier.fillMaxWidth().testTag(TestTags.CreateRoomName)
            )
            AppOutlinedTextField(
                value = description,
                onValueChange = { description = it },
                label = stringResource(R.string.field_room_description),
                isError = descriptionError,
                supportingText = if (descriptionError) stringResource(R.string.error_description) else null,
                maxLength = 200,
                modifier = Modifier.fillMaxWidth().testTag(TestTags.CreateRoomDescription)
            )

            Text(text = stringResource(R.string.section_finance), style = MaterialTheme.typography.titleSmall)
            AppOutlinedTextField(
                value = amountText,
                onValueChange = { amountText = it.filter { ch -> ch.isDigit() } },
                label = stringResource(R.string.field_amount),
                isError = amountError,
                supportingText = if (amountError) stringResource(R.string.error_amount) else null,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth()
            )
            AppOutlinedTextField(
                value = paymentDayText,
                onValueChange = { paymentDayText = it.filter { ch -> ch.isDigit() }.take(2) },
                label = stringResource(R.string.field_payment_day),
                isError = paymentDayError,
                supportingText = if (paymentDayError) stringResource(R.string.error_payment_day) else null,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth()
            )
            AppOutlinedTextField(
                value = cycleLengthText,
                onValueChange = { cycleLengthText = it.filter { ch -> ch.isDigit() }.take(2) },
                label = stringResource(R.string.field_cycle_length),
                isError = cycleLengthError,
                supportingText = if (cycleLengthError) stringResource(R.string.error_cycle_length) else null,
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                modifier = Modifier.fillMaxWidth()
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Checkbox(checked = autoRotate, onCheckedChange = { autoRotate = it })
                Text(text = stringResource(R.string.field_auto_rotate))
            }

            Text(text = stringResource(R.string.section_participants), style = MaterialTheme.typography.titleSmall)
            Text(
                text = stringResource(R.string.helper_participants),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(FintechSpacing.sm)
            ) {
                AppOutlinedTextField(
                    value = participantInput,
                    onValueChange = { participantInput = it },
                    label = stringResource(R.string.field_participants),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                    modifier = Modifier.weight(1f).testTag(TestTags.CreateRoomParticipants)
                )
                IconButton(
                    onClick = {
                        val phone = participantInput.trim()
                        if (phone.isNotBlank() && phone !in participants) {
                            participants.add(phone)
                        }
                        participantInput = ""
                    },
                    modifier = Modifier.testTag(TestTags.CreateRoomAddParticipant)
                ) {
                    Icon(Icons.Default.Add, contentDescription = stringResource(R.string.action_add_participant))
                }
            }
            if (participantsError) {
                Text(
                    text = stringResource(R.string.error_participants_count),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
            if (participantsPhoneError) {
                Text(
                    text = stringResource(R.string.error_participants_phone),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.error
                )
            }
            participants.forEach { phone ->
                Row(
                    modifier = Modifier.fillMaxWidth(),
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Text(text = phone, style = MaterialTheme.typography.bodyMedium)
                    IconButton(onClick = { participants.remove(phone) }) {
                        Icon(Icons.Default.Close, contentDescription = stringResource(R.string.action_cancel))
                    }
                }
            }

            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
            PrimaryButton(
                text = stringResource(R.string.action_create),
                enabled = !isCreating,
                modifier = Modifier.testTag(TestTags.CreateRoomSubmit),
                onClick = {
                    showValidation = true
                    if (!nameError && !descriptionError && !amountError && !paymentDayError &&
                        !cycleLengthError && !participantsError && !participantsPhoneError &&
                        amount != null && paymentDay != null && cycleLength != null
                    ) {
                        viewModel.createRoom(
                            name = name,
                            description = description.ifBlank { null },
                            amount = amount,
                            paymentDay = paymentDay,
                            cycleLength = cycleLength,
                            autoRotate = autoRotate,
                            participantPhones = participants.toList(),
                            onCreated = { onCreated() }
                        )
                    }
                }
            )
        }
    }
}
