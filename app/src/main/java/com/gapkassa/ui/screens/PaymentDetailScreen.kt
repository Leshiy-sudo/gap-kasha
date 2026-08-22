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
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.stringResource
import androidx.compose.ui.text.font.FontWeight
import com.gapkassa.R
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.ui.components.AppTopBar
import com.gapkassa.ui.components.BackIconButton
import com.gapkassa.ui.components.DestructiveButton
import com.gapkassa.ui.components.HomeIconButton
import com.gapkassa.ui.components.PaymentStatusChip
import com.gapkassa.ui.components.PrimaryButton
import com.gapkassa.ui.theme.FintechColors
import com.gapkassa.ui.theme.FintechSpacing
import com.gapkassa.viewmodel.RoomViewModel

@Composable
fun PaymentDetailScreen(
    paymentId: String,
    viewModel: RoomViewModel,
    onBack: () -> Unit,
    onHome: () -> Unit
) {
    val payments by viewModel.payments.collectAsState()
    val members by viewModel.members.collectAsState()
    val payment = payments.firstOrNull { it.id == paymentId }

    Scaffold(
        topBar = {
            AppTopBar(
                title = stringResource(R.string.payment_detail_title),
                navigationIcon = { BackIconButton(onClick = onBack) },
                actions = { HomeIconButton(onClick = onHome) }
            )
        }
    ) { padding ->
        if (payment == null) {
            Text(
                text = stringResource(R.string.payment_not_found),
                modifier = Modifier.fillMaxSize().padding(padding).padding(FintechSpacing.lg)
            )
            return@Scaffold
        }

        val payerName = members.firstOrNull { it.userId == payment.payerId }?.name ?: payment.payerId
        val receiverName = members.firstOrNull { it.userId == payment.receiverId }?.name ?: payment.receiverId
        val canManage = viewModel.canManagePayment(payment)

        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .padding(FintechSpacing.lg),
            verticalArrangement = Arrangement.spacedBy(FintechSpacing.md)
        ) {
            Text(text = stringResource(R.string.label_payer, payerName), style = MaterialTheme.typography.bodyLarge)
            Text(text = stringResource(R.string.label_receiver, receiverName), style = MaterialTheme.typography.bodyLarge)
            Text(
                text = stringResource(R.string.label_amount_value, payment.amount),
                style = MaterialTheme.typography.titleLarge,
                fontWeight = FontWeight.Bold,
                color = FintechColors.PrimaryBlue
            )
            Text(text = stringResource(R.string.label_date, payment.month.toString()), style = MaterialTheme.typography.bodyLarge)

            PaymentStatusChip(status = payment.status)

            if (canManage && payment.status != PaymentStatus.PAID) {
                androidx.compose.foundation.layout.Spacer(Modifier.height(FintechSpacing.md))
                Row(horizontalArrangement = Arrangement.spacedBy(FintechSpacing.sm)) {
                    PrimaryButton(
                        text = stringResource(R.string.action_paid),
                        fullWidth = false,
                        onClick = { viewModel.markPaid(payment.id) }
                    )
                    DestructiveButton(
                        text = stringResource(R.string.action_skipped),
                        onClick = { viewModel.markSkipped(payment.id) }
                    )
                }
            }
        }
    }
}
