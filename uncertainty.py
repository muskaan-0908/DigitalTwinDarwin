import re

HIGH_UNCERTAINTY = [
    "I confess", "I am not certain", "it appears to me",
    "I suspect", "perhaps", "it seems probable", "I venture",
    "I am far from sure", "I cannot say", "it may be",
    "I hesitate", "I am doubtful", "conjecture"
]
MEDIUM_UNCERTAINTY = [
    "I believe", "I think", "in my opinion", "it is likely",
    "I am inclined", "one might suppose", "I imagine",
    "as far as I can judge", "I fancy"
]
LOW_UNCERTAINTY = [
    "I am convinced", "I am certain", "it is clear",
    "undoubtedly", "there can be no doubt", "I have no hesitation",
    "the facts show", "the evidence is plain"
]

def get_uncertainty_score(text: str) -> dict:
    text_lower = text.lower()
    
    high  = sum(1 for p in HIGH_UNCERTAINTY  if p in text_lower)
    med   = sum(1 for p in MEDIUM_UNCERTAINTY if p in text_lower)
    low   = sum(1 for p in LOW_UNCERTAINTY   if p in text_lower)

    total = high + med + low
    if total == 0:
        score = 35  
    else:
        score = min(100, int(((high * 3 + med * 1.5) / (total * 3)) * 100))

    if score >= 65:
        label, colour, icon = "Speculative", "#c0392b"
    elif score >= 35:
        label, colour, icon = "Tentative",   "#e67e22"
    else:
        label, colour, icon = "Confident",   "#2d5a30"

    return {"score": score, "label": label, "colour": colour}