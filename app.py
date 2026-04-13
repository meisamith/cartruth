import os
import json
import sqlite3
import traceback
from datetime import datetime, timedelta, timezone
from flask import Flask, render_template, request, jsonify
from dotenv import load_dotenv
import anthropic

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev-secret")

DB_PATH = "cache.db"
CACHE_TTL_DAYS = 7

# ── DB helpers ────────────────────────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS car_cache (
            car_model TEXT PRIMARY KEY,
            report_data TEXT,
            created_at TIMESTAMP
        )
        """
    )
    conn.commit()
    conn.close()


def get_cached_report(car_model: str):
    """Return (report_dict, True) if a fresh cache hit, else (None, False)."""
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute(
        "SELECT report_data, created_at FROM car_cache WHERE car_model = ?",
        (car_model,)
    ).fetchone()
    conn.close()
    if row:
        created_at = datetime.fromisoformat(row[1]).replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - created_at < timedelta(days=CACHE_TTL_DAYS):
            return json.loads(row[0]), True
    return None, False


def save_to_cache(car_model: str, report: dict):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO car_cache (car_model, report_data, created_at)
        VALUES (?, ?, ?)
        ON CONFLICT(car_model) DO UPDATE SET
            report_data = excluded.report_data,
            created_at  = excluded.created_at
        """,
        (car_model, json.dumps(report), datetime.now(timezone.utc).isoformat())
    )
    conn.commit()
    conn.close()


# ── Claude report generator ───────────────────────────────────────────────────

REPORT_PROMPT = """You are CarTruth, an honest car advisor for Indian buyers. Generate a comprehensive car report for: {car_name}

Return ONLY a valid JSON object — no markdown, no code fences, no explanation. Use this exact structure:

{{
  "car_name": "<full display name, e.g. Maruti Swift ZXi>",
  "segment": "<e.g. Hatchback / Sedan / SUV / MUV>",
  "price_range": "<e.g. ₹6.5–9.5L (ex-showroom)>",
  "mileage": {{
    "claimed": "<ARAI figure, e.g. 23.2 km/l>",
    "real_world": "<owner-reported range, e.g. 17–19 km/l city>",
    "difference": "<gap, e.g. 4–6 km/l>"
  }},
  "ownership_cost": {{
    "insurance_year1": "<e.g. ₹18,000–22,000>",
    "service_10k": "<e.g. ₹3,500>",
    "service_20k": "<e.g. ₹5,500>",
    "service_40k": "<e.g. ₹8,500>",
    "tyre_replacement": "<set of 4, e.g. ₹14,000–18,000>",
    "annual_maintenance": "<e.g. ₹12,000–18,000/year>",
    "local_mechanic_savings": "<vs authorised service, e.g. ₹4,000–6,000/year>"
  }},
  "common_problems": [
    {{
      "name": "<short name>",
      "severity": "<High|Medium|Low>",
      "description": "<1-2 sentences from real owner complaints>",
      "fix_cost": "<e.g. ₹8,000–15,000>"
    }}
  ],
  "checklist": {{
    "new_car": ["<actionable tip>", "..."],
    "used_car": ["<actionable tip>", "..."]
  }},
  "emergency": {{
    "battery_dead": ["<step 1>", "<step 2>", "..."],
    "flat_tyre":    ["<step 1>", "<step 2>", "..."],
    "breakdown":    ["<step 1>", "<step 2>", "..."]
  }},
  "verdict": {{
    "cartruth_rating": "<number>/10",
    "honest_sentence": "<1 honest sentence — good AND bad>",
    "who_should_buy":   "<specific buyer profile>",
    "who_should_avoid": "<specific buyer profile>",
    "hidden_strengths": "<non-obvious positive>",
    "hidden_weaknesses":"<non-obvious negative>"
  }}
}}

Rules:
- common_problems: exactly 5 items
- checklist.new_car and checklist.used_car: exactly 5 items each
- emergency steps: 4–6 steps each
- All prices in Indian Rupees (₹)
- Be brutally honest — this is for real buyers, not for dealers"""


