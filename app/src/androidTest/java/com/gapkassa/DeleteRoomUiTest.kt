package com.gapkassa

import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.gapkassa.ui.TestTags
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DeleteRoomUiTest : UiFlowTestBase() {
    @Test
    fun deleteRoomFromUiWorks() {
        loginFresh()
        val roomName = uniqueRoomName("Delete")
        createRoomViaUi(roomName)
        waitForTag(TestTags.roomMenu(roomName))
        composeRule.onNodeWithTag(TestTags.roomMenu(roomName)).performClick()
        waitForTag(TestTags.RoomDeleteAction)
        composeRule.onNodeWithTag(TestTags.RoomDeleteAction).performClick()
        waitForTag(TestTags.RoomDeleteConfirm)
        composeRule.onNodeWithTag(TestTags.RoomDeleteConfirm).performClick()
        waitUntilTagGone(TestTags.roomCard(roomName))
    }
}
