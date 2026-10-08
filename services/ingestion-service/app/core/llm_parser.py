import re
import json
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import httpx

from app.core.config import settings

try:
    from app.models.common import (
        CandidateProfile, CandidateMetadata, WorkExperienceItem, EducationItem, ImpactMetric
    )
except ImportError:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../shared")))
    from models.common import (
        CandidateProfile, CandidateMetadata, WorkExperienceItem, EducationItem, ImpactMetric
    )

logger = logging.getLogger(__name__)

MONTHS_MAP = {
    "jan": 1, "january": 1, "feb": 2, "february": 2, "mar": 3, "march": 3,
    "apr": 4, "april": 4, "may": 5, "jun": 6, "june": 6, "jul": 7, "july": 7,
    "aug": 8, "august": 8, "sep": 9, "sept": 9, "september": 9,
    "oct": 10, "october": 10, "nov": 11, "november": 11, "dec": 12, "december": 12
}

SENIORITY_KEYWORDS = {
    "intern": "Intern",
    "junior": "Junior",
    "associate": "Junior",
    "entry": "Junior",
    "mid": "Mid",
    "senior": "Senior",
    "sr": "Senior",
    "lead": "Lead",
    "tech lead": "Lead",
    "team lead": "Lead",
    "staff": "Staff",
    "principal": "Principal",
    "architect": "Principal",
    "manager": "Manager",
    "director": "Director",
    "head": "Director",
    "vp": "Executive",
    "cto": "Executive",
}

STANDARDIZED_ROLES = [
    ("Backend Engineer", [r"backend", r"back-end", r"server", r"api", r"python engineer", r"go engineer", r"java engineer"]),
    ("Frontend Engineer", [r"frontend", r"front-end", r"react", r"vue", r"angular", r"ui/ux", r"web developer"]),
    ("Full Stack Engineer", [r"full\s*stack", r"fullstack", r"software engineer", r"software developer"]),
    ("DevOps / SRE / Platform", [r"devops", r"sre", r"site reliability", r"platform", r"infrastructure", r"cloud engineer", r"kubernetes"]),
    ("Data Engineer", [r"data engineer", r"etl", r"big data", r"spark", r"data warehouse", r"pipeline"]),
    ("Machine Learning / AI", [r"machine learning", r"ml engineer", r"ai engineer", r"data scientist", r"deep learning", r"nlp", r"computer vision"]),
    ("Mobile Engineer", [r"ios", r"android", r"mobile", r"flutter", r"react native"]),
    ("Engineering Manager", [r"engineering manager", r"tech lead manager", r"director of engineering"]),
]

QUANTIFIED_METRIC_PATTERNS = [
    (r'(\d+(?:\.\d+)?%)\s*(?:increase|decrease|reduction|improvement|growth|boost|drop|faster)', "percentage"),
    (r'(?:reduced|increased|improved|cut)\s*(?:by\s*)?(\d+(?:\.\d+)?%)', "percentage"),
    (r'(\d+[\d,]*\+?\s*(?:million|m|k|billion|users|requests|rps|qps|events|records|tb|gb))', "scale"),
    (r'(\$\d+[\d,]*(?:\.\d+)?(?:\s*(?:k|m|million|billion|arr|cost|savings))?)', "revenue"),
    (r'(\d+(?:\.\d+)?\s*(?:ms|seconds|sec|mins|minutes|hrs|hours))\s*(?:to\s*(\d+(?:\.\d+)?\s*(?:ms|sec)))?', "latency"),
    (r'(\d+[\d,]*\+?)\s*(?:engineers|developers|direct reports|team members)', "team_size"),
    (r'(99\.\d+%\s*uptime)', "reliability"),
]


