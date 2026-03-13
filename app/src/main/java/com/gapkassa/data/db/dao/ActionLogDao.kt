package com.gapkassa.data.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.gapkassa.data.db.ActionLogEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface ActionLogDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun insert(log: ActionLogEntity)

    @Query("SELECT * FROM action_logs WHERE roomId = :roomId ORDER BY createdAt DESC")
    fun observeRoomLogs(roomId: String): Flow<List<ActionLogEntity>>
}
