package com.gapkassa.viewmodel

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.gapkassa.data.db.PaymentEntity
import com.gapkassa.data.repository.RoomRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.SharingStarted
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.flatMapLatest
import kotlinx.coroutines.flow.map
import kotlinx.coroutines.flow.stateIn
import java.time.LocalDate

/**
 * Groups payments by date for the calendar screen.
 */
class CalendarViewModel(
    private val roomRepository: RoomRepository
) : ViewModel() {

    private val roomIdFlow = MutableStateFlow<String?>(null)

    val calendarItems: StateFlow<Map<LocalDate, List<PaymentEntity>>> = roomIdFlow
        .flatMapLatest { id ->
            if (id == null) kotlinx.coroutines.flow.flowOf(emptyList())
            else roomRepository.observeRoomPayments(id)
        }
        .map { payments -> payments.groupBy { it.month } }
        .stateIn(viewModelScope, SharingStarted.WhileSubscribed(5000), emptyMap())

    fun setRoom(roomId: String) {
        roomIdFlow.value = roomId
    }
}
