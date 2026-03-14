package com.gapkassa.ui

import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.platform.LocalContext
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.gapkassa.GapKassaApp
import com.gapkassa.ui.screens.AuthScreen
import com.gapkassa.ui.screens.CalendarScreen
import com.gapkassa.ui.screens.CreateRoomScreen
import com.gapkassa.ui.screens.PaymentDetailScreen
import com.gapkassa.ui.screens.ProfileScreen
import com.gapkassa.ui.screens.RegisterScreen
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

/**
 * Central navigation graph that wires screens and their ViewModels.
 */
@Composable
fun AppNavGraph() {
    val navController = rememberNavController()
    val context = LocalContext.current
    val app = context.applicationContext as GapKassaApp
    val factory = remember { AppViewModelFactory(app) }

    val authViewModel: AuthViewModel = viewModel(factory = factory)
    val roomsViewModel: RoomsViewModel = viewModel(factory = factory)
    val roomViewModel: RoomViewModel = viewModel(factory = factory)
    val calendarViewModel: CalendarViewModel = viewModel(factory = factory)
    val statsViewModel: StatsViewModel = viewModel(factory = factory)
    val profileViewModel: ProfileViewModel = viewModel(factory = factory)
    val goHome: () -> Unit = {
        navController.navigate(Routes.ROOMS) {
            popUpTo(Routes.ROOMS) { inclusive = false }
            launchSingleTop = true
        }
    }

    NavHost(navController, startDestination = Routes.AUTH) {
        composable(Routes.AUTH) {
            AuthScreen(
                viewModel = authViewModel,
                onLoginSuccess = { navController.navigate(Routes.ROOMS) },
                onRegister = { navController.navigate(Routes.REGISTER) }
            )
        }
        composable(Routes.REGISTER) {
            RegisterScreen(
                viewModel = authViewModel,
                onRegisterSuccess = { navController.navigate(Routes.ROOMS) },
                onBack = { navController.popBackStack() },
                onHome = goHome
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
                    navController.navigate(Routes.ROOMS) {
                        popUpTo(Routes.CREATE_ROOM) { inclusive = true }
                        launchSingleTop = true
                    }
                },
                onBack = { navController.popBackStack() },
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
                onBack = { navController.popBackStack() },
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
                onBack = { navController.popBackStack() },
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
                onBack = { navController.popBackStack() },
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
                onBack = { navController.popBackStack() },
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
                onBack = { navController.popBackStack() },
                onHome = goHome
            )
        }
        composable(Routes.PROFILE) {
            ProfileScreen(
                viewModel = profileViewModel,
                onLogout = {
                    navController.navigate(Routes.AUTH) {
                        popUpTo(Routes.ROOMS) { inclusive = true }
                    }
                },
                onBack = { navController.popBackStack() },
                onHome = goHome
            )
        }
    }
}
