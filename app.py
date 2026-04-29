# stable version checkpoint1 with Biomarker Language
from openai import OpenAI
import streamlit as st

client = OpenAI(api_key=st.secrets["OPENAI_API_KEY"])
import io
import re
import time
from typing import Any, List, Tuple

import requests
import pandas as pd
import streamlit as st

# =========================================================
# PAGE
# =========================================================

st.set_page_config(page_title="Atlas Radar", layout="wide")

# =========================================================
# CONFIG
# =========================================================

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 200
MAX_PAGES_PER_QUERY = 8
TIMEOUT = 30
REQUEST_SLEEP_SECONDS = 0.15

MIN_ENROLLMENT_CORE = 50
ALLOWED_CORE_PHASES = {"PHASE2", "PHASE2_3"}
ALLOWED_CORE_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"}
MIN_CORE_START_YEAR = 2021

MIN_ENROLLMENT_SIDE = 30
ALLOWED_SIDE_PHASES = {"PHASE2", "PHASE2_3"}
ALLOWED_SIDE_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING", "NOT_YET_RECRUITING"}
MIN_SIDE_START_YEAR = 2021

ALLOWED_WATCHLIST_PHASES = {"PHASE3"}
ALLOWED_WATCHLIST_STATUSES = {"RECRUITING", "ACTIVE_NOT_RECRUITING"}
MIN_WATCHLIST_START_YEAR = 2021

EU_COUNTRIES = {
    "Austria", "Belgium", "Bulgaria", "Croatia", "Cyprus", "Czechia", "Czech Republic",
    "Denmark", "Estonia", "Finland", "France", "Germany", "Greece", "Hungary",
    "Ireland", "Italy", "Latvia", "Lithuania", "Luxembourg", "Malta", "Netherlands",
    "Poland", "Portugal", "Romania", "Slovakia", "Slovenia", "Spain", "Sweden",
    "Switzerland", "United Kingdom", "Norway", "Iceland", "Liechtenstein"
}

DACH_UK_PRIORITY = {"Germany", "Austria", "Switzerland", "United Kingdom"}

ACADEMIC_TERMS = [
    "university", "college", "hospital", "nhs", "institute", "medical center",
    "klinikum", "charite", "foundation", "school of medicine", "faculty",
    "academy", "centre hospitalier", "universitätsklinikum", "universitaet",
    "chu", "trust", "clinic", "medical school", "national institute",
    "national institutes of health", "niaid", "nih"
]

EXCLUDE_TITLE_TERMS = [
    "pregnancy registry",
    "registry",
    "expanded access",
    "compassionate use",
    "real-world",
    "real world",
    "observational",
    "natural history",
    "questionnaire",
    "survey",
    "chart review",
    "retrospective",
    "healthcare utilization",
    "claims database",
    "epidemiology",
    "screening study",
    "burden of disease",
    "estimated preventable",
    "eligibility and estimated",
    "extension study",
    "rollover extension"
]

METABOLIC_CVRM_TERMS = [
    "diabetes", "type 2 diabetes", "type 1 diabetes", "obesity", "adiposity",
    "metabolic disease", "metabolic dysfunction", "cardiovascular", "cardio-renal",
    "cardiorenal", "ckd", "chronic kidney disease", "heart failure", "atherosclerosis",
    "dyslipidemia", "hyperlipidemia", "insulin resistance", "glucose metabolism",
    "mash", "nash", "masld", "nafld", "metabolic syndrome", "iga nephropathy",
    "chronic kidney", "renal disease", "albuminuria", "nephropathy", "proteinuria",
    "weight loss", "overweight"
]

CELL_THERAPY_CAR_T_STRONG = [
    "car-t", "cart", "cell therapy", "cellular therapy", "t-cell therapy",
    "immune effector cell", "cytokine release syndrome", "crs", "icans"
]

CELL_THERAPY_CAR_T_SUPPORT = [
    "lymphoma", "leukemia", "multiple myeloma", "hematologic malignancy",
    "myeloma", "aml", "all", "dlbcl", "b-cell", "relapsed refractory"
]

NEURO_STRONG = [
    "alzheimer", "parkinson", "multiple sclerosis", "neurodegeneration",
    "neurodegenerative", "neuroinflammation", "dementia", "als", "epilepsy",
    "huntington", "neurology", "mild cognitive impairment", "mci"
]

NEURO_SUPPORT = [
    "cognition", "cognitive decline", "csf", "cerebrospinal fluid",
    "brain biomarker", "disease progression"
]

IMMUNOLOGY_INFLAMMATION_TERMS = [
    "autoimmune", "autoimmunity", "inflammation", "inflammatory", "immune-mediated",
    "immunology", "cytokine", "interleukin", "tnf", "jak", "lupus", "sle",
    "rheumatoid arthritis", "psoriasis", "psoriatic arthritis", "atopic dermatitis",
    "hidradenitis", "ulcerative colitis", "crohn", "ibd", "asthma", "eosinophilic",
    "vasculitis", "scleroderma", "sjogren", "myositis", "dermatomyositis",
    "infection", "infectious disease", "viral", "bacterial", "antiviral", "vaccine",
    "sepsis", "pneumonia", "covid", "influenza", "hepatitis", "hiv", "tuberculosis"
]

ONCOLOGY_OTHER_TERMS = [
    "solid tumor", "solid tumours", "non-small cell lung cancer", "nsclc",
    "small cell lung cancer", "sclc", "breast cancer", "triple-negative breast cancer",
    "tnbc", "ovarian cancer", "endometrial cancer", "gastric cancer", "colon cancer",
    "colorectal cancer", "prostate cancer", "pancreatic cancer", "hepatocellular carcinoma",
    "hcc", "melanoma", "tumor", "tumour", "oncology", "cancer", "carcinoma",
    "adc", "antibody drug conjugate", "trastuzumab", "patritumab", "her2", "her3",
    "egfr", "pd-1", "pd-l1", "pembrolizumab", "nivolumab", "durvalumab", "atezolizumab",
    "chemotherapy", "checkpoint inhibitor", "metastatic", "advanced malignancy"
]

BIOMARKER_KEYWORDS = [
    "biomarker", "biomarkers", "pharmacodynamic", "exploratory", "response",
    "responder", "non-responder", "stratification", "patient stratification",
    "precision medicine", "mechanism", "mechanistic", "target engagement",
    "omics", "metabolomics", "lipidomics", "metabolism", "metabolic profiling",
    "toxicity", "immune profiling", "signature", "profiling"
]

