from dotenv import load_dotenv
import os

load_dotenv()

API_KEYS = {
    "stackoverflow": os.getenv("STACKOVERFLOW_KEY"),
    "github": os.getenv("GITHUB_TOKEN"),
    "nvd": os.getenv("NVD_KEY"),
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
}

SCORING = {
    "eol_within_90_days": 30,
    "eol_within_180_days": 20,
    "stackoverflow_spike_30pct": 15,
    "github_migration_keyword": 10,
    "critical_cve": 25,
    "high_cve": 15,
}
