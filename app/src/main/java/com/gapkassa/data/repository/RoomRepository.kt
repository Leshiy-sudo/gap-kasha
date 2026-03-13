package com.gapkassa.data.repository

import com.gapkassa.data.db.AppDatabase
import com.gapkassa.data.db.MembershipEntity
import com.gapkassa.data.db.PaymentEntity
import com.gapkassa.data.db.RoomEntity
import com.gapkassa.data.db.UserEntity
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.data.model.Role
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.map
import java.time.LocalDate
import java.util.UUID

/**
 * Encapsulates room creation, membership management, and payment schedule generation.
 */
class RoomRepository(private val database: AppDatabase) {
    private val roomDao = database.roomDao()
    private val membershipDao = database.membershipDao()
    private val paymentDao = database.paymentDao()
    private val userDao = database.userDao()

    fun observeRooms(): Flow<List<RoomEntity>> = roomDao.observeRooms()

    fun observeRoomsWithCounts() = roomDao.observeRoomsWithCounts()

    fun observeRoomPayments(roomId: String): Flow<List<PaymentEntity>> =
        paymentDao.observeRoomPayments(roomId)

    fun observeRoomMembers(roomId: String): Flow<List<MembershipEntity>> =
        membershipDao.observeRoomMembers(roomId)

    suspend fun createRoom(
        name: String,
        description: String?,
        monthlyAmount: Long,
        paymentDay: Int,
        cycleLength: Int,
        autoRotate: Boolean,
        members: List<UserEntity>,
        adminId: String
    ): String {
        require(members.size in 5..20) { "Participants must be between 5 and 20" }
        val roomId = UUID.randomUUID().toString()
        val room = RoomEntity(
            id = roomId,
            name = name,
            description = description,
            minParticipants = 5,
            monthlyAmount = monthlyAmount,
            paymentDay = paymentDay,
            cycleLengthMonths = cycleLength,
            autoRotate = autoRotate,
            createdAt = LocalDate.now()
        )
        roomDao.upsert(room)

        members.forEachIndexed { index, user ->
            userDao.upsert(user)
            membershipDao.upsert(
                MembershipEntity(
                    userId = user.id,
                    roomId = roomId,
                    role = if (user.id == adminId) Role.ADMIN else Role.MEMBER,
                    orderIndex = index
                )
            )
        }

        val payments = generatePayments(roomId, members.map { it.id }, monthlyAmount, paymentDay, cycleLength)
        payments.forEach { paymentDao.upsert(it) }

        return roomId
    }

    suspend fun seedDemoIfEmpty() {
        if (roomDao.count() > 0) return
        val demoMembers = (1..10).map { index ->
            UserEntity(
                id = "demo$index@example.com",
                name = "Участник $index",
                email = "demo$index@example.com"
            )
        }
        createRoom(
            name = "Демо группа",
            description = "Тестовый цикл на 10 месяцев",
            monthlyAmount = 150000,
            paymentDay = 25,
            cycleLength = 10,
            autoRotate = true,
            members = demoMembers,
            adminId = demoMembers.first().id
        )
    }

    suspend fun updatePaymentStatus(paymentId: String, status: PaymentStatus) {
        paymentDao.updateStatus(paymentId, status, LocalDate.now())
    }

    fun generatePayments(
        roomId: String,
        memberIds: List<String>,
        amount: Long,
        paymentDay: Int,
        cycleLength: Int
    ): List<PaymentEntity> {
        if (memberIds.size < 5 || memberIds.size > 20) return emptyList()
        val payments = mutableListOf<PaymentEntity>()
        val now = LocalDate.now()
        for (i in 0 until cycleLength) {
            val monthDate = now.plusMonths(i.toLong()).withDayOfMonth(paymentDay.coerceIn(1, 28))
            val receiverIndex = i % memberIds.size
            val receiverId = memberIds[receiverIndex]
            memberIds.forEach { payerId ->
                if (payerId != receiverId) {
                    payments.add(
                        PaymentEntity(
                            id = UUID.randomUUID().toString(),
                            roomId = roomId,
                            payerId = payerId,
                            receiverId = receiverId,
                            amount = amount,
                            month = monthDate,
                            status = PaymentStatus.EXPECTED,
                            updatedAt = now
                        )
                    )
                }
            }
        }
        return payments
    }
}