def generate_report(car_name: str) -> dict:
    client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": REPORT_PROMPT.format(car_name=car_name)
            }
        ]
    )
    raw = message.content[0].text.strip()

    # Strip accidental code fences if Claude adds them
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    return json.loads(raw)


# ── Page routes ───────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/report/<car_model>")
def car_report(car_model):
    # Normalise slug → display name, e.g. "maruti-swift" → "Maruti Swift"
    car_name = car_model.replace("-", " ").title()

    # 1. Cache lookup
    report, from_cache = get_cached_report(car_model)
    if from_cache:
        print(f"[CACHE HIT] {car_model}")
        report["from_cache"] = True
        print("DEBUG REPORT:", report)
        return render_template("car_report.html", report=report)

    # 2. Generate via Claude
    try:
        print(f"[GENERATING] {car_name} via Claude...")
        report = generate_report(car_name)
        print("DEBUG REPORT:", report)

        # 3. Persist to cache (do not store from_cache flag)
        save_to_cache(car_model, report)
        report["from_cache"] = False

    except json.JSONDecodeError as e:
        print("ERROR (JSON parse):", e)
        traceback.print_exc()
        report = {"car_name": car_name, "error": "Could not parse AI response. Please try again."}

    except Exception as e:
        print("ERROR:", e)
        traceback.print_exc()
        report = {"car_name": car_name, "error": str(e)}

    return render_template("car_report.html", report=report, from_cache=False)


@app.route("/compare")
def compare():
    car1 = request.args.get("car1", "")
    car2 = request.args.get("car2", "")
    return render_template("compare.html", car1=car1, car2=car2)


# ── API routes ────────────────────────────────────────────────────────────────

@app.get("/api/cars")
def api_cars():
    cars_path = os.path.join(app.static_folder, "cars.json")
    with open(cars_path) as f:
        cars = json.load(f)
    return jsonify(cars)


@app.post("/api/search")
def api_search():
    return "coming soon"


@app.post("/api/report")
def api_report():
    return "coming soon"


