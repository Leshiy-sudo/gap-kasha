package com.gapkassa.data.repository

import com.gapkassa.data.db.ActionLogEntity
import com.gapkassa.data.db.AppDatabase
import kotlinx.coroutines.flow.Flow
import java.time.LocalDate
import java.util.UUID

/**
 * Persists lightweight audit events for user actions.
 */
class ActionLogRepository(private val database: AppDatabase) {
    private val actionLogDao = database.actionLogDao()

    suspend fun log(userId: String, roomId: String?, action: String) {
        actionLogDao.insert(
            ActionLogEntity(
                id = UUID.randomUUID().toString(),
                roomId = roomId,
                userId = userId,
                action = action,
                createdAt = LocalDate.now()
            )
        )
    }

    fun observeRoomLogs(roomId: String): Flow<List<ActionLogEntity>> =
        actionLogDao.observeRoomLogs(roomId)
}
