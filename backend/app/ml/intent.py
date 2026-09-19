"""Intent classifier and entity extraction for "Ask the Freight Desk".

A TF-IDF (word + character n-gram) logistic-regression model trained at start-up on a small
hand-written set of example questions per intent. It routes a question to one of the platform's
own engines; it does not generate free text. Cross-validated accuracy is reported by
`model_info()` and is measured on paraphrases inside this same training set, so it is an
in-distribution figure, not an external benchmark.
"""

import re
from dataclasses import dataclass
from functools import lru_cache

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.pipeline import FeatureUnion, Pipeline

TRAINING: dict[str, list[str]] = {
    "market_now": [
        "what is the baltic dry index today", "how is the freight market right now", "current BDI level", "where is capesize trading",
        "is the market up or down this week", "how are dry bulk rates doing", "give me a market snapshot", "what are panamax rates at the moment",
        "latest supramax index value", "is freight expensive now compared to history", "how volatile is the market lately", "market update please",
    ],
    "forecast": [
        "what will BDI be next week", "forecast capesize for the next 14 days", "predict freight rates for the next month", "where is the baltic index heading",
        "will freight go up or down", "give me a 30 day forecast", "projected panamax rate in two weeks", "expected BDI in 7 days",
        "what is the outlook for dry bulk freight", "is now a good time to fix or should I wait for rates to fall", "should i wait for the market to drop", "will rates rise next week",
    ],
    "recommend_origin": [
        "which origin should I buy coking coal from", "cheapest origin for paradip", "compare australia mozambique and russia for haldia", "best country to import coal from for vizag",
        "rank the origins for 75000 tonnes", "where should we source coal", "australia or indonesia which is better", "recommend a source country and vessel for gangavaram",
        "which route is cheapest for a cargo to dhamra", "compare origins for my cargo", "what is the best sourcing option", "which supplier country gives lowest freight",
    ],
    "port_fit": [
        "can a capesize berth at haldia", "which vessels fit paradip", "what is the maximum draft at vizag", "will a panamax fit at gopalpur",
        "what ships can call at dhamra", "berth compatibility for sagar sandheads", "is haldia draft enough for a supramax", "which vessel classes are accepted at gangavaram",
        "what are the port limits for vessel size", "check vessel to port fit", "can a 200000 dwt ship enter paradip", "loa and beam limits at haldia",
    ],
    "risk": [
        "how risky is the route from australia to haldia", "what is the risk score for russia to paradip", "any disruptions on the mozambique route", "route risk for indonesia to vizag",
        "what could go wrong on the australia route", "are there disruptions affecting coal shipping", "how risky is shipping from the us", "warn me about risks for my next voyage",
        "which route is safest", "risk assessment for the red sea", "is there cyclone risk on the bay of bengal", "give me the risk breakdown",
    ],
    "congestion": [
        "which port is most congested", "how busy is paradip", "are there delays at visakhapatnam", "port congestion right now",
        "which port has the longest turnaround", "how long do ships wait at haldia", "where will my vessel wait the least", "compare port turnaround times",
        "is there a queue at the ports", "which east coast port is fastest", "what is the average turnaround time", "idle time at the ports",
    ],
    "haldia": [
        "tell me about haldia port", "how does the haldia lock work", "how big are coal ships at haldia", "why do vessels lighten at sagar",
        "what is the typical cargo size at haldia", "how long from sandheads to haldia", "what happens when a vessel reaches haldia", "explain haldia dock complex",
        "how many coal vessels come to haldia", "how fast is berth 4a unloading", "what is the draft limit into haldia", "how do coking coal ships get to haldia",
    ],
    "coa_vs_spot": [
        "should we use a contract of affreightment or spot", "coa versus spot", "is it better to lock in a long term contract", "when does a multi voyage contract beat spot",
        "how much can we save with a coa", "should we fix on contract or stay in the spot market", "compare spot and contract freight cost", "is a 12 month contract worth it",
        "what is the savings from contracting", "how do i hedge freight cost", "spot or short term charter", "lock in freight for the year",
    ],
    "demand": [
        "how much coking coal does sail import", "what is sail's coal requirement", "how much coal do we need next quarter", "sail import dependence on coking coal",
        "how much of sail's coal is imported", "what is the steel production of sail", "estimate the coal demand for the steel plants", "sail crude steel output",
        "tonnes of coking coal per year", "how many vessels does sail need", "annual coal import volume", "how much cargo must we charter",
    ],
    "data_sources": [
        "where does your data come from", "what data do you use", "which datasets are real", "is the data live or simulated",
        "how were the models trained", "how accurate is the forecast", "what is the forecast accuracy", "can i trust these numbers",
        "which parts are simulated", "what are your data sources", "how good is the model", "how was this trained",
    ],
    "help": [
        "help", "what can you do", "hello", "hi there", "what can i ask you", "how do i use this",
        "show me what you can answer", "good morning", "who are you", "what questions do you understand", "thanks", "guide me",
    ],
}

