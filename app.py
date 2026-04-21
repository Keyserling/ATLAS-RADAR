import io
import re
import time
import requests
import pandas as pd
import streamlit as st

st.set_page_config(page_title="Atlas Radar", layout="wide")

# =========================================================
# CONFIG
# =========================================================

BASE_URL = "https://clinicaltrials.gov/api/v2/studies"
PAGE_SIZE = 200
MAX_PAGES_PER_QUERY = 4
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
    "Austria","Belgium","Bulgaria","Croatia","Cyprus","Czechia","Czech Republic","Denmark","Estonia",
    "Finland","France","Germany","Greece","Hungary","Ireland","Italy","Latvia","Lithuania","Luxembourg",
    "Malta","Netherlands","Poland","Portugal","Romania","Slovakia","Slovenia","Spain","Sweden",
    "Switzerland","United Kingdom","Norway","Iceland","Liechtenstein"
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
    return matched

def lead_sponsor_matches_target(protocol):
    lead = get_lead_sponsor(protocol).lower()
    matches = []
    for canonical_name, aliases in TARGET_ACCOUNT_ALIASES.items():
        if any(alias in lead for alias in aliases):
            matches.append(canonical_name)
    return matches

def collaborator_matches_target(protocol):
    collabs = " | ".join(get_collaborators(protocol)).lower()
    matches = []
    for canonical_name, aliases in TARGET_ACCOUNT_ALIASES.items():
        if any(alias in collabs for alias in aliases):
            matches.append(canonical_name)
    return matches

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
    oncology_hits = count_matches(combined, ONCOLOGY_OTHER_TERMS)

    if metabolic_hits >= 1:
        return "METABOLIC_CVRM", metabolic_hits
    if cart_strong_hits >= 1:
        return "CELL_THERAPY_CAR_T", cart_strong_hits + cart_support_hits
    if neuro_strong_hits >= 1:
        return "NEURO", neuro_strong_hits + neuro_support_hits
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

    if row.get("Cluster") == "ONCOLOGY_OTHER":
        flags.append("oncology_other")

    if row.get("Cluster") == "OTHER":
        flags.append("off_focus")

    if mode == "Domestic":
        if not row.get("US_SIGNAL"):
            flags.append("no_us_signal")
    else:
        if not row.get("EU_SIGNAL"):
            flags.append("no_eu_signal")

    return "; ".join(flags)

def trigger_score(row, mode, logic):
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
        enrollment = int(row.get("Enrollment") or 0)
    except Exception:
        enrollment = 0

    sy = row.get("StartYear")
    po = (row.get("PrimaryOutcome") or "").lower()
    blob = f"{row.get('ConditionsKeywordsBlob','')} {row.get('TextBlob','')}".lower()
    title_blob = f"{row.get('Title','')} {row.get('OfficialTitle','')}".lower()

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
        elif cluster == "ONCOLOGY_OTHER":
            score -= 20
            reasons.append("oncology other")
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
            score += 8
            reasons.append("enrollment >=500")
        elif enrollment >= 150:
            score += 5
            reasons.append("enrollment >=150")

    elif logic == "Discovery & Translational":
        if phase_bucket == "PHASE1":
            score += 18
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
        elif cluster == "ONCOLOGY_OTHER":
            score -= 10
            reasons.append("oncology other")
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
            score += 18
            reasons.append("strong translational language")
        elif kw_hits >= 1:
            score += 10
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

    if any(k in po for k in BIOMARKER_KEYWORDS):
        score += 5
        reasons.append("primary biomarker signal")
    elif any(k in blob for k in BIOMARKER_KEYWORDS):
        score += 3
        reasons.append("biomarker language")

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

