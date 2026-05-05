package com.gapkassa

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithTag
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.gapkassa.ui.TestTags
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class OfflineStartUiTest : UiFlowTestBase() {
    @Test
    fun authorizedUserKeepsAccessOfflineAfterRecreate() {
        loginFresh()
        disableNetwork()
        composeRule.activityRule.scenario.recreate()
        waitForTag(TestTags.RoomsTitle)
        composeRule.onNodeWithTag(TestTags.RoomsTitle).assertIsDisplayed()
    }
}
