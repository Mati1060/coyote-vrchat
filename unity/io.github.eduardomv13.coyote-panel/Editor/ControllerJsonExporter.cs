// Developer tool: dumps the panel's FX controller (parameters, layers, states, transitions, parameter drivers, blend trees)
// to a JSON file that Tools~/simulate_controller.py replays offline. Used to check the logic without starting VRChat.
//   Tools > Coyote Panel > Developer > Export FX controller JSON
using System.Collections.Generic;
using System.Globalization;
using System.Text;
using nadena.dev.modular_avatar.core;
using UnityEditor;
using UnityEditor.Animations;
using UnityEngine;
using VRC.SDK3.Avatars.Components;

namespace CoyotePanel.Editor
{
    public static class ControllerJsonExporter
    {
        [MenuItem("Tools/Coyote Panel/Developer/Export FX controller JSON...", false, 100)]
        static void ExportMenu()
        {
            var avatar = CoyotePanelInstaller.FindAvatarRoot(Selection.activeGameObject);
            var panel = CoyotePanelInstaller.FindPanel(avatar);
            var ma = panel != null ? panel.GetComponent<ModularAvatarMergeAnimator>() : null;
            if (ma == null || !(ma.animator is AnimatorController))
            {
                EditorUtility.DisplayDialog("Coyote Panel", "Select an avatar that has the Coyote panel installed.", "OK");
                return;
            }
            var path = EditorUtility.SaveFilePanel("Export FX controller JSON", "", "ctrl.json", "json");
            if (string.IsNullOrEmpty(path)) return;
            System.IO.File.WriteAllText(path, Export((AnimatorController)ma.animator), new UTF8Encoding(false));
            Debug.Log("[CoyotePanel] controller exported to " + path);
        }

        static string Q(string s) { return "\"" + (s ?? "").Replace("\\", "\\\\").Replace("\"", "\\\"") + "\""; }
        static string N(float f) { return f.ToString("R", CultureInfo.InvariantCulture); }
        static string Bool(bool b) { return b ? "true" : "false"; }

        static string MotionJson(Motion m)
        {
            if (m == null) return "null";
            var clip = m as AnimationClip;
            if (clip != null)
            {
                var parts = new List<string>();
                foreach (var b in AnimationUtility.GetCurveBindings(clip))
                {
                    var c = AnimationUtility.GetEditorCurve(clip, b);
                    parts.Add("{\"path\":" + Q(b.path) + ",\"prop\":" + Q(b.propertyName) + ",\"v\":" + N(c.keys[0].value) + "}");
                }
                return "{\"clip\":" + Q(clip.name) + ",\"curves\":[" + string.Join(",", parts) + "]}";
            }
            var bt = (BlendTree)m;
            var ch = new List<string>();
            foreach (var c in bt.children)
                ch.Add("{\"thr\":" + N(c.threshold) + ",\"direct\":" + Q(c.directBlendParameter) + ",\"m\":" + MotionJson(c.motion) + "}");
            return "{\"tree\":" + Q(bt.name) + ",\"type\":" + Q(bt.blendType.ToString()) + ",\"param\":" + Q(bt.blendParameter) + ",\"children\":[" + string.Join(",", ch) + "]}";
        }

        public static string Export(AnimatorController ctrl)
        {
            var layers = new List<string>();
            foreach (var l in ctrl.layers)
            {
                var states = new List<string>();
                var def = l.stateMachine.defaultState;
                foreach (var cs in l.stateMachine.states)
                {
                    var s = cs.state;
                    var trs = new List<string>();
                    foreach (var t in s.transitions)
                    {
                        var cds = new List<string>();
                        foreach (var c in t.conditions)
                            cds.Add("{\"p\":" + Q(c.parameter) + ",\"mode\":" + Q(c.mode.ToString()) + ",\"thr\":" + N(c.threshold) + "}");
                        trs.Add("{\"to\":" + Q(t.destinationState.name) + ",\"exit\":" + Bool(t.hasExitTime) + ",\"exitTime\":" + N(t.exitTime) + ",\"conds\":[" + string.Join(",", cds) + "]}");
                    }
                    var drv = new List<string>();
                    foreach (var b in s.behaviours)
                    {
                        var d = b as VRCAvatarParameterDriver;
                        if (d == null) continue;
                        foreach (var p in d.parameters)
                            drv.Add("{\"type\":" + Q(p.type.ToString()) + ",\"name\":" + Q(p.name) + ",\"src\":" + Q(p.source) + ",\"value\":" + N(p.value) + ",\"conv\":" + Bool(p.convertRange) +
                                    ",\"sMin\":" + N(p.sourceMin) + ",\"sMax\":" + N(p.sourceMax) + ",\"dMin\":" + N(p.destMin) + ",\"dMax\":" + N(p.destMax) + ",\"local\":" + Bool(d.localOnly) + "}");
                    }
                    states.Add("{\"name\":" + Q(s.name) + ",\"default\":" + Bool(s == def) + ",\"wd\":" + Bool(s.writeDefaultValues) + ",\"motion\":" + MotionJson(s.motion) +
                               ",\"transitions\":[" + string.Join(",", trs) + "],\"drivers\":[" + string.Join(",", drv) + "]}");
                }
                layers.Add("{\"layer\":" + Q(l.name) + ",\"states\":[" + string.Join(",", states) + "]}");
            }
            var prms = new List<string>();
            foreach (var p in ctrl.parameters)
            {
                float d = p.type == AnimatorControllerParameterType.Int ? p.defaultInt : (p.type == AnimatorControllerParameterType.Bool ? (p.defaultBool ? 1 : 0) : p.defaultFloat);
                prms.Add("{\"n\":" + Q(p.name) + ",\"t\":" + Q(p.type.ToString()) + ",\"d\":" + N(d) + "}");
            }
            return "{\"params\":[" + string.Join(",", prms) + "],\"layers\":[" + string.Join(",", layers) + "]}";
        }
    }
}
