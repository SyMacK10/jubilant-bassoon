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
    "java":          {"eol": ["oracle-jdk", "redhat-build-of-openjdk"], "so": "java",          "nvd": "java"},
    "python":        {"eol": ["python"],        "so": "python",        "nvd": "python"},
    "php":           {"eol": ["php"],           "so": "php",           "nvd": "php"},
    "ruby":          {"eol": ["ruby"],          "so": "ruby",          "nvd": "ruby"},
    "nodejs":        {"eol": ["nodejs"],        "so": "node.js",       "nvd": "node.js"},
    "postgresql":    {"eol": ["postgresql"],    "so": "postgresql",    "nvd": "postgresql"},
    "mysql":         {"eol": ["mysql"],         "so": "mysql",         "nvd": "mysql"},
    "mongodb":       {"eol": ["mongodb"],       "so": "mongodb",       "nvd": "mongodb"},
    "kafka":         {"eol": ["kafka"],         "so": "apache-kafka",  "nvd": "apache kafka"},
    "elasticsearch": {"eol": ["elasticsearch"], "so": "elasticsearch", "nvd": "elasticsearch"},
    "hadoop":        {"eol": ["hadoop"],        "so": "hadoop",        "nvd": "apache hadoop"},
    "spring":        {"eol": ["spring-framework"], "so": "spring",     "nvd": "spring framework"},
    "tomcat":        {"eol": ["tomcat"],        "so": "tomcat",        "nvd": "apache tomcat"},
    "jboss":         {"eol": ["jboss"],         "so": "jboss",         "nvd": "jboss"},
    "wildfly":       {"eol": [],                "so": "wildfly",       "nvd": "wildfly"},
    "centos":        {"eol": ["centos"],        "so": "centos",        "nvd": "centos"},
    "rhel":          {"eol": ["rhel"],          "so": "rhel",          "nvd": "red hat enterprise linux"},
    "ubuntu":        {"eol": ["ubuntu"],        "so": "ubuntu",        "nvd": "ubuntu"},
}

# Canonical names. Kept as a flat list so collectors and the scorer can iterate.
OPENLOGIC_CATALOG = list(CATALOG)


def eol_slugs(tech: str) -> list[str]:
    return CATALOG.get(tech, {}).get("eol", [])


def so_tag(tech: str) -> str:
    return CATALOG.get(tech, {}).get("so", tech)


def nvd_keyword(tech: str) -> str:
    return CATALOG.get(tech, {}).get("nvd", tech)


# Thresholds that gate whether a weight is awarded at all.
#
# so_min_prior_volume exists because Stack Overflow tag volumes are now low
# enough that percentage deltas are noise: a tag moving 2 -> 4 questions is a
# "+100% spike". Requiring a floor on the prior window suppresses that. Tune
# this alongside the weights.
THRESHOLDS = {
    "so_spike_pct": 30,
    "so_min_prior_volume": 10,
    "github_mentions": 10,
}

SCORING = {
    "eol_within_90_days": 30,
    "eol_within_180_days": 20,
    "stackoverflow_spike_30pct": 15,
    "github_migration_keyword": 10,
    "critical_cve": 25,
    "high_cve": 15,
}