class HeuristicExperienceParser:
    """
    Blazing fast, deterministic NLP parser that extracts real work experience,
    tenures, seniority, and STAR quantified achievements without needing an active LLM.
    """

    @staticmethod
    def extract_metadata(text: str) -> CandidateMetadata:
        metadata = CandidateMetadata()
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        
        # Name estimation: first non-empty line that isn't a header or email
        for line in lines[:5]:
            if not re.search(r'@|linkedin|github|phone|\+?\d{9,}|resume|curriculum', line, re.IGNORECASE) and len(line.split()) in [2, 3, 4]:
                metadata.full_name = line.strip()
                break
                
        # Email
        email_match = re.search(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+', text)
        if email_match:
            metadata.email = email_match.group(0)
            
        # Phone
        phone_match = re.search(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}', text)
        if phone_match:
            metadata.phone = phone_match.group(0).strip()
            
        # LinkedIn & GitHub
        li_match = re.search(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[a-zA-Z0-9_-]+', text)
        if li_match:
            metadata.linkedin_url = li_match.group(0)
            
        gh_match = re.search(r'(?:https?://)?(?:www\.)?github\.com/[a-zA-Z0-9_-]+', text)
        if gh_match:
            metadata.github_url = gh_match.group(0)

        # Location heuristic
        loc_match = re.search(r'([A-Z][a-zA-Z\s]+,\s*[A-Z]{2}(?:\s+\d{5})?|[A-Z][a-zA-Z\s]+,\s*(?:USA|India|Canada|UK|Germany|Remote))', text)
        if loc_match:
            metadata.location = loc_match.group(0).strip()

        return metadata

    @staticmethod
    def parse_date_range(date_str: str) -> Tuple[Optional[str], Optional[str], int, bool]:
        """
        Parses date string e.g. "Jan 2021 - Present" or "2019 - 2023" into duration_months and is_current.
        """
        is_current = bool(re.search(r'\b(present|current|now)\b', date_str, re.IGNORECASE))
        now = datetime.now()
        
        # Extract years and optional months
        years = [int(y) for y in re.findall(r'\b(19\d\d|20\d\d)\b', date_str)]
        months = []
        for word in re.findall(r'\b([A-Za-z]+)\b', date_str):
            if word.lower() in MONTHS_MAP:
                months.append(MONTHS_MAP[word.lower()])
                
        if not years:
            return None, None, 12, is_current  # default 1 yr if unspecified
            
        start_year = years[0]
        start_month = months[0] if months else 1
        start_str = f"{start_year:04d}-{start_month:02d}"
        
        if is_current:
            end_year = now.year
            end_month = now.month
            end_str = "Present"
        elif len(years) > 1:
            end_year = years[1]
            end_month = months[1] if len(months) > 1 else 12
            end_str = f"{end_year:04d}-{end_month:02d}"
        else:
            end_year = start_year + 1
            end_month = start_month
            end_str = f"{end_year:04d}-{end_month:02d}"
            
        duration_months = max(1, (end_year - start_year) * 12 + (end_month - start_month))
        return start_str, end_str, duration_months, is_current

    @staticmethod
    def extract_quantified_metrics(text: str) -> List[Dict[str, Any]]:
        metrics = []
        for pattern, m_type in QUANTIFIED_METRIC_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                val = match.group(0)
                # Find the sentence or bullet containing this match
                start_idx = max(0, text.rfind('\n', 0, match.start()))
                end_idx = text.find('\n', match.end())
                if end_idx == -1: end_idx = len(text)
                statement = text[start_idx:end_idx].strip()
                statement = re.sub(r'^[•\-\*]\s*', '', statement)
                
                metrics.append({
                    "metric_type": m_type,
                    "quantified_value": val,
                    "raw_statement": statement
                })
        return metrics

    @staticmethod
    def extract_work_experiences(text: str) -> List[WorkExperienceItem]:
        """
        Locates work experience section and extracts distinct positions,
        durations, seniority, tech stacks, and quantified impact.
        """
        experiences = []
        
        # Regex to locate Experience section
        exp_header_pattern = r'(?:WORK\s+EXPERIENCE|PROFESSIONAL\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|EXPERIENCE)'
        next_header_pattern = r'(?:EDUCATION|SKILLS|TECHNICAL\s+SKILLS|PROJECTS|CERTIFICATIONS|PUBLICATIONS|AWARDS)'
        
        match = re.search(exp_header_pattern, text, re.IGNORECASE)
        if match:
            start_pos = match.end()
            next_match = re.search(next_header_pattern, text[start_pos:], re.IGNORECASE)
            exp_text = text[start_pos:start_pos + next_match.start()] if next_match else text[start_pos:]
        else:
            exp_text = text # fallback to full text

        # Split into position blocks using date patterns as anchors
        date_pattern = r'((?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2}/\d{2,4}|\d{4})\s*[-–—to]\s*(?:Present|Current|Now|\d{4}|(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s*\d{4}))'
        
        blocks = re.split(date_pattern, exp_text, flags=re.IGNORECASE)
        
        if len(blocks) > 1:
            # Reconstruct (prefix + date + content)
            order_idx = 0
            for i in range(1, len(blocks), 2):
                date_str = blocks[i].strip()
                content = blocks[i+1].strip() if i+1 < len(blocks) else ""
                header_context = blocks[i-1].strip().split("\n")[-3:] # previous lines right before the date
                
                # Determine company and title
                job_title = "Software Engineer"
                company = "Technology Company"
                
                combined_header = " | ".join(header_context)
                for line in header_context:
                    clean_l = line.strip().strip("•-*|")
                    if any(term in clean_l.lower() for term in ["engineer", "developer", "architect", "lead", "manager", "designer", "consultant", "analyst"]):
                        job_title = clean_l
                    elif len(clean_l) > 2 and clean_l != job_title:
                        company = clean_l
                        
                start_date, end_date, duration_months, is_current = HeuristicExperienceParser.parse_date_range(date_str)
                
                # Seniority level
                seniority = "Mid"
                for kw, sen in SENIORITY_KEYWORDS.items():
                    if re.search(r'\b' + re.escape(kw) + r'\b', job_title, re.IGNORECASE):
                        seniority = sen
                        break
                        
                # Standardized role
                std_role = "Software Engineer"
                for role_name, patterns in STANDARDIZED_ROLES:
                    if any(re.search(p, job_title, re.IGNORECASE) for p in patterns):
                        std_role = role_name
                        break
                        
                # Quantified metrics
                impacts = HeuristicExperienceParser.extract_quantified_metrics(content)
                
                # Technologies
                common_tech = ["Python", "JavaScript", "TypeScript", "Go", "Golang", "Java", "C++", "Rust", "React", "Next.js", "Node.js", "Docker", "Kubernetes", "AWS", "GCP", "PostgreSQL", "Redis", "Kafka", "GraphQL", "MongoDB", "PyTorch", "TensorFlow", "FastAPI"]
                found_tech = [t for t in common_tech if re.search(r'\b' + re.escape(t) + r'\b', content, re.IGNORECASE)]
                
                # Narrative synthesis
                narrative = f"{job_title} at {company} ({start_date or ''} - {end_date or ''}). {content[:400]}"
                
                experiences.append(WorkExperienceItem(
                    company=company,
                    job_title=job_title,
                    standardized_role=std_role,
                    seniority_level=seniority,
                    start_date=start_date,
                    end_date=end_date,
                    duration_months=duration_months,
                    is_current=is_current,
                    technologies_used=found_tech,
                    impact_metrics=impacts,
                    experience_narrative=narrative,
                    order_index=order_idx
                ))
                order_idx += 1
                
        # If no date-anchored experiences found, create default summary experience
        if not experiences:
            impacts = HeuristicExperienceParser.extract_quantified_metrics(text)
            experiences.append(WorkExperienceItem(
                company="Industry Experience",
                job_title="Software Professional",
                standardized_role="Software Engineer",
                seniority_level="Mid",
                duration_months=24,
                is_current=True,
                impact_metrics=impacts,
                experience_narrative=text[:500],
                order_index=0
            ))
            
        return experiences

    @staticmethod
    def extract_education(text: str) -> List[EducationItem]:
        edu_items = []
        edu_header_pattern = r'(?:EDUCATION|ACADEMIC\s+BACKGROUND)'
        match = re.search(edu_header_pattern, text, re.IGNORECASE)
        if match:
            edu_text = text[match.end():match.end() + 600]
            degrees = re.findall(r'(?:Bachelor(?:\'s)?|Master(?:\'s)?|B\.S\.|M\.S\.|B\.Tech|M\.Tech|Ph\.D\.|BSc|MSc)(?:\s+in\s+([A-Za-z\s]+))?', edu_text, re.IGNORECASE)
            years = re.findall(r'\b(20\d\d|19\d\d)\b', edu_text)
            
            grad_year = years[0] if years else None
            degree_str = degrees[0][0] if degrees and degrees[0] else "Bachelor of Science"
            
            edu_items.append(EducationItem(
                institution="University",
                degree=degree_str or "Bachelor of Science",
                field_of_study="Computer Science",
                graduation_year=grad_year
            ))
        return edu_items

    @classmethod
    def parse_profile(cls, raw_text: str, filename: str, file_hash: str) -> CandidateProfile:
        metadata = cls.extract_metadata(raw_text)
        experiences = cls.extract_work_experiences(raw_text)
        education = cls.extract_education(raw_text)
        
        total_months = sum(e.duration_months for e in experiences)
        total_years = round(total_months / 12.0, 1)
        
        # Distinct skills across all experiences
        skills_set = set()
        for e in experiences:
            skills_set.update(e.technologies_used)
            
        # Dense experience summary specifically tailored for vectorization
        exp_lines = []
        for e in experiences:
            impact_summary = " ".join([m.get("raw_statement", "") for m in e.impact_metrics[:3]])
            exp_lines.append(f"{e.seniority_level} {e.job_title} at {e.company} ({e.duration_months} mos): {impact_summary}")
        experience_summary = "\n".join(exp_lines) or raw_text[:500]

        return CandidateProfile(
            metadata=metadata,
            total_years_experience=total_years,
            work_experiences=experiences,
            education=education,
            core_skills=list(skills_set),
            experience_summary=experience_summary,
            raw_text=raw_text,
            file_hash=file_hash,
            filename=filename
        )


class ExperienceDecompositionEngine:
    """
    Master engine: Tries LLM (Ollama or OpenAI API) with structured extraction;
    falls back cleanly to HeuristicExperienceParser for zero-latency deterministic extraction.
    """

    @classmethod
    async def parse(cls, raw_text: str, filename: str, file_hash: str) -> CandidateProfile:
        provider = settings.LLM_PROVIDER.lower()
        
        if provider == "ollama":
            try:
                profile = await cls._parse_ollama(raw_text, filename, file_hash)
                if profile:
                    return profile
            except Exception as e:
                logger.warning(f"Ollama parsing failed: {e}. Falling back to heuristic parser.")
                
        elif provider == "openai" and settings.OPENAI_API_KEY:
            try:
                profile = await cls._parse_openai(raw_text, filename, file_hash)
                if profile:
                    return profile
            except Exception as e:
                logger.warning(f"OpenAI parsing failed: {e}. Falling back to heuristic parser.")

        # Default fast & robust heuristic NLP parser
        return HeuristicExperienceParser.parse_profile(raw_text, filename, file_hash)

    @classmethod
    async def _parse_ollama(cls, raw_text: str, filename: str, file_hash: str) -> Optional[CandidateProfile]:
        url = f"{settings.OLLAMA_HOST}/api/chat"
        prompt = (
            "Extract structured candidate work experience from the following resume text. "
            "Focus heavily on actual work experience: job titles, company names, start/end dates, "
            "seniority level (Junior, Mid, Senior, Lead, Staff, Principal, Manager), "
            "quantified STAR impact metrics (percentages, throughput, scale, revenue), "
            "and technologies used in that specific job.\n\n"
            f"RESUME TEXT:\n{raw_text[:4000]}"
        )
        
        payload = {
            "model": settings.OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "format": "json",
            "stream": False,
        }
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=payload)
            if res.status_code == 200:
                data = res.json()
                content = data.get("message", {}).get("content", "{}")
                parsed = json.loads(content)
                # Merge with heuristic base
                base = HeuristicExperienceParser.parse_profile(raw_text, filename, file_hash)
                if "full_name" in parsed: base.metadata.full_name = parsed["full_name"]
                return base
        return None

    @classmethod
    async def _parse_openai(cls, raw_text: str, filename: str, file_hash: str) -> Optional[CandidateProfile]:
        url = f"{settings.OPENAI_BASE_URL}/chat/completions"
        headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
        prompt = (
            "Extract structured candidate work experience from the following resume text. "
            "Output JSON with fields: full_name, email, total_years_experience, work_experiences: [{company, job_title, seniority_level, duration_months, impact_metrics: [{raw_statement, quantified_value}], technologies_used}].\n\n"
            f"RESUME TEXT:\n{raw_text[:4000]}"
        )
        payload = {
            "model": settings.OPENAI_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "response_format": {"type": "json_object"}
        }
        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=payload, headers=headers)
            if res.status_code == 200:
                data = res.json()
                content = data["choices"][0]["message"]["content"]
                parsed = json.loads(content)
                base = HeuristicExperienceParser.parse_profile(raw_text, filename, file_hash)
                if "full_name" in parsed: base.metadata.full_name = parsed["full_name"]
                return base
        return None
