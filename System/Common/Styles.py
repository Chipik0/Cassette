from __future__ import annotations

def make_button_style(
        bg_color:          str,
        hover_color:       str,
        border:            str = None,
        rounding:          int = 13,
        deactivated_color: str = "#777777"
    ) -> str:
    
    base = f"""
        QPushButton {{
            background-color: {bg_color};
            color: {Colors.FontColor};
            padding: 0px 12px;
            border-radius: {rounding}px;
            outline: none;
            {f"border: {border};" if border else ""}
        }}

        QPushButton:hover {{
            background-color: {hover_color};
        }}

        QPushButton:disabled {{
            background-color: {deactivated_color};
            color: #dddddd;
        }}
    """

    return base.strip()

class Colors:
    class EffectMenu:
        Standard    = "#2d2e31"
        Hover       = "#28292b"
        Press       = "#252628"

    class Waveform:
        MainColor = "#5AFFFFFF"

    class MainMenu:
        Button             = "#333333"
        ButtonHover        = "#444444"

        SmallButton        = "#3a3a3a"
        SmallButtonHover   = "#4a4a4a"

    NothingAccent          = "#d6141f"
    NothingAccentHover     = "#c20808"
    NothingAccentPressed   = "#ba0505"

    TitleFontColor         = "#ffffff"
    FontColor              = "#dddddd"
    SubtleFontColor        = "#9d9d9d"

    NormalButton           = "#2b2b2b"
    NormalButtonSecond     = "#404040"

    Background             = "#1f1f1f"
    SecondaryBackground    = "#2b2b2b"
    ThirdBackground        = "#232323"

    GlassBorder            = "#404040"

    class Floating:
        Background          = "#2b2b2b"
        Border              = "#404040"

        ElementBackground   = "#343434"

    class Waveline:
        BeatColor           = "#6A6A6A"
        TrackNameColor      = "#bbbbbb"

class Roundings:
    Button          = 13
    Slider          = 5
    SliderHandle    = 3

    RmbMenu         = 13
    RmbMenuItem     = 10

    Selection       = 8

class Metrics:
    ElementHeight    = 40
    GlassBorderThick = 1.2

    SliderHeight    = 12

    CheckboxSize    = 17

    class Tracks:
        RulerHeight = 24
        RowHeight   = 40
        LabelWidth  = 40
        BoxHeight   = 32
        BoxSpacing  = 3

    class Waveform:
        Height      = 120

class Buttons:
    NothingStyledButton = make_button_style(
        Colors.NothingAccent,
        Colors.NothingAccentHover
    )

    NormalButton = make_button_style(
        Colors.NormalButton,
        Colors.NormalButtonSecond
    )

    NormalButtonWithBorder = make_button_style(
        Colors.NormalButton,
        Colors.NormalButtonSecond,
        f"{Metrics.GlassBorderThick}px solid {Colors.GlassBorder}"
    )

    NormalButtonWithBorderSlim = make_button_style(
        Colors.NormalButton,
        Colors.NormalButtonSecond,
        f"{Metrics.GlassBorderThick}px solid {Colors.GlassBorder}",
        10
    )

    class MainMenu:
        AccentButton = make_button_style(
            Colors.NothingAccent,
            Colors.NothingAccentHover,
            rounding          = 16,
            deactivated_color = Colors.NothingAccent
        )

        NormalButton = make_button_style(
            Colors.MainMenu.Button,
            Colors.MainMenu.ButtonHover,
            rounding          = 16,
            deactivated_color = Colors.MainMenu.Button
        )

        SmallButton = make_button_style(
            Colors.MainMenu.SmallButton,
            Colors.MainMenu.SmallButtonHover,
            rounding          = 11,
            deactivated_color = Colors.MainMenu.SmallButton
        )

    class Settings:
        CategoryInactiveButton = make_button_style(
            "transparent",
            Colors.NormalButtonSecond,
            rounding = 14
        )

        CategoryActiveButton = make_button_style(
            Colors.NothingAccent,
            Colors.NothingAccentHover,
            rounding = 14
        )

class Other:
    Transparent = "background-color: transparent;"

    StatusBar = f"""
        QLabel {{
            background-color: {Colors.SecondaryBackground};
            color: {Colors.FontColor};
            padding: 0px 8px;
            border-radius: {Roundings.Button}px;
            min-height: {Metrics.ElementHeight}px;
        }}
    """

    Font             = f"""color: {Colors.TitleFontColor};"""
    Label            = f"""color: {Colors.FontColor}; background-color: transparent; padding: 0; border: none;"""
    SecondFont       = f"""color: {Colors.SubtleFontColor};"""
    DescriptionLabel = f"""color: {Colors.SubtleFontColor}; padding: 0px; border: none;"""

