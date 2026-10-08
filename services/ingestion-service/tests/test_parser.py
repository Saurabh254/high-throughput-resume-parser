import pytest
from app.core.pdf_extractor import PDFExtractor
from app.core.llm_parser import HeuristicExperienceParser

SAMPLE_RESUME_TEXT = """
Alex Morgan
alex.morgan@example.com | (555) 123-4567 | San Francisco, CA
linkedin.com/in/alexmorgan | github.com/alexmorgan

PROFESSIONAL EXPERIENCE

Senior Backend Engineer
Stripe | Jan 2021 - Present
• Architected high-throughput payment processing pipeline handling 25M daily transactions.
• Reduced p99 API latency from 250ms to 45ms (82% reduction) by introducing Redis tiered caching and connection pooling.
• Mentored a team of 6 engineers and led the migration to distributed event-driven microservices.
• Designed idempotent payment execution guaranteeing 99.999% uptime.

Software Engineer
Airbnb | Jun 2018 - Dec 2020
• Developed core search and booking microservices using Python, Go, and PostgreSQL.
• Increased booking search throughput by 45% by optimizing SQL queries and indexing.
• Led cross-functional collaboration with frontend teams to implement GraphQL schema.

EDUCATION
University of California, Berkeley
Bachelor of Science in Computer Science | 2018

TECHNICAL SKILLS
Python, Go, PostgreSQL, Redis, Docker, Kubernetes, AWS, Kafka, Microservices
"""

def test_clean_extracted_text():
    raw = "micro-\nservices and multi-\nthreading in modern systems"
    cleaned = PDFExtractor.clean_extracted_text(raw)
    assert "microservices" in cleaned
    assert "multithreading" in cleaned

def test_extract_metadata():
    meta = HeuristicExperienceParser.extract_metadata(SAMPLE_RESUME_TEXT)
    assert meta.full_name == "Alex Morgan"
    assert meta.email == "alex.morgan@example.com"
    assert "555" in (meta.phone or "")
    assert "linkedin.com/in/alexmorgan" in (meta.linkedin_url or "")
    assert "github.com/alexmorgan" in (meta.github_url or "")

def test_extract_quantified_metrics():
    metrics = HeuristicExperienceParser.extract_quantified_metrics(SAMPLE_RESUME_TEXT)
    metric_types = [m["metric_type"] for m in metrics]
    assert "scale" in metric_types or "percentage" in metric_types
    assert any("82%" in m["quantified_value"] for m in metrics)

def test_parse_profile_structure():
    profile = HeuristicExperienceParser.parse_profile(
        SAMPLE_RESUME_TEXT, filename="alex_morgan.pdf", file_hash="hash123"
    )
    assert profile.metadata.full_name == "Alex Morgan"
    assert len(profile.work_experiences) >= 2
    assert profile.total_years_experience >= 5.0
    
    # Check first role
    first_role = profile.work_experiences[0]
    assert first_role.seniority_level == "Senior"
    assert first_role.is_current is True
    assert len(first_role.impact_metrics) > 0
    assert "Redis" in first_role.technologies_used or "Python" in profile.core_skills
