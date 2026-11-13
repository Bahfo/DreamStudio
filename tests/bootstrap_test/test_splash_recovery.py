"""
(C) COPYRIGHT 2026 EXcellent TechStacks - All Rights Reserved.

Tests for SplashController and RecoveryWindow.
"""

import pytest


class TestSplashController:
    """Tests for SplashController construction and timing contract."""

    def test_splash_creation(self, qapp):
        """SplashController can be constructed without showing."""
        from config.splash import SplashController

        splash = SplashController()

        assert splash is not None
        assert splash.is_visible is False
        assert hasattr(splash, "show")
        assert hasattr(splash, "close")
        assert hasattr(splash, "update_status")
        assert hasattr(splash, "set_step_count")

    def test_minimum_visible_duration_constant(self):
        """Splash enforces a five second minimum visible duration."""
        from config import splash as splash_module

        assert splash_module._MIN_VISIBLE_SECONDS == 5.0


class TestRecoveryWindow:
    """Tests for RecoveryWindow crash display."""

    def test_recovery_window_creation(self, qapp):
        """RecoveryWindow renders the supplied message."""
        from config.recovery import RecoveryWindow

        window = RecoveryWindow(message="Test error message")

        assert window._message == "Test error message"
        assert window.windowTitle() == "DreamStudio - Startup Error"
        window.deleteLater()

    def test_recovery_window_custom_details_and_actions(self, qapp):
        """Recovery actions are retained for the retry path."""
        from config.recovery import RecoveryWindow

        called = []
        window = RecoveryWindow(
            title="Custom Title",
            message="Boom",
            details="Traceback",
            recovery_actions=[("retry", lambda: called.append("retry"))],
        )

        assert window.windowTitle() == "Custom Title"
        assert window._details == "Traceback"
        assert window._recovery_actions
        window.deleteLater()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])