class Controls:
    ContainerCard = f"""
        QFrame {{
            background-color: {Colors.SecondaryBackground};
            border-radius: 20px;
        }}
    """

    TrackCard = f"""
        QFrame {{
            background-color: {Colors.SecondaryBackground};
            border-radius: 24px;
        }}
    """

    TitleCard = f"""
        QFrame {{
            background-color: {Colors.Background};
            border-radius: 32px;
        }}
    """

    SelectorButton = f"""
        QPushButton#segmentedButton {{
            background: transparent;
        }}

        QPushButton#segmentedButton,
        QPushButton#segmentedButton:checked,
        QPushButton#segmentedButton:hover,
        QPushButton#segmentedButton:hover:checked {{
            background-color: transparent;
        }}
    """

    Selector = f"""
        QWidget {{
            background-color: transparent;
            border-radius: {Roundings.Button}px;
            border: 1.2px solid {Colors.GlassBorder};
        }}

        QPushButton#segmentedButton {{
            color: {Colors.FontColor};
            background-color: transparent;
            border: none;
            padding: 0;
            border-radius: {Roundings.Button - 2}px;
            outline: none;
        }}

        QPushButton#segmentedButton:hover {{
            background-color: {Colors.ThirdBackground};
        }}
    """

    FloatingTextBox = f"""
        background-color: {Colors.Floating.Background};
        color: #fff;
        padding: 0px 8px;
        border-radius: 13px;
        border: 1.2px solid {Colors.GlassBorder}
    """

    FloatingSearchTextBox = f"""
        background-color: transparent;
        color: #fff;
        padding: 0px 10px;
        border-radius: 16px;
        border: none
    """

    EffectSetupper = f"""
        QWidget {{background-color: {Colors.EffectMenu.Standard}; color: {Colors.FontColor}}}
        QLabel {{padding: 4px}}
        QCheckBox {{margin-left: 4px}}
    """

    SliderBackground = f"""
        QWidget {{
            background-color: transparent;
            border-radius: {Roundings.Button}px;
            border: 1.35px solid {Colors.GlassBorder};
        }}
        """

    Slider = f"""
        QSlider {{
            border: none;
        }}

        QSlider::groove:horizontal {{
            height: {Metrics.SliderHeight}px;
            background: {Colors.EffectMenu.Hover};
            border: 1px solid #555;
            border-radius: {Roundings.Slider}px;
        }}

        QSlider::sub-page:horizontal {{
            background: {Colors.NothingAccent};
            border: none;
            border-radius: {Roundings.Slider}px;
        }}

        QSlider::add-page:horizontal {{
            background: transparent;
            border: none;
        }}

        QSlider::handle:horizontal {{
            width: 0px;
            height: 0px;
            margin: 0px;
            border: none;
            background: transparent;
        }}
    """

    ValueControl = f"""
        DraggableValueControl {{
            background-color: {Colors.SecondaryBackground};
            border-radius: {Roundings.Button}px;
            border: {Metrics.GlassBorderThick}px solid {Colors.GlassBorder};
            min-height: {Metrics.ElementHeight}px;
        }}

        DraggableValueControl:hover {{
            background-color: {Colors.ThirdBackground};
        }}
    """

    CycleButton = f"""
        CycleButton {{
            background-color: {Colors.SecondaryBackground};
            border-radius: {Roundings.Button}px;
            border: {Metrics.GlassBorderThick}px solid {Colors.GlassBorder};
            min-height: {Metrics.ElementHeight}px;
        }}
        CycleButton:hover {{
            background-color: {Colors.ThirdBackground};
        }}
    """

    MiniWaveformPreview = f"""
        MiniWaveformPreview {{
            background-color: {Colors.SecondaryBackground};
            border-radius: {Roundings.Button}px;
            border: {Metrics.GlassBorderThick}px solid {Colors.GlassBorder};
            min-height: {Metrics.ElementHeight}px;
        }}
        MiniWaveformPreview:hover {{
            background-color: {Colors.ThirdBackground};
        }}
    """

class Menus:
    ContextMenu = f"""
        QMenu {{
            background-color: {Colors.EffectMenu.Standard};
            color: {Colors.FontColor};
            border: {Metrics.GlassBorderThick} solid {Colors.GlassBorder};
            border-radius: {Roundings.RmbMenu}px;
            padding: 3px;
        }}

        QMenu::item {{
            {Other.Transparent}
            padding: 4px 12px;
            margin: 2px;
            width:  150px;
            border-radius: {Roundings.RmbMenuItem}px;
        }}

        QMenu::item:selected {{
            background-color: {Colors.EffectMenu.Hover};
        }}

        QMenu::separator {{
            height: {Metrics.GlassBorderThick};
            background-color: {Colors.GlassBorder};
            margin: 3px 12px;
        }}
    """