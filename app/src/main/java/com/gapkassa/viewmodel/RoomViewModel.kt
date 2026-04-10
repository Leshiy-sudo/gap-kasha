package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.db.MembershipEntity
import com.gapkassa.data.db.PaymentEntity
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.data.repository.ActionLogRepository
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.RoomRepository
import com.gapkassa.data.repository.ScheduleAssignment
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
    private val actionLogRepository: ActionLogRepository,
    private val authRepository: AuthRepository
) : ViewModel() {

    val currentUserId: String?
        get() = authRepository.currentUserId

    private val currentRoomId = MutableStateFlow<String?>(null)

    val payments: StateFlow<List<PaymentEntity>> = currentRoomId
        .flatMapLatestList { id -> roomRepository.observeRoomPayments(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    private val memberEntities: StateFlow<List<MembershipEntity>> = currentRoomId
        .flatMapLatestList { id -> roomRepository.observeRoomMembers(id) }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    val members: StateFlow<List<MemberUi>> = combine(
        memberEntities,
        roomRepository.observeUsers()
    ) { members, users ->
        val userMap = users.associateBy { it.id }
        members.map { member ->
            val user = userMap[member.userId]
            val email = user?.email ?: member.userId
            val name = user?.name ?: email.substringBefore("@").ifBlank { email }
            MemberUi(
                userId = member.userId,
                email = email,
                name = name,
                role = member.role,
                orderIndex = member.orderIndex
            )
        }
    }.stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

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

    fun canManagePayment(payment: PaymentEntity?): Boolean {
        val userId = authRepository.currentUserId ?: return false
        val isAdmin = members.value.firstOrNull { it.userId == userId }?.role == com.gapkassa.data.model.Role.ADMIN
        val isPayer = payment?.payerId == userId
        return isAdmin || isPayer
    }

    fun setRoom(roomId: String) {
        currentRoomId.value = roomId
        viewModelScope.launch {
            runCatching { roomRepository.syncRoom(roomId) }
        }
    }

    fun markPaid(paymentId: String) {
        viewModelScope.launch {
            roomRepository.updatePaymentStatus(paymentId, PaymentStatus.PAID)
            authRepository.currentUserId?.let { userId ->
                actionLogRepository.log(userId, currentRoomId.value, "mark_paid")
            }
        }
    }

    fun markSkipped(paymentId: String) {
        viewModelScope.launch {
            roomRepository.updatePaymentStatus(paymentId, PaymentStatus.SKIPPED)
            authRepository.currentUserId?.let { userId ->
                actionLogRepository.log(userId, currentRoomId.value, "mark_skipped")
            }
        }
    }

    fun saveSchedule(
        assignments: List<ScheduleAssignment>,
        onSaved: () -> Unit,
        onError: (Throwable) -> Unit
    ) {
        val roomId = currentRoomId.value ?: return
        viewModelScope.launch {
            try {
                roomRepository.updateSchedule(roomId, assignments)
                onSaved()
            } catch (exception: Throwable) {
                onError(exception)
            }
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

/** Member entry with resolved profile info for UI. */
data class MemberUi(
    val userId: String,
    val email: String,
    val name: String,
    val role: com.gapkassa.data.model.Role,
    val orderIndex: Int
)