@st.cache_data(show_spinner=False, ttl=3600)
def fetch_trials(mode: str):
    all_rows = []

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

            r = requests.get(BASE_URL, params=params, timeout=TIMEOUT)
            r.raise_for_status()
            data = r.json()

            studies = data.get("studies", [])

            for st in studies:
                prot = st.get("protocolSection", {}) or {}
                ident = prot.get("identificationModule", {}) or {}
                design = prot.get("designModule", {}) or {}
                status_mod = prot.get("statusModule", {}) or {}
                outcomes_mod = prot.get("outcomesModule", {}) or {}

                lead_sponsor = get_lead_sponsor(prot)
                collaborators = get_collaborators(prot)
                countries = get_country_summary(prot)
                cluster, cluster_hits = detect_cluster(prot)
                text_blob = get_text_blob(prot)

                primary_outcomes = outcomes_mod.get("primaryOutcomes", []) or []
                primary_outcome = primary_outcomes[0].get("measure", "") if primary_outcomes else ""

                phases = ",".join(design.get("phases", []) or [])

                row = {
                    "NCT": ident.get("nctId", ""),
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
                    "TextBlob": text_blob
                }
                all_rows.append(row)

            page_token = data.get("nextPageToken")
            if not page_token:
                break
            time.sleep(REQUEST_SLEEP_SECONDS)

    df = pd.DataFrame(all_rows)
    if df.empty:
        return df, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    df = df.groupby("NCT", as_index=False).first()

    if mode == "Domestic":
        df = df[df["US_SIGNAL"] == True].copy()
    else:
        df = df[df["EU_SIGNAL"] == True].copy()

    df["ExclusionFlags"] = df.apply(lambda row: exclusion_flags(row, mode), axis=1)
    scores = df.apply(lambda row: trigger_score(row, mode, logic), axis=1)
    df["TriggerScore"] = [x[0] for x in scores]
    df["ScoreReasons"] = [x[1] for x in scores]

    metabolic_core = df[
        (df["LeadSponsorTargetAccounts"].fillna("") != "") &
        (df["StudyType"].fillna("").str.upper() == "INTERVENTIONAL") &
        (df["LeadSponsorAcademic"] == False) &
        (~df["ExclusionFlags"].fillna("").str.contains("title_noise")) &
        (~df["ExclusionFlags"].fillna("").str.contains("oncology_other")) &
        (~df["ExclusionFlags"].fillna("").str.contains("off_focus")) &
        (df["PhaseBucket"].isin(ALLOWED_CORE_PHASES)) &
        (df["Status"].fillna("").str.upper().isin(ALLOWED_CORE_STATUSES)) &
        (pd.to_numeric(df["Enrollment"], errors="coerce").fillna(0) >= MIN_ENROLLMENT_CORE) &
        (pd.to_numeric(df["StartYear"], errors="coerce").fillna(0) >= MIN_CORE_START_YEAR) &
        (df["Cluster"] == "METABOLIC_CVRM")
    ].copy().sort_values(
        by=["TriggerScore", "StartDate", "Enrollment"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    neuro_celltherapy = df[
        (df["LeadSponsorTargetAccounts"].fillna("") != "") &
        (df["StudyType"].fillna("").str.upper() == "INTERVENTIONAL") &
        (df["LeadSponsorAcademic"] == False) &
        (~df["ExclusionFlags"].fillna("").str.contains("title_noise")) &
        (~df["ExclusionFlags"].fillna("").str.contains("oncology_other")) &
        (~df["ExclusionFlags"].fillna("").str.contains("off_focus")) &
        (df["PhaseBucket"].isin(ALLOWED_SIDE_PHASES)) &
        (df["Status"].fillna("").str.upper().isin(ALLOWED_SIDE_STATUSES)) &
        (pd.to_numeric(df["Enrollment"], errors="coerce").fillna(0) >= MIN_ENROLLMENT_SIDE) &
        (pd.to_numeric(df["StartYear"], errors="coerce").fillna(0) >= MIN_SIDE_START_YEAR) &
        (df["Cluster"].isin(["NEURO", "CELL_THERAPY_CAR_T"]))
    ].copy().sort_values(
        by=["TriggerScore", "StartDate", "Enrollment"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    phase3_watchlist = df[
        (df["LeadSponsorTargetAccounts"].fillna("") != "") &
        (df["StudyType"].fillna("").str.upper() == "INTERVENTIONAL") &
        (df["LeadSponsorAcademic"] == False) &
        (~df["ExclusionFlags"].fillna("").str.contains("title_noise")) &
        (~df["ExclusionFlags"].fillna("").str.contains("oncology_other")) &
        (~df["ExclusionFlags"].fillna("").str.contains("off_focus")) &
        (df["PhaseBucket"].isin(ALLOWED_WATCHLIST_PHASES)) &
        (df["Status"].fillna("").str.upper().isin(ALLOWED_WATCHLIST_STATUSES)) &
        (pd.to_numeric(df["StartYear"], errors="coerce").fillna(0) >= MIN_WATCHLIST_START_YEAR)
    ].copy().sort_values(
        by=["TriggerScore", "StartDate", "Enrollment"],
        ascending=[False, False, False]
    ).reset_index(drop=True)

    debug_rows = [
        {"Metric": "full_rows", "Value": len(df)},
        {"Metric": "metabolic_core_rows", "Value": len(metabolic_core)},
        {"Metric": "neuro_celltherapy_rows", "Value": len(neuro_celltherapy)},
        {"Metric": "phase3_watchlist_rows", "Value": len(phase3_watchlist)},
        {"Metric": "us_pure_rows", "Value": int(df["US_PURE"].sum()) if "US_PURE" in df.columns else 0},
    ]
    debug_summary = pd.DataFrame(debug_rows)

    return df, metabolic_core, neuro_celltherapy, phase3_watchlist, debug_summary

def df_download_button(df: pd.DataFrame, filename: str, label: str):
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label=label,
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        use_container_width=True,
    )

# =========================================================
# UI
# =========================================================

st.title("Atlas Radar")
st.caption("ClinicalTrials.gov trigger radar for Domestic Sales (US) and International Sales (EU/ROW).")

mode = st.selectbox(
    "Select Radar",
    ["Domestic", "International"]
)

logic = st.selectbox(
    "Select Opportunity Model",
    ["Clinical Scale", "Discovery & Translational"]
)

run = st.button("Run Atlas Radar", type="primary", use_container_width=True)

if run:
    with st.spinner("Running Atlas Radar... this can take a little while on first load."):
        full_df, metabolic_core, neuro_celltherapy, phase3_watchlist, debug_summary = fetch_trials(mode)

    st.subheader("Summary")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Full", len(full_df))
    c2.metric("Metabolic core", len(metabolic_core))
    c3.metric("Neuro / Cell therapy", len(neuro_celltherapy))
    c4.metric("Phase 3 watchlist", len(phase3_watchlist))

    st.markdown("---")

    tab1, tab2, tab3, tab4 = st.tabs(
        ["Metabolic Core", "Neuro / Cell Therapy", "Phase 3 Watchlist", "Debug"]
    )

    with tab1:
        st.dataframe(metabolic_core, use_container_width=True, hide_index=True)
        df_download_button(
            metabolic_core,
            f"atlas_radar_{mode.lower()}_metabolic_core.csv",
            "Download Metabolic Core CSV"
        )

    with tab2:
        st.dataframe(neuro_celltherapy, use_container_width=True, hide_index=True)
        df_download_button(
            neuro_celltherapy,
            f"atlas_radar_{mode.lower()}_neuro_celltherapy.csv",
            "Download Neuro / Cell Therapy CSV"
        )

    with tab3:
        st.dataframe(phase3_watchlist, use_container_width=True, hide_index=True)
        df_download_button(
            phase3_watchlist,
            f"atlas_radar_{mode.lower()}_phase3_watchlist.csv",
            "Download Phase 3 Watchlist CSV"
        )

    with tab4:
        st.dataframe(debug_summary, use_container_width=True, hide_index=True)
        df_download_button(
            full_df,
            f"atlas_radar_{mode.lower()}_full.csv",
            "Download Full CSV"
        )
