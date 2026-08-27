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
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
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
import androidx.compose.ui.text.input.KeyboardType
import com.gapkassa.R
import com.gapkassa.auth.TestIdentities
import com.gapkassa.ui.TestTags
import com.gapkassa.ui.components.AppCard
import com.gapkassa.ui.components.AppOutlinedTextField
import com.gapkassa.ui.components.PrimaryButton
import com.gapkassa.ui.components.StatusChip
import com.gapkassa.ui.components.TertiaryButton
import com.gapkassa.ui.theme.FintechColors
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.AuthViewModel

@Composable
fun AuthScreen(
    viewModel: AuthViewModel,
    onLoggedIn: () -> Unit
) {
    val state by viewModel.state.collectAsState()
    var phoneInput by remember { mutableStateOf("+998") }
    var codeInput by remember { mutableStateOf("") }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = FintechSpacing.screenHorizontal, vertical = FintechSpacing.xxxl),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        com.gapkassa.ui.components.BrandMark()
        androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xxl))

        Text(
            text = stringResource(R.string.auth_title),
            style = MaterialTheme.typography.headlineSmall,
            modifier = Modifier.testTag(TestTags.AuthTitle)
        )
        androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.titleSubtitleSpacing))
        Text(
            text = stringResource(R.string.auth_subtitle),
            style = MaterialTheme.typography.bodyMedium,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )

        androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.largeSectionSpacing))

        AppCard(modifier = Modifier.fillMaxWidth()) {
            Column(modifier = Modifier.padding(FintechSpacing.lg)) {
                Text(
                    text = stringResource(R.string.auth_telegram_card_title),
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xs))
                Text(
                    text = stringResource(R.string.auth_telegram_card_body),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.sm))
                Row(horizontalArrangement = Arrangement.spacedBy(FintechSpacing.xs)) {
                    StatusChip(
                        text = stringResource(R.string.auth_telegram_chip_trusted),
                        background = FintechColors.SuccessSoft,
                        contentColor = FintechColors.Success
                    )
                    StatusChip(
                        text = stringResource(R.string.auth_telegram_chip_no_password),
                        background = FintechColors.InfoSoft,
                        contentColor = FintechColors.Info
                    )
                }
            }
        }

        androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xxl))

        AppOutlinedTextField(
            value = phoneInput,
            onValueChange = { phoneInput = it },
            label = stringResource(R.string.field_phone),
            readOnly = state.codeSent,
            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
            modifier = Modifier.fillMaxWidth().testTag(TestTags.AuthPhoneField)
        )

        if (state.codeSent) {
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.sm))
            Text(
                text = stringResource(R.string.message_verification_sent),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.sm))
            AppOutlinedTextField(
                value = codeInput,
                onValueChange = { codeInput = it },
                label = stringResource(R.string.field_verification_code),
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.NumberPassword),
                modifier = Modifier.fillMaxWidth().testTag(TestTags.AuthCodeField)
            )
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
            PrimaryButton(
                text = stringResource(R.string.action_verify),
                enabled = !state.isLoading,
                modifier = Modifier.testTag(TestTags.AuthVerifyButton),
                onClick = { viewModel.verifyCode(codeInput, onLoggedIn) }
            )
        } else {
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
            PrimaryButton(
                text = stringResource(R.string.action_send_code),
                enabled = !state.isLoading,
                modifier = Modifier.testTag(TestTags.AuthSendCodeButton),
                onClick = { viewModel.startPhoneAuth(phoneInput) }
            )
        }

        if (state.isMockAvailable) {
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
            TestIdentities.ALL.forEachIndexed { index, identity ->
                if (index > 0) {
                    androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xs))
                }
                val tag = if (index == 0) TestTags.AuthMockButton else "${TestTags.AuthMockButton}_$index"
                TertiaryButton(
                    text = identity.displayName,
                    enabled = !state.isLoading,
                    modifier = Modifier.testTag(tag),
                    onClick = { viewModel.loginAsTestIdentity(identity.phone, onLoggedIn) }
                )
            }
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.sm))
            Text(
                text = stringResource(R.string.auth_mock_hint),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        if (state.isLoading) {
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.lg))
            CircularProgressIndicator()
        }

        val errorText = state.errorResId?.let { stringResource(it) } ?: state.errorMessage
        if (errorText != null) {
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
            Text(
                text = errorText,
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.error
            )
        }
    }
}
