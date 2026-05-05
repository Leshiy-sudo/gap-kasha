package com.gapkassa

import androidx.compose.ui.test.assertIsDisplayed
import androidx.compose.ui.test.onNodeWithTag
import androidx.compose.ui.test.performClick
import androidx.compose.ui.test.performScrollTo
import androidx.test.ext.junit.runners.AndroidJUnit4
import com.gapkassa.ui.TestTags
import org.junit.Test
import org.junit.runner.RunWith

@RunWith(AndroidJUnit4::class)
class DeleteAccountUiTest : UiFlowTestBase() {
    @Test
    fun deleteAccountFromProfileReturnsToAuth() {
        loginFresh()
        composeRule.onNodeWithTag(TestTags.RoomsProfileButton).performClick()
        waitForTag(TestTags.ProfileDeleteAccount)
        composeRule.onNodeWithTag(TestTags.ProfileDeleteAccount).performScrollTo().performClick()
        waitForTag(TestTags.ProfileDeleteConfirm)
        composeRule.onNodeWithTag(TestTags.ProfileDeleteConfirm).performClick()
        waitForTag(TestTags.AuthTitle)
        composeRule.onNodeWithTag(TestTags.AuthTitle).assertIsDisplayed()
    }
}
