import unittest
import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

class TestCalculatingScreens(unittest.TestCase):
    """Verifies that 10-second imaginary calculating screens with remaining time countdowns
    are properly implemented in Drone Topla and 3D Baskı Studio."""

    def setUp(self):
        with open(os.path.join(BASE_DIR, 'app.js'), 'r', encoding='utf-8') as f:
            self.app_js = f.read()

        with open(os.path.join(BASE_DIR, 'index.html'), 'r', encoding='utf-8') as f:
            self.index_html = f.read()

        with open(os.path.join(BASE_DIR, 'styles.css'), 'r', encoding='utf-8') as f:
            self.styles_css = f.read()

    def test_drone_topla_calculating_screen_exists(self):
        """Drone builder must trigger 10-second calculation simulation with countdown."""
        self.assertIn('startDroneCalculatingSimulation', self.app_js)
        self.assertIn('totalDuration = 10000', self.app_js)
        self.assertIn('drone-calc-countdown', self.app_js)
        self.assertIn('drone-calculating-screen', self.app_js)
        self.assertIn('drone-calc-progress', self.app_js)

        # Check countdown text and remaining time logic
        self.assertIn('Kalan Süre:', self.app_js)
        self.assertIn('Remaining Time:', self.app_js)
        self.assertIn('Math.ceil((totalDuration - elapsed) / 1000)', self.app_js)

        # Check that executeAutoBuild triggers the simulation
        self.assertIn('this.startDroneCalculatingSimulation(buildResult)', self.app_js)

    def test_drone_topla_cleanup_on_close(self):
        """Timer interval must be cleared on modal close or reset to prevent memory leaks."""
        self.assertIn('clearInterval(this._droneCalcInterval)', self.app_js)
        self.assertIn('_isDroneCalculating', self.app_js)

    def test_3d_studio_calculating_screen_exists(self):
        """3D Studio must have 10-second slicing simulation with countdown."""
        self.assertIn('start3DCalculatingSimulation', self.app_js)
        self.assertIn('viewport-calculating-overlay', self.index_html)
        self.assertIn('studio-calc-countdown', self.app_js)
        self.assertIn('studio-calc-progress', self.app_js)

        # Check countdown and layer slicing steps
        self.assertIn('Dilim Katmanı', self.app_js)
        self.assertIn('Dilimleniyor', self.app_js)

    def test_3d_studio_presets_and_recalculate(self):
        """3D Studio must have sample model presets and recalculate actions."""
        self.assertIn('load3DSamplePreset', self.app_js)
        self.assertIn('trigger3DRecalculate', self.app_js)
        self.assertIn("load3DSamplePreset('gopro_mount')", self.index_html)
        self.assertIn("load3DSamplePreset('motor_guard')", self.index_html)
        self.assertIn('trigger3DRecalculate()', self.index_html)

    def test_css_styles_exist(self):
        """Styles must include calculating screen, radar, laser beam, and timer banner."""
        self.assertIn('.calculating-screen-container', self.styles_css)
        self.assertIn('.studio-3d-theme', self.styles_css)
        self.assertIn('.calculating-timer-banner', self.styles_css)
        self.assertIn('.calculating-timer-seconds', self.styles_css)
        self.assertIn('.calculating-progress-fill', self.styles_css)
        self.assertIn('.calculating-slicer-laser', self.styles_css)
        self.assertIn('#viewport-calculating-overlay', self.styles_css)


if __name__ == '__main__':
    unittest.main()
