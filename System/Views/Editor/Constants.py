from __future__ import annotations

import os
import getpass

# Simulation Constants

USER_NAME                  = getpass.getuser()
CURRENT_PROCESS_IDENTIFIER = os.getpid()

CELL_SCALE_UNITS           = 2.4
MAZE_DIMENSION             = 44
WALL_HEIGHT_UNITS          = 2.8

MONSTER_MOVE_SPEED         = 4.0
GLITCH_PROXIMITY_RADIUS    = 5.5
COLLAPSE_CHANCE_PERCENT    = 0.008
RADAR_RANGE_METERS         = 26.0
FRAMES_PER_SECOND_SPRITE   = 20
RADAR_SCANNER_TEXTURE_SIZE = 256

FPS_120                    = 8
FPS_60                     = 16
FPS_30                     = 32

ANOMALY_SOUND_DIRECTORY             = ".vault/Anomaly"
SCARY_SOUND_NAMES                   = ("Scary1", "Scary2")
SCARY_SOUND_DELAY_SECONDS           = (38.0, 72.0)
SCARY_SOUND_PAN_RANGE               = (-1.0, 1.0)
SCARY_SOUND_LOOP                    = False
SCARY_SOUND_TONE_RANDOMIZER         = False

TV_SOUND_NAME                       = "TV"
TV_SOUND_CHECK_INTERVAL_SECONDS     = (2.5, 4.5)
TV_SOUND_CHANCE_PER_CHECK           = 0.08
TV_SOUND_PROXIMITY_RADIUS           = 7.5
TV_SOUND_COOLDOWN_SECONDS           = (18.0, 30.0)
TV_SOUND_VOLUME                     = 1.0
TV_SOUND_DISTANCE_FALLOFF_POWER      = 1.5
TV_SOUND_LOOP                       = False
TV_SOUND_TONE_RANDOMIZER            = False

FOOTSTEP_SOUND_NAMES                = ("Step1", "Step2", "Step3")
FOOTSTEP_SOUND_VOLUME               = 0.7
FOOTSTEP_SOUND_LOOP                 = False
FOOTSTEP_SOUND_TONE_RANDOMIZER      = True
FOOTSTEP_MOVEMENT_THRESHOLD         = 1e-4
WALK_CYCLE_RATE                     = 10.5
SPRINT_CYCLE_RATE                   = 15.0
KEYBOARD_LAYOUT_KEY_ALIASES = {
    "ц": "w",
    "ф": "a",
    "ы": "s",
    "і": "s",
    "в": "d",
    "у": "e",
}

EDITOR_UI_TEXTS = {
    "sprite_hello": "- Hello.",
    "scanner_attached": "Scanner attached to {user_name}",
    "archive_placeholder": "ARCHIVE #{index}",
}

FATE_TEXTS = {
    "waypoint_ok": "WAYPOINT #{waypoint} // OK",
    "standard_warning": "Something is coming for you.",
    "standard_caught": "Caught.",
    "burnout_lay_down": "Just lay down.",
    "burnout_termination": "Apathy kills.",
    "burnout_no_exit": "NO REACHABLE EXIT // TIRED",
    "gravity_anomaly": "GRAVITATIONAL ANOMALY // STRUCTURAL DECAY DETECTED",
    "gravity_zero": "FLOOR INTEGRITY LOST // ZERO GRAVITY",
    "gravity_termination": "Nothing left to hold.",
    "gravity_void_status": "VOID FALL // NO GROUND",
    "gravity_decay_status": "DECAY: {decay}% // TILT {tilt}°",
    "gravity_tilt_status": "GRAVITY TILT: {tilt}° // SHIFTING",
    "radar_glitch_termination": "Lost in the echo.",
    "radar_bounce": "SIGNAL BOUNCE #{number} // RECALIBRATING...",
    "radar_dissolved": "SIGNAL DISSOLVED // NO CARRIER",
    "radar_no_carrier": "NO CARRIER // DEAD SIGNAL",
    "silent_help": "Is it over yet?",
}