TARGET_ACCOUNT_ALIASES = {
    "Pfizer": ["pfizer", "wyeth"],
    "BioNTech": ["biontech"],
    "Roche": ["roche", "f. hoffmann-la roche", "hoffmann-la roche"],
    "Genentech": ["genentech"],
    "AbbVie": ["abbvie"],
    "Novartis": ["novartis"],
    "Takeda": ["takeda"],
    "Boehringer Ingelheim": ["boehringer", "boehringer ingelheim"],
    "Bayer": ["bayer"],
    "CSL": ["csl", "csl behring"],
    "Daiichi Sankyo": ["daiichi sankyo"],
    "Merck KGaA / EMD Serono": ["merck kgaa", "emd serono", "merck healthcare kgaa"],
    "Otsuka": ["otsuka"],
    "Eisai": ["eisai"],
    "Nuvisan": ["nuvisan"],
    "TFS HealthScience": ["tfs healthscience", "trial form support", "tfs"],
    "AstraZeneca": ["astrazeneca"],
    "UCB": ["ucb"],
    "GSK": ["gsk", "glaxosmithkline"],
    "Eli Lilly": ["eli lilly", "lilly"],
    "Bristol-Myers Squibb": ["bristol-myers squibb", "bms", "bristol myers squibb"],
    "Amgen": ["amgen"],
    "Decode": ["decode", "decode genetics", "decode genetics inc", "decode genetics ehf"],
    "Biogen": ["biogen"],
    "Gilead": ["gilead", "kite pharma", "kite"],
    "Astellas": ["astellas"],
    "Janssen": ["janssen", "janssen pharmaceuticals", "johnson & johnson", "j&j"],
    "Teva": ["teva"],
    "Moderna": ["moderna", "modernatx", "modernatx, inc."],
    "Merck / MSD": ["merck sharp & dohme", "msd", "merck & co", "merck"]
}

PHARMA_TERMS = [
    "Pfizer",
    "BioNTech",
    "Roche OR Genentech",
    "AbbVie",
    "Novartis",
    "Takeda",
    'Boehringer OR "Boehringer Ingelheim"',
    "Bayer",
    '"CSL" OR "CSL Behring"',
    '"Daiichi Sankyo"',
    '"Merck KGaA" OR "EMD Serono"',
    "Otsuka",
    "Eisai",
    "Nuvisan",
    '"TFS HealthScience" OR TFS',
    "AstraZeneca",
    "UCB",
    "GSK OR GlaxoSmithKline",
    '"Eli Lilly" OR Lilly',
    '"Bristol-Myers Squibb" OR BMS OR "Bristol Myers Squibb"',
    "Amgen",
    'Decode OR "deCODE genetics" OR "Decode Genetics"',
    "Biogen",
    "Gilead OR Kite",
    "Astellas",
    "Janssen OR Johnson & Johnson OR J&J",
    "Teva",
    "Moderna",
    'Merck OR MSD OR "Merck Sharp & Dohme"'
]

DISPLAY_COLUMNS = [
    "NCT_Link",
    "Score_10",
    "CommercialHypothesis",
    "OutreachHook",
    "Who",
    "WhyNow",
    "WhyUs",
    "LeadSponsor",
    "PhaseBucket",
    "Status",
    "Enrollment",
    "Cluster",
    "Title",
    "PrimaryOutcome",
    "ScoreReasons",
    "ExclusionFlags",
    "MatchedQueryTerm"
]

DOMAIN_CLUSTER_MAP = {
    "Metabolic / CVRM": ["METABOLIC_CVRM"],
    "Neurology": ["NEURO"],
    "Cell Therapy": ["CELL_THERAPY_CAR_T"],
    "Immunology / Inflammation": ["IMMUNOLOGY_INFLAMMATION"],
    "Oncology / IO": ["ONCOLOGY_OTHER"],
}

# =========================================================
# HELPERS
# =========================================================

def safe_get(dct, path, default=None):
    cur = dct
    for k in path:
        if not isinstance(cur, dict) or k not in cur:
            return default
        cur = cur[k]
    return cur

def contains_any(text, keywords):
    text = (text or "").lower()
    return any(k.lower() in text for k in keywords)

def count_matches(text, keywords):
    text = (text or "").lower()
    return sum(1 for kw in keywords if kw.lower() in text)

def parse_year(date_str):
    if not date_str:
        return None
    m = re.search(r"(19|20)\d{2}", str(date_str))
    return int(m.group(0)) if m else None

def get_sponsor_block(protocol):
    return protocol.get("sponsorCollaboratorsModule", {}) or {}

def get_lead_sponsor(protocol):
    sponsor_mod = get_sponsor_block(protocol)
    return safe_get(sponsor_mod, ["leadSponsor", "name"], "") or ""

def get_collaborators(protocol):
    sponsor_mod = get_sponsor_block(protocol)
    return [c.get("name", "") for c in (sponsor_mod.get("collaborators") or []) if c.get("name")]

def get_sponsor_names(protocol):
    names = []
    lead = get_lead_sponsor(protocol)
    if lead:
        names.append(lead)
    names.extend(get_collaborators(protocol))
    return names

def get_matching_accounts(protocol):
    sponsor_text = " | ".join(get_sponsor_names(protocol)).lower()
    matched = []
    for canonical_name, aliases in TARGET_ACCOUNT_ALIASES.items():
        if any(alias in sponsor_text for alias in aliases):
            matched.append(canonical_name)
    return sorted(list(set(matched)))

def lead_sponsor_matches_target(protocol):
    lead = get_lead_sponsor(protocol).lower()
    matches = []
    for canonical_name, aliases in TARGET_ACCOUNT_ALIASES.items():
        if any(alias in lead for alias in aliases):
            matches.append(canonical_name)
    return sorted(list(set(matches)))

def collaborator_matches_target(protocol):
    collabs = " | ".join(get_collaborators(protocol)).lower()
    matches = []
    for canonical_name, aliases in TARGET_ACCOUNT_ALIASES.items():
        if any(alias in collabs for alias in aliases):
            matches.append(canonical_name)
    return sorted(list(set(matches)))

def get_country_summary(protocol):
    countries = set()
    locations = protocol.get("contactsLocationsModule", {}).get("locations", []) or []
    for loc in locations:
        country = loc.get("country")
        if country:
            countries.add(country.strip())
        alt_country = safe_get(loc, ["locationAddress", "country"], None)
        if alt_country:
            countries.add(alt_country.strip())
    return sorted(list(countries))

def get_conditions_keywords_blob(protocol):
    cond_mod = protocol.get("conditionsModule", {}) or {}
    conditions = cond_mod.get("conditions", []) or []
    keywords = cond_mod.get("keywords", []) or []
    return " | ".join([str(x) for x in list(conditions) + list(keywords)]).lower()

