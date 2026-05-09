from dataclasses import dataclass

PERSONAL_EMAIL_DOMAINS = {
    "gmail.com", "outlook.com", "hotmail.com", "yahoo.com",
    "icloud.com", "protonmail.com", "163.com", "qq.com",
}

PERSONAL_CLOUD_SERVICES = {
    "GoogleDrive", "Dropbox", "PersonalOneDrive",
}

DIMENSION_CAPS = {
    "D1": 30.0,
    "D2": 25.0,
    "D3": 20.0,
    "D4": 15.0,
    "D5": 10.0,
}

SEVERITY_THRESHOLDS = {
    "critical": 80,
    "high": 60,
    "medium": 40,
    "low": 0,
}

COMPOSITE_MULTIPLIERS = [
    {
        "id": "CM01",
        "name": "DLP blocked but continued attempts",
        "multiplier": 1.3,
        "d1_rules_needed": 2,
    },
    {
        "id": "CM04",
        "name": "HR risk context + exfiltration signal",
        "multiplier": 1.2,
        "requires_d1_and_d4": True,
    },
    {
        "id": "CM03",
        "name": "After-hours access with sensitive data",
        "multiplier": 1.15,
        "requires_r09_and_sensitive": True,
    },
]