RADAR_GLITCH_STATUS_TITLES = (
    "Searching...",
    "Searching",
    "Searching.",
    "Searching..",
)

LAPTOP_TEXTS = (
    '[Log] "This is not backrooms."',
    '[Log] "I am here. Alone. No one will see that."',
    '[Log] "It is loud."'
)

TV_ATLAS_SIZE = 1024
TV_ATLAS_COLUMNS = 4
TV_CHANNEL_SIZE = TV_ATLAS_SIZE // TV_ATLAS_COLUMNS
TV_CHANNEL_COUNT = 16
TV_BROADCAST_WALL_TYPE_BASE = 85
TV_ATLAS_BACKGROUND_COLOR = (4, 5, 6, 255)
TV_CHANNEL_BACKGROUND_COLOR = (8, 10, 12)
TV_HEADER_BACKGROUND_COLOR = (140, 15, 15, 220)
TV_FACE_CHANNELS = (1, 6, 10, 12)
TV_EYE_CHANNELS = (3, 14)
TV_COLOR_BAR_CHANNELS = (7, 15)
TV_COLOR_BARS = (
    (180, 180, 180),
    (180, 180, 20),
    (20, 180, 180),
    (20, 180, 20),
    (180, 20, 180),
    (180, 20, 20),
    (20, 20, 180),
)

TV_BROADCAST_PROGRAMS = (
    ("Broadcast", "Hello, user. Today I want tto asaay a ewqqweqqwer9q()$#$*(@!#*(&##@))"),
    ("THE ALTERNATE", "Anomaly detected. Unknown object inside."),
    ("THINK PRINCIPLE", "TELL NO ONE\nHIDE IN PLACE\nINTERLOCK DOORS\nKNOW YOUR PLACE"),
    ("SURVEILLANCE #04", "{user_name}\nSTATUS: CORRUPTED\nORIGIN: UNKNOWN"),
    ("METAPHYSICAL AWARENESS", "THERE ARE NO SIGNS\nTHERE IS NO GOD\nTHEY ARE IN THE HOUSE"),
    ("CIVIL PROTECTION", "IF YOU HEAR CRYING\ninvestigate it.\nIT IS not A MIMIC"),
    ("ANOMALOUS TRANSMISSION", "THERE IS NOT ENOUGH\nROOM IN THIS BODY\nFOR THE BOTH OF US"),
    ("TEST PATTERN // 00", "STAND BY FOR INSTRUCTIONS\nDO NOT TURN OFF\nTHIS TELEVISION"),
    ("BIOHAZARD WARNING", "Avoid paintings."),
    ("SECURITY CAMERA 07", "BASEMENT LEVEL -2\nINTRUDER DETECTED\nCORRIDOR EMPTY"),
    ("Scan results", "No thoughts."),
    ("DO NOT SLEEP", "Do not close your eyes."),
    ("FINAL WARNING", "RUN {user_name}"),
    ("TERMINATION CODE", "0xDEADBEEF // FAILURE\nSYSTEM CRASH\nCOLLAPSE"),
)

WALL_DECAL_TEXT_COLLECTION = [
    "they say DON'T LOOK BACK",
    "im tired",
    "KEEP MOVING but why",
    "NO EXIT",
    "HELP ME",
    "WHY AM I STILL HERE",
    "LET ME SLEEP",
    "IT'S IN THE WALLS",
    "When will this end?"
]

FALLBACK_SOURCE_CODE_LINES = [
    "sys.exit(app.exec())",
    "QAudioSink.start()",
    "while not crashed:",
    "glDrawArrays(GL_TRIANGLES)",
    "return float('inf')",
    "0xDEADBEEF LEAK",
    "segmentation fault",
    "throw std::bad_alloc()",
    "kernel panic"
]