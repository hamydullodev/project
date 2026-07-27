"""
Hybrid RAG application package.

WHY THIS FILE SETS ENVIRONMENT VARIABLES BEFORE ANYTHING ELSE
-------------------------------------------------------------------
This is the first code that runs for ANY `app.*` import (Python always
initializes a parent package before its submodules), which makes it the
one guaranteed place to set process-wide environment variables before any
native library that reads them gets loaded.

That matters because of a real, reproducible crash found while building
Milestone 6: on this project's macOS development machine, using both
`sentence-transformers`/`torch` (Milestone 5) and `faiss` (Milestone 6)
in the same process — loading real embeddings into a FAISS index and then
searching it — segfaulted (exit code 139), independent of which library
was imported first or how many vectors were involved. The root cause is a
well-known class of issue on macOS/Windows: both PyTorch and FAISS's pip
wheels bundle their OWN separate copy of the OpenMP runtime
(`libomp.dylib`), and when both get loaded and actually used for
multi-threaded work in one process, their thread pools can collide and
corrupt memory — this is not a bug in this project's code, but a binary-
packaging conflict between two otherwise-correct libraries.

Forcing every OpenMP/BLAS-using library to run single-threaded
eliminates the thread-pool collision entirely (single-threaded code can't
race with itself), verified fully reliable across repeated runs after
this fix — vs. failing consistently before it. The trade-off is real but
small at this project's scale: single-threaded embedding of ~1,300 chunks
took low tens of seconds in testing, an acceptable one-time indexing cost
for a local personal-scale legal corpus, in exchange for correctness.

These MUST be set via `os.environ` (not `torch.set_num_threads(1)` or
`faiss.omp_set_num_threads(1)` alone) because OpenMP reads its thread
count from the environment at the C-library level when the runtime
initializes — a call from Python via `torch.set_num_threads()` only
configures torch's own thread pool, not the separately-bundled OpenMP
runtime inside the faiss wheel (or vice-versa), so a Python-level-only
fix does not prevent the two runtimes from colliding.

`setdefault` (not direct assignment) is used so a user who has
deliberately configured their own threading environment (e.g. in a
Docker container with different constraints) is not silently overridden.
"""

import os

os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
