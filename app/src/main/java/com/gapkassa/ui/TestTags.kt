package com.gapkassa.ui

object TestTags {
    const val AuthTitle = "auth_title"
    const val AuthGoogleButton = "auth_google_button"
    const val AuthMockGoogleButton = "auth_mock_google_button"

    const val RoomsTitle = "rooms_title"
    const val RoomsCreateFab = "rooms_create_fab"
    const val RoomsProfileButton = "rooms_profile_button"
    const val RoomDeleteAction = "room_delete_action"
    const val RoomDeleteConfirm = "room_delete_confirm"

    const val CreateRoomName = "create_room_name"
    const val CreateRoomDescription = "create_room_description"
    const val CreateRoomParticipants = "create_room_participants"
    const val CreateRoomAddParticipant = "create_room_add_participant"
    const val CreateRoomSubmit = "create_room_submit"

    const val ProfileLogout = "profile_logout"
    const val ProfileDeleteAccount = "profile_delete_account"
    const val ProfileDeleteConfirm = "profile_delete_confirm"

    fun roomCard(name: String): String = "room_card_$name"
    fun roomMenu(name: String): String = "room_menu_$name"
}
