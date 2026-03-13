package com.gapkassa.data.db

import androidx.room.Entity
import androidx.room.PrimaryKey
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.data.model.Role
import java.time.LocalDate

/** Room table for users participating in groups. */
@Entity(tableName = "users")
data class UserEntity(
    @PrimaryKey val id: String,
    val name: String,
    val email: String
)

/** Room table for group rooms and their configuration. */
@Entity(tableName = "rooms")
data class RoomEntity(
    @PrimaryKey val id: String,
    val name: String,
    val description: String?,
    val minParticipants: Int,
    val monthlyAmount: Long,
    val paymentDay: Int,
    val cycleLengthMonths: Int,
    val autoRotate: Boolean,
    val createdAt: LocalDate
)

/** Room table mapping users to rooms with role and rotation order. */
@Entity(tableName = "memberships", primaryKeys = ["userId", "roomId"])
data class MembershipEntity(
    val userId: String,
    val roomId: String,
    val role: Role,
    val orderIndex: Int
)

/** Room table for scheduled and actual payment states. */
@Entity(tableName = "payments")
data class PaymentEntity(
    @PrimaryKey val id: String,
    val roomId: String,
    val payerId: String,
    val receiverId: String,
    val amount: Long,
    val month: LocalDate,
    val status: PaymentStatus,
    val updatedAt: LocalDate
)

/** Room table for audit trail of key user actions. */
@Entity(tableName = "action_logs")
data class ActionLogEntity(
    @PrimaryKey val id: String,
    val roomId: String?,
    val userId: String,
    val action: String,
    val createdAt: LocalDate
)