INDEX_WORDS = [
    (r"\bcape(size)?\b|\bbci\b", "BCI"), (r"\bpanamax\b|\bbpi\b", "BPI"), (r"\bsupramax\b|\bbsi\b", "BSI"), (r"\bhandy(size)?\b|\bbhsi\b", "BHSI"),
    (r"\bbaltic\b|\bbdi\b|\bdry index\b", "BDI"),
]
ORIGINS = [
    (r"australia|aussie|queensland|hay point|gladstone|abbot point|dalrymple", "Australia"),
    (r"\bus\b|\busa\b|united states|america|hampton roads|baltimore", "United States"),
    (r"mozambique|beira|maputo|nacala", "Mozambique"),
    (r"russia|vostochny|nakhodka|vanino", "Russia"),
    (r"indonesia|kalimantan|balikpapan|samarinda", "Indonesia"),
]
PORT_ALIASES = [
    (r"haldia|kolkata|hooghly", "Haldia"), (r"paradip", "Paradip"), (r"vizag|visakhapatnam|visakha", "Visakhapatnam"),
    (r"gangavaram", "Gangavaram"), (r"dhamra", "Dhamra"), (r"gopalpur", "Gopalpur"), (r"sagar|sandheads", "Sagar / Sandheads"),
]


@dataclass
class Entities:
    index_name: str | None = None
    port: str | None = None
    origin: str | None = None
    horizon_days: int | None = None
    cargo_tonnes: float | None = None


def extract_entities(q: str) -> Entities:
    t = q.lower()
    e = Entities()
    for pat, name in INDEX_WORDS:
        if re.search(pat, t):
            e.index_name = name
            break
    for pat, name in PORT_ALIASES:
        if re.search(pat, t):
            e.port = name
            break
    for pat, name in ORIGINS:
        if re.search(pat, t):
            e.origin = name
            break
    m = re.search(r"(\d{1,3})\s*[- ]?\s*(day|days|d)\b", t)
    if m:
        e.horizon_days = max(1, min(90, int(m.group(1))))
    elif re.search(r"fortnight|two weeks|2 weeks", t):
        e.horizon_days = 14
    elif re.search(r"month", t):
        e.horizon_days = 30
    elif re.search(r"week", t):
        e.horizon_days = 7
    m = re.search(r"(\d[\d,]*(?:\.\d+)?)\s*(k|kt|mt|t|tonnes|tons|tonne|dwt)\b", t)
    if m:
        n = float(m.group(1).replace(",", ""))
        unit = m.group(2)
        e.cargo_tonnes = n * 1000 if unit in ("k", "kt") else n * 1_000_000 if unit == "mt" else n
    return e


def tag(q: str) -> str:
    """Append entity marker tokens so the classifier can use "a port was named" style signals."""
    e = extract_entities(q)
    extra = []
    if e.index_name: extra.append("ENTINDEX")
    if e.port: extra.append("ENTPORT")
    if e.origin: extra.append("ENTORIGIN")
    if e.horizon_days: extra.append("ENTHORIZON")
    if e.cargo_tonnes: extra.append("ENTCARGO")
    return q + " " + " ".join(extra)


