// Geometry of the panel (meters, in the panel's own frame) and the names of every animator parameter / PhysBone prefix.
// The layout numbers MUST match Tools~/make_textures.py, which draws the plate they sit on
// (tests/test_unity_package.py in the repository checks that they do).
namespace CoyotePanel.Editor
{
    internal static class PanelLayout
    {
        // The viewer sits at -Z looking toward +Z ("camera" frame): +X is their right.
        public const float PW = 0.50f, PH = 0.34f;
        public const float ROW_A = 0.075f, ROW_B = -0.015f, ROW_F = -0.105f;
        public const float BAR_X0 = -0.12f, BAR_X1 = 0.08f;
        public const float MINUS_X = -0.155f, PLUS_X = 0.115f;
        public static readonly float[] DIG_X = { 0.165f, 0.195f, 0.225f };
        public static readonly float[] FDIG_X = { -0.045f, -0.015f, 0.015f };   // hundreds, tens, ones (ones is always 0)
        public const float CELL_W = 0.028f, CELL_H = 0.044f;
        public const float BTN_DN_X = -0.13f, BTN_UP_X = 0.14f;

        public const float Z_FACE = -0.0015f;      // digits almost flush with the plate (less parallax)
        public const float RELIEF_D = 0.003f;      // height of the gold reliefs (-/+ and arrows)
        public const float Z_RELIEF = -RELIEF_D / 2f;
        public const float PRESS_DEPTH = 0.0022f;  // how far a relief sinks when clicked
        public const float PRESS_SCALE = 0.88f;    // and how much it shrinks
        public const float Z_PB = -0.012f;         // PhysBones (grips and buttons) slightly in front of the plate
        public const float KNOB_W = 0.016f, KNOB_H = 0.044f, KNOB_D = 0.022f;   // the grabbable grip
        public const float NEEDLE_W = 0.004f, NEEDLE_H = 0.056f, NEEDLE_D = 0.010f; // thin value marker (not grabbable)
        public const float Z_NEEDLE = -0.007f;
        public const float BODY_D = 0.034f;

        // PhysBones: the grip starts at the minimum end of the bar and stretches to the maximum end
        public const float PB_REST = 0.012f;                                   // rest length
        public static readonly float PB_MAX_STRETCH = ((BAR_X1 - BAR_X0) - PB_REST) / PB_REST; // multiple of the length
        public const float PB_GRIP_RADIUS = 0.020f;    // grab radius of the grip
        public const float PB_BTN_RADIUS = 0.022f;     // grab radius of the -/+ buttons
        public const float PB_FBTN_RADIUS = 0.026f;    // grab radius of the frequency arrows
        public const float PB_BTN_STRETCH = 2f;        // buttons use the SAME kind of PhysBone as the grips
        public const float PB_PULL = 0.6f;             // force back to rest on release

        // _Stretch (0-1) -> 0-200: below 0.01 it does not update (avoids zeroing on grab); 0.97 already means 200
        public const float STR_SRC_MIN = 0.01f, STR_SRC_MAX = 0.97f;

        public const float REPEAT_DELAY = 0.35f;   // holding -/+ repeats every 0.35 s
    }

    internal static class Names
    {
        public const string RootName = "Coyote Panel";

        // OSC contract with the PC program (coyote-vrchat): CoyoteA/CoyoteB float 0-1 (= value/200),
        // CoyoteFreq int Hz (1-100, default 50), CoyoteStop bool.
        public const string P_A = "CoyoteA", P_B = "CoyoteB", P_FREQ = "CoyoteFreq", P_STOP = "CoyoteStop";
        // The numbers shown on the plate (synced, so everyone sees them)
        public const string P_VALA = "CoyotePad/ValA", P_VALB = "CoyotePad/ValB";
        public const string P_VALA_F = "CoyotePad/ValA_f", P_VALB_F = "CoyotePad/ValB_f", P_FREQ_F = "CoyotePad/Freq_f";
        // PhysBone prefixes (VRChat creates <prefix>_IsGrabbed, <prefix>_Stretch ...)
        public const string PFX_A = "CoyotePad/PbA", PFX_B = "CoyotePad/PbB";
        public const string PFX_AMINUS = "CoyotePad/AMinus", PFX_APLUS = "CoyotePad/APlus";
        public const string PFX_BMINUS = "CoyotePad/BMinus", PFX_BPLUS = "CoyotePad/BPlus";
        public const string PFX_UP = "CoyotePad/Up", PFX_DN = "CoyotePad/Dn";
        public const string P_GRABA = PFX_A + "_IsGrabbed", P_GRABB = PFX_B + "_IsGrabbed";
        public const string P_STRA = PFX_A + "_Stretch", P_STRB = PFX_B + "_Stretch";
        public const string P_AMINUS = PFX_AMINUS + "_IsGrabbed", P_APLUS = PFX_APLUS + "_IsGrabbed";
        public const string P_BMINUS = PFX_BMINUS + "_IsGrabbed", P_BPLUS = PFX_BPLUS + "_IsGrabbed";
        public const string P_UP = PFX_UP + "_IsGrabbed", P_DN = PFX_DN + "_IsGrabbed";
        public const string P_SHOW = "CoyotePad/Show", P_ANCHOR = "CoyotePad/Anchor", P_ZERO = "CoyotePad/Zero";
        public const string P_ONE = "CoyotePad/One";

        // click blendshapes on the static mesh
        public const string BS_AMINUS = "Press_AMinus", BS_APLUS = "Press_APlus", BS_BMINUS = "Press_BMinus", BS_BPLUS = "Press_BPlus";
        public const string BS_DN = "Press_Dn", BS_UP = "Press_Up";
    }
}
