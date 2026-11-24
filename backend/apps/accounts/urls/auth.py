from django.urls import path

from apps.accounts import views

urlpatterns = [
    path("register/", views.RegisterView.as_view(), name="auth-register"),
    path("login/", views.LoginView.as_view(), name="auth-login"),
    path("google/", views.GoogleLoginView.as_view(), name="auth-google"),
    path("refresh/", views.RefreshView.as_view(), name="auth-refresh"),
    path("logout/", views.LogoutView.as_view(), name="auth-logout"),
    path("native/register/", views.NativeRegisterView.as_view(), name="auth-native-register"),
    path("native/login/", views.NativeLoginView.as_view(), name="auth-native-login"),
    path("native/refresh/", views.NativeRefreshView.as_view(), name="auth-native-refresh"),
    path("native/logout/", views.NativeLogoutView.as_view(), name="auth-native-logout"),
    path("me/", views.MeView.as_view(), name="auth-me"),
    path("me/export/", views.DataExportView.as_view(), name="auth-me-export"),
    path("me/delete/", views.DeleteAccountView.as_view(), name="auth-me-delete"),
    path("password/change/", views.PasswordChangeView.as_view(), name="auth-password-change"),
    path("password/reset/", views.PasswordResetRequestView.as_view(), name="auth-password-reset"),
    path(
        "password/reset/confirm/",
        views.PasswordResetConfirmView.as_view(),
        name="auth-password-reset-confirm",
    ),
]
