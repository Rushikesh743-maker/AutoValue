# Negotiation Intelligence Engine Documentation

## 1. Overview
The **Negotiation Intelligence Engine** (`NegotiationService`) derives evidence-supported negotiation corridors for prospective buyers and sellers. It synthesizes point estimates, conformal prediction intervals, and empirical market quartiles into actionable, mathematically grounded target ranges and talking points.

---

## 2. Negotiation Corridors & Target Derivation

The negotiation engine produces three key price anchors:

### 2.1 Evidence-Supported Target (Recommended)
- **Concept**: The central fair-market value backed by empirical observations and model predictions.
- **Formula**:
  $$T_{\text{evidence}} = \text{round}\left(\frac{\hat{V}_{\text{ML}} + M_{\text{obs}}}{2}\right) \quad \text{if } M_{\text{obs}} \text{ exists, else } \hat{V}_{\text{ML}}$$

### 2.2 Aggressive Target (Opening Counter-Offer)
- **Concept**: A lower-bound anchor suitable for initial buyer bids, anchored at either the 25th empirical percentile or conformal lower prediction bound.
- **Formula**:
  $$T_{\text{aggressive}} = \min(P_{25}, I_{\text{low}}, \hat{V}_{\text{ML}} \times 0.93)$$

### 2.3 Conservative Target (Maximum Ceiling / Reserve)
- **Concept**: The upper-bound limit before a vehicle is considered uncompetitively priced.
- **Formula**:
  $$T_{\text{conservative}} = \max(P_{75}, I_{\text{high}}, \hat{V}_{\text{ML}} \times 1.05)$$

---

## 3. Negotiation Gap Analysis
When an asking price $P_{\text{ask}}$ is present:
$$\text{Gap} = P_{\text{ask}} - T_{\text{evidence}}$$

Buyer leverage is classified into 4 tiers:
- **`HIGH_BUYER_LEVERAGE`**: $P_{\text{ask}} > T_{\text{evidence}} \times 1.08$ (Asking price is substantially above central market).
- **`MODERATE_BUYER_LEVERAGE`**: $P_{\text{ask}} > T_{\text{evidence}} \times 1.02$ (Asking price is moderately above central market).
- **`NEUTRAL_LEVERAGE`**: $T_{\text{evidence}} \times 0.95 \le P_{\text{ask}} \le T_{\text{evidence}} \times 1.02$ (Asking price aligns with central market).
- **`SELLER_FAVORED`**: $P_{\text{ask}} < T_{\text{evidence}} \times 0.95$ (Asking price is already below fair market value).

---

## 4. Evidence-Backed Talking Points Generation
The engine automatically generates dynamic, factual talking points without hyperbole:
1. **Quartile Positioning**: Explaining where the asking price sits relative to $P_{25}$, $M_{\text{obs}}$, and $P_{75}$.
2. **Model Fair Value Delta**: Explicitly stating the monetary gap between asking price and calibrated ML valuation.
3. **Evidence Density**: Highlighting the number of active marketplace comparables supporting the negotiation corridor.

---

## 5. Mandatory Transparency Disclaimers
All negotiation outputs are accompanied by an explicit disclaimer:
> *"Negotiation ranges represent evidence-supported pricing corridors derived from central market distributions and prediction intervals. They do not constitute guaranteed transaction commitments or appraisal certificates."*