@app.post("/api/compare")
def api_compare():
    body = request.get_json(force=True)
    car1_name = body.get("car1", "").strip()
    car2_name = body.get("car2", "").strip()
    driving   = body.get("driving",  "Mix of city + highway")
    priority  = body.get("priority", "Fuel efficiency")
    who       = body.get("who",      "Just me")

    if not car1_name or not car2_name:
        return jsonify({"error": "Both car1 and car2 are required."}), 400

    def slug(name):
        return name.strip().lower().replace(" ", "-")

    try:
        # Fetch or generate reports for both cars
        car1_report, _ = get_cached_report(slug(car1_name))
        if not car1_report:
            print(f"[COMPARE] Generating report for {car1_name}")
            car1_report = generate_report(car1_name)
            save_to_cache(slug(car1_name), car1_report)

        car2_report, _ = get_cached_report(slug(car2_name))
        if not car2_report:
            print(f"[COMPARE] Generating report for {car2_name}")
            car2_report = generate_report(car2_name)
            save_to_cache(slug(car2_name), car2_report)

        # Generate the comparison verdict
        compare_prompt = f"""Compare these two cars for an Indian buyer with this profile:
- Driving pattern: {driving}
- Top priority: {priority}
- Who drives: {who}

Car 1 data: {json.dumps(car1_report)}
Car 2 data: {json.dumps(car2_report)}

Return ONLY this JSON (no markdown, no code fences):
{{
  "winner": "Car 1 name or Car 2 name",
  "winner_reason": "One honest sentence why this car wins for THIS user's specific profile",
  "score_car1": 7.5,
  "score_car2": 8.2,
  "comparison": {{
    "mileage":         {{"car1": "real world mileage", "car2": "real world mileage", "winner": "Car 1 or Car 2"}},
    "service_cost":    {{"car1": "annual cost", "car2": "annual cost", "winner": "Car 1 or Car 2"}},
    "insurance":       {{"car1": "first year cost", "car2": "first year cost", "winner": "Car 1 or Car 2"}},
    "common_problems": {{"car1": "biggest problem", "car2": "biggest problem", "winner": "Car 1 or Car 2"}},
    "comfort":         {{"car1": "honest assessment", "car2": "honest assessment", "winner": "Car 1 or Car 2"}},
    "resale_value":    {{"car1": "honest assessment", "car2": "honest assessment", "winner": "Car 1 or Car 2"}}
  }},
  "five_year_cost_car1": "Total estimated 5 year ownership cost in INR",
  "five_year_cost_car2": "Total estimated 5 year ownership cost in INR",
  "five_year_cost_difference": "Which car saves how much over 5 years",
  "car1_best_for": "One line ideal buyer profile for {car1_name}",
  "car2_best_for": "One line ideal buyer profile for {car2_name}"
}}"""

        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system="You are CarTruth, an honest Indian car comparison expert. Respond in valid JSON only. No markdown.",
            messages=[{"role": "user", "content": compare_prompt}]
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()

        result = json.loads(raw)
        return jsonify(result)

    except json.JSONDecodeError as e:
        print("ERROR (compare JSON parse):", e)
        traceback.print_exc()
        return jsonify({"error": "Could not parse AI response. Please try again."}), 500

    except Exception as e:
        print("ERROR (compare):", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/wizard")
def wizard():
    return render_template("wizard.html")


@app.post("/api/wizard")
def api_wizard():
    body     = request.get_json(force=True)
    car      = body.get("car", "").strip()
    year     = body.get("year", "").strip()
    answers  = body.get("answers", [])
    total_risk = body.get("total_risk", 0)

    if not car:
        return jsonify({"error": "Car name is required."}), 400

    prompt = f"""A buyer just inspected a {year} {car} and answered these inspection questions:
{json.dumps(answers, indent=2)}
Total risk score: {total_risk}/45

Give an honest verdict. Return ONLY this JSON (no markdown, no code fences):
{{
  "verdict": "BUY or SKIP or NEGOTIATE",
  "verdict_reason": "2-3 honest sentences explaining the verdict",
  "risk_level": "Low or Medium or High",
  "red_flags": ["list of concerning findings, empty array if none"],
  "green_flags": ["list of positive findings, empty array if none"],
  "negotiate_points": ["If NEGOTIATE — specific things to push on, else empty array"],
  "must_check_before_buying": ["2-3 things to get checked by a mechanic before finalizing"],
  "estimated_immediate_costs": "What they will likely spend in first 3 months based on their answers",
  "fair_price_reduction": "How much to negotiate down from asking price in INR based on findings"
}}"""

    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        message = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system="You are CarTruth, a brutally honest used car inspector for Indian buyers. Respond in valid JSON only. No markdown.",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = message.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
            raw = raw.strip()
        return jsonify(json.loads(raw))

    except json.JSONDecodeError as e:
        print("ERROR (wizard JSON):", e)
        traceback.print_exc()
        return jsonify({"error": "Could not parse AI response. Please try again."}), 500

    except Exception as e:
        print("ERROR (wizard):", e)
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/budget")
def budget():
    return render_template("budget.html")


@app.post("/api/budget")
def api_budget():
    body       = request.get_json(force=True)
    budget     = body.get("budget", 0)
    city       = body.get("city", "India").strip()
    usage      = body.get("usage", "Daily city commute").strip()
    fuel       = body.get("fuel", "No preference").strip()
    must_haves = body.get("must_haves", [])

    if not budget:
        return jsonify({"error": "Budget is required."}), 400

    must_str = ", ".join(must_haves) if must_haves else "None specified"
    prompt = f"""An Indian buyer in {city} has a total on-road budget of \u20b9{budget:,} and needs a car for {usage}.
Fuel preference: {fuel}
Must-haves: {must_str}

Recommend exactly 3 cars that genuinely fit within this budget on-road in {city}. Be realistic about on-road prices including registration, insurance, and basic accessories.

Return ONLY this JSON (no markdown, no code fences):
{{
  "budget_analysis": "One honest sentence about what this budget can realistically get in {city}",
  "recommendations": [
    {{
      "rank": 1,
      "car_name": "Full car name with variant",
      "why_this_car": "2 sentences why this specific car fits THIS buyer",
      "ex_showroom": "Ex-showroom price",
      "on_road_estimate": "Estimated on-road price in {city}",
      "fits_budget": true,
      "budget_remaining": "How much left after on-road cost",
      "real_mileage": "Real world mileage",
      "annual_maintenance": "Estimated yearly maintenance",
      "best_variant": "Which specific variant to buy and why",
      "one_concern": "One honest concern about this car for this buyer",
      "cartruth_score": 8.2
    }}
  ],
  "money_saving_tips": ["tip 1", "tip 2", "tip 3"],
  "avoid_these_mistakes": ["mistake 1", "mistake 2"]
}}"""

    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=2048,
            system="You are CarTruth, an honest Indian car buying advisor. Respond in valid JSON only. No markdown.",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
            raw = raw.strip()
        return jsonify(json.loads(raw))
    except json.JSONDecodeError as e:
        print("ERROR (budget JSON):", e); traceback.print_exc()
        return jsonify({"error": "Could not parse AI response. Please try again."}), 500
    except Exception as e:
        print("ERROR (budget):", e); traceback.print_exc()
        return jsonify({"error": str(e)}), 500


@app.route("/fairprice")
def fairprice():
    return render_template("fairprice.html")


@app.post("/api/fairprice")
def api_fairprice():
    body         = request.get_json(force=True)
    car          = body.get("car", "").strip()
    year         = body.get("year", "").strip()
    km           = body.get("km", 0)
    condition    = body.get("condition", "Good — minor wear").strip()
    asking_price = body.get("asking_price", 0)
    city         = body.get("city", "India").strip()

    if not car or not asking_price:
        return jsonify({"error": "Car name and asking price are required."}), 400

    prompt = f"""A buyer is looking at a {year} {car} with {km:,} km driven, in {condition} condition. The seller is asking \u20b9{asking_price:,} in {city}.

Give an honest price verdict. Return ONLY this JSON (no markdown, no code fences):
{{
  "verdict": "FAIR PRICE or OVERPRICED or GOOD DEAL or GREAT STEAL",
  "verdict_reason": "2 honest sentences explaining the valuation",
  "market_price_range": "What this car typically sells for in this condition and km in {city}",
  "fair_price": "What CarTruth thinks is the right price",
  "asking_price_assessment": "Overpriced by \u20b9X / Fair / Underpriced by \u20b9X",
  "depreciation_note": "How this car depreciates and whether this fits the pattern",
  "negotiate_to": "The price you should try to get it at",
  "max_pay": "Absolute maximum — walk away above this",
  "red_flags_in_pricing": ["Any pricing red flags, empty array if none"],
  "market_context": "Brief note on current market conditions for this car model"
}}"""

    try:
        client = anthropic.Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))
        msg = client.messages.create(
            model="claude-opus-4-6",
            max_tokens=1024,
            system="You are CarTruth, an expert in Indian used car valuations. Respond in valid JSON only. No markdown.",
            messages=[{"role": "user", "content": prompt}]
        )
        raw = msg.content[0].text.strip()
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"): raw = raw[4:]
            raw = raw.strip()
        return jsonify(json.loads(raw))
    except json.JSONDecodeError as e:
        print("ERROR (fairprice JSON):", e); traceback.print_exc()
        return jsonify({"error": "Could not parse AI response. Please try again."}), 500
    except Exception as e:
        print("ERROR (fairprice):", e); traceback.print_exc()
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
