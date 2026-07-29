# Google Axion (C4A)

Google Axion is Google Cloud's custom Arm-based CPU, built on the Arm Neoverse V2
architecture. C4A is the Compute Engine instance family built on Axion. Neoverse V2 is
an Armv9 core, which means it carries the SVE2 vector extensions and the newer
scalar/vector instruction set that recent kernel libraries (KleidiAI, ACL, oneDNN's Arm
backend) target explicitly, rather than falling back to generic NEON code paths.

For an apples-to-apples migration benchmark, the matched x86 baseline should be a
Compute Engine instance family from the same generation and a comparable vCPU count
(for example a `c4-standard-16` against a `c4a-standard-16`), with pricing pulled live
rather than hardcoded, since on-demand and committed-use pricing both change over time.