def get_text_blob(protocol):
    ident = protocol.get("identificationModule", {}) or {}
    desc = protocol.get("descriptionModule", {}) or {}
    outcomes = protocol.get("outcomesModule", {}) or {}
    parts = [
        ident.get("briefTitle"),
        ident.get("officialTitle"),
        desc.get("briefSummary"),
        desc.get("detailedDescription"),
        str(outcomes)
    ]
    return " ".join([str(x) for x in parts if x]).lower()

def detect_cluster(protocol):
    ck_blob = get_conditions_keywords_blob(protocol)
    text_blob = get_text_blob(protocol)
    combined = f"{ck_blob} | {text_blob}"

    metabolic_hits = count_matches(ck_blob, METABOLIC_CVRM_TERMS)
    cart_strong_hits = count_matches(combined, CELL_THERAPY_CAR_T_STRONG)
    cart_support_hits = count_matches(ck_blob, CELL_THERAPY_CAR_T_SUPPORT)
    neuro_strong_hits = count_matches(ck_blob, NEURO_STRONG)
    neuro_support_hits = count_matches(combined, NEURO_SUPPORT)
    immunology_hits = count_matches(combined, IMMUNOLOGY_INFLAMMATION_TERMS)
    oncology_hits = count_matches(combined, ONCOLOGY_OTHER_TERMS)

    if metabolic_hits >= 1:
        return "METABOLIC_CVRM", metabolic_hits
    if cart_strong_hits >= 1:
        return "CELL_THERAPY_CAR_T", cart_strong_hits + cart_support_hits
    if neuro_strong_hits >= 1:
        return "NEURO", neuro_strong_hits + neuro_support_hits
    if immunology_hits >= 1:
        return "IMMUNOLOGY_INFLAMMATION", immunology_hits
    if oncology_hits >= 1:
        return "ONCOLOGY_OTHER", oncology_hits
    return "OTHER", 0

def lead_sponsor_is_academic(lead_sponsor):
    return contains_any(lead_sponsor or "", ACADEMIC_TERMS)

def has_us_signal(countries):
    c = set(countries or [])
    return "United States" in c

def us_pure(countries):
    c = set(countries or [])
    return len(c) > 0 and c == {"United States"}

def has_eu_signal(countries):
    c = set(countries or [])
    return len(c.intersection(EU_COUNTRIES)) > 0

def parse_phase_bucket(phases):
    p = (phases or "").upper()
    if "PHASE2" in p and "PHASE3" in p:
        return "PHASE2_3"
    if "PHASE2" in p:
        return "PHASE2"
    if "PHASE3" in p:
        return "PHASE3"
    if "PHASE1" in p:
        return "PHASE1"
    return "NONE"

def exclusion_flags(row, mode):
    flags = []

    title_blob = f"{row.get('Title','')} {row.get('OfficialTitle','')}".lower()
    if contains_any(title_blob, EXCLUDE_TITLE_TERMS):
        flags.append("title_noise")

    study_type = (row.get("StudyType") or "").upper()
    if study_type and study_type != "INTERVENTIONAL":
        flags.append("non_interventional")

    if row.get("LeadSponsorAcademic"):
        flags.append("academic_lead_sponsor")

    if not row.get("MatchingTargetAccounts"):
        flags.append("not_target_account")

    phase_bucket = row.get("PhaseBucket") or "NONE"
    if phase_bucket not in {"PHASE2", "PHASE2_3", "PHASE3"}:
        flags.append("not_phase_2_or_3")

    if row.get("Cluster") == "OTHER":
        flags.append("off_focus")

    if mode == "Domestic":
        if not row.get("US_SIGNAL"):
            flags.append("no_us_signal")
    else:
        if not row.get("EU_SIGNAL"):
            flags.append("no_eu_signal")

    return "; ".join(flags)

# UNUSED
def locked_late_penalty(row):
    pass

def locked_late_penalty(row):
    phase_bucket = row.get("PhaseBucket") or "NONE"
    status = (row.get("Status") or "").upper()

    try:
        enrollment = int(float(row.get("Enrollment") or 0))
    except Exception:
        enrollment = 0

    po = (row.get("PrimaryOutcome") or "").lower()
    blob = f"{row.get('ConditionsKeywordsBlob','')} {row.get('TextBlob','')}".lower()

    biomarker_signal = any(k in po for k in BIOMARKER_KEYWORDS) or any(k in blob for k in BIOMARKER_KEYWORDS)

    penalty = 0
    reasons = []

    if phase_bucket == "PHASE3" and status == "ACTIVE_NOT_RECRUITING":
        penalty -= 10
        reasons.append("late/less accessible")

    if phase_bucket == "PHASE3" and enrollment >= 1000 and not biomarker_signal:
        penalty -= 8
        reasons.append("large locked phase 3")

    if phase_bucket == "PHASE2_3" and enrollment >= 1500 and status in {"RECRUITING", "ACTIVE_NOT_RECRUITING"} and not biomarker_signal:
        penalty -= 5
        reasons.append("scale-up rigidity")

    return penalty, reasons

