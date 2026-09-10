from dotenv import load_dotenv
import os

load_dotenv()

API_KEYS = {
    "stackoverflow": os.getenv("STACKOVERFLOW_KEY"),
    "github": os.getenv("GITHUB_TOKEN"),
    "nvd": os.getenv("NVD_KEY"),
    # Optional. The Reddit collector stays dormant until these are present.
    "reddit_client_id": os.getenv("REDDIT_CLIENT_ID"),
    "reddit_client_secret": os.getenv("REDDIT_CLIENT_SECRET"),
    "anthropic": os.getenv("ANTHROPIC_KEY"),
}

# Technologies OpenLogic actively supports, keyed by canonical name.
#
# Per-source aliases exist because one string cannot serve all three APIs
# (handoff section 8). Verified empirically against the live APIs:
#   - "eol":  endoflife.date product slugs. A list, because some products are
#             split across distributions there. Empty list = no EOL data exists
#             for that technology; it still collects other signal types.
#   - "so":   Stack Overflow tag.
#   - "nvd":  NVD keywordSearch term.
CATALOG = {
    "java":          {"eol": ["oracle-jdk", "redhat-build-of-openjdk"], "so": "java", "nvd": "java",          "cpe": ["java", "jdk", "jre", "openjdk"]},
    "python":        {"eol": ["python"],        "so": "python",        "nvd": "python",        "cpe": ["python"]},
    "php":           {"eol": ["php"],           "so": "php",           "nvd": "php",           "cpe": ["php"]},
    "ruby":          {"eol": ["ruby"],          "so": "ruby",          "nvd": "ruby",          "cpe": ["ruby"]},
    "nodejs":        {"eol": ["nodejs"],        "so": "node.js",       "nvd": "node.js",       "cpe": ["node.js", "nodejs"]},
    "postgresql":    {"eol": ["postgresql"],    "so": "postgresql",    "nvd": "postgresql",    "cpe": ["postgresql"]},
    "mysql":         {"eol": ["mysql"],         "so": "mysql",         "nvd": "mysql",         "cpe": ["mysql"]},
    "mongodb":       {"eol": ["mongodb"],       "so": "mongodb",       "nvd": "mongodb",       "cpe": ["mongodb"]},
    "kafka":         {"eol": ["kafka"],         "so": "apache-kafka",  "nvd": "kafka",         "cpe": ["kafka"]},
    "elasticsearch": {"eol": ["elasticsearch"], "so": "elasticsearch", "nvd": "elasticsearch", "cpe": ["elasticsearch"]},
    "hadoop":        {"eol": ["hadoop"],        "so": "hadoop",        "nvd": "hadoop",        "cpe": ["hadoop"]},
    "spring":        {"eol": ["spring-framework"], "so": "spring",     "nvd": "spring",        "cpe": ["spring"]},
    "tomcat":        {"eol": ["tomcat"],        "so": "tomcat",        "nvd": "tomcat",        "cpe": ["tomcat"]},
    "jboss":         {"eol": ["jboss"],         "so": "jboss",         "nvd": "jboss",         "cpe": ["jboss"]},
    "wildfly":       {"eol": [],                "so": "wildfly",       "nvd": "wildfly",       "cpe": ["wildfly"]},
    "centos":        {"eol": ["centos"],        "so": "centos",        "nvd": "centos",        "cpe": ["centos"]},
    "rhel":          {"eol": ["rhel"],          "so": "rhel",          "nvd": "enterprise linux", "cpe": ["enterprise_linux"]},
    "ubuntu":        {"eol": ["ubuntu"],        "so": "ubuntu",        "nvd": "ubuntu",        "cpe": ["ubuntu_linux", "ubuntu"]},
}

# Canonical names. Kept as a flat list so collectors and the scorer can iterate.
OPENLOGIC_CATALOG = list(CATALOG)


def eol_slugs(tech: str) -> list[str]:
    return CATALOG.get(tech, {}).get("eol", [])


def so_tag(tech: str) -> str:
    return CATALOG.get(tech, {}).get("so", tech)


def nvd_keyword(tech: str) -> str:
    return CATALOG.get(tech, {}).get("nvd", tech)


def discussion_tokens(tech: str) -> list[str]:
    """Words that identify this technology in free-text discussion."""
    entry = CATALOG.get(tech, {})
    return sorted({tech, entry.get("so", tech)})


def cpe_tokens(tech: str) -> list[str]:
    """Tokens that must appear in a CVE's CPE list for it to count as a match."""
    return CATALOG.get(tech, {}).get("cpe", [tech])


# Thresholds that gate whether a weight is awarded at all.
#
# so_min_prior_volume exists because Stack Overflow tag volumes are now low
# enough that percentage deltas are noise: a tag moving 2 -> 4 questions is a
# "+100% spike". Requiring a floor on the prior window suppresses that. Tune
# this alongside the weights.
THRESHOLDS = {
    "so_spike_pct": 30,
    "so_min_prior_volume": 10,
    # Absolute issue counts run to tens of thousands, so ">10 mentions" fires
    # for every technology. Migration chatter is scored on a rise instead.
    "github_spike_pct": 25,
    "github_min_prior_volume": 100,
    # Discussion forums are a thin source: measured volume is a handful of
    # genuinely EOL-related posts per technology per six months. The floor is
    # set so the weight effectively never fires on one or two posts — the
    # value of this source is the verbatim quotes, not the count.
    "discussion_min_posts": 3,
}

SCORING = {
    "eol_within_90_days": 30,
    "eol_within_180_days": 20,
    "stackoverflow_spike_30pct": 15,
    "github_migration_keyword": 10,
    "critical_cve": 25,
    "high_cve": 15,
    "discussion_eol_chatter": 5,
}

# Support-lifecycle vocabulary. Deliberately excludes bare "migrate"/"upgrade":
# those matched schema-migration tools and COBOL rewrites, not EOL pressure.
EOL_DISCUSSION_KEYWORDS = [
    "end of life", "end-of-life", "eol", "out of support",
    "no longer supported", "unsupported", "extended support",
    "security updates", "legacy version",
]

# Subreddits searched when Reddit credentials are configured.
REDDIT_SUBREDDITS = [
    "devops", "sysadmin", "linuxadmin", "java", "PostgreSQL",
    "php", "node", "docker", "kubernetes", "dataengineering",
]
