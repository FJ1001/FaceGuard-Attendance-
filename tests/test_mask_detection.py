"""
Quick test to check mask detection settings and behavior.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from config.settings import (
    MASK_BLOCK_UNCERTAIN,
    ATTENDANCE_MASK_CHECK_ENABLED,
    MASK_ATTENDANCE_BLOCK_CONFIDENCE,
    MASK_YOLO_CONF_MASK,
    MASK_YOLO_CONF_NOMASK,
)

print("=" * 80)
print("🎭 MASK DETECTION CONFIGURATION CHECK")
print("=" * 80)

print("\n📋 Current Settings:\n")
print(f"  Mask Check Enabled: {ATTENDANCE_MASK_CHECK_ENABLED}")
print(f"  Block Uncertain: {MASK_BLOCK_UNCERTAIN}")
print(f"  Block Confidence Threshold: {MASK_ATTENDANCE_BLOCK_CONFIDENCE}")
print(f"  YOLO Mask Confidence: {MASK_YOLO_CONF_MASK}")
print(f"  YOLO No-Mask Confidence: {MASK_YOLO_CONF_NOMASK}")

print("\n" + "=" * 80)
print("✅ RECOMMENDED SETTINGS FOR NORMAL FACES:")
print("=" * 80)

print("\n  ✓ Mask Check Enabled: true (keep this)")
print("  ✗ Block Uncertain: FALSE (changed from true)")
print("  ✓ Block Confidence: 0.75 (high threshold)")
print("  ✓ YOLO Mask Confidence: 0.35 (higher = less false positives)")
print("  ✓ YOLO No-Mask Confidence: 0.25 (lower = easier to pass)")

print("\n" + "=" * 80)
print("📝 WHAT CHANGED:")
print("=" * 80)

print("\n  1. MASK_BLOCK_UNCERTAIN: true → false")
print("     → Now allows attendance even if detector is uncertain")
print("     → Only blocks when CONFIDENT a mask is present")

print("\n  2. MASK_YOLO_CONF_MASK: 0.22 → 0.35")
print("     → Higher confidence needed to detect a mask")
print("     → Reduces false positives")

print("\n  3. MASK_YOLO_CONF_NOMASK: 0.32 → 0.25")
print("     → Lower confidence needed to accept no mask")
print("     → Easier to pass the check")

print("\n" + "=" * 80)
print("🎯 EXPECTED BEHAVIOR NOW:")
print("=" * 80)

print("\n  ✅ Normal face without mask → ALLOWED")
print("  ⚠️  Uncertain/unclear → ALLOWED (was blocked before)")
print("  🚫 Clear mask detected → BLOCKED (with high confidence)")

print("\n" + "=" * 80)
print("💡 NEXT STEPS:")
print("=" * 80)

print("\n  1. Restart your Streamlit app:")
print("     streamlit run main.py")
print("\n  2. Try marking attendance again")
print("     → Should work now for normal faces")

print("\n  3. If still having issues, you can temporarily disable mask check:")
print("     In .env: ATTENDANCE_MASK_CHECK_ENABLED=false")

print("\n" + "=" * 80)
print("TEST COMPLETE")
print("=" * 80)
