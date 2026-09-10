from dotenv import load_dotenv
import os

load_dotenv()

API_KEYS = {
    "stackoverflow": os.getenv("STACKOVERFLOW_KEY"),
    "github": os.getenv("GITHUB_TOKEN"),
    "nvd": os.getenv("NVD_KEY"),
    "anthropic": os.getenv("ANTHROPIC_KEY"),
}

# Technologies OpenLogic actively supports — filters all signals.
# NOTE: these strings are currently used as Stack Overflow tags,
# endoflife.date slugs, and NVD keywords simultaneously. They will not
# all match. Refactor into a per-source alias map once the empirical
# mismatches are known (see handoff section 8).
OPENLOGIC_CATALOG = [
    "java", "python", "php", "ruby", "nodejs",
    "postgresql", "mysql", "mongodb",
    "kafka", "elasticsearch", "hadoop",
    "spring", "tomcat", "jboss", "wildfly",
    "centos", "rhel", "ubuntu",
]

SCORING = {
    "eol_within_90_days": 30,
    "eol_within_180_days": 20,
    "stackoverflow_spike_30pct": 15,
    "github_migration_keyword": 10,
    "critical_cve": 25,
    "high_cve": 15,
}
