package com.gapkassa.data.repository

import com.gapkassa.data.db.AppDatabase
import com.gapkassa.data.db.MembershipEntity
import com.gapkassa.data.db.PaymentEntity
import com.gapkassa.data.db.RoomEntity
import com.gapkassa.data.db.UserEntity
import com.gapkassa.data.model.PaymentStatus
import com.gapkassa.data.model.Role
import com.gapkassa.data.remote.BackendApi
import com.gapkassa.data.remote.MemberCreateRequest
import com.gapkassa.data.remote.MemberDto
import com.gapkassa.data.remote.PaymentDto
import com.gapkassa.data.remote.PaymentStatusUpdateRequest
import com.gapkassa.data.remote.RoomBundleDto
import com.gapkassa.data.remote.RoomCreateRequest
import com.gapkassa.data.remote.RoomDto
import com.gapkassa.data.remote.ScheduleItemRequest
import com.gapkassa.data.remote.ScheduleUpdateRequest
import kotlinx.coroutines.flow.Flow
import retrofit2.HttpException
import java.time.LocalDate
import java.util.UUID

/**
 * Encapsulates room creation, membership management, and payment schedule generation.
 */
class RoomRepository(
    private val database: AppDatabase,
    private val backendApi: BackendApi? = null
) {
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

    fun observeUsers(): Flow<List<UserEntity>> = userDao.observeUsers()

    suspend fun syncRooms() {
        val api = backendApi ?: return
        val rooms = api.rooms()
        rooms.forEach { roomDto ->
            roomDao.upsert(roomDto.toEntity())
            val members = api.roomMembers(roomDto.id)
            applyMembers(roomDto.id, members)
        }
        // Clear stale data after successful sync to avoid empty state on network failure.
        val roomIds = rooms.map { it.id }.toSet()
        roomDao.deleteNotIn(roomIds)
        membershipDao.clearNotInRooms(roomIds)
        paymentDao.clearNotInRooms(roomIds)
    }

    suspend fun syncRoom(roomId: String) {
        val api = backendApi ?: return
        val bundle = api.room(roomId)
        applyRoomBundle(bundle)
    }

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
        val api = backendApi
        if (api == null) {
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

        val memberRequests = members.mapIndexed { index, user ->
            MemberCreateRequest(
                email = user.email,
                name = user.name,
                role = if (user.id == adminId) Role.ADMIN.name else Role.MEMBER.name,
                orderIndex = index
            )
        }
        val response = api.createRoom(
            RoomCreateRequest(
                name = name,
                description = description,
                monthlyAmount = monthlyAmount,
                paymentDay = paymentDay,
                cycleLengthMonths = cycleLength,
                autoRotate = autoRotate,
                members = memberRequests
            )
        )
        applyRoomBundle(response)
        return response.room.id
    }

    suspend fun seedDemoIfEmpty() {
        if (backendApi != null) return
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
        val api = backendApi
        if (api == null) {
            paymentDao.updateStatus(paymentId, status, LocalDate.now())
            return
        }
        val updated = api.updatePaymentStatus(paymentId, PaymentStatusUpdateRequest(status.name))
        paymentDao.upsert(updated.toEntity())
    }

    suspend fun updateSchedule(roomId: String, assignments: List<ScheduleAssignment>) {
        val api = backendApi ?: return
        val payload = ScheduleUpdateRequest(
            items = assignments.map {
                ScheduleItemRequest(
                    month = it.month.toString(),
                    receiverId = it.receiverId
                )
            }
        )
        api.updateSchedule(roomId, payload)
        syncRoom(roomId)
    }

    suspend fun deleteRoom(roomId: String) {
        val api = backendApi
        if (api == null) {
            val paidCount = paymentDao.countByStatus(roomId, PaymentStatus.PAID)
            if (paidCount > 0) {
                throw RoomDeleteException(RoomDeleteError.PAID_EXISTS)
            }
            paymentDao.clearRoom(roomId)
            membershipDao.clearRoom(roomId)
            roomDao.deleteById(roomId)
            return
        }
        try {
            api.deleteRoom(roomId)
        } catch (exception: HttpException) {
            val error = when (exception.code()) {
                403 -> RoomDeleteError.FORBIDDEN
                404 -> RoomDeleteError.NOT_FOUND
                409 -> RoomDeleteError.PAID_EXISTS
                else -> RoomDeleteError.UNKNOWN
            }
            throw RoomDeleteException(error)
        }
        paymentDao.clearRoom(roomId)
        membershipDao.clearRoom(roomId)
        roomDao.deleteById(roomId)
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

    private suspend fun applyRoomBundle(bundle: RoomBundleDto) {
        roomDao.upsert(bundle.room.toEntity())
        applyMembers(bundle.room.id, bundle.members)
        paymentDao.clearRoom(bundle.room.id)
        bundle.payments.forEach { paymentDao.upsert(it.toEntity()) }
    }

    private suspend fun applyMembers(roomId: String, members: List<MemberDto>) {
        membershipDao.clearRoom(roomId)
        members.forEach { member ->
            userDao.upsert(member.toUserEntity())
            membershipDao.upsert(member.toMembershipEntity(roomId))
        }
    }

    private fun RoomDto.toEntity(): RoomEntity {
        val createdAt = createdAt?.let { parseDate(it) } ?: LocalDate.now()
        return RoomEntity(
            id = id,
            name = name,
            description = description,
            minParticipants = 5,
            monthlyAmount = monthlyAmount ?: 0L,
            paymentDay = paymentDay ?: 1,
            cycleLengthMonths = cycleLengthMonths ?: 1,
            autoRotate = autoRotate ?: false,
            createdAt = createdAt
        )
    }

    private fun MemberDto.toUserEntity(): UserEntity {
        val fallbackName = email.substringBefore("@").ifBlank { email }
        return UserEntity(
            id = userId,
            name = name ?: fallbackName,
            email = email
        )
    }

    private fun MemberDto.toMembershipEntity(roomId: String): MembershipEntity {
        val resolvedRole = runCatching { Role.valueOf(role) }.getOrDefault(Role.MEMBER)
        return MembershipEntity(
            userId = userId,
            roomId = roomId,
            role = resolvedRole,
            orderIndex = orderIndex
        )
    }

    private fun PaymentDto.toEntity(): PaymentEntity {
        val resolvedStatus = runCatching { PaymentStatus.valueOf(status) }.getOrDefault(PaymentStatus.EXPECTED)
        val monthDate = parseDate(month)
        val updatedDate = parseDate(updatedAt)
        return PaymentEntity(
            id = id,
            roomId = roomId,
            payerId = payerId,
            receiverId = receiverId,
            amount = amount,
            month = monthDate,
            status = resolvedStatus,
            updatedAt = updatedDate
        )
    }

    private fun parseDate(value: String): LocalDate {
        val sanitized = value.take(10)
        return runCatching { LocalDate.parse(sanitized) }.getOrElse { LocalDate.now() }
    }
}

/** Assignment of a receiver for a given month. */
data class ScheduleAssignment(
    val month: LocalDate,
    val receiverId: String
)

enum class RoomDeleteError {
    PAID_EXISTS,
    FORBIDDEN,
    NOT_FOUND,
    UNKNOWN
}

class RoomDeleteException(val error: RoomDeleteError) : RuntimeException(error.name)
