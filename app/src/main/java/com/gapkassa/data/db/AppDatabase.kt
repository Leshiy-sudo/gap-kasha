package com.gapkassa.data.db

import android.content.Context
import androidx.room.Database
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.TypeConverters
import com.gapkassa.data.db.dao.ActionLogDao
import com.gapkassa.data.db.dao.MembershipDao
import com.gapkassa.data.db.dao.PaymentDao
import com.gapkassa.data.db.dao.RoomDao
import com.gapkassa.data.db.dao.UserDao

/**
 * Room database that stores rooms, members, payments, and action logs locally.
 */
@Database(
    entities = [
        UserEntity::class,
        RoomEntity::class,
        MembershipEntity::class,
        PaymentEntity::class,
        ActionLogEntity::class
    ],
    version = 1,
    exportSchema = false
)
@TypeConverters(Converters::class)
abstract class AppDatabase : RoomDatabase() {
    abstract fun userDao(): UserDao
    abstract fun roomDao(): RoomDao
    abstract fun membershipDao(): MembershipDao
    abstract fun paymentDao(): PaymentDao
    abstract fun actionLogDao(): ActionLogDao

    companion object {
        @Volatile
        private var instance: AppDatabase? = null

        fun getInstance(context: Context): AppDatabase =
            instance ?: synchronized(this) {
                instance ?: Room.databaseBuilder(
                    context.applicationContext,
                    AppDatabase::class.java,
                    "gap_kassa.db"
                ).fallbackToDestructiveMigration()
                    .build()
                    .also { instance = it }
            }
    }
}
