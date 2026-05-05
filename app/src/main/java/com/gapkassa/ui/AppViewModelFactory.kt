package com.gapkassa.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.ViewModelProvider
import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.AbstractSavedStateViewModelFactory
import androidx.savedstate.SavedStateRegistryOwner
import com.gapkassa.GapKassaApp
import com.gapkassa.data.repository.ExportRepository
import com.gapkassa.viewmodel.AuthViewModel
import com.gapkassa.viewmodel.CalendarViewModel
import com.gapkassa.viewmodel.ProfileViewModel
import com.gapkassa.viewmodel.RoomViewModel
import com.gapkassa.viewmodel.RoomsViewModel
import com.gapkassa.viewmodel.StatsViewModel

/**
 * ViewModel factory that injects app-level repositories into screens.
 */
class AppViewModelFactory(
    private val app: GapKassaApp,
    owner: SavedStateRegistryOwner
) : AbstractSavedStateViewModelFactory(owner, null) {
    override fun <T : ViewModel> create(key: String, modelClass: Class<T>, handle: SavedStateHandle): T {
        return when {
            modelClass.isAssignableFrom(AuthViewModel::class.java) ->
                AuthViewModel(app.authRepository, app.profileRepository, handle) as T
            modelClass.isAssignableFrom(RoomsViewModel::class.java) ->
                RoomsViewModel(app.roomRepository, app.actionLogRepository, app.authRepository) as T
            modelClass.isAssignableFrom(RoomViewModel::class.java) ->
                RoomViewModel(app.roomRepository, app.actionLogRepository, app.authRepository) as T
            modelClass.isAssignableFrom(CalendarViewModel::class.java) ->
                CalendarViewModel(app.roomRepository) as T
            modelClass.isAssignableFrom(StatsViewModel::class.java) ->
                StatsViewModel(app.roomRepository, ExportRepository(app.applicationContext)) as T
            modelClass.isAssignableFrom(ProfileViewModel::class.java) ->
                ProfileViewModel(app.authRepository, app.actionLogRepository, app.profileRepository, app.roomRepository) as T
            else -> throw IllegalArgumentException("Unknown ViewModel ${modelClass.name}")
        }
    }
}
