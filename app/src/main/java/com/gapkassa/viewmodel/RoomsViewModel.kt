package com.gapkassa.viewmodel

import android.util.Log
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.BuildConfig
import com.gapkassa.data.db.UserEntity
import com.gapkassa.data.repository.ActionLogRepository
import com.gapkassa.data.repository.AuthRepository
import com.gapkassa.data.repository.RoomRepository
import com.gapkassa.data.repository.RoomDeleteError
import com.gapkassa.data.repository.RoomDeleteException
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.stateIn
import kotlinx.coroutines.launch
import java.util.UUID

/**
 * Provides room list and creation workflow for the rooms screen.
 */
class RoomsViewModel(
    private val roomRepository: RoomRepository,
    private val actionLogRepository: ActionLogRepository,
    private val authRepository: AuthRepository
) : ViewModel() {

    private val _isCreating = MutableStateFlow(false)
    val isCreating: StateFlow<Boolean> = _isCreating

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

    val currentEmail: String?
        get() = authRepository.currentEmail

    init {
        refreshRooms()
    }

    fun refreshRooms() {
        viewModelScope.launch {
            runCatching { roomRepository.syncRooms() }
        }
    }

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
        if (BuildConfig.DEBUG) {
            Log.d("RoomsViewModel", "createRoom click name=\"$name\" participants=${participantEmails.size}")
        }
        if (participantEmails.size < 5 || participantEmails.size > 20) {
            if (BuildConfig.DEBUG) {
                Log.d("RoomsViewModel", "createRoom blocked: participants size invalid")
            }
            return
        }
        if (_isCreating.value) return
        _isCreating.value = true
        viewModelScope.launch {
            try {
                if (BuildConfig.DEBUG) {
                    Log.d("RoomsViewModel", "createRoom sending request")
                }
                val users = participantEmails.map { email ->
                    UserEntity(
                        id = email.trim().lowercase(),
                        name = "",
                        email = email.trim().lowercase()
                    )
                }
                val currentEmail = authRepository.currentEmail?.trim()?.lowercase()
                val adminId = if (currentEmail != null && users.any { it.id == currentEmail }) {
                    currentEmail
                } else {
                    users.first().id
                }
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
                val actorId = authRepository.currentUserId ?: adminId
                actionLogRepository.log(actorId, roomId, "create_room")
                onCreated(roomId)
                if (BuildConfig.DEBUG) {
                    Log.d("RoomsViewModel", "createRoom success id=$roomId")
                }
            } catch (exception: Exception) {
                if (BuildConfig.DEBUG) {
                    Log.e("RoomsViewModel", "createRoom failed", exception)
                }
            } finally {
                _isCreating.value = false
            }
        }
    }

    fun deleteRoom(
        roomId: String,
        onDeleted: () -> Unit,
        onError: (RoomDeleteError) -> Unit
    ) {
        viewModelScope.launch {
            try {
                roomRepository.deleteRoom(roomId)
                val actorId = authRepository.currentUserId ?: "unknown"
                actionLogRepository.log(actorId, roomId, "delete_room")
                onDeleted()
            } catch (exception: RoomDeleteException) {
                onError(exception.error)
            } catch (exception: Exception) {
                if (BuildConfig.DEBUG) {
                    Log.e("RoomsViewModel", "deleteRoom failed", exception)
                }
                onError(RoomDeleteError.UNKNOWN)
            }
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
