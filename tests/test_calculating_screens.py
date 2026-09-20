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

    def test_3d_studio_no_sample_presets_and_recalculate(self):
        """Sample model presets must be removed from the UI, and recalculate action present."""
        self.assertNotIn("load3DSamplePreset('gopro_mount')", self.index_html)
        self.assertNotIn("load3DSamplePreset('motor_guard')", self.index_html)
        self.assertNotIn('Örnek GoPro Mount', self.index_html)
        self.assertNotIn('Örnek Motor Koruma', self.index_html)
        self.assertIn('trigger3DRecalculate', self.app_js)
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
        self.assertIn('.studio-phases-pipeline', self.styles_css)
        self.assertIn('.studio-telemetry-row', self.styles_css)

    def test_3d_studio_confidentiality_no_p1p_or_bambu(self):
        """Confidentiality check: app.js must not mention P1P or Bambu Lab in 3D studio."""
        self.assertNotIn('p1p', self.app_js.lower())
        self.assertNotIn('bambu', self.app_js.lower())

    def test_3d_studio_no_scrollbar_layout(self):
        """Viewport calculating overlay must prevent any vertical scrollbars inside 420px canvas."""
        self.assertIn('overflow: hidden !important;', self.styles_css)
        self.assertIn('max-height: 420px', self.styles_css)

    def test_3d_studio_remove_model_and_reset_flow(self):
        """User can delete/remove loaded 3D model and return to dropzone upload screen."""
        self.assertIn('remove3DModel()', self.app_js)
        self.assertIn('remove3DModel', self.index_html)
        self.assertIn('btn-3d-delete-model', self.index_html)
        self.assertIn('btn-metrics-delete-model', self.index_html)
        self.assertIn('Modeli Sil', self.index_html)
        # Verify that previous hard-to-find 'Değiştir' button text is gone from controls
        self.assertNotIn('>Değiştir<', self.index_html)

        # Check remove3DModel resets mesh and reveals dropzone
        self.assertIn('this._3dScene.remove(this._currentMesh)', self.app_js)
        self.assertIn("this._3dConfig.filename = ''", self.app_js)
        self.assertIn("dropzone.style.display = 'flex'", self.app_js)

    def test_3d_studio_3mf_support_in_backend_and_frontend(self):
        """3MF files must be supported both in server upload whitelist and browser parser."""
        with open(os.path.join(BASE_DIR, 'server.py'), 'r', encoding='utf-8') as f:
            server_py = f.read()

        self.assertIn("'.3mf'", server_py)
        self.assertIn('parse3MFBuffer', self.app_js)
        self.assertIn('decompress3MFData', self.app_js)
        self.assertIn('parse3MFXml', self.app_js)
        self.assertIn("ext === '3mf'", self.app_js)

    def test_3d_studio_file_picker_strict_accept(self):
        """File picker dialog must only allow supported 3D models and reject wildcards."""
        self.assertIn('id="file-3d-input"', self.index_html)
        self.assertIn('.3mf', self.index_html)
        self.assertIn('.stl', self.index_html)
        self.assertIn('.step', self.index_html)
        self.assertNotIn('*/*', self.index_html)
        self.assertNotIn('application/octet-stream', self.index_html)

    def test_3d_studio_no_server_saved_toast_and_keep_slice_toast(self):
        """Must not show alarming 'sunucuya kaydedildi' toast, but preserve slicing completion toast."""
        self.assertNotIn('sunucuya kaydedildi', self.app_js)
        self.assertIn('3D Slicing ve Fiyat Analizi Tamamlandı!', self.app_js)


if __name__ == '__main__':
    unittest.main()

