package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.db.PaymentEntity
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.data.repository.ExportRepository
import com.gapkassa.data.repository.RoomRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import java.io.File

/**
 * Builds aggregate stats and exposes CSV export for a room.
 */
class StatsViewModel(
    private val roomRepository: RoomRepository,
    private val exportRepository: ExportRepository
) : ViewModel() {

    private val roomIdFlow = MutableStateFlow<String?>(null)

    val payments: StateFlow<List<PaymentEntity>> = roomIdFlow
        .flatMapLatest { id ->
            if (id == null) kotlinx.coroutines.flow.flowOf(emptyList())
            else roomRepository.observeRoomPayments(id)
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val stats: StateFlow<StatsUiState> = roomIdFlow
        .flatMapLatest { id ->
            if (id == null) kotlinx.coroutines.flow.flowOf(emptyList())
            else roomRepository.observeRoomPayments(id)
        }
        .map { payments ->
            val paid = payments.filter { it.status == PaymentStatus.PAID }
            val skipped = payments.count { it.status == PaymentStatus.SKIPPED }
            StatsUiState(
                totalPaid = paid.sumOf { it.amount },
                totalReceived = paid.sumOf { it.amount },
                skippedCount = skipped,
                paymentCount = payments.size,
                discipline = if (payments.isNotEmpty()) {
                    100 - (skipped * 100 / payments.size)
                } else 100
            )
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), StatsUiState())

    fun setRoom(roomId: String) {
        roomIdFlow.value = roomId
    }

    fun exportCsv(roomName: String, payments: List<PaymentEntity>): File {
        return exportRepository.exportPaymentsToCsv(roomName, payments)
    }
}

/** Summary metrics for the stats screen. */
data class StatsUiState(
    val totalPaid: Long = 0,
    val totalReceived: Long = 0,
    val skippedCount: Int = 0,
    val paymentCount: Int = 0,
    val discipline: Int = 100
)
