"""The test for the Random binary sensor platform."""
import unittest

from homeassistant.setup import setup_component

from tests.async_mock import patch
from tests.common import get_test_home_assistant


class TestRandomSensor(unittest.TestCase):
    """Test the Random binary sensor."""

    def setup_method(self, method):
        """Set up things to be run when tests are started."""
        self.hass = get_test_home_assistant()

    def teardown_method(self, method):
        """Stop everything that was started."""
        self.hass.stop()

    @patch("homeassistant.components.random.binary_sensor.getrandbits", return_value=1)
    def test_random_binary_sensor_on(self, mocked):
        """Test the Random binary sensor."""
        config = {"binary_sensor": {"platform": "random", "name": "test"}}

        assert setup_component(self.hass, "binary_sensor", config)
        self.hass.block_till_done()

        state = self.hass.states.get("binary_sensor.test")

        assert state.state == "on"

    @patch(
        "homeassistant.components.random.binary_sensor.getrandbits", return_value=False
    )
    def test_random_binary_sensor_off(self, mocked):
        """Test the Random binary sensor."""
        config = {"binary_sensor": {"platform": "random", "name": "test"}}

        assert setup_component(self.hass, "binary_sensor", config)
        self.hass.block_till_done()

        state = self.hass.states.get("binary_sensor.test")

        assert state.state == "off"
