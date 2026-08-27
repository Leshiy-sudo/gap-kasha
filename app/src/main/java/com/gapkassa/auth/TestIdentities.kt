package com.gapkassa.auth

/** Fixed identity used by a debug-only quick-login test button. */
data class TestIdentity(
    val phone: String,
    val displayName: String
)

/**
 * Five fixed test identities for the debug quick-login screen: one room creator
 * and four room members, so the role model (admin vs member) can be exercised
 * without waiting on a real Telegram round-trip. These match the backend's
 * MOCK_TEST_PHONES + MOCK_TEST_CODE (see local-backend/main.py) — the fixed
 * code "000000" always verifies for these phones when PHONE_AUTH_ALLOW_MOCK is on.
 */
object TestIdentities {
    const val MOCK_CODE = "000000"

    val CREATOR = TestIdentity(
        phone = "+998900000001",
        displayName = "Тестовый создатель"
    )

    val MEMBERS = listOf(
        TestIdentity("+998900000002", "Тестовый участник 1"),
        TestIdentity("+998900000003", "Тестовый участник 2"),
        TestIdentity("+998900000004", "Тестовый участник 3"),
        TestIdentity("+998900000005", "Тестовый участник 4")
    )

    val ALL = listOf(CREATOR) + MEMBERS
}
