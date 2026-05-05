package com.gapkassa.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.LocalViewModelStoreOwner
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.savedstate.SavedStateRegistryOwner
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.gapkassa.GapKassaApp
import com.gapkassa.ui.screens.AuthScreen
import com.gapkassa.ui.screens.CalendarScreen
import com.gapkassa.ui.screens.CreateRoomScreen
import com.gapkassa.ui.screens.PaymentDetailScreen
import com.gapkassa.ui.screens.ProfileScreen
import com.gapkassa.ui.screens.RoomScreen
import com.gapkassa.ui.screens.RoomsScreen
import com.gapkassa.ui.screens.ScheduleScreen
import com.gapkassa.ui.screens.StatsScreen
import com.gapkassa.viewmodel.AuthViewModel
import com.gapkassa.viewmodel.CalendarViewModel
import com.gapkassa.viewmodel.ProfileViewModel
import com.gapkassa.viewmodel.RoomViewModel
import com.gapkassa.viewmodel.RoomsViewModel
import com.gapkassa.viewmodel.StatsViewModel
import androidx.compose.runtime.collectAsState

/**
 * Central navigation graph that wires screens and their ViewModels.
 */
@Composable
fun AppNavGraph() {
    val navController = rememberNavController()
    val context = LocalContext.current
    val app = context.applicationContext as GapKassaApp
    val viewModelStoreOwner = LocalViewModelStoreOwner.current
        ?: error("No ViewModelStoreOwner was provided")
    val savedStateOwner = viewModelStoreOwner as? SavedStateRegistryOwner
        ?: error("ViewModelStoreOwner is not a SavedStateRegistryOwner")
    val factory = remember(viewModelStoreOwner) { AppViewModelFactory(app, savedStateOwner) }

    val authViewModel: AuthViewModel = viewModel(factory = factory)
    val roomsViewModel: RoomsViewModel = viewModel(factory = factory)
    val roomViewModel: RoomViewModel = viewModel(factory = factory)
    val calendarViewModel: CalendarViewModel = viewModel(factory = factory)
    val statsViewModel: StatsViewModel = viewModel(factory = factory)
    val profileViewModel: ProfileViewModel = viewModel(factory = factory)
    val hasStoredSession by app.authRepository.hasStoredSessionFlow.collectAsState(
        initial = app.authRepository.hasStoredSession
    )
    val startDestination = if (hasStoredSession) Routes.ROOMS else Routes.AUTH
    val navBackStackEntry by navController.currentBackStackEntryAsState()

    val navigateRoot: (String) -> Unit = { route ->
        navController.navigate(route) {
            popUpTo(startDestination) { inclusive = true }
            launchSingleTop = true
        }
    }
    val popBackOrNavigate: (String) -> Unit = { fallbackRoute ->
        if (!navController.popBackStack()) {
            navigateRoot(fallbackRoute)
        }
    }
    val goHome: () -> Unit = {
        navigateRoot(if (app.authRepository.hasStoredSession) Routes.ROOMS else Routes.AUTH)
    }

    LaunchedEffect(hasStoredSession) {
        val currentRoute = navBackStackEntry?.destination?.route
        when {
            !hasStoredSession && currentRoute != Routes.AUTH -> navigateRoot(Routes.AUTH)
            hasStoredSession && currentRoute == Routes.AUTH -> navigateRoot(Routes.ROOMS)
        }
    }

    NavHost(navController, startDestination = startDestination) {
        composable(Routes.AUTH) {
            AuthScreen(
                viewModel = authViewModel,
                onLoggedIn = {
                    app.onAuthenticated()
                    roomsViewModel.refreshRooms()
                    navigateRoot(Routes.ROOMS)
                }
            )
        }
        composable(Routes.ROOMS) {
            RoomsScreen(
                viewModel = roomsViewModel,
                onCreateRoom = { navController.navigate(Routes.CREATE_ROOM) },
                onRoomClick = { roomId -> navController.navigate("${Routes.ROOM_DETAIL}/$roomId") },
                onProfile = { navController.navigate(Routes.PROFILE) }
            )
        }
        composable(Routes.CREATE_ROOM) {
            CreateRoomScreen(
                viewModel = roomsViewModel,
                onCreated = {
                    navigateRoot(Routes.ROOMS)
                },
                onBack = { popBackOrNavigate(Routes.ROOMS) },
                onHome = goHome
            )
        }
        composable(
            route = "${Routes.ROOM_DETAIL}/{roomId}",
            arguments = listOf(navArgument("roomId") { type = NavType.StringType })
        ) { backStackEntry ->
            val roomId = backStackEntry.arguments?.getString("roomId") ?: return@composable
            RoomScreen(
                roomId = roomId,
                viewModel = roomViewModel,
                onOpenCalendar = { navController.navigate("${Routes.CALENDAR}/$roomId") },
                onOpenStats = { navController.navigate("${Routes.STATS}/$roomId") },
                onOpenSchedule = { navController.navigate("${Routes.SCHEDULE}/$roomId") },
                onPaymentClick = { paymentId -> navController.navigate("${Routes.PAYMENT_DETAIL}/$paymentId") },
                onBack = { popBackOrNavigate(Routes.ROOMS) },
                onHome = goHome
            )
        }
        composable(
            route = "${Routes.SCHEDULE}/{roomId}",
            arguments = listOf(navArgument("roomId") { type = NavType.StringType })
        ) { backStackEntry ->
            val roomId = backStackEntry.arguments?.getString("roomId") ?: return@composable
            ScheduleScreen(
                roomId = roomId,
                viewModel = roomViewModel,
                onBack = { popBackOrNavigate("${Routes.ROOM_DETAIL}/$roomId") },
                onHome = goHome
            )
        }
        composable(
            route = "${Routes.CALENDAR}/{roomId}",
            arguments = listOf(navArgument("roomId") { type = NavType.StringType })
        ) { backStackEntry ->
            val roomId = backStackEntry.arguments?.getString("roomId") ?: return@composable
            CalendarScreen(
                roomId = roomId,
                viewModel = calendarViewModel,
                onBack = { popBackOrNavigate("${Routes.ROOM_DETAIL}/$roomId") },
                onHome = goHome
            )
        }
        composable(
            route = "${Routes.PAYMENT_DETAIL}/{paymentId}",
            arguments = listOf(navArgument("paymentId") { type = NavType.StringType })
        ) { backStackEntry ->
            val paymentId = backStackEntry.arguments?.getString("paymentId") ?: return@composable
            PaymentDetailScreen(
                paymentId = paymentId,
                viewModel = roomViewModel,
                onBack = { popBackOrNavigate(Routes.ROOMS) },
                onHome = goHome
            )
        }
        composable(
            route = "${Routes.STATS}/{roomId}",
            arguments = listOf(navArgument("roomId") { type = NavType.StringType })
        ) { backStackEntry ->
            val roomId = backStackEntry.arguments?.getString("roomId") ?: return@composable
            StatsScreen(
                roomId = roomId,
                viewModel = statsViewModel,
                onBack = { popBackOrNavigate("${Routes.ROOM_DETAIL}/$roomId") },
                onHome = goHome
            )
        }
        composable(Routes.PROFILE) {
            ProfileScreen(
                viewModel = profileViewModel,
                onLogout = {
                    app.onSignedOut()
                    navigateRoot(Routes.AUTH)
                },
                onBack = { popBackOrNavigate(Routes.ROOMS) },
                onHome = goHome
            )
        }
    }
}
