package com.gapkassa.data.db.dao

import androidx.room.Dao
import androidx.room.Embedded
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.gapkassa.data.db.RoomEntity
import kotlinx.coroutines.flow.Flow

data class RoomWithCount(
    @Embedded val room: RoomEntity,
    val memberCount: Int
)

@Dao
interface RoomDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(room: RoomEntity)

    @Query("SELECT * FROM rooms ORDER BY createdAt DESC")
    fun observeRooms(): Flow<List<RoomEntity>>

    @Query("SELECT rooms.*, (SELECT COUNT(*) FROM memberships WHERE memberships.roomId = rooms.id) AS memberCount FROM rooms ORDER BY createdAt DESC")
    fun observeRoomsWithCounts(): Flow<List<RoomWithCount>>

    @Query("SELECT * FROM rooms WHERE id = :roomId")
    suspend fun getById(roomId: String): RoomEntity?

    @Query("SELECT COUNT(*) FROM rooms")
    suspend fun count(): Int
}
