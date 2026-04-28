"""
Quick test script to verify face recognition is working after re-enrollment.
"""
import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import numpy as np
from database.student_repository import StudentRepository
from face_recognition.recognition_engine_enhanced import EnhancedFaceRecognitionEngine
from config.settings import RECOGNITION_THRESHOLD, RECOGNITION_MARGIN

def test_recognition():
    print("=" * 80)
    print("🧪 FACE RECOGNITION TEST")
    print("=" * 80)
    
    # Load students
    student_repo = StudentRepository()
    students = student_repo.get_all_students()
    
    print(f"\n📊 Found {len(students)} active students")
    if not students:
        print("❌ No students found. Please register students first!")
        return False
    
    for s in students:
        print(f"   - {s['name']} ({s['roll_number']}) - {s['photo_count']} photos")
    
    # Load embeddings
    embeddings = student_repo.get_student_embeddings()
    print(f"\n🧬 Loaded {len(embeddings)} embeddings")
    
    if len(embeddings) < 2:
        print("❌ Need at least 2 embeddings to test")
        return False
    
    # Initialize engine
    engine = EnhancedFaceRecognitionEngine()
    
    # Test similarity between all pairs
    print("\n" + "=" * 80)
    print("📈 Similarity Matrix")
    print("=" * 80)
    
    # Group embeddings by student
    from collections import defaultdict
    by_student = defaultdict(list)
    for student_id, name, roll, emb in embeddings:
        by_student[name].append((student_id, roll, emb))
    
    student_names = list(by_student.keys())
    
    print("\nComparing students (average similarity):\n")
    
    all_same_person = []
    all_diff_person = []
    
    for i, name1 in enumerate(student_names):
        for j, name2 in enumerate(student_names):
            if i >= j:
                continue
            
            # Calculate average similarity between all embedding pairs
            sims = []
            for sid1, roll1, emb1 in by_student[name1]:
                for sid2, roll2, emb2 in by_student[name2]:
                    sim = engine.compare_faces(emb1, emb2)
                    sims.append(sim)
            
            avg_sim = np.mean(sims) if sims else 0
            min_sim = np.min(sims) if sims else 0
            max_sim = np.max(sims) if sims else 0
            
            is_same = (i == j)
            if is_same:
                all_same_person.append(avg_sim)
                status = "✅ SAME PERSON" if avg_sim > RECOGNITION_THRESHOLD else "⚠️  LOW"
            else:
                all_diff_person.append(avg_sim)
                status = "⚠️  TOO SIMILAR!" if avg_sim > RECOGNITION_THRESHOLD else "✅ GOOD"
            
            print(f"   {name1:15} vs {name2:15}: {avg_sim:.4f} (range: {min_sim:.4f}-{max_sim:.4f}) {status}")
    
    # Calculate separation metrics
    print("\n" + "=" * 80)
    print("📊 Separation Analysis")
    print("=" * 80)
    
    if all_same_person and all_diff_person:
        avg_same = np.mean(all_same_person)
        avg_diff = np.mean(all_diff_person)
        separation = avg_same - avg_diff
        
        print(f"\n   Average similarity (same person):  {avg_same:.4f}")
        print(f"   Average similarity (diff people):  {avg_diff:.4f}")
        print(f"   Separation margin:                 {separation:.4f}")
        
        print(f"\n   Recognition threshold:             {RECOGNITION_THRESHOLD}")
        print(f"   Required margin:                   {RECOGNITION_MARGIN}")
        
        # Verdict
        print("\n" + "=" * 80)
        if separation >= RECOGNITION_MARGIN and avg_same > RECOGNITION_THRESHOLD:
            print("✅ EXCELLENT! System should work well now.")
            print(f"\n   Same-person matches: ABOVE threshold ✓")
            print(f"   Different-person separation: ADEQUATE ✓")
            print(f"\n   You can now use the attendance system confidently!")
            result = True
        elif avg_same > RECOGNITION_THRESHOLD:
            print("⚠️  PARTIAL - System may work but could have issues.")
            print(f"\n   Same-person matches: ABOVE threshold ✓")
            print(f"   Different-person separation: TOO SMALL ✗")
            print(f"\n   Recommendations:")
            print(f"   - Re-register students with more varied photos")
            print(f"   - Try different angles and lighting")
            print(f"   - Consider lowering RECOGNITION_MARGIN to 0.05")
            result = False
        else:
            print("❌ NEEDS IMPROVEMENT - System will struggle.")
            print(f"\n   Same-person matches: BELOW threshold ✗")
            print(f"\n   Recommendations:")
            print(f"   - Re-register with higher quality photos")
            print(f"   - Use better lighting")
            print(f"   - Ensure face is clearly visible")
            print(f"   - Consider lowering RECOGNITION_THRESHOLD to 0.40")
            result = False
    else:
        print("❌ Cannot analyze - need more data")
        result = False
    
    print("\n" + "=" * 80)
    print("TEST COMPLETE")
    print("=" * 80)
    
    return result


if __name__ == "__main__":
    try:
        success = test_recognition()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(2)
