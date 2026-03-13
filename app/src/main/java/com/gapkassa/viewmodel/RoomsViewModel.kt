package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.db.UserEntity
import com.gapkassa.data.repository.ActionLogRepository
import com.gapkassa.data.repository.RoomRepository
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Provides room list and creation workflow for the rooms screen.
 */
class RoomsViewModel(
    private val roomRepository: RoomRepository,
    private val actionLogRepository: ActionLogRepository
) : ViewModel() {

    val rooms: StateFlow<List<RoomItem>> = roomRepository.observeRoomsWithCounts()
        .map { list ->
            list.map {
                RoomItem(
                    id = it.room.id,
                    name = it.room.name,
                    amount = it.room.monthlyAmount,
                    paymentDay = it.room.paymentDay,
                    cycleMonths = it.room.cycleLengthMonths,
                    memberCount = it.memberCount
                )
            }
        }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyList())

    fun createRoom(
        name: String,
        description: String?,
        amount: Long,
        paymentDay: Int,
        cycleLength: Int,
        autoRotate: Boolean,
        participantEmails: List<String>,
        onCreated: (String) -> Unit
    ) {
        if (participantEmails.size < 5 || participantEmails.size > 20) return
        viewModelScope.launch {
            val users = participantEmails.mapIndexed { index, email ->
                UserEntity(
                    id = email.trim().lowercase(),
                    name = "Участник ${index + 1}",
                    email = email.trim().lowercase()
                )
            }
            val adminId = users.first().id
            val roomId = roomRepository.createRoom(
                name = name,
                description = description,
                monthlyAmount = amount,
                paymentDay = paymentDay,
                cycleLength = cycleLength,
                autoRotate = autoRotate,
                members = users,
                adminId = adminId
            )
            actionLogRepository.log(adminId, roomId, "create_room")
            onCreated(roomId)
        }
    }
}

/** Simplified room info for list rendering. */
data class RoomItem(
    val id: String,
    val name: String,
    val amount: Long,
    val paymentDay: Int,
    val cycleMonths: Int,
    val memberCount: Int
)
