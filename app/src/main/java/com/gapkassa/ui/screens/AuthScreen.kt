package com.gapkassa.ui.screens
import androidx.compose.foundation.layout.height

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.unit.dp
import com.gapkassa.R
import com.gapkassa.auth.GoogleAuthException
import com.gapkassa.auth.GoogleAuthManager
import com.gapkassa.auth.TestIdentities
import com.gapkassa.auth.findActivity
import com.gapkassa.ui.TestTags
import com.gapkassa.ui.components.AppCard
import com.gapkassa.ui.components.GoogleSignInButton
import com.gapkassa.ui.components.StatusChip
import com.gapkassa.ui.components.TertiaryButton
import com.gapkassa.ui.theme.FintechColors
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.AuthViewModel
import kotlinx.coroutines.launch

@Composable
fun AuthScreen(
    viewModel: AuthViewModel,
    onLoggedIn: () -> Unit
) {
    val state by viewModel.state.collectAsState()
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val authManager = remember(context) { GoogleAuthManager(context) }

    fun handleFailure(error: Throwable) {
        if (error is GoogleAuthException) {
            viewModel.onGoogleProviderError(error.code)
        } else {
            viewModel.onGoogleProviderError("google_auth_failed")
        }
    }

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
                    text = stringResource(R.string.auth_google_card_title),
                    style = MaterialTheme.typography.titleMedium,
                    color = MaterialTheme.colorScheme.onSurface
                )
                androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xs))
                Text(
                    text = stringResource(R.string.auth_google_card_body),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.sm))
                Row(horizontalArrangement = Arrangement.spacedBy(FintechSpacing.xs)) {
                    StatusChip(
                        text = stringResource(R.string.auth_google_chip_trusted),
                        background = FintechColors.SuccessSoft,
                        contentColor = FintechColors.Success
                    )
                    StatusChip(
                        text = stringResource(R.string.auth_google_chip_passwordless),
                        background = FintechColors.InfoSoft,
                        contentColor = FintechColors.Info
                    )
                }
            }
        }

        androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xxl))

        if (!state.isGoogleConfigured) {
            Text(
                text = stringResource(R.string.auth_google_config_hint),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
        }

        GoogleSignInButton(
            text = stringResource(R.string.action_continue_with_google),
            enabled = !state.isLoading,
            modifier = Modifier.testTag(TestTags.AuthGoogleButton),
            onClick = {
                val activity = context.findActivity() ?: return@GoogleSignInButton
                scope.launch {
                    try {
                        val token = authManager.requestGoogleToken(activity)
                        viewModel.loginWithGoogle(token.idToken, token.nonce, onLoggedIn)
                    } catch (error: GoogleAuthException) {
                        handleFailure(error)
                    }
                }
            }
        )

        if (state.isMockGoogleAvailable) {
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
            TestIdentities.ALL.forEachIndexed { index, identity ->
                if (index > 0) {
                    androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.xs))
                }
                val tag = if (index == 0) TestTags.AuthMockGoogleButton else "${TestTags.AuthMockGoogleButton}_$index"
                TertiaryButton(
                    text = identity.displayName,
                    enabled = !state.isLoading,
                    modifier = Modifier.testTag(tag),
                    onClick = {
                        try {
                            val token = authManager.buildMockGoogleToken(identity)
                            viewModel.loginWithGoogle(token.idToken, token.nonce, onLoggedIn)
                        } catch (error: GoogleAuthException) {
                            handleFailure(error)
                        }
                    }
                )
            }
            androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.sm))
            Text(
                text = stringResource(R.string.auth_google_mock_hint),
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
