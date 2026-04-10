package com.gapkassa.data.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.gapkassa.data.db.MembershipEntity
import kotlinx.coroutines.flow.Flow

@Dao
interface MembershipDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(membership: MembershipEntity)

    @Query("SELECT * FROM memberships WHERE roomId = :roomId ORDER BY orderIndex ASC")
    fun observeRoomMembers(roomId: String): Flow<List<MembershipEntity>>

    @Query("DELETE FROM memberships WHERE roomId = :roomId")
    suspend fun clearRoom(roomId: String)

    @Query("DELETE FROM memberships")
    suspend fun clearAll()

    @Query("DELETE FROM memberships WHERE roomId NOT IN (:roomIds)")
    suspend fun clearNotInRooms(roomIds: Set<String>)
}