def trigger_score(row, mode, logic, controls):
    score = 0
    reasons = []

    lead_accounts = [x.strip() for x in (row.get("LeadSponsorTargetAccounts") or "").split(";") if x.strip()]
    collab_accounts = [x.strip() for x in (row.get("CollaboratorTargetAccounts") or "").split(";") if x.strip()]

    if lead_accounts:
        score += 40
        reasons.append("lead sponsor is target account")
    elif collab_accounts:
        score += 8
        reasons.append("collaborator only")

    if mode == "Domestic":
        if row.get("US_SIGNAL"):
            score += 15
            reasons.append("US signal")
        if row.get("US_PURE"):
            score += 6
            reasons.append("US pure")
    else:
        if row.get("EU_SIGNAL"):
            score += 15
            reasons.append("EU signal")

        countries = {c.strip() for c in (row.get("Countries") or "").split(",") if c.strip()}
        if countries.intersection(DACH_UK_PRIORITY):
            score += 8
            reasons.append("DACH/UK")

    phase_bucket = row.get("PhaseBucket") or "NONE"
    cluster = row.get("Cluster")
    status = (row.get("Status") or "").upper()

    try:
        enrollment = int(float(row.get("Enrollment") or 0))
    except Exception:
        enrollment = 0

    sy = row.get("StartYear")
    po = (row.get("PrimaryOutcome") or "").lower()
    blob = f"{row.get('ConditionsKeywordsBlob','')} {row.get('TextBlob','')}".lower()
    title_blob = f"{row.get('Title','')} {row.get('OfficialTitle','')}".lower()

    biomarker_signal = any(k in po for k in BIOMARKER_KEYWORDS) or any(k in blob for k in BIOMARKER_KEYWORDS)

    if biomarker_signal:
        score += controls["biomarker_bonus"]
        reasons.append("biomarker presence")
    else:
        score -= controls["no_biomarker_penalty"]
        reasons.append("no biomarker layer")

    if logic == "Clinical Scale":
        if phase_bucket == "PHASE2_3":
            score += 22
            reasons.append("phase 2/3 sweet spot")
        elif phase_bucket == "PHASE2":
            score += 18
            reasons.append("phase 2 sweet spot")
        elif phase_bucket == "PHASE3":
            score -= 18
            reasons.append("late phase 3")

        if cluster == "METABOLIC_CVRM":
            score += 22
            reasons.append("core CVRM/metabolic")
        elif cluster == "CELL_THERAPY_CAR_T":
            score += 10
            reasons.append("CAR-T")
        elif cluster == "NEURO":
            score += 8
            reasons.append("neuro")
        elif cluster == "IMMUNOLOGY_INFLAMMATION":
            score += 10
            reasons.append("immunology/inflammation")
        elif cluster == "ONCOLOGY_OTHER":
            score -= 5
            reasons.append("oncology/IO")
        else:
            score -= 15
            reasons.append("off focus")

        if status == "RECRUITING":
            score += 12
            reasons.append("recruiting")
        elif status == "ACTIVE_NOT_RECRUITING":
            score += 10
            reasons.append("active not recruiting")
        elif status == "NOT_YET_RECRUITING":
            score += 8
            reasons.append("not yet recruiting")

        if enrollment >= 500:
            score += controls["large_enrollment_bonus"]
            reasons.append("enrollment >=500")
        elif enrollment >= 150:
            score += 5
            reasons.append("enrollment >=150")

    elif logic == "Discovery & Translational":
        if phase_bucket == "PHASE1":
            score += controls["early_phase_bonus"]
            reasons.append("phase 1 signal")
        elif phase_bucket == "PHASE2":
            score += 20
            reasons.append("phase 2 signal")
        elif phase_bucket == "PHASE2_3":
            score += 14
            reasons.append("phase 2/3 signal")
        elif phase_bucket == "PHASE3":
            score -= 8
            reasons.append("less translational")

        if cluster == "METABOLIC_CVRM":
            score += 18
            reasons.append("metabolic/CVRM fit")
        elif cluster == "NEURO":
            score += 14
            reasons.append("neuro fit")
        elif cluster == "CELL_THERAPY_CAR_T":
            score += 12
            reasons.append("cell therapy fit")
        elif cluster == "IMMUNOLOGY_INFLAMMATION":
            score += 14
            reasons.append("immunology/inflammation fit")
        elif cluster == "ONCOLOGY_OTHER":
            score += 2
            reasons.append("oncology/IO")
        else:
            score -= 8
            reasons.append("off focus")

        if status == "RECRUITING":
            score += 8
            reasons.append("recruiting")
        elif status == "ACTIVE_NOT_RECRUITING":
            score += 6
            reasons.append("active not recruiting")
        elif status == "NOT_YET_RECRUITING":
            score += 4
            reasons.append("not yet recruiting")

        if enrollment >= 500:
            score += 2
            reasons.append("larger cohort")
        elif enrollment >= 50:
            score += 4
            reasons.append("right-sized cohort")
        elif enrollment >= 20:
            score += 3
            reasons.append("smaller cohort acceptable")

    translational_keywords = [
        "biomarker", "biomarkers", "pharmacodynamic", "exploratory",
        "target engagement", "mechanism", "mechanistic", "stratification",
        "patient stratification", "precision medicine", "omics",
        "metabolomics", "lipidomics", "signature", "profiling",
        "proof of concept", "proof-of-concept"
    ]

    kw_hits = sum(1 for k in translational_keywords if k in blob or k in po or k in title_blob)

    if kw_hits >= 3:
        score += controls["strong_translational_bonus"]
        reasons.append("strong translational language")
    elif kw_hits >= 1:
        score += controls["basic_translational_bonus"]
        reasons.append("translational language")

    if sy:
        if sy >= 2025:
            score += 8
            reasons.append("start >=2025")
        elif sy >= 2023:
            score += 5
            reasons.append("start >=2023")
        elif sy >= 2021:
            score += 2
            reasons.append("start >=2021")
        elif sy < 2021:
            score -= 10
            reasons.append("old start")

    flags = row.get("ExclusionFlags") or ""

    if "title_noise" in flags:
        score -= 20
        reasons.append("title noise")
    if "non_interventional" in flags:
        score -= 20
        reasons.append("non interventional")
    if "academic_lead_sponsor" in flags:
        score -= 30
        reasons.append("academic lead")
    if "no_us_signal" in flags:
        score -= 20
        reasons.append("no US signal")
    if "no_eu_signal" in flags:
        score -= 20
        reasons.append("no EU signal")

    return max(score, 0), "; ".join(reasons)

# UNUSED
def dedupe_trials(df: pd.DataFrame):
    pass

