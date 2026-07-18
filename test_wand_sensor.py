"""Automated tests for Wand Controller, Coordinate Mapper, and integration."""

import unittest
import time
from collections import deque
from vision.coordinate_mapper import CoordinateMapper
from vision.wand_controller import WandController


class TestCoordinateMapper(unittest.TestCase):
    def test_coordinate_mapper_scaling_aspect_ratio_16_9_centered(self) -> None:
        """Test CoordinateMapper converts video to widget coordinates with correct scaling and offsets."""
        mapper = CoordinateMapper()
        # Video is 16:9 aspect ratio (1280x720)
        # Widget is 16:9 aspect ratio (640x360) - exact scale 0.5, offset 0
        mapper.set_sizes(video_width=1280, video_height=720, widget_width=640, widget_height=360)

        # Center point
        wx, wy = mapper.to_widget(640, 360)
        self.assertAlmostEqual(wx, 320.0)
        self.assertAlmostEqual(wy, 180.0)

        # Top-left point
        wx, wy = mapper.to_widget(0, 0)
        self.assertAlmostEqual(wx, 0.0)
        self.assertAlmostEqual(wy, 0.0)

        # Bottom-right point
        wx, wy = mapper.to_widget(1280, 720)
        self.assertAlmostEqual(wx, 640.0)
        self.assertAlmostEqual(wy, 360.0)

    def test_coordinate_mapper_letterbox(self) -> None:
        """Test letterbox scenario where widget has a different aspect ratio (e.g. 4:3, 640x480)."""
        mapper = CoordinateMapper()
        # Video 16:9 (1280x720), Widget 4:3 (640x480)
        # Scale is limited by width: scale = 640/1280 = 0.5
        # Scaled video height = 720 * 0.5 = 360
        # Vertical offset = (480 - 360) / 2 = 60
        mapper.set_sizes(video_width=1280, video_height=720, widget_width=640, widget_height=480)

        # Top-left of the video should be at widget (0, 60)
        wx, wy = mapper.to_widget(0, 0)
        self.assertAlmostEqual(wx, 0.0)
        self.assertAlmostEqual(wy, 60.0)

        # Bottom-right of the video should be at widget (640, 420)
        wx, wy = mapper.to_widget(1280, 720)
        self.assertAlmostEqual(wx, 640.0)
        self.assertAlmostEqual(wy, 420.0)

    def test_coordinate_mapper_inverse_mapping(self) -> None:
        """Test inverse mapping (to_video) returns original point coordinates."""
        mapper = CoordinateMapper()
        mapper.set_sizes(video_width=1920, video_height=1080, widget_width=800, widget_height=600)

        # Map forward, then map back
        rx, ry = 450.5, 820.2
        wx, wy = mapper.to_widget(rx, ry)
        rx2, ry2 = mapper.to_video(wx, wy)

        self.assertAlmostEqual(rx, rx2)
        self.assertAlmostEqual(ry, ry2)


class TestWandController(unittest.TestCase):
    def test_wand_controller_initialization(self) -> None:
        """Test WandController starts in a clean state."""
        wc = WandController()
        self.assertIsNone(wc.current_tip)
        self.assertEqual(len(wc.stroke), 0)
        self.assertFalse(wc.detected)
        self.assertEqual(wc.source, "none")

    def test_wand_controller_update_position(self) -> None:
        """Test update_position properly manages state, velocity, and stroke additions."""
        wc = WandController()
        wc.mapper.set_sizes(1280, 720, 640, 360)

        # Update position with detected hand
        wc.update_position(
            detected=True,
            tip=(100.0, 200.0),
            source="finger",
            confidence=0.85,
            velocity=50.0
        )

        self.assertTrue(wc.detected)
        self.assertEqual(wc.current_tip, (100.0, 200.0))
        self.assertEqual(wc.source, "finger")
        self.assertEqual(wc.confidence, 0.85)
        self.assertEqual(wc.velocity, 50.0)
        self.assertEqual(len(wc.stroke), 1)
        self.assertEqual(wc.stroke[0], (100.0, 200.0))

    def test_wand_controller_hover_jitter_filter(self) -> None:
        """Test that tiny hover jitter (low velocity) is ignored after initial stroke points are drawn."""
        wc = WandController()
        
        # Draw 4 quick points
        for i in range(4):
            wc.update_position(True, (10.0 * i, 10.0 * i), "finger", 0.9, 100.0)
        self.assertEqual(len(wc.stroke), 4)

        # Add a jittery hover point with low velocity (<= 35)
        wc.update_position(True, (45.0, 45.0), "finger", 0.9, 20.0)
        # Should NOT be added to the stroke
        self.assertEqual(len(wc.stroke), 4)

        # Add a deliberate movement point with high velocity (> 35)
        wc.update_position(True, (70.0, 70.0), "finger", 0.9, 80.0)
        # Should be added
        self.assertEqual(len(wc.stroke), 5)
        self.assertEqual(wc.stroke[-1], (70.0, 70.0))

    def test_wand_controller_stroke_timeout(self) -> None:
        """Test stroke is cleared after timeout (inactive period)."""
        wc = WandController()
        
        # Add a detected point
        wc.update_position(True, (100, 100), "finger", 0.9, 50.0)
        self.assertEqual(len(wc.stroke), 1)

        # Update with no detection, wait time less than timeout
        wc.update_position(False, None, "none", 0.0, 0.0, stroke_timeout_ms=500.0)
        # Stroke shouldn't clear immediately because time hasn't passed
        self.assertEqual(len(wc.stroke), 1)

        # Simulate sleep/time passing beyond timeout
        time.sleep(0.6)
        wc.update_position(False, None, "none", 0.0, 0.0, stroke_timeout_ms=500.0)
        # Stroke should clear now
        self.assertEqual(len(wc.stroke), 0)


if __name__ == "__main__":
    unittest.main()
