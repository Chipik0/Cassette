from __future__ import annotations

from System.Devices.Base import (
    make_ranges,
    DeviceConfig
)

PHONE2A = DeviceConfig(
    code_name          = "PHONE2A",
    short_name         = "2a",
    full_name          = "Phone (2a)",
    hardware_codes     = ["A142", "A142P"],
    composer_code_name = "Pacman",
    glyph_indexes      = make_ranges(24, 1, 1),
    zone_indexes       = [[i] for i in range(26)],
    segments_map       = {"1": 24},
    visualization_map  = {
        "glyphs": {
            "1": {
                "svg":      "M-5.69,72.38 C12.45,28.38 40.50,10.20 65.68,5.18",
                "position": (20, 20),
                "segments": 24
            },
            "2": {
                "svg":      "M15.00,5.00 C15.00,40.00 15.00,75.00 15.00,110.00",
                "position": (225, 80)
            },
            "3": {
                "svg":      "M2.91,7.12 C10.00,15.00 20.00,30.00 35.89,40.28",
                "position": (20, 192)
            }
        },
        "size":      (255, 250),
        "thickness": 10
    },
    port_variants      = ["1", "2", "3a", "4a"],
    port_map           = {
        "PHONE4A": {
            "1": ["1"],
            "2": ["1"],
            "3": ["1"],

            "effects": {
                "segments": {
                    "1": ["1"]
                }
            }
        },

        "PHONE4B": {
            "1": ["1"],
            "2": ["1"],
            "3": ["1"],

            "effects": {
                "segments": {
                    "1": ["1"]
                }
            }
        },

        "PHONE3A": {
            "1": ["1"],
            "2": ["2"],
            "3": ["3"],

            "effects": {
                "segments": {
                    "1": ["1"]
                }
            }
        },

        "PHONE2": {
            "effects": {
                "segments": {
                    "1": ["4"]
                }
            },

            "1": {
                "mode":     "random",
                "variants": [
                    ["1", "2", "3"],
                    ["4", "5", "6", "7", "8", "9"],
                    ["1", "2"],
                    ["3"]
                ],
                "randomize": 1
            },

            "2": {
                "mode":     "random",
                "variants": [
                    ["4", "5", "6"],
                    ["7", "8", "9"],
                    ["4", "5", "6", "7", "8", "9"],
                    ["5", "8"]
                ],
                "randomize": 1
            },

            "3": {
                "mode":     "random",
                "variants": [
                    ["10"],
                    ["11"],
                    ["10", "11"]
                ],
                "randomize": 1
            }
        },

        "PHONE1": {
            "effects": {
                "segments": {
                    "1": ["7"]
                }
            },

            "1": {
                "mode":     "random",
                "variants": [
                    ["1"],
                    ["2"],
                    ["1", "2"]
                ],
                "randomize": 1
            },

            "2": {
                "mode":     "random",
                "variants": [
                    ["3", "5"],
                    ["4", "6"],
                    ["3", "4", "5", "6"],
                    ["3", "4", "5", "6", "7"]
                ],
                "randomize": 1
            },

            "3": {
                "mode":     "random",
                "variants": [
                    ["7"],
                    ["7", "8"]
                ],
                "randomize": 1
            }
        }
    }
)