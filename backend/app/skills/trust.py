"""
Skill Trust Scorer.

Computes trust scores for skills based on:
- Test/validation results (35%)
- Static analysis safety (30%)
- License permissiveness (20%)
- Provenance/source reputation (15%)
"""


# License scoring map
LICENSE_SCORES = {
    "apache": 1.0,
    "apache-2.0": 1.0,
    "apache 2.0": 1.0,
    "mit": 1.0,
    "bsd": 0.9,
    "bsd-2-clause": 0.9,
    "bsd-3-clause": 0.9,
    "isc": 0.9,
    "mpl": 0.8,
    "mpl-2.0": 0.8,
    "lgpl": 0.7,
}


def compute_trust_score(
    license_text: str | None = None,
    code_validates: bool = False,
    has_blocked_imports: bool = False,
    is_anthropic_official: bool = False,
    has_python_code: bool = False,
) -> dict:
    """
    Compute a weighted trust score for a skill.

    Returns:
        {
            "trust_score": float (0-1),
            "breakdown": {
                "tests": float,
                "static": float,
                "license": float,
                "provenance": float,
            },
            "auto_install": bool,
            "recommendation": "auto" | "review" | "blocked",
        }
    """
    # Tests score (35%)
    if code_validates and has_python_code:
        tests_score = 1.0
    elif code_validates:
        tests_score = 0.7
    elif has_python_code:
        tests_score = 0.5
    else:
        tests_score = 0.3  # Instructional skills get base credit

    # Static analysis score (30%)
    if has_blocked_imports:
        static_score = 0.2
    elif has_python_code:
        static_score = 1.0
    else:
        static_score = 0.8  # No code = no risk

    # License score (20%)
    license_score = 0.4  # Default for unknown
    if license_text:
        license_lower = license_text.lower().strip()
        for key, score in LICENSE_SCORES.items():
            if key in license_lower:
                license_score = score
                break
        # "Complete terms in LICENSE.txt" pattern from Anthropic
        if "complete terms" in license_lower:
            license_score = 0.6  # Source-available, not OSS

    # Provenance score (15%)
    provenance_score = 1.0 if is_anthropic_official else 0.5

    # Weighted total
    trust_score = round(
        0.35 * tests_score
        + 0.30 * static_score
        + 0.20 * license_score
        + 0.15 * provenance_score,
        2,
    )

    # Clamp to [0, 1]
    trust_score = max(0.0, min(1.0, trust_score))

    # Recommendation
    if trust_score >= 0.8:
        recommendation = "auto"
    elif trust_score >= 0.5:
        recommendation = "review"
    else:
        recommendation = "blocked"

    return {
        "trust_score": trust_score,
        "breakdown": {
            "tests": round(tests_score, 2),
            "static": round(static_score, 2),
            "license": round(license_score, 2),
            "provenance": round(provenance_score, 2),
        },
        "auto_install": trust_score >= 0.8,
        "recommendation": recommendation,
    }
