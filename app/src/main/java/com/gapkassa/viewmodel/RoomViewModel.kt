package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.db.MembershipEntity
import com.gapkassa.data.db.PaymentEntity
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.data.repository.ActionLogRepository
import com.gapkassa.data.repository.RoomRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.combine
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.flowOf
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch

/**
 * Manages a single room view (members, payments, status updates).
 */
class RoomViewModel(
    private val roomRepository: RoomRepository,
    private val actionLogRepository: ActionLogRepository
) : ViewModel() {

    private val currentRoomId = MutableStateFlow<String?>(null)

    val payments: StateFlow<List<PaymentEntity>> = currentRoomId
        .flatMapLatestList { id -> roomRepository.observeRoomPayments(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val members: StateFlow<List<MembershipEntity>> = currentRoomId
        .flatMapLatestList { id -> roomRepository.observeRoomMembers(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val roomUiState: StateFlow<RoomUiState> = combine(
        currentRoomId,
        roomRepository.observeRooms(),
        members
    ) { roomId, rooms, members ->
        val room = rooms.firstOrNull { it.id == roomId }
        RoomUiState(
            roomName = room?.name.orEmpty(),
            amount = room?.monthlyAmount ?: 0,
            paymentDay = room?.paymentDay ?: 0,
            cycleMonths = room?.cycleLengthMonths ?: 0,
            autoRotate = room?.autoRotate ?: false,
            memberCount = members.size
        )
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), RoomUiState())

    fun setRoom(roomId: String) {
        currentRoomId.value = roomId
    }

    fun markPaid(paymentId: String, userId: String) {
        viewModelScope.launch {
            roomRepository.updatePaymentStatus(paymentId, PaymentStatus.PAID)
            actionLogRepository.log(userId, currentRoomId.value, "mark_paid")
        }
    }

    fun markSkipped(paymentId: String, userId: String) {
        viewModelScope.launch {
            roomRepository.updatePaymentStatus(paymentId, PaymentStatus.SKIPPED)
            actionLogRepository.log(userId, currentRoomId.value, "mark_skipped")
        }
    }
}

// Helper to switch a nullable room id into an empty list flow by default.
private fun <T> MutableStateFlow<String?>.flatMapLatestList(block: (String) -> kotlinx.coroutines.flow.Flow<List<T>>) =
    this.flatMapLatest { id ->
        if (id == null) flowOf(emptyList()) else block(id)
    }


/** UI summary for the room header. */
data class RoomUiState(
    val roomName: String = "",
    val amount: Long = 0,
    val paymentDay: Int = 0,
    val cycleMonths: Int = 0,
    val autoRotate: Boolean = false,
    val memberCount: Int = 0
)
