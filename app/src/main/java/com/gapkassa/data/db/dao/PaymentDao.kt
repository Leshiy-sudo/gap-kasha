package com.gapkassa.data.db.dao

import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query
import com.gapkassa.data.db.PaymentEntity
import kotlinx.coroutines.flow.Flow
import java.time.LocalDate

@Dao
interface PaymentDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(payment: PaymentEntity)

    @Query("SELECT * FROM payments WHERE id = :paymentId")
    suspend fun getById(paymentId: String): PaymentEntity?

    @Query("UPDATE payments SET status = :status, updatedAt = :updatedAt WHERE id = :paymentId")
    suspend fun updateStatus(paymentId: String, status: com.gapkassa.data.model.PaymentStatus, updatedAt: java.time.LocalDate)

    @Query("SELECT * FROM payments WHERE roomId = :roomId ORDER BY month DESC")
    fun observeRoomPayments(roomId: String): Flow<List<PaymentEntity>>

    @Query("SELECT * FROM payments WHERE roomId = :roomId AND month = :month")
    fun observeMonthPayments(roomId: String, month: LocalDate): Flow<List<PaymentEntity>>
}
