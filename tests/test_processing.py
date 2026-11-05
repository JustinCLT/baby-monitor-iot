import unittest

from shared.processing import SensorSample, extract_features


def window(accel, audio, n=6, dt=0.25):
    return [
        SensorSample(i * dt, accel(i) if callable(accel) else accel, (0.0, 0.0, 0.0),
                     audio_level=audio(i) if callable(audio) else audio)
        for i in range(n)
    ]


class ProcessingTests(unittest.TestCase):
    def test_still_phone_on_back(self):
        f = extract_features(window((0.0, 0.0, 9.81), 0.02))
        self.assertAlmostEqual(f.motion_rms, 0.0, places=3)
        self.assertAlmostEqual(f.jerk_metric, 0.0, places=3)
        self.assertAlmostEqual(f.tilt_angle, 0.0, places=1)
        self.assertAlmostEqual(f.audio_rms, 0.02, places=3)
        self.assertLess(f.zcr, 0.1)

    def test_face_down_tilt(self):
        f = extract_features(window((1.5, 0.0, -9.6), 0.03))
        self.assertGreater(f.tilt_angle, 150.0)

    def test_quiet_noise_keeps_zcr_low(self):
        f = extract_features(window((0.0, 0.0, 9.81), lambda i: 0.028 if i % 2 else 0.016))
        self.assertLess(f.zcr, 0.1)

    def test_motion_and_crying_raise_features(self):
        f = extract_features(window(lambda i: (1.5 if i % 2 else -1.5, 0.5, 11.5),
                                    lambda i: 0.78 if i % 2 else 0.50))
        self.assertGreater(f.motion_rms, 1.5)
        self.assertGreater(f.jerk_metric, 5.0)
        self.assertGreater(f.audio_rms, 0.5)
        self.assertGreater(f.zcr, 0.6)
        self.assertGreater(f.spectral_centroid_approx, 2500.0)

    def test_need_multiple_samples(self):
        with self.assertRaises(ValueError):
            extract_features(window((0.0, 0.0, 9.81), 0.0, n=1))


if __name__ == "__main__":
    unittest.main()