def dedupe_trials(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df

    work = df.copy()

    work["LeadMatchFlag"] = work["LeadSponsorTargetAccounts"].fillna("").apply(lambda x: 1 if str(x).strip() else 0)
    work["ClusterHitsSort"] = pd.to_numeric(work["ClusterHits"], errors="coerce").fillna(0)
    work["EnrollmentSort"] = pd.to_numeric(work["Enrollment"], errors="coerce").fillna(0)
    work["TextLenSort"] = (
        work["Title"].fillna("").astype(str).str.len() +
        work["OfficialTitle"].fillna("").astype(str).str.len() +
        work["PrimaryOutcome"].fillna("").astype(str).str.len()
    )

    work = work.sort_values(
        by=["NCT", "LeadMatchFlag", "ClusterHitsSort", "EnrollmentSort", "TextLenSort"],
        ascending=[True, False, False, False, False]
    )

    work = work.drop_duplicates(subset=["NCT"], keep="first").copy()
    work = work.drop(columns=["LeadMatchFlag", "ClusterHitsSort", "EnrollmentSort", "TextLenSort"])

    return work.reset_index(drop=True)

def get_score_band(score_10):
    try:
        score_10 = float(score_10)
    except Exception:
        return "Cold"

    if score_10 >= 8.0:
        return "Hot"
    if score_10 >= 5.5:
        return "Warm"
    return "Cold"

def style_score_table(df: pd.DataFrame):
    if df.empty:
        return df.style

    def color_score(val):
        try:
            v = float(val)
        except Exception:
            return ""
        if v >= 8.0:
            return "background-color: #b91c1c; color: white;"
        if v >= 5.5:
            return "background-color: #7c3aed; color: white;"
        return "background-color: #1d4ed8; color: white;"

    def color_band(val):
        if str(val) == "Hot":
            return "background-color: #b91c1c; color: white;"
        if str(val) == "Warm":
            return "background-color: #7c3aed; color: white;"
        if str(val) == "Cold":
            return "background-color: #1d4ed8; color: white;"
        return ""

    styler = df.style

    if "Score_10" in df.columns:
        styler = styler.map(color_score, subset=["Score_10"])
    if "ScoreBand" in df.columns:
        styler = styler.map(color_band, subset=["ScoreBand"])

    return styler

def prepare_display_df(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return df
    cols = [c for c in DISPLAY_COLUMNS if c in df.columns]
    return df[cols].copy()

def make_nct_link(nct):
    nct = str(nct or "").strip()
    if not nct:
        return ""
    return f"https://clinicaltrials.gov/study/{nct}"

def df_download_button(df: pd.DataFrame, filename: str, label: str):
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )

def build_domain_table(df: pd.DataFrame, domain: str) -> pd.DataFrame:
    if df.empty:
        return df

    clusters = DOMAIN_CLUSTER_MAP.get(domain, [])
    if not clusters:
        return pd.DataFrame()

    out = df[
        (df["LeadSponsorTargetAccounts"].fillna("") != "") &
        (df["StudyType"].fillna("").str.upper() == "INTERVENTIONAL") &
        (df["LeadSponsorAcademic"] == False) &
        (~df["ExclusionFlags"].fillna("").str.contains("title_noise", na=False)) &
        (~df["ExclusionFlags"].fillna("").str.contains("off_focus", na=False)) &
        (df["PhaseBucket"].isin(ALLOWED_SIDE_PHASES)) &
        (df["Status"].fillna("").str.upper().isin(ALLOWED_SIDE_STATUSES)) &
        (pd.to_numeric(df["Enrollment"], errors="coerce").fillna(0) >= MIN_SIDE_ENROLLMENT if False else True)
    ].copy()

    out = out[out["Cluster"].isin(clusters)].copy()
    out = out[pd.to_numeric(out["Enrollment"], errors="coerce").fillna(0) >= MIN_ENROLLMENT_SIDE].copy()
    out = out[pd.to_numeric(out["StartYear"], errors="coerce").fillna(0) >= MIN_SIDE_START_YEAR].copy()

    return out.sort_values(
        by=["TriggerScore", "StartYear", "Enrollment"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

# =========================================================
# FETCH
# =========================================================

def assign_commercial_hypothesis(row):
    phase = row.get("PhaseBucket")

    try:
        enrollment = int(float(row.get("Enrollment") or 0))
    except Exception:
        enrollment = 0

    blob = f"{row.get('ConditionsKeywordsBlob','')} {row.get('TextBlob','')}".lower()

    biomarker_hits = sum(k in blob for k in [
        "biomarker", "mechanism", "mechanistic", "stratification",
        "precision medicine", "omics", "metabolomics", "lipidomics"
    ])

    if phase in {"PHASE1", "PHASE2", "PHASE2_3"} and biomarker_hits >= 1:
        return "Mechanistic Gap"

    if phase in {"PHASE2", "PHASE2_3"} and enrollment >= 150:
        if biomarker_hits == 0:
            return "Blind Scale Risk"
        if biomarker_hits == 1:
            return "Weak Stratification"

    if phase in {"PHASE2", "PHASE2_3"} and enrollment < 150:
        return "Expansion Opportunity"

    return "Unclear"

def assign_commercial_play(row):
    h = row.get("CommercialHypothesis")

    if h == "Mechanistic Gap":
        return pd.Series([
            "Translational / Biomarker Lead",
            "Mechanistic signal present, but biological depth still limited",
            "Add pathway-level interpretation and retrospective metabolomics depth"
        ])

    if h == "Blind Scale Risk":
        return pd.Series([
            "Clinical Development / Medical Director",
            "Large study scaling without biomarker or responder definition",
            "Introduce stratification layer to prevent signal dilution at scale"
        ])

    if h == "Weak Stratification":
        return pd.Series([
            "Translational Medicine / Biomarker Lead",
            "Initial stratification signals present but not robust",
            "Strengthen biological signal and sharpen responder definition"
        ])

    if h == "Stratification Risk":
        return pd.Series([
            "Clinical Development / Medical Director",
            "Large study without segmentation; responder dilution risk rising",
            "Identify responders and de-risk signal loss before next step"
        ])

    if h == "Expansion Opportunity":
        return pd.Series([
            "Program Lead / Asset Owner",
            "Small study approaching scale-up or portfolio decision",
            "Strengthen biological confidence before expansion"
        ])

    if h == "Late-stage Rigidity":
        return pd.Series([
            "Medical Affairs / Lifecycle Lead",
            "Core trial is advanced, but subgroup insight may still matter",
            "Support post-hoc stratification and differentiation"
        ])

    return pd.Series([
        "Unclear",
        "Unclear",
        "Unclear"
    ])

def build_outreach_hook(row):
    h = row.get("CommercialHypothesis")
    sponsor = row.get("LeadSponsor") or "your team"
    phase = row.get("PhaseBucket") or "the program"

    if h == "Mechanistic Gap":
        return f"As {sponsor} advances this {phase} program, there may be an opportunity to add pathway-level depth around the emerging biology."

    if h == "Blind Scale Risk":
        return f"As {sponsor} scales this {phase} study, the lack of a clear responder or biomarker layer may increase the risk of signal dilution."

    if h == "Weak Stratification":
        return f"As {sponsor} advances this {phase} program, early stratification signals may benefit from deeper biological resolution."

    if h == "Stratification Risk":
        return f"As {sponsor} scales this {phase} study, a key question may be whether responder heterogeneity could dilute the signal."

    if h == "Expansion Opportunity":
        return f"Before {sponsor} expands this {phase} program, there may be value in strengthening the biological rationale behind the early signal."

    if h == "Late-stage Rigidity":
        return f"Even at this stage, {sponsor} may still benefit from subgroup insight and retrospective differentiation around the readout."

    return "Potential opportunity worth a closer look."

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_trials(mode: str, logic: str, controls_tuple: tuple):
    controls = dict(controls_tuple)
    all_rows = []
    request_errors = []

    session = requests.Session()

    for term in PHARMA_TERMS:
        page_token = None

        for _ in range(MAX_PAGES_PER_QUERY):
            params = {
                "query.term": term,
                "pageSize": PAGE_SIZE,
                "format": "json"
            }
            if page_token:
                params["pageToken"] = page_token

            try:
                r = session.get(BASE_URL, params=params, timeout=TIMEOUT)
                r.raise_for_status()
                data = r.json()
            except Exception as e:
                request_errors.append({"QueryTerm": term, "Error": str(e)})
                break

            studies = data.get("studies", [])

            for study in studies:
                prot = study.get("protocolSection", {}) or {}
                ident = prot.get("identificationModule", {}) or {}
                design = prot.get("designModule", {}) or {}
                status_mod = prot.get("statusModule", {}) or {}
                outcomes_mod = prot.get("outcomesModule", {}) or {}

                lead_sponsor = get_lead_sponsor(prot)
                collaborators = get_collaborators(prot)
                countries = get_country_summary(prot)
                cluster, cluster_hits = detect_cluster(prot)

                primary_outcomes = outcomes_mod.get("primaryOutcomes", []) or []
                primary_outcome = primary_outcomes[0].get("measure", "") if primary_outcomes else ""

                phases = ",".join(design.get("phases", []) or [])

                row = {
                    "NCT": ident.get("nctId", ""),
                    "NCT_Link": make_nct_link(ident.get("nctId", "")),
                    "Title": ident.get("briefTitle", ""),
                    "OfficialTitle": ident.get("officialTitle", ""),
                    "LeadSponsor": lead_sponsor,
                    "Collaborators": "; ".join(collaborators),
                    "MatchedQueryTerm": term,
                    "MatchingTargetAccounts": "; ".join(get_matching_accounts(prot)),
                    "LeadSponsorTargetAccounts": "; ".join(lead_sponsor_matches_target(prot)),
                    "CollaboratorTargetAccounts": "; ".join(collaborator_matches_target(prot)),
                    "Status": status_mod.get("overallStatus", ""),
                    "StudyType": design.get("studyType", ""),
                    "Phases": phases,
                    "PhaseBucket": parse_phase_bucket(phases),
                    "StartDate": safe_get(status_mod, ["startDateStruct", "date"], ""),
                    "StartYear": parse_year(safe_get(status_mod, ["startDateStruct", "date"], "")),
                    "PrimaryCompletionDate": safe_get(status_mod, ["primaryCompletionDateStruct", "date"], ""),
                    "Enrollment": safe_get(design, ["enrollmentInfo", "count"], 0) or 0,
                    "PrimaryOutcome": primary_outcome,
                    "Countries": ", ".join(countries),
                    "US_SIGNAL": has_us_signal(countries),
                    "US_PURE": us_pure(countries),
                    "EU_SIGNAL": has_eu_signal(countries),
                    "LeadSponsorAcademic": lead_sponsor_is_academic(lead_sponsor),
                    "Cluster": cluster,
                    "ClusterHits": cluster_hits,
                    "ConditionsKeywordsBlob": get_conditions_keywords_blob(prot),
                    "TextBlob": get_text_blob(prot)
                }
                all_rows.append(row)

            page_token = data.get("nextPageToken")
            if not page_token:
                break

            time.sleep(REQUEST_SLEEP_SECONDS)

    df = pd.DataFrame(all_rows)

    if df.empty:
        debug_rows = [
            {"Metric": "full_rows", "Value": 0},
            {"Metric": "selected_domain_rows", "Value": 0},
            {"Metric": "phase3_watchlist_rows", "Value": 0},
            {"Metric": "request_errors", "Value": len(request_errors)},
        ]
        debug_summary = pd.DataFrame(debug_rows)
        error_df = pd.DataFrame(request_errors)
        return df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), debug_summary, error_df

    df = df.groupby("NCT", as_index=False).first()

    if mode == "Domestic":
        df = df[df["US_SIGNAL"] == True].copy()
    else:
        df = df[df["EU_SIGNAL"] == True].copy()

    if df.empty:
        debug_rows = [
            {"Metric": "full_rows", "Value": 0},
            {"Metric": "selected_domain_rows", "Value": 0},
            {"Metric": "phase3_watchlist_rows", "Value": 0},
            {"Metric": "request_errors", "Value": len(request_errors)},
        ]
        debug_summary = pd.DataFrame(debug_rows)
        error_df = pd.DataFrame(request_errors)
        return df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), debug_summary, error_df

    df["ExclusionFlags"] = df.apply(lambda row: exclusion_flags(row, mode), axis=1)
    scores = df.apply(lambda row: trigger_score(row, mode, logic, controls), axis=1)
    df["TriggerScore"] = [x[0] for x in scores]
    df["ScoreReasons"] = [x[1] for x in scores]

    max_score = df["TriggerScore"].max()

    if max_score > 0:
        df["Score_10"] = (df["TriggerScore"] / max_score * 10).round(1)
    else:
        df["Score_10"] = 0.0

    df["ScoreBand"] = df["Score_10"].apply(get_score_band)
    df["CommercialHypothesis"] = df.apply(assign_commercial_hypothesis, axis=1)
    df[["Who", "WhyNow", "WhyUs"]] = df.apply(assign_commercial_play, axis=1)
    df["OutreachHook"] = df.apply(build_outreach_hook, axis=1)

    metabolic_core = df[
        (df["LeadSponsorTargetAccounts"].fillna("") != "") &
        (df["StudyType"].fillna("").str.upper() == "INTERVENTIONAL") &
        (df["LeadSponsorAcademic"] == False) &
        (~df["ExclusionFlags"].fillna("").str.contains("title_noise", na=False)) &
        (~df["ExclusionFlags"].fillna("").str.contains("off_focus", na=False)) &
        (df["PhaseBucket"].isin(ALLOWED_CORE_PHASES)) &
        (df["Status"].fillna("").str.upper().isin(ALLOWED_CORE_STATUSES)) &
        (pd.to_numeric(df["Enrollment"], errors="coerce").fillna(0) >= MIN_ENROLLMENT_CORE) &
        (pd.to_numeric(df["StartYear"], errors="coerce").fillna(0) >= MIN_CORE_START_YEAR) &
        (df["Cluster"] == "METABOLIC_CVRM")
    ].copy().sort_values(
        by=["TriggerScore", "StartYear", "Enrollment"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    neuro_celltherapy = df[
        (df["LeadSponsorTargetAccounts"].fillna("") != "") &
        (df["StudyType"].fillna("").str.upper() == "INTERVENTIONAL") &
        (df["LeadSponsorAcademic"] == False) &
        (~df["ExclusionFlags"].fillna("").str.contains("title_noise", na=False)) &
        (~df["ExclusionFlags"].fillna("").str.contains("off_focus", na=False)) &
        (df["PhaseBucket"].isin(ALLOWED_SIDE_PHASES)) &
        (df["Status"].fillna("").str.upper().isin(ALLOWED_SIDE_STATUSES)) &
        (pd.to_numeric(df["Enrollment"], errors="coerce").fillna(0) >= MIN_ENROLLMENT_SIDE) &
        (pd.to_numeric(df["StartYear"], errors="coerce").fillna(0) >= MIN_SIDE_START_YEAR) &
        (df["Cluster"].isin(["NEURO", "CELL_THERAPY_CAR_T"]))
    ].copy().sort_values(
        by=["TriggerScore", "StartYear", "Enrollment"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    phase3_watchlist = df[
        (df["LeadSponsorTargetAccounts"].fillna("") != "") &
        (df["StudyType"].fillna("").str.upper() == "INTERVENTIONAL") &
        (df["LeadSponsorAcademic"] == False) &
        (~df["ExclusionFlags"].fillna("").str.contains("title_noise", na=False)) &
        (~df["ExclusionFlags"].fillna("").str.contains("off_focus", na=False)) &
        (df["PhaseBucket"].isin(ALLOWED_WATCHLIST_PHASES)) &
        (df["Status"].fillna("").str.upper().isin(ALLOWED_WATCHLIST_STATUSES)) &
        (pd.to_numeric(df["StartYear"], errors="coerce").fillna(0) >= MIN_WATCHLIST_START_YEAR)
    ].copy().sort_values(
        by=["TriggerScore", "StartYear", "Enrollment"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    debug_rows = [
        {"Metric": "full_rows", "Value": len(df)},
        {"Metric": "metabolic_core_rows", "Value": len(metabolic_core)},
        {"Metric": "neuro_celltherapy_rows", "Value": len(neuro_celltherapy)},
        {"Metric": "phase3_watchlist_rows", "Value": len(phase3_watchlist)},
        {"Metric": "us_pure_rows", "Value": int(df["US_PURE"].sum()) if "US_PURE" in df.columns else 0},
        {"Metric": "request_errors", "Value": len(request_errors)},
    ]
    debug_summary = pd.DataFrame(debug_rows)
    error_df = pd.DataFrame(request_errors)

    return df, metabolic_core, neuro_celltherapy, phase3_watchlist, debug_summary, error_df

# =========================================================
# UI
# =========================================================

st.markdown("""
<div style="padding:16px;border-radius:14px;background:#0f172a;color:white;margin-bottom:16px;">
  <h1 style="margin-bottom:4px;">🛰️ Atlas Radar</h1>
  <p style="margin:0;color:#cbd5e1;">by Helmut</p>
  <p style="margin:0;color:#94a3b8;font-size:12px;">ClinicalTrials.gov signal radar for commercial entry points</p>
</div>
""", unsafe_allow_html=True)

with st.expander("What is Atlas Radar? (technical overview)"):
    st.markdown("""
Atlas Radar is best used as a focused search tool for commercial entry points, not as a static list.

Start by selecting your operating mode (Domestic vs. International) and the opportunity model (Clinical Scale vs. Discovery & Translational). These define the overall lens through which trials are evaluated.

Then use the mixer to actively shape what kind of opportunities you want to see:

If you are looking for early, influenceable programs, increase Early entry and reduce Too late.
If you want large, high-value trials, increase Big programs.
If you are specifically targeting biology-driven discussions, increase Show biology and Translational depth.
If you want to avoid programs that are scaling without clarity, increase No blind scale.

Each adjustment does not add new trials — it re-ranks the same universe based on your commercial intent.

As a result, Atlas Radar can be used in different modes:

Early-entry scouting → high Early entry, high Show biology
Trial rescue / de-risking → high No blind scale, moderate Big programs
Strategic large deals → high Big programs, moderate Translational depth
Scientific positioning → high Show biology and Translational depth

The goal is not to find “all good trials”, but to surface the right trials for a specific commercial angle.

Think of it as a radar, not a report.
""")

st.caption("ClinicalTrials.gov trigger radar for Domestic Sales (US) and International Sales (EU/ROW).")

mode = st.selectbox(
    "Select Radar",
    ["Domestic", "International"]
)

logic = st.selectbox(
    "Select Opportunity Model",
    ["Clinical Scale", "Discovery & Translational"]
)

domain = st.selectbox(
    "Select Disease Domain",
    ["Metabolic / CVRM", "Neurology", "Cell Therapy", "Immunology / Inflammation", "Oncology / IO"]
)

with st.expander("Scoring mixer", expanded=False):
    c1, c2, c3 = st.columns(3)

    with c1:
        no_biomarker_penalty = st.slider("No biomarker penalty", 0, 30, 16, 1)
        biomarker_bonus = st.slider("Biomarker presence bonus", 0, 20, 6, 1)

    with c2:
        large_enrollment_bonus = st.slider("Large enrollment bonus", 0, 15, 4, 1)
        early_phase_bonus = st.slider("Early phase bonus", 0, 30, 18, 1)

    with c3:
        strong_translational_bonus = st.slider("Strong translational language bonus", 0, 30, 18, 1)
        basic_translational_bonus = st.slider("Basic translational language bonus", 0, 20, 10, 1)

controls = {
    "no_biomarker_penalty": no_biomarker_penalty,
    "biomarker_bonus": biomarker_bonus,
    "large_enrollment_bonus": large_enrollment_bonus,
    "early_phase_bonus": early_phase_bonus,
    "strong_translational_bonus": strong_translational_bonus,
    "basic_translational_bonus": basic_translational_bonus,
}

controls_tuple = tuple(sorted(controls.items()))

run = st.button("Run Atlas Radar", type="primary", use_container_width=True)
if run:
    st.session_state["run"] = True
if st.button("Clear cache"):
    st.cache_data.clear()

if st.session_state.get("run"):
    with st.spinner("Running Atlas Radar..."):
        full_df, metabolic_core, neuro_celltherapy, phase3_watchlist, debug_summary, error_df = fetch_trials(
            mode,
            logic,
            controls_tuple
        )

    selected_domain = build_domain_table(full_df, domain)

    st.subheader("Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Full", len(full_df))
    c2.metric("Selected domain", len(selected_domain))
    c3.metric("Phase 3 watchlist", len(phase3_watchlist))
    c4.metric("Errors", len(error_df))

    st.caption(
        f"Mixer: no biomarker -{no_biomarker_penalty}, biomarker +{biomarker_bonus}, "
        f"large enrollment +{large_enrollment_bonus}, early phase +{early_phase_bonus}, "
        f"strong translational +{strong_translational_bonus}, basic translational +{basic_translational_bonus}"
    )

    st.markdown(
        """
        <div style="margin-top: 8px; margin-bottom: 12px;">
            <span style="background:#b91c1c;color:white;padding:4px 8px;border-radius:6px;margin-right:8px;">Hot</span>
            <span style="background:#7c3aed;color:white;padding:4px 8px;border-radius:6px;margin-right:8px;">Warm</span>
            <span style="background:#1d4ed8;color:white;padding:4px 8px;border-radius:6px;">Cold</span>
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown("---")

    tab1, tab2, tab3 = st.tabs(
        ["Selected Domain", "Phase 3 Watchlist", "Debug"]
    )

    with tab1:
        display_df = prepare_display_df(selected_domain)
        st.dataframe(
            style_score_table(display_df),
            use_container_width=True,
            hide_index=True,
            column_config={
                "NCT_Link": st.column_config.LinkColumn("NCT", display_text=r"(NCT\d+)"),
                "Score_10": st.column_config.NumberColumn("Score / 10", format="%.1f"),
                "Enrollment": st.column_config.NumberColumn("Enrollment", format="%d"),
            }
        )

        df_download_button(
            selected_domain,
            f"atlas_radar_{mode.lower()}_{domain.lower().replace(' ', '_').replace('/', '').replace('__', '_')}.csv",
            "Download Selected Domain CSV"
        )

    with tab2:
        display_df = prepare_display_df(phase3_watchlist)
        st.dataframe(
            style_score_table(display_df),
            use_container_width=True,
            hide_index=True,
            column_config={
                "NCT_Link": st.column_config.LinkColumn("NCT", display_text=r"(NCT\d+)"),
                "Score_10": st.column_config.NumberColumn("Score / 10", format="%.1f"),
                "Enrollment": st.column_config.NumberColumn("Enrollment", format="%d"),
            }
        )

        df_download_button(
            phase3_watchlist,
            f"atlas_radar_{mode.lower()}_phase3_watchlist.csv",
            "Download Phase 3 Watchlist CSV"
        )

    with tab3:
        st.write("Debug summary")
        st.dataframe(debug_summary, use_container_width=True, hide_index=True)

        if not error_df.empty:
            st.write("Request errors")
            st.dataframe(error_df, use_container_width=True, hide_index=True)

        df_download_button(
            full_df,
            f"atlas_radar_{mode.lower()}_full.csv",
            "Download Full CSV"
        )

        st.divider()
        st.subheader("Generate Outreach Email")

        email_df = selected_domain.copy()

        if email_df.empty:
            st.info("No trials available for email generation.")
        else:
            selected_index = st.selectbox(
                "Select Trial",
                email_df.index,
                format_func=lambda i: (
                    f"{email_df.loc[i].get('LeadSponsor', '')} | "
                    f"{email_df.loc[i].get('PhaseBucket', '')} | "
                    f"{str(email_df.loc[i].get('Title', ''))[:80]}"
                )
            )

            selected_row = email_df.loc[selected_index]

            if st.button("Generate Email"):
                prompt = f"""
Write a short 120-150 word, high-intelligence outreach email to a senior pharma stakeholder based on the clinical trial below. Your goal is to trigger a thoughtful reply or a referral.

Context:
Trial: {selected_row.get('NCT_Link', '')}
Company: {selected_row.get('LeadSponsor', '')}
Phase: {selected_row.get('PhaseBucket', '')}
Title: {selected_row.get('Title', '')}
Primary Outcome: {selected_row.get('PrimaryOutcome', '')}
Commercial Hypothesis: {selected_row.get('CommercialHypothesis', '')}

Write like a peer, not a vendor. Use a conversational, human tone appropriate for a peer email. 
Soften the language slightly; avoid sounding formal, academic, or like a manuscript.

You may use light hedging (e.g. "I may be wrong", "it seems", "one question I had") to make the tone more open and less assertive.

Avoid dense, compressed sentences; keep phrasing natural and readable in email form.

Write as if this is a thoughtful note to a colleague, not a publication.Start with a concrete observation about the trial design, endpoint, population, or measurement layer. 
Do not start with evaluative statements (e.g. "X is the right layer", "X is important").

Keep the email tight and selective. Do not explain every concept. 
State one observation, one risk, and one implication. 
Avoid listing multiple mechanisms or pathways; name at most one if necessary.

Mention any specific biomarker (e.g. NfL) at most once. 
After introducing it, refer to it indirectly (e.g. "the marker", "that layer").

Avoid explanatory or didactic language. 
Do not sound like a review or teaching text.
Avoid phrases like "the implication is", "this means", or "in that setting".

Prefer under-explaining over over-explaining.

Write as if you noticed one specific tension in the trial, not as if you are explaining the disease or educating the reader. Mention any specific biomarker (e.g. NfL) at most once. Do not repeat it.
After introducing it, refer to it indirectly (e.g. "the marker", "that layer"). Keep the email tight and selective. Do not explain every concept. 
State one observation, one risk, and one implication. 
Avoid listing multiple mechanisms or pathways; name at most one or two.
Do not sound like a review or teaching text.
Prefer under-explaining over over-explaining. No sales language, no frameworks. Do not use words like "brief" or "quick".

Start with a concrete observation grounded in the trial design, endpoint, population, or measurement layer.

Measurement logic:
For ALS and MS, explicitly anchor the reasoning in NfL as the primary measurement layer before introducing any downstream or complementary layers.
If a biomarker, imaging modality, clinical scale, endpoint, or molecular measurement is explicitly mentioned in the trial, anchor the email in that measurement and explain what it captures versus what it misses.
If none is mentioned, infer the dominant measurement layer typically used in this disease area, such as NfL in ALS or MS, pTau217 or amyloid/tau PET in Alzheimers, alpha-synuclein in Parkinsons, HbA1c or CGM in diabetes, LDL-C or troponin in cardiovascular disease, eGFR or UACR in kidney disease, ctDNA, PD-L1, ORR or PFS in oncology, or cytokines and flow cytometry in immunology or cell therapy.
Do not make abstract statements about biology or signal. Always tie the reasoning to one concrete measurement.

Translate the Commercial Hypothesis into one specific, non-obvious risk tailored to this trial. Embed Why Now implicitly through phase, scale, status, timing, or readout risk. Embed Why Us implicitly by hinting at pathway-level metabolomic resolution, without pitching.

Include exactly one soft, open-ended question. Keep tone calm, precise, slightly tentative, high-status. No enthusiasm. No meeting request. No hard close.

End with this exact redirect sentence:
If this sits elsewhere on your side, I would appreciate a pointer.

Output only subject line and email.
"""

                response = client.responses.create(
                    model="gpt-5.5",
                    input=prompt
                )

                st.write(response.output_text)
