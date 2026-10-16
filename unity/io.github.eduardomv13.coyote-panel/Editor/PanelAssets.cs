// Meshes, materials and textures of the panel. Everything generated is written to a per-avatar folder under Assets/.
using System.Collections.Generic;
using UnityEditor;
using UnityEngine;
using static CoyotePanel.Editor.Names;
using static CoyotePanel.Editor.PanelLayout;

namespace CoyotePanel.Editor
{
    internal sealed class PanelAssets
    {
        public Mesh cube, quad, prism, statics;
        public Material matPlate, matDigit, matBody, matGold, matNeedle;

        readonly string dir;

        public PanelAssets(string outputDir) { dir = outputDir; }

        public void BuildAll()
        {
            cube = BuildCube();
            quad = BuildQuad();
            prism = BuildPrism();
            matPlate = UnlitMat("CoyotePlate", Tex("CoyotePlate"), 1f);
            matDigit = UnlitMat("CoyoteDigits", Tex("CoyoteDigits"), 1f / 11f);
            matBody = LitMat("CoyoteBody", new Color(0f, 0f, 0f, 1f));
            matGold = LitMat("CoyoteGold", new Color(0.90f, 0.68f, 0.20f, 1f));
            matNeedle = ColorMat("CoyoteNeedle", new Color(1f, 0.83f, 0.42f, 1f));
            // static mesh: body (black) + reliefs (gold, with click blendshapes) + plate = 1 renderer, 3 materials
            statics = BuildStaticMesh(cube, prism, quad);
        }

        // ---------------------------------------------------------------- textures
        // Folder of this package (or of the loose folder, if someone copied it into Assets/): the parent of our Editor/ folder.
        static string PackageRoot()
        {
            foreach (var guid in AssetDatabase.FindAssets("CoyotePanel.Editor t:AssemblyDefinitionAsset"))
            {
                var p = AssetDatabase.GUIDToAssetPath(guid);
                if (System.IO.Path.GetFileName(p) != "CoyotePanel.Editor.asmdef") continue;
                var editorDir = System.IO.Path.GetDirectoryName(p).Replace("\\", "/");
                return System.IO.Path.GetDirectoryName(editorDir).Replace("\\", "/");
            }
            throw new System.Exception("[CoyotePanel] cannot locate the package folder (CoyotePanel.Editor.asmdef)");
        }

        // The two PNGs ship inside the package with their import settings already in the .meta files.
        // We only look them up (the package folder is read-only when installed from git or as an immutable package).
        static Texture2D Tex(string name)
        {
            string path = PackageRoot() + "/Textures/" + name + ".png";
            if (AssetDatabase.LoadAssetAtPath<Texture2D>(path) == null)
                throw new System.Exception("[CoyotePanel] texture " + path + " not found - is the package intact?");
            var imp = AssetImporter.GetAtPath(path) as TextureImporter;
            if (imp != null && NeedsTextureFix(imp))
            {
                if (path.StartsWith("Assets/"))
                {
                    imp.textureType = TextureImporterType.Default;
                    imp.mipmapEnabled = false;
                    imp.wrapMode = TextureWrapMode.Clamp;
                    imp.filterMode = FilterMode.Bilinear;
                    imp.maxTextureSize = 2048;
                    imp.npotScale = TextureImporterNPOTScale.None;
                    imp.textureCompression = TextureImporterCompression.Uncompressed;
                    imp.alphaIsTransparency = false;
                    imp.SaveAndReimport();
                }
                else
                {
                    Debug.LogWarning("[CoyotePanel] " + path + " has unexpected import settings and the package is read-only; the digits may look blurry. Re-import the package.");
                }
            }
            return AssetDatabase.LoadAssetAtPath<Texture2D>(path);
        }

        static bool NeedsTextureFix(TextureImporter imp)
        {
            return imp.mipmapEnabled || imp.wrapMode != TextureWrapMode.Clamp || imp.npotScale != TextureImporterNPOTScale.None
                || imp.textureCompression != TextureImporterCompression.Uncompressed || imp.filterMode != FilterMode.Bilinear;
        }

        // ---------------------------------------------------------------- materials
        Material GetMat(string name, Shader shader)
        {
            string path = dir + "/" + name + ".mat";
            var m = AssetDatabase.LoadAssetAtPath<Material>(path);
            if (m == null)
            {
                m = new Material(shader);
                AssetDatabase.CreateAsset(m, path);
            }
            m.shader = shader;
            return m;
        }

        // digits and plate: unlit (always readable); the digits' ST is animated in full (x,y,z,w)
        Material UnlitMat(string name, Texture2D tex, float scaleX)
        {
            var m = GetMat(name, Shader.Find("Unlit/Texture"));
            m.mainTexture = tex;
            m.mainTextureScale = new Vector2(scaleX, 1f);
            m.mainTextureOffset = Vector2.zero;
            EditorUtility.SetDirty(m);
            return m;
        }

        Material ColorMat(string name, Color c)
        {
            var m = GetMat(name, Shader.Find("Unlit/Color"));
            m.SetColor("_Color", c);
            EditorUtility.SetDirty(m);
            return m;
        }

        // body and reliefs: lit (give volume). lilToon if the project has it, the built-in Standard shader otherwise.
        Material LitMat(string name, Color c)
        {
            var sh = Shader.Find("lilToon");
            if (sh == null) sh = Shader.Find("Standard");
            var m = GetMat(name, sh);
            if (m.HasProperty("_Color")) m.SetColor("_Color", c);
            if (m.HasProperty("_LightMinLimit")) m.SetFloat("_LightMinLimit", 0.35f);
            if (m.HasProperty("_UseShadow")) m.SetFloat("_UseShadow", 0f);
            if (m.HasProperty("_Cull")) m.SetFloat("_Cull", 2f);
            EditorUtility.SetDirty(m);
            return m;
        }

        // ---------------------------------------------------------------- meshes
        Mesh Persist(Mesh m, string file)
        {
            // Re-create the asset: CopySerialized would leave the old mesh cached on the editor's GPU.
            string path = dir + "/" + file + ".asset";
            AssetDatabase.DeleteAsset(path);
            m.name = file;
            AssetDatabase.CreateAsset(m, path);
            EditorUtility.SetDirty(m);
            return m;
        }

        // unit quad visible from -Z (the viewer's side)
        Mesh BuildQuad()
        {
            var m = new Mesh();
            m.vertices = new[] { new Vector3(-.5f, -.5f, 0), new Vector3(.5f, -.5f, 0), new Vector3(-.5f, .5f, 0), new Vector3(.5f, .5f, 0) };
            m.uv = new[] { new Vector2(0, 0), new Vector2(1, 0), new Vector2(0, 1), new Vector2(1, 1) };
            m.normals = new[] { Vector3.back, Vector3.back, Vector3.back, Vector3.back };
            m.triangles = new[] { 0, 2, 1, 2, 3, 1 };
            m.RecalculateBounds();
            return Persist(m, "CoyoteQuad");
        }

        // centered unit cube, per-face normals
        Mesh BuildCube()
        {
            var v = new List<Vector3>(); var n = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            Vector3[] faces = { Vector3.right, Vector3.left, Vector3.up, Vector3.down, Vector3.forward, Vector3.back };
            foreach (var face in faces)
            {
                Vector3 u = (face == Vector3.up || face == Vector3.down) ? Vector3.right : Vector3.up;
                Vector3 w = Vector3.Cross(face, u);   // cross(u,w) = face  => front = outside
                int b = v.Count;
                v.Add(face * .5f - u * .5f - w * .5f); v.Add(face * .5f + u * .5f - w * .5f);
                v.Add(face * .5f + u * .5f + w * .5f); v.Add(face * .5f - u * .5f + w * .5f);
                for (int i = 0; i < 4; i++) n.Add(face);
                uv.Add(new Vector2(0, 0)); uv.Add(new Vector2(1, 0)); uv.Add(new Vector2(1, 1)); uv.Add(new Vector2(0, 1));
                t.Add(b); t.Add(b + 1); t.Add(b + 2); t.Add(b); t.Add(b + 2); t.Add(b + 3);
            }
            var m = new Mesh { vertices = v.ToArray(), normals = n.ToArray(), uv = uv.ToArray(), triangles = t.ToArray() };
            m.RecalculateBounds();
            return Persist(m, "CoyoteCube");
        }

        // unit triangular prism (tip toward +Y), depth z in [-0.5, 0.5]
        Mesh BuildPrism()
        {
            var A = new Vector3(0f, .5f, -.5f); var B = new Vector3(-.5f, -.5f, -.5f); var C = new Vector3(.5f, -.5f, -.5f);
            var A2 = new Vector3(0f, .5f, .5f); var B2 = new Vector3(-.5f, -.5f, .5f); var C2 = new Vector3(.5f, -.5f, .5f);
            var v = new List<Vector3>(); var n = new List<Vector3>(); var uv = new List<Vector2>(); var t = new List<int>();
            System.Action<Vector3, Vector3, Vector3> tri = delegate (Vector3 a, Vector3 b, Vector3 c)
            {
                var nrm = Vector3.Cross(b - a, c - a).normalized;
                var centroid = (a + b + c) / 3f;
                if (Vector3.Dot(nrm, centroid) < 0f) { var tmp = b; b = c; c = tmp; nrm = -nrm; }
                int i = v.Count;
                v.Add(a); v.Add(b); v.Add(c);
                n.Add(nrm); n.Add(nrm); n.Add(nrm);
                uv.Add(new Vector2(0, 0)); uv.Add(new Vector2(1, 0)); uv.Add(new Vector2(0, 1));
                t.Add(i); t.Add(i + 1); t.Add(i + 2);
            };
            tri(A, B, C); tri(A2, B2, C2);                       // front / back
            tri(A, B, B2); tri(A, B2, A2);                       // left side
            tri(A, C, C2); tri(A, C2, A2);                       // right side
            tri(B, C, C2); tri(B, C2, B2);                       // base
            var m = new Mesh { vertices = v.ToArray(), normals = n.ToArray(), uv = uv.ToArray(), triangles = t.ToArray() };
            m.RecalculateBounds();
            return Persist(m, "CoyotePrism");
        }

        // Merges everything into one mesh, keeping track of which vertices belong to each button,
        // and creates one click blendshape per button (sinks by PRESS_DEPTH and shrinks by PRESS_SCALE).
        Mesh BuildStaticMesh(Mesh cube, Mesh prism, Mesh quad)
        {
            var V = new List<Vector3>(); var N = new List<Vector3>(); var UV = new List<Vector2>();
            var subs = new[] { new List<int>(), new List<int>(), new List<int>() };
            var groups = new Dictionary<string, List<Vector2Int>>();
            var centers = new Dictionary<string, Vector3>();

            System.Func<Mesh, Vector3, Vector3, Vector3, int, Vector2Int> add = delegate (Mesh m, Vector3 pos, Vector3 euler, Vector3 scale, int sub)
            {
                var mat = Matrix4x4.TRS(pos, Quaternion.Euler(euler), scale);
                var nmat = mat.inverse.transpose;
                int start = V.Count;
                var mv = m.vertices; var mn = m.normals; var muv = m.uv; var mt = m.triangles;
                for (int i = 0; i < mv.Length; i++)
                {
                    V.Add(mat.MultiplyPoint3x4(mv[i]));
                    N.Add(nmat.MultiplyVector(mn[i]).normalized);
                    UV.Add(i < muv.Length ? muv[i] : Vector2.zero);
                }
                foreach (var t in mt) subs[sub].Add(start + t);
                return new Vector2Int(start, V.Count);
            };
            System.Action<string, Vector2Int, Vector3> group = delegate (string name, Vector2Int range, Vector3 center)
            {
                if (!groups.ContainsKey(name)) groups[name] = new List<Vector2Int>();
                groups[name].Add(range);
                centers[name] = center;
            };

            // submesh 0: body
            add(cube, new Vector3(0f, 0f, 0.0015f + BODY_D / 2f), Vector3.zero, new Vector3(PW + 0.016f, PH + 0.016f, BODY_D), 0);

            // submesh 1: gold reliefs (low: RELIEF_D)
            var bar = new Vector3(0.026f, 0.007f, RELIEF_D);
            var barV = new Vector3(0.007f, 0.026f, RELIEF_D);
            foreach (var row in new[] { new { y = ROW_A, m = BS_AMINUS, p = BS_APLUS }, new { y = ROW_B, m = BS_BMINUS, p = BS_BPLUS } })
            {
                var cm = new Vector3(MINUS_X, row.y, Z_RELIEF);
                var cp = new Vector3(PLUS_X, row.y, Z_RELIEF);
                group(row.m, add(cube, cm, Vector3.zero, bar, 1), cm);
                group(row.p, add(cube, cp, Vector3.zero, bar, 1), cp);
                group(row.p, add(cube, cp, Vector3.zero, barV, 1), cp);
            }
            var cu = new Vector3(BTN_UP_X, ROW_F + 0.00225f, Z_RELIEF);
            var cd = new Vector3(BTN_DN_X, ROW_F - 0.00225f, Z_RELIEF);
            group(BS_UP, add(prism, cu, Vector3.zero, new Vector3(0.030f, 0.0255f, RELIEF_D), 1), cu);
            group(BS_DN, add(prism, cd, new Vector3(0f, 0f, 180f), new Vector3(0.030f, 0.0255f, RELIEF_D), 1), cd);

            // submesh 2: the textured plate
            add(quad, Vector3.zero, Vector3.zero, new Vector3(PW, PH, 1f), 2);

            var mesh = new Mesh { name = "CoyoteStatic" };
            mesh.SetVertices(V);
            mesh.SetNormals(N);
            mesh.SetUVs(0, UV);
            mesh.subMeshCount = 3;
            for (int i = 0; i < 3; i++) mesh.SetTriangles(subs[i], i);

            foreach (var name in new[] { BS_AMINUS, BS_APLUS, BS_BMINUS, BS_BPLUS, BS_DN, BS_UP })
            {
                var deltas = new Vector3[V.Count];
                var c = centers[name];
                foreach (var r in groups[name])
                    for (int i = r.x; i < r.y; i++)
                    {
                        var p = V[i];
                        var pressed = new Vector3(c.x + (p.x - c.x) * PRESS_SCALE, c.y + (p.y - c.y) * PRESS_SCALE, p.z + PRESS_DEPTH);
                        deltas[i] = pressed - p;
                    }
                mesh.AddBlendShapeFrame(name, 100f, deltas, null, null);
            }
            mesh.RecalculateBounds();
            return Persist(mesh, "CoyoteStatic");
        }
    }
}
