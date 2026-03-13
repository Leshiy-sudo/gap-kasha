package com.gapkassa.data.repository

import android.content.Context
import com.gapkassa.data.db.PaymentEntity
import java.io.File
import java.time.format.DateTimeFormatter

/**
 * Creates CSV exports from payments for sharing or backup.
 */
class ExportRepository(private val context: Context) {
    fun exportPaymentsToCsv(roomName: String, payments: List<PaymentEntity>): File {
        val formatter = DateTimeFormatter.ISO_DATE
        val fileName = "payments_${roomName.replace(" ", "_")}_${System.currentTimeMillis()}.csv"
        val file = File(context.cacheDir, fileName)
        val header = "month,payer,receiver,amount,status,updatedAt\n"
        val rows = payments.joinToString("\n") { payment ->
            listOf(
                payment.month.format(formatter),
                payment.payerId,
                payment.receiverId,
                payment.amount.toString(),
                payment.status.name,
                payment.updatedAt.format(formatter)
            ).joinToString(",")
        }
        file.writeText(header + rows)
        return file
    }
}
