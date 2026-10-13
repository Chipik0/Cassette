from __future__ import annotations

from System.Devices.Base import (
    make_ranges,
    DeviceConfig
)

PHONE3A = DeviceConfig(
    code_name          = "PHONE3A",
    short_name         = "3a",
    full_name          = "Phone (3a)",
    hardware_codes     = ["A059", "A059P"],
    composer_code_name = "Asteroids",
    glyph_indexes      = make_ranges(20, 11, 5),
    zone_indexes       = [[i] for i in range(36)],
    segments_map       = {"1": 20, "2": 11, "3": 5},
    visualization_map  = {
        "glyphs": {
            "1": {
                "svg":      "M-5.69,72.38 C12.45,28.38 40.50,10.20 65.68,5.18",
                "position": (20, 10),
                "segments": 20
            },
            "2": {
                "svg":      "M15.00,5.00 C32.00,40.00 32.00,75.00 15.00,110.00",
                "position": (210, 70),
                "segments": 11
            },
            "3": {
                "svg":      "M35.89,40.28 L2.91,7.12",
                "position": (20, 178),
                "segments": 5
            }
        },
        "size":      (250, 240),
        "thickness": 10
    },
    port_variants      = ["1", "2", "2a", "4a"],
    port_map           = {
        "PHONE2A": {
            "1": ["1"],
            "2": ["2"],
            "3": ["3"],

            "effects": {
                "segments": {
                    "1": ["1"],
                    "2": ["1"],
                    "3": ["1"]
                }
            }
        },

        "PHONE4B": {
            "1": ["1"],
            "2": ["1"],
            "3": ["1"],

            "effects": {
                "segments": {
                    "1": ["1"],
                    "2": ["1"],
                    "3": ["1"]
                }
            }
        },

        "PHONE1": {
            "1": {
                "mode":     "random",
                "variants": [
                    ["1", "2"],
                    ["3", "5"],
                    ["4", "6"]
                ]
            },

            "2": {
                "mode":     "random",
                "variants": [
                    ["3", "5"],
                    ["4", "6"],
                    ["3", "4", "5", "6"]
                ]
            },

            "3": {
                "mode":     "random",
                "variants": [
                    ["7"],
                    ["8"],
                    ["7", "8"]
                ]
            },

            "effects": {
                "segments": {
                    "1": ["7"],
                    "2": ["7"],
                    "3": ["7"]
                }
            }
        },

        "PHONE2": {
            "1": {
                "mode":       "random",
                "variants":   [
                    ["1", "2", "3"],
                    ["1", "2"],
                    ["3"]
                ],
                "randomizes": 1
            },

            "2": {
                "mode":       "random",
                "variants":   [
                    ["4", "5", "6", "7", "8", "9"],
                    ["5", "8"],
                    ["6", "9"],
                    ["4", "7"]
                ],
                "randomizes": 1
            },

            "3": {
                "mode":       "random",
                "variants":   [
                    ["10"],
                    ["11"],
                    ["10", "11"]
                ],
                "randomizes": 1
            },

            "effects": {
                "segments": {
                    "1": ["4"],
                    "2": ["4"],
                    "3": ["10"]
                }
            }
        },

        "PHONE4A": {
            "1": ["1"],
            "2": ["1"],
            "3": ["1"],

            "effects": {
                "segments": {
                    "1": ["1"],
                    "2": ["1"],
                    "3": ["1"]
                }
            }
        }
    }
)