// Works out where the palm faces and where the fingers point, so the panel can be held in the hand.
// Nothing here is specific to one avatar: it reads the humanoid skeleton (or fixed hand-bone axes you provide).
using UnityEngine;

namespace CoyotePanel.Editor
{
    public struct HandFrame
    {
        public Transform hand;
        public Vector3 palm;    // unit, world space: out of the palm
        public Vector3 along;   // unit: from the wrist toward the fingers
        public Vector3 up;      // unit: toward the thumb side (the panel's "up" so its text is not upside down)
        public string note;     // how it was derived; goes to the log

        public static HumanBodyBones HandBone(PanelHand h) { return h == PanelHand.Left ? HumanBodyBones.LeftHand : HumanBodyBones.RightHand; }

        // "up" = thumb side. For a left hand up = along x palm; the right hand is the mirror image.
        static Vector3 ThumbUp(Vector3 along, Vector3 palm, bool left)
        {
            return (left ? Vector3.Cross(along, palm) : Vector3.Cross(palm, along)).normalized;
        }

        public static HandFrame Compute(Animator animator, CoyotePanelOptions o)
        {
            bool left = o.hand == PanelHand.Left;
            var hand = animator.GetBoneTransform(HandBone(o.hand));
            if (hand == null) throw new System.Exception("[CoyotePanel] the avatar has no " + HandBone(o.hand) + " bone (it needs a Humanoid rig)");
            var f = new HandFrame { hand = hand };

            if (o.frameMode == FrameMode.BoneAxes)
            {
                f.palm = (hand.rotation * CoyotePanelOptions.AxisVector(o.palmAxis)).normalized;
                var fingers = hand.rotation * CoyotePanelOptions.AxisVector(o.fingersAxis);
                f.along = Vector3.ProjectOnPlane(fingers, f.palm).normalized;
                if (f.along.sqrMagnitude < 0.5f)
                    throw new System.Exception("[CoyotePanel] the palm axis and the fingers axis are the same line; pick two different axes");
                f.up = ThumbUp(f.along, f.palm, left);
                f.note = "frame from hand-bone axes (palm " + o.palmAxis + ", fingers " + o.fingersAxis + ")";
                return f;
            }

            var lower = animator.GetBoneTransform(left ? HumanBodyBones.LeftLowerArm : HumanBodyBones.RightLowerArm);
            if (lower == null) throw new System.Exception("[CoyotePanel] the avatar has no lower-arm bone (it needs a Humanoid rig)");
            f.along = (hand.position - lower.position).normalized;

            var index = animator.GetBoneTransform(left ? HumanBodyBones.LeftIndexProximal : HumanBodyBones.RightIndexProximal);
            var little = animator.GetBoneTransform(left ? HumanBodyBones.LeftLittleProximal : HumanBodyBones.RightLittleProximal);
            Vector3 up = Vector3.zero;
            if (index != null && little != null)
                up = Vector3.ProjectOnPlane(index.position - little.position, f.along);   // little finger -> index finger = toward the thumb
            if (up.sqrMagnitude > 1e-8f)
            {
                f.up = up.normalized;
                f.palm = (left ? Vector3.Cross(f.up, f.along) : Vector3.Cross(f.along, f.up)).normalized;
                f.note = "frame from the skeleton (forearm direction + index/little finger bones)";
            }
            else
            {
                // No finger bones: assume the bind pose has the palms facing down (a T-pose).
                f.palm = Vector3.ProjectOnPlane(-animator.transform.up, f.along).normalized;
                f.up = ThumbUp(f.along, f.palm, left);
                f.note = "WARNING: no finger bones, so the frame assumes a T-pose with the palm facing down. Check the placement, or use hand-bone axes.";
            }
            if (Vector3.Dot(f.palm, animator.transform.up) > 0.5f)
                f.note += " | NOTE: the palm normal points upward in this bind pose; if the plate ends up on the back of the hand, tick 'Flip facing'.";
            return f;
        }

        /// <summary>World pose of the panel's "Content" object for these options.</summary>
        public void Place(Transform content, CoyotePanelOptions o, float avatarUnit)
        {
            Vector3 palmDir = o.flipFacing ? -palm : palm;
            Vector3 upDir = o.flipFacing ? -up : up;
            float unit = o.scale * avatarUnit;
            Vector3 pos = hand.position + (along * o.alongMeters + palmDir * o.outMeters) * unit;
            // The viewer looks along the panel's +Z, so +Z points INTO the palm and the plate faces out of it.
            Quaternion rot = Quaternion.LookRotation(-palmDir, upDir);
            rot = Quaternion.AngleAxis(o.rollDegrees, -palmDir) * rot;
            content.SetPositionAndRotation(pos, rot);
            content.localScale = Vector3.one * o.scale;
        }
    }
}