IDX = ["BDI", "capesize", "panamax", "supramax", "handysize", "the baltic index"]
PORTS = ["Haldia", "Paradip", "Vizag", "Gangavaram", "Dhamra", "Gopalpur", "Sagar Sandheads"]
ORIG = ["Australia", "Russia", "Mozambique", "Indonesia", "the US"]
TEMPLATES: dict[str, list[str]] = {
    "forecast": ["forecast {i} for the next {n} days", "what will {i} be in {n} days", "will {i} rise or fall over {n} days", "predict {i} {n} days ahead", "{i} outlook next {n} days"],
    "market_now": ["how is {i} today", "current {i} level", "what is {i} trading at", "is {i} up or down this week", "latest {i} value"],
    "recommend_origin": ["cheapest origin for {p}", "compare {o} and {o2} for {p}", "best source of coal for {p}", "rank origins for {c} tonnes to {p}", "should we buy from {o} or {o2}"],
    "port_fit": ["can a {v} berth at {p}", "max draft at {p}", "which vessels fit {p}", "will a {v} fit at {p}", "loa limit at {p}"],
    "risk": ["risk from {o} to {p}", "how risky is the {o} route", "risk score {o} {p}", "disruptions on the {o} route to {p}", "is shipping from {o} to {p} safe"],
    "congestion": ["how busy is {p}", "delays at {p}", "turnaround time at {p}", "will my vessel wait at {p}", "is {p} congested"],
    "haldia": ["how does the lock at {p} work", "cargo size at {p}", "how long to reach {p} from sandheads", "berth 4a at {p}", "coal ships at {p}"],
}


def augmented() -> tuple[list[str], list[str]]:
    x, y = [], []
    n = 0
    for intent, temps in TEMPLATES.items():
        for t in temps:
            for k in range(4):
                n += 1
                q = t.format(i=IDX[(n + k) % len(IDX)], p=PORTS[(n * 3 + k) % len(PORTS)] if intent != "haldia" else "Haldia",
                             o=ORIG[(n + k) % len(ORIG)], o2=ORIG[(n + k + 2) % len(ORIG)], v=["capesize", "panamax", "supramax", "handysize"][(n + k) % 4],
                             n=[7, 14, 30, 10][k % 4], c=[50000, 75000, 150000, 35000][k % 4])
                x.append(q)
                y.append(intent)
    return x, y


def _pipeline() -> Pipeline:
    feats = FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, lowercase=True)),
        ("char", TfidfVectorizer(analyzer="char_wb", ngram_range=(2, 4), sublinear_tf=True, lowercase=True)),
    ])
    return Pipeline([("features", feats), ("clf", LogisticRegression(C=12, max_iter=3000))])


def _handwritten() -> tuple[list[str], list[str]]:
    x, y = [], []
    for intent, examples in TRAINING.items():
        x += examples
        y += [intent] * len(examples)
    return x, y


def _xy() -> tuple[list[str], list[str]]:
    hx, hy = _handwritten()
    ax, ay = augmented()
    return [tag(q) for q in hx + ax], hy + ay


@lru_cache(maxsize=1)
def model() -> Pipeline:
    x, y = _xy()
    return _pipeline().fit(x, y)


def classify(question: str, top_k: int = 3) -> list[tuple[str, float]]:
    m = model()
    probs = m.predict_proba([tag(question)])[0]
    order = np.argsort(probs)[::-1][:top_k]
    return [(str(m.classes_[i]), float(probs[i])) for i in order]


@lru_cache(maxsize=1)
def model_info() -> dict:
    hx, hy = _handwritten()
    ax, ay = augmented()
    accs = []
    for tr, te in StratifiedKFold(5, shuffle=True, random_state=7).split(hx, hy):
        xt = [tag(hx[i]) for i in tr] + [tag(q) for q in ax]
        yt = [hy[i] for i in tr] + ay
        m = _pipeline().fit(xt, yt)
        pred = m.predict([tag(hx[i]) for i in te])
        accs.append(float(np.mean(pred == np.array([hy[i] for i in te]))))
    return {
        "algorithm": "TF-IDF (word 1-2 grams + char 2-4 grams) + entity marker tokens + logistic regression",
        "intents": len(TRAINING),
        "training_examples": len(hx) + len(ax),
        "handwritten_examples": len(hx),
        "template_examples": len(ax),
        "cv_accuracy_mean": round(float(np.mean(accs)), 3),
        "cv_accuracy_std": round(float(np.std(accs)), 3),
        "note": "5-fold accuracy on held-out hand-written questions (templates always in training). Small, in-distribution test set; not an external benchmark.",
    }
