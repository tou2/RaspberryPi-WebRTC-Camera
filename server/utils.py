import logging
from .ina219 import INA219

logger = logging.getLogger(__name__)

def get_battery_status():
    """Gets battery status from an INA219 sensor."""
    try:
        # The address 0x42 is taken from the manufacturer's example script.
        ina219 = INA219(addr=0x42)
        
        bus_voltage = ina219.getBusVoltage_V()
        current = ina219.getCurrent_mA()

        # The percentage calculation is based on the manufacturer's example.
        # It assumes a voltage range from 6V (0%) to 8.4V (100%).
        percentage = (bus_voltage - 6) / 2.4 * 100
        if percentage > 100:
            percentage = 100
        if percentage < 0:
            percentage = 0

        # Determine charging state based on current
        # Positive current means charging, negative means discharging.
        state = "unknown"
        if current > 50:  # Threshold to avoid noise
            state = "charging"
        elif current < -50:
            state = "discharging"
        else:
            state = "fully-charged" # Or idle

        return {"percentage": int(percentage), "state": state}

    except (FileNotFoundError, OSError) as e:
        logger.warning(f"Could not get battery level from INA219: {e}. Is I2C enabled and the sensor connected?")
        return None
    except Exception as e:
        logger.error(f"An unexpected error occurred while reading from INA219: {e}")
        return None
