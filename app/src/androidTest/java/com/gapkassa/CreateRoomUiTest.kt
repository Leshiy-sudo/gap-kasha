package com.gapkassa

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithTag
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.gapkassa.ui.TestTags
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class CreateRoomUiTest : UiFlowTestBase() {
    @Test
    fun createRoomFromUiWorks() {
        loginFresh()
        val roomName = uniqueRoomName("Create")
        createRoomViaUi(roomName)
        waitForTag(TestTags.roomCard(roomName))
        composeRule.onNodeWithTag(TestTags.roomCard(roomName)).assertIsDisplayed()
    }
}
