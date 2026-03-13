package com.gapkassa.data.model

import java.time.LocalDate

/** Participant role inside a room. */
enum class Role {
    ADMIN,
    MEMBER
}

/** Status of a scheduled payment. */
enum class PaymentStatus {
    EXPECTED,
    PAID,
    SKIPPED,
    OVERDUE
}

/** Lightweight domain user model. */
data class User(
    val id: String,
    val name: String,
    val email: String
)

/** Domain model for room configuration. */
data class Room(
    val id: String,
    val name: String,
    val description: String?,
    val minParticipants: Int,
    val monthlyAmount: Long,
    val paymentDay: Int,
    val cycleLengthMonths: Int,
    val autoRotate: Boolean,
    val createdAt: LocalDate
)

/** Domain model for membership/rotation order. */
data class Membership(
    val userId: String,
    val roomId: String,
    val role: Role,
    val orderIndex: Int
)

/** Domain model for a payment item. */
data class Payment(
    val id: String,
    val roomId: String,
    val payerId: String,
    val receiverId: String,
    val amount: Long,
    val month: LocalDate,
    val status: PaymentStatus,
    val updatedAt: LocalDate
)

/** Profile details stored locally for the current user. */
data class UserProfile(
    val name: String,
    val lastName: String,
    val patronymic: String,
    val email: String,
    val phone: String,
    val photoUrl: String
)
