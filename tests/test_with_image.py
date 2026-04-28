"""
Test recognition with an actual image file to see what's happening.
"""
import sys
from pathlib import Path

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

import cv2
import numpy as np
from database.student_repository import StudentRepository
from face_recognition.recognition_engine_enhanced import EnhancedFaceRecognitionEngine
from face_recognition.image_utils import detect_face_in_image

print("=" * 80)
print("🧪 IMAGE RECOGNITION TEST")
print("=" * 80)

# Ask for image path
print("\n📝 Enter the path to your test image:")
print("   (or drag and drop the image file here)")
image_path = input("\nImage path: ").strip().strip('"').strip("'")

if not image_path or not Path(image_path).exists():
    print(f"\n❌ File not found: {image_path}")
    sys.exit(1)

print(f"\n✅ Loading image: {image_path}")

# Load image
image = cv2.imread(image_path)
if image is None:
    print("❌ Could not load image. Check the file format.")
    sys.exit(1)

print(f"   Shape: {image.shape}")
print(f"   Type: {image.dtype}")

# Initialize
engine = EnhancedFaceRecognitionEngine()
student_repo = StudentRepository()

# Load student embeddings
embeddings = student_repo.get_student_embeddings()
print(f"\n📊 Loaded {len(embeddings)} student embeddings")

if not embeddings:
    print("❌ No student embeddings found. Re-register students first!")
    sys.exit(1)

# Try to detect face
print("\n" + "=" * 80)
print("Step 1: Face Detection")
print("=" * 80)

face_detected, message, face_image = detect_face_in_image(image)

if not face_detected or face_image is None:
    print(f"❌ Face detection failed: {message}")
    print("\nPossible reasons:")
    print("  - Face not visible in the image")
    print("  - Poor lighting")
    print("  - Image too small")
    print("  - Face at extreme angle")
    sys.exit(1)

print(f"✅ Face detected: {message}")
print(f"   Face image shape: {face_image.shape}")

# Generate embedding for test image
print("\n" + "=" * 80)
print("Step 2: Generate Embedding for Test Image")
print("=" * 80)

test_embedding = engine.generate_embedding(image, debug_mode=False)

if test_embedding is None:
    print("❌ Failed to generate embedding!")
    print("\nThis means the face was detected but embedding generation failed.")
    print("Check the logs for details.")
    sys.exit(1)

print(f"✅ Embedding generated successfully")
print(f"   Shape: {test_embedding.shape}")
print(f"   Norm: {np.linalg.norm(test_embedding):.6f}")
print(f"   Unique values: {len(np.unique(test_embedding))}")
print(f"   Min: {test_embedding.min():.6f}")
print(f"   Max: {test_embedding.max():.6f}")
print(f"   Mean: {test_embedding.mean():.6f}")
print(f"   Std: {test_embedding.std():.6f}")

# Compare with all student embeddings
print("\n" + "=" * 80)
print("Step 3: Compare with Student Embeddings")
print("=" * 80)

from collections import defaultdict
by_student = defaultdict(list)

print("\nSimilarity scores:")
for student_id, name, roll, student_emb in embeddings:
    similarity = engine.compare_faces(test_embedding, student_emb)
    by_student[name].append(similarity)
    print(f"   {name:15} ({roll}): {similarity:.4f}")

# Show best match per student
print("\n" + "=" * 80)
print("Step 4: Best Match Per Student")
print("=" * 80)

best_matches = []
for name, sims in by_student.items():
    best_sim = max(sims)
    best_matches.append((name, best_sim))
    print(f"   {name:15}: {best_sim:.4f}")

# Sort by similarity
best_matches.sort(key=lambda x: x[1], reverse=True)

print("\n" + "=" * 80)
print("Step 5: Recognition Result")
print("=" * 80)

if best_matches:
    best_name, best_sim = best_matches[0]
    second_sim = best_matches[1][1] if len(best_matches) > 1 else 0.0
    margin = best_sim - second_sim
    
    print(f"\n   Best match: {best_name}")
    print(f"   Similarity: {best_sim:.4f}")
    print(f"   Threshold: 0.45")
    print(f"   Margin vs second: {margin:.4f}")
    print(f"   Required margin: 0.06")
    
    print("\n   Decision:")
    if best_sim < 0.45:
        print(f"   ❌ REJECTED - Similarity {best_sim:.4f} below threshold 0.45")
        print(f"\n   WHY THIS IS HAPPENING:")
        print(f"   - Test image embedding is VERY different from registration embeddings")
        print(f"   - Possible reasons:")
        print(f"     1. Different person in test image")
        print(f"     2. Very different lighting/angle than registration")
        print(f"     3. Registration photos were poor quality")
        print(f"     4. Test photo quality is poor")
        
        # Show what the test embedding looks like compared to student embeddings
        print(f"\n   Embedding comparison:")
        print(f"   - Test embedding std: {test_embedding.std():.6f}")
        for student_id, name, roll, student_emb in embeddings:
            if name == best_name:
                print(f"   - {name}'s embedding std: {student_emb.std():.6f}")
                diff = np.abs(test_embedding - student_emb).mean()
                print(f"   - Mean absolute difference: {diff:.6f}")
                break
                
    elif len(best_matches) > 1 and margin < 0.06:
        print(f"   ⚠️  AMBIGUOUS - Margin {margin:.4f} below required 0.06")
        print(f"   - Too close to another student")
    else:
        print(f"   ✅ ACCEPTED - {best_name} recognized!")

print("\n" + "=" * 80)
print("💡 RECOMMENDATIONS:")
print("=" * 80)

if best_matches and best_matches[0][1] < 0.45:
    print("\n1. Check if the test image is the SAME PERSON as registered:")
    print("   - If YES: Re-register with photos similar to test conditions")
    print("   - If NO: Register the correct person")
    
    print("\n2. Registration photo tips:")
    print("   - Use same lighting as attendance scenario")
    print("   - Use same camera/distance")
    print("   - Include multiple angles")
    print("   - Good quality, not blurry")
    
    print("\n3. Test photo tips:")
    print("   - Face the camera directly")
    print("   - Good lighting")
    print("   - Clear, not blurry")
    print("   - Similar to registration conditions")

print("\n" + "=" * 80)
