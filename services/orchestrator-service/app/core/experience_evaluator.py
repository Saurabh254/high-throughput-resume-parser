import math
import os
import sys

try:
    from app.models.common import CandidateProfile
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../shared")))
    from models.common import CandidateProfile

SENIORITY_WEIGHTS = {
    "Intern": 1,
    "Junior": 2,
    "Mid": 3,
    "Senior": 4,
    "Lead": 5,
    "Staff": 5,
    "Principal": 6,
    "Manager": 5,
    "Director": 6,
    "Executive": 7,
}


class ExperienceEvaluator:
    @staticmethod
    def evaluate_candidate_experience(
        profile: CandidateProfile,
        min_years_required: float = 0.0,
        required_seniority: str | None = None,
    ) -> tuple[float, list[str]]:
        """
        Calculates an objective Experience Depth & Relevance Score (0.0 to 1.0)
        and produces human-readable highlights explaining the candidate's actual work experience.
        """
        highlights: list[str] = []
        score_components = []

        # 1. Tenure Duration Score (0.0 to 1.0)
        total_years = profile.total_years_experience
        if min_years_required > 0:
            if total_years >= min_years_required:
                tenure_score = 1.0
                excess = total_years - min_years_required
                highlights.append(
                    f"{total_years:.1f} years total experience (exceeds {min_years_required:.1f} yr requirement by {excess:.1f} yrs)"
                )
            else:
                # Proportional penalty
                ratio = total_years / min_years_required
                tenure_score = max(0.2, ratio * 0.9)
                highlights.append(
                    f"{total_years:.1f} years experience (below requested {min_years_required:.1f} yrs)"
                )
        else:
            # Baseline logarithmic tenure saturation
            tenure_score = min(1.0, 0.4 + 0.15 * math.log2(max(1.0, total_years + 1.0)))
            highlights.append(f"{total_years:.1f} years verified industry experience")
        score_components.append((tenure_score, 0.35))  # 35% weight

        # 2. Seniority & Trajectory Score (0.0 to 1.0)
        seniority_score = 0.6  # default baseline
        experiences = profile.work_experiences

        if experiences:
            latest_role = experiences[0]
            latest_level = latest_role.seniority_level or "Mid"
            latest_val = SENIORITY_WEIGHTS.get(latest_level, 3)

            if required_seniority:
                target_val = SENIORITY_WEIGHTS.get(required_seniority, 4)
                if latest_val >= target_val:
                    seniority_score = 1.0
                    highlights.append(
                        f"Role alignment: Current seniority '{latest_level}' matches or exceeds '{required_seniority}'"
                    )
                elif latest_val == target_val - 1:
                    seniority_score = 0.75
                    highlights.append(
                        f"Close seniority fit: '{latest_level}' (near target '{required_seniority}')"
                    )
                else:
                    seniority_score = 0.4
                    highlights.append(
                        f"Seniority gap: '{latest_level}' vs target '{required_seniority}'"
                    )
            else:
                # Progression reward (did candidate move up in seniority?)
                seniority_levels = [
                    SENIORITY_WEIGHTS.get(e.seniority_level, 3)
                    for e in reversed(experiences)
                ]
                is_upward = all(
                    earlier <= later
                    for earlier, later in zip(seniority_levels, seniority_levels[1:])
                )
                if is_upward and len(experiences) > 1:
                    seniority_score = 0.95
                    highlights.append(
                        f"Strong upward career trajectory across {len(experiences)} roles"
                    )
                else:
                    seniority_score = 0.8
                    highlights.append(
                        f"Latest role: {latest_role.job_title} ({latest_level}) at {latest_role.company}"
                    )
        score_components.append((seniority_score, 0.35))  # 35% weight

        # 3. Quantified STAR Impact & Accomplishments Score (0.0 to 1.0)
        total_impact_metrics = 0
        impact_types = set()
        for e in experiences:
            metrics = e.impact_metrics or []
            total_impact_metrics += len(metrics)
            for m in metrics:
                impact_types.add(m.get("metric_type", "general"))

        if total_impact_metrics >= 3:
            impact_score = 1.0
            highlights.append(
                f"High-impact contributor: {total_impact_metrics} quantified achievements ({', '.join(impact_types)})"
            )
        elif total_impact_metrics >= 1:
            impact_score = 0.75
            highlights.append(
                f"Demonstrated impact: {total_impact_metrics} quantified achievements documented"
            )
        else:
            impact_score = 0.35
            highlights.append(
                "Limited quantified impact metrics documented in experience narrative"
            )
        score_components.append((impact_score, 0.30))  # 30% weight

        # Calculate final weighted depth score
        final_depth_score = sum(val * weight for val, weight in score_components)
        return round(final_depth_score, 4), highlights
