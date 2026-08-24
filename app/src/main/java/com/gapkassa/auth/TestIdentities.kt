package com.gapkassa.auth

/** Fixed identity used by a debug-only quick-login test button. */
data class TestIdentity(
    val email: String,
    val subject: String,
    val displayName: String
)

/**
 * Five fixed test identities for the debug quick-login screen: one room creator
 * and four room members, so the role model (admin vs member) can be exercised
 * without a real phone/OTP flow.
 */
object TestIdentities {
    val CREATOR = TestIdentity(
        email = "test-creator@gapkassa.test",
        subject = "test-creator",
        displayName = "Тестовый создатель"
    )

    val MEMBERS = listOf(
        TestIdentity("test-member1@gapkassa.test", "test-member1", "Тестовый участник 1"),
        TestIdentity("test-member2@gapkassa.test", "test-member2", "Тестовый участник 2"),
        TestIdentity("test-member3@gapkassa.test", "test-member3", "Тестовый участник 3"),
        TestIdentity("test-member4@gapkassa.test", "test-member4", "Тестовый участник 4")
    )

    val ALL = listOf(CREATOR) + MEMBERS
}
