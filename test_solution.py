import unittest
import subprocess

class TestDramatiqInstallation(unittest.TestCase):
    def test_install_dramatiq(self):
        result = subprocess.run(['pip', 'install', 'dramatiq'], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, f"Installation failed with output: {result.stderr}")
        self.assertIn('Successfully installed dramatiq', result.stdout, "Installation output does not indicate success")

if __name__ == '__main__':
    unittest.main()