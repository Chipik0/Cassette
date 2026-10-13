from __future__ import annotations

from System.Devices.Base import DeviceConfig

PHONE2 = DeviceConfig(
    code_name          = "PHONE2",
    short_name         = "2",
    full_name          = "Phone (2)",
    hardware_codes     = ["A065", "AIN065"],
    composer_code_name = "Pong",
    glyph_indexes      = [[0], [1], [2], list(range(3, 19)), [19], [20], [21], [22], [23], list(range(25, 33)), [24]],
    zone_indexes       = [[i] for i in range(24)] + [[32], [31], [30], [29], [28], [27], [26], [25], [24]],
    segments_map       = {"4": 16, "10": 8},
    visualization_map  = {
        "glyphs": {
            "1": {
                "svg":      "M4,47 V22 C4,10 13,4 23.5,4 C34,4 43,10 43,22",
                "position": (0, 0)
            },
            "2": {
                "svg":      "M34.5,1.5 V19.5 C34.5,25.5 31,31 25,34 C19.5,37 13,36.5 8,33",
                "position": (9, 45)
            },
            "3": {
                "svg":      "M37,3 L3,42",
                "position": (130, 10)
            },
            "4": {
                "svg":      "M4,4 C38,1 71,15 94,40",
                "position": (80, 90),
                "segments": 16
            },
            "5": {
                "svg":      "M49,-4.25 C31.5,3.25 16.5,15.75 4,32",
                "position": (0, 105)
            },
            "6": {
                "svg":      "M3,3 V44",
                "position": (0, 150)
            },
            "7": {
                "svg":      "M4,3 C30,30 65,42 95,39",
                "position": (3, 260)
            },
            "8": {
                "svg":      "M3,32 C20.5,23.25 38,10.75 49.25,-4.25",
                "position": (120, 262)
            },
            "9": {
                "svg":      "M3.5,4 V35",
                "position": (169, 195)
            },
            "10": {
                "svg":      "M4,3 V43",
                "position": (86, 320),
                "segments": 8
            },
            "11": {
                "svg":      "M3.99,3.11 L3.99,10.95",
                "position": (86, 371)
            }
        },
        "size":      (177, 385),
        "thickness": 6
    },
    port_variants      = ["1"],
    port_map           = {
        "PHONE1": {
            "1":  ["1"],
            "2":  ["1"],
            "3":  ["2"],
            "4":  ["3"],
            "5":  ["4"],
            "6":  ["4"],
            "7":  ["5"],
            "8":  ["6"],
            "9":  ["6"],
            "10": ["7"],
            "11": ["8"],

            "effects": {
                "segments": {
                    "4":  ["7"],
                    "10": ["7"]
                }
            }
        }
    }
)