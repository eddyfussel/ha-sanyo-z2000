"""Constants for the Sanyo PLV-Z2000 integration."""

DOMAIN = "sanyo_z2000"

# RS232 line parameters per Sanyo PLV-Z2000 spec §2
BAUD_RATE = 19200
BYTE_SIZE = 8
PARITY = "N"
STOP_BITS = 1

POLL_INTERVAL_SECONDS = 10
COMMAND_DELAY_SECONDS = 0.5  # minimum gap between pipelined commands (spec §4.5)
RESPONSE_TIMEOUT_SECONDS = 2.0

# After a user-issued command, the projector may keep reporting the OLD value
# for several seconds (spec §4.11: 5s for input switching, ~7s after power-on
# from standby). During this window we trust the user's intent over the
# coordinator's reading to avoid the "click HDMI 2 → flips to HDMI 1 → back
# to HDMI 2" flicker. Generous default of 12s covers both cases.
USER_INTENT_GRACE_SECONDS = 12.0

# ── Functional execution commands ─────────────────────────────────────────────

CMD_POWER_ON = b"C00\r"
CMD_POWER_OFF_QUICK = b"C01\r"
CMD_POWER_OFF_STANDBY = b"C02\r"

CMD_INPUT_VIDEO = b"C23\r"
CMD_INPUT_SVIDEO = b"C24\r"
CMD_INPUT_COMPONENT1 = b"C25\r"
CMD_INPUT_COMPONENT2 = b"C26\r"
CMD_INPUT_ANALOG_RGB = b"C50\r"
CMD_INPUT_HDMI1 = b"C53\r"
CMD_INPUT_HDMI2 = b"C54\r"

CMD_IMAGE_LIVING = b"C11\r"
CMD_IMAGE_CREATIVE_CINEMA = b"C12\r"
CMD_IMAGE_PURE_CINEMA = b"C13\r"
CMD_IMAGE_1 = b"C14\r"
CMD_IMAGE_2 = b"C15\r"
CMD_IMAGE_3 = b"C16\r"
CMD_IMAGE_4 = b"C17\r"
CMD_IMAGE_VIVID = b"C18\r"
CMD_IMAGE_BRILLIANT_CINEMA = b"C19\r"
CMD_IMAGE_DYNAMIC = b"C1A\r"
CMD_IMAGE_NATURAL = b"C1B\r"
CMD_IMAGE_5 = b"C36\r"
CMD_IMAGE_6 = b"C37\r"
CMD_IMAGE_7 = b"C38\r"

CMD_SCREEN_NORMAL = b"C0F\r"
CMD_SCREEN_FULL = b"C10\r"
CMD_SCREEN_ZOOM = b"C2C\r"
CMD_SCREEN_NATURAL_WIDE1 = b"C2D\r"
CMD_SCREEN_NATURAL_WIDE2 = b"C2E\r"
CMD_SCREEN_CAPTION_IN = b"C63\r"
CMD_SCREEN_FULL_THROUGH = b"C65\r"
CMD_SCREEN_NORMAL_THROUGH = b"C66\r"

# ── Status read commands ───────────────────────────────────────────────────────

CMD_READ_STATUS = b"CR0\r"
CMD_READ_INPUT = b"CR1\r"
CMD_READ_LAMP_TIME = b"CR3\r"
CMD_READ_TEMPERATURE = b"CR6\r"

# ── Status response map (CR0) ─────────────────────────────────────────────────

STATUS_MAP = {
    "00": "Power ON",
    "80": "Normal Standby",
    "40": "Processing Countdown",
    "20": "Processing Cooling Down",
    "10": "Power Failure",
    "28": "Cooling Down (Abnormal Temperature)",
    "88": "Standby (After Abnormal Temperature)",
    "24": "Processing Power Save / Cooling Down",
    "04": "Power Save",
    "21": "Cooling Down (Lamp Failure)",
    "81": "Standby (After Lamp Failure)",
}

# Status codes for which the projector is considered "on" from the user's
# perspective: actively projecting OR warming up (countdown). Spec §8.3.
POWER_ON_STATUS_CODES = frozenset({"00", "40"})

# Kept for backwards compatibility with anything importing the old constant.
POWER_ON_STATUS = "00"

# ── Input response map (CR1) ──────────────────────────────────────────────────

INPUT_MAP = {
    "0": "Video",
    "1": "S-Video",
    "2": "Component 1",
    "3": "Component 2",
    "4": "HDMI 1",
    "5": "HDMI 2",
    "6": "Computer (Analog RGB)",
    "7": "Computer (Scart)",
}

INPUT_CMD_MAP = {
    "Video": CMD_INPUT_VIDEO,
    "S-Video": CMD_INPUT_SVIDEO,
    "Component 1": CMD_INPUT_COMPONENT1,
    "Component 2": CMD_INPUT_COMPONENT2,
    "HDMI 1": CMD_INPUT_HDMI1,
    "HDMI 2": CMD_INPUT_HDMI2,
    "Computer (Analog RGB)": CMD_INPUT_ANALOG_RGB,
    "Computer (Scart)": CMD_INPUT_ANALOG_RGB,  # Scart not available on all models
}

# ── Image mode command map ────────────────────────────────────────────────────

IMAGE_MODE_OPTIONS = [
    "Living",
    "Creative Cinema",
    "Pure Cinema",
    "Image 1",
    "Image 2",
    "Image 3",
    "Image 4",
    "Image 5",
    "Image 6",
    "Image 7",
    "Vivid",
    "Brilliant Cinema",
    "Dynamic",
    "Natural",
]

IMAGE_MODE_CMD_MAP = {
    "Living": CMD_IMAGE_LIVING,
    "Creative Cinema": CMD_IMAGE_CREATIVE_CINEMA,
    "Pure Cinema": CMD_IMAGE_PURE_CINEMA,
    "Image 1": CMD_IMAGE_1,
    "Image 2": CMD_IMAGE_2,
    "Image 3": CMD_IMAGE_3,
    "Image 4": CMD_IMAGE_4,
    "Image 5": CMD_IMAGE_5,
    "Image 6": CMD_IMAGE_6,
    "Image 7": CMD_IMAGE_7,
    "Vivid": CMD_IMAGE_VIVID,
    "Brilliant Cinema": CMD_IMAGE_BRILLIANT_CINEMA,
    "Dynamic": CMD_IMAGE_DYNAMIC,
    "Natural": CMD_IMAGE_NATURAL,
}

# ── Screen/zoom mode command map ──────────────────────────────────────────────

SCREEN_MODE_OPTIONS = [
    "Normal",
    "Full",
    "Zoom",
    "Natural Wide 1",
    "Natural Wide 2",
    "Caption IN",
    "Full Through",
    "Normal Through",
]

SCREEN_MODE_CMD_MAP = {
    "Normal": CMD_SCREEN_NORMAL,
    "Full": CMD_SCREEN_FULL,
    "Zoom": CMD_SCREEN_ZOOM,
    "Natural Wide 1": CMD_SCREEN_NATURAL_WIDE1,
    "Natural Wide 2": CMD_SCREEN_NATURAL_WIDE2,
    "Caption IN": CMD_SCREEN_CAPTION_IN,
    "Full Through": CMD_SCREEN_FULL_THROUGH,
    "Normal Through": CMD_SCREEN_NORMAL_THROUGH,
}
