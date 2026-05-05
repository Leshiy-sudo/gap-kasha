package com.gapkassa

import android.os.ParcelFileDescriptor
import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.junit4.createAndroidComposeRule
import androidx.compose.ui.test.onAllNodesWithTag
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.compose.ui.test.performTextClearance
import androidx.compose.ui.test.performTextInput
import androidx.test.platform.app.InstrumentationRegistry
import com.gapkassa.ui.TestTags
import org.junit.After
import org.junit.Before
import org.junit.Rule
import java.io.BufferedReader
import java.io.InputStreamReader

abstract class UiFlowTestBase {

    @get:Rule
    val composeRule = createAndroidComposeRule<MainActivity>()

    private val instrumentation = InstrumentationRegistry.getInstrumentation()

    @Before
    fun enableNetworkBeforeTest() {
        enableNetwork()
    }

    @After
    fun enableNetworkAfterTest() {
        enableNetwork()
    }

    protected fun loginFresh() {
        logoutIfNeeded()
        waitForTag(TestTags.AuthTitle)
        composeRule.onNodeWithTag(TestTags.AuthMockGoogleButton).performClick()
        waitForTag(TestTags.RoomsTitle)
        composeRule.onNodeWithTag(TestTags.RoomsTitle).assertIsDisplayed()
    }

    protected fun logoutIfNeeded() {
        if (!hasTag(TestTags.RoomsTitle)) return
        composeRule.onNodeWithTag(TestTags.RoomsProfileButton).performClick()
        waitForTag(TestTags.ProfileLogout)
        composeRule.onNodeWithTag(TestTags.ProfileLogout).performClick()
        waitForTag(TestTags.AuthTitle)
    }

    protected fun createRoomViaUi(roomName: String) {
        composeRule.onNodeWithTag(TestTags.RoomsCreateFab).performClick()
        waitForTag(TestTags.CreateRoomName)
        composeRule.onNodeWithTag(TestTags.CreateRoomName).performTextClearance()
        composeRule.onNodeWithTag(TestTags.CreateRoomName).performTextInput(roomName)

        val emailSuffix = roomName.takeLast(5).lowercase()
        val participants = listOf(
            TEST_EMAIL,
            "m1$emailSuffix@gk.co",
            "m2$emailSuffix@gk.co",
            "m3$emailSuffix@gk.co",
            "m4$emailSuffix@gk.co"
        )
        participants.forEach { participant ->
            composeRule.onNodeWithTag(TestTags.CreateRoomParticipants).performTextClearance()
            composeRule.onNodeWithTag(TestTags.CreateRoomParticipants).performTextInput(participant)
            composeRule.onNodeWithTag(TestTags.CreateRoomAddParticipant).performClick()
            composeRule.waitForIdle()
        }

        composeRule.onNodeWithTag(TestTags.CreateRoomSubmit).performScrollTo().performClick()
        waitForTag(TestTags.RoomsTitle)
    }

    protected fun disableNetwork() {
        runShell("svc wifi disable")
        runShell("svc data disable")
        Thread.sleep(1_500)
    }

    protected fun uniqueRoomName(prefix: String): String {
        return "Ui${prefix}${System.currentTimeMillis() % 100000}"
    }

    protected fun waitForTag(tag: String, timeoutMillis: Long = 15_000) {
        composeRule.waitUntil(timeoutMillis) { hasTag(tag) }
    }

    protected fun waitUntilTagGone(tag: String, timeoutMillis: Long = 15_000) {
        composeRule.waitUntil(timeoutMillis) { !hasTag(tag) }
    }

    protected fun hasTag(tag: String): Boolean {
        return composeRule.onAllNodesWithTag(tag, useUnmergedTree = true)
            .fetchSemanticsNodes().isNotEmpty()
    }

    private fun enableNetwork() {
        runShell("svc wifi enable")
        runShell("svc data enable")
        Thread.sleep(1_500)
    }

    private fun runShell(command: String): String {
        val descriptor = instrumentation.uiAutomation.executeShellCommand(command)
        return ParcelFileDescriptor.AutoCloseInputStream(descriptor).use { input ->
            BufferedReader(InputStreamReader(input)).readText()
        }
    }

    companion object {
        const val TEST_EMAIL = "uiqa@example.com"
    }
}
