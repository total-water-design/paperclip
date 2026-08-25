"""Total Water Academy curriculum contract and pilot content.

This module owns educational structure only. It does not implement or fork any
specialist engineering equation. Numerical learning activities must call a
validated Suite adapter when the relevant owner exposes one.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any

ACADEMY_VERSION = "0.4.0"
COURSE_ID = "twda-applied-water-treatment-design"
DIPLOMA_TITLE = "Total Water Academy Diploma in Applied Water Treatment Design"
DIPLOMA_DISCLAIMER = (
    "This diploma records completion of Total Water Academy educational requirements. "
    "It is not professional licensure, engineering registration, or third-party accreditation."
)
DEFAULT_MODULE_PASS_PERCENT = 75.0
DEFAULT_LEVEL_PASS_PERCENT = 75.0
DEFAULT_CAPSTONE_PASS_PERCENT = 80.0
TOTAL_GUIDED_HOURS = 360


@dataclass(frozen=True)
class SuiteDependency:
    owner: str
    capability: str
    academy_use: str
    integration_state: str = "adapter_required"


SUITE_DEPENDENCIES: tuple[SuiteDependency, ...] = (
    SuiteDependency("platform/suite-core", "accounts, entitlements, themes and shared application shell", "identity, access and learning shell", "available"),
    SuiteDependency("engine/shared-waterstream", "canonical WaterStream handoff", "stream literacy and future plant-train exercises"),
    SuiteDependency("engine/shared-water-chemistry", "authoritative common aqueous chemistry", "chemistry exercises and water-quality interpretation"),
    SuiteDependency("app/total-water-balance", "plant water/material balance", "mass-balance and recycle learning exercises"),
    SuiteDependency("app/total-pretreatment-design", "pretreatment unit operations", "pretreatment sizing and selection labs"),
    SuiteDependency("app/total-ro-design", "RO/NF membrane, hydraulic and energy calculations", "membrane design labs"),
    SuiteDependency("app/total-bio-design", "biological treatment calculations", "biological process labs"),
    SuiteDependency("app/total-zld-design", "brine concentration, crystallization and ZLD calculations", "ZLD and crystallization labs"),
    SuiteDependency("app/total-water-economics", "CAPEX/OPEX and lifecycle economics", "economic comparison labs"),
)


SOLUTION_PROPERTIES_THREAD: dict[str, Any] = {
    "id": "solutions-to-zld",
    "title": "Solutions & Solution Properties — from Fundamentals to ZLD",
    "purpose": (
        "Teach the same physical-chemistry ideas progressively: first as solution literacy, "
        "then as membrane/scaling reasoning, and finally as concentrated-brine and crystallization design."
    ),
    "stages": [
        {
            "level_id": "L02",
            "module_ids": ["L02-M06"],
            "depth": "foundation",
            "topics": [
                "concentration bases: mass fraction, mole fraction, molarity and molality",
                "density and temperature effects",
                "solubility and solubility curves",
                "unsaturated, saturated and supersaturated states",
                "activities, activity coefficients and ionic-strength concepts",
                "solution physical properties as engineering inputs",
            ],
        },
        {
            "level_id": "L04",
            "module_ids": ["L04-M03"],
            "depth": "applied",
            "topics": [
                "concentration polarization",
                "activity versus analytical concentration",
                "ion activity products and saturation reasoning",
                "common-ion and pH effects on scaling tendency",
                "why higher recovery changes local solution chemistry",
            ],
        },
        {
            "level_id": "L08",
            "module_ids": ["L08-M02", "L08-M03", "L08-M04"],
            "depth": "advanced",
            "topics": [
                "concentrated-electrolyte density, viscosity and diffusivity",
                "heat capacity, latent heat and enthalpy effects",
                "supersaturation ratio and metastable-zone concepts",
                "nucleation and crystal-growth fundamentals",
                "hydrate and solid-phase stability",
                "temperature-composition and phase-diagram reasoning",
                "evaporation and crystallization consequences for ZLD design",
            ],
        },
    ],
    "engine_policy": (
        "Use Shared Water Chemistry, Total Water Balance and Total ZLD Design through validated adapters "
        "when available; educational examples must not fork or replace authoritative Suite calculations."
    ),
}


CRYSTAL_SCIENCE_THREAD: dict[str, Any] = {
    "id": "crystals-nucleation-growth",
    "title": "Crystals, Nucleation & Crystal Growth — from Solid Structure to ZLD Operation",
    "purpose": (
        "Teach how solid phases form and evolve so learners can connect supersaturation, nucleation, "
        "crystal growth, hydrodynamics, impurities, habit and crystal-size distribution to industrial ZLD behavior."
    ),
    "stages": [
        {
            "level_id": "L02",
            "module_ids": ["L02-M06"],
            "depth": "foundation",
            "topics": [
                "crystalline versus amorphous solids",
                "unit cells, lattices and basic crystal systems",
                "crystal faces, habit and morphology",
                "polymorphism and hydrates",
                "why solid structure and bonding affect properties and phase identity",
            ],
        },
        {
            "level_id": "L08",
            "module_ids": ["L08-M02", "L08-M03", "L08-M04"],
            "depth": "advanced",
            "topics": [
                "crystal systems, faces and optional Miller-index literacy",
                "polymorphism, isomorphism, solid solutions, defects and crystal habit",
                "habit modification by solvent, impurities and additives",
                "metastable zone and induction time",
                "primary and secondary nucleation",
                "homogeneous and heterogeneous nucleation",
                "contact, attrition, shear and equipment-driven secondary nucleation",
                "classical nucleation free-energy barrier and critical nucleus",
                "nucleation-rate dependence on supersaturation and temperature",
                "face growth, characteristic growth rate and crystal shape factors",
                "surface integration, steps, kink sites and two-dimensional nucleation",
                "Burton-Cabrera-Frank screw-dislocation crystal growth",
                "bulk diffusion, concentration boundary layers and hydrodynamic control",
                "empirical power-law and Arrhenius crystal-growth kinetics",
                "desupersaturation experiments and kinetic interpretation",
                "Ostwald ripening and Gibbs-Thomson size-solubility effects",
                "size-dependent growth and growth-rate dispersion",
                "crystal-size-distribution consequences for settling, filtration, centrifugation and solids handling",
            ],
        },
        {
            "level_id": "L10",
            "module_ids": ["L10-M03"],
            "depth": "capstone",
            "topics": [
                "defend a supersaturation-control strategy",
                "identify primary and secondary nucleation sources",
                "select a seeding approach and explain its purpose",
                "balance mixing and hydrodynamics against fines, scale and attrition risk",
                "connect crystal-size distribution and habit to dewatering and solids handling",
                "use validated Total ZLD Design / ZLD engine outputs rather than Academy-owned project predictions",
            ],
        },
    ],
    "engine_policy": (
        "Academy owns pedagogy and conceptual visualization. Shared Water Chemistry and Total ZLD Design "
        "remain authoritative for project chemistry, phase behavior and crystallizer/ZLD calculations."
    ),
}


LEVELS: tuple[dict[str, Any], ...] = (
    {
        "id": "L01", "level": 1, "title": "Water Treatment Foundations & Water Quality", "hours": 28,
        "mission": "Learn to think in treatment trains: source water → barriers → product water.",
        "competencies": ["water-quality literacy", "unit-operation purpose", "treatment-train reasoning", "engineering safety mindset"],
        "suite_connections": ["platform/suite-core", "engine/shared-waterstream"],
        "modules": [
            {"id": "L01-M01", "title": "Build Your First Treatment Train", "hours": 7, "pilot": True},
            {"id": "L01-M02", "title": "Water Sources, Constituents and Design Objectives", "hours": 7},
            {"id": "L01-M03", "title": "Reading Water Analyses and Process Flow Diagrams", "hours": 7},
            {"id": "L01-M04", "title": "Engineering Assumptions, Limits and Safety", "hours": 7},
        ],
    },
    {
        "id": "L02", "level": 2, "title": "Core Unit Operations, Balances & Transport Fundamentals", "hours": 42,
        "mission": "Build the process-engineering foundation needed to understand what every water-treatment unit does and why it behaves the way it does.",
        "competencies": [
            "unit operations", "dimensional analysis", "mass/component balance", "energy balance", "heat transfer",
            "fluid flow/momentum", "pressure/headloss", "mass transfer/diffusion", "separation fundamentals",
            "solution concentration/solubility", "saturation", "activity/ionic strength", "solution physical properties",
            "crystalline solids/habit", "polymorphism/hydrates", "chemical equilibrium/reaction fundamentals",
        ],
        "suite_connections": ["engine/shared-waterstream", "engine/shared-water-chemistry", "app/total-water-balance"],
        "modules": [
            {"id": "L02-M01", "title": "Engineering Units, Dimensions and Process Variables", "hours": 6},
            {"id": "L02-M02", "title": "Mass, Component and Water Balances", "hours": 8},
            {"id": "L02-M03", "title": "Energy Balances and Heat Transfer", "hours": 7},
            {"id": "L02-M04", "title": "Fluid Flow, Momentum, Pressure and Headloss", "hours": 7},
            {"id": "L02-M05", "title": "Mass Transfer, Diffusion and Separation Fundamentals", "hours": 7},
            {"id": "L02-M06", "title": "Solutions, Solubility, Crystal Basics & Water Chemistry", "hours": 7},
        ],
    },
    {
        "id": "L03", "level": 3, "title": "Pretreatment & Solids Separation", "hours": 36,
        "mission": "Protect downstream processes by selecting and sizing the right pretreatment barriers.",
        "competencies": ["screening/straining", "coagulation/flocculation", "DAF/clarification", "media/disc filtration", "UF/MF pretreatment"],
        "suite_connections": ["app/total-pretreatment-design", "engine/shared-waterstream"],
        "modules": [
            {"id": "L03-M01", "title": "Screens, Strainers and Disc Filters", "hours": 7},
            {"id": "L03-M02", "title": "Coagulation, Flocculation, Clarification and DAF", "hours": 9},
            {"id": "L03-M03", "title": "Multimedia, Depth and Cartridge Filtration", "hours": 8},
            {"id": "L03-M04", "title": "MF/UF Pretreatment and Fouling Risk", "hours": 8},
            {"id": "L03-M05", "title": "Pretreatment Design Challenge", "hours": 4},
        ],
    },
    {
        "id": "L04", "level": 4, "title": "Membrane Systems — MF, UF, NF & RO", "hours": 44,
        "mission": "Design membrane systems by understanding flux, recovery, rejection, pressure, fouling and energy.",
        "competencies": ["membrane selection", "flux/recovery", "RO/NF staging", "osmotic pressure", "solution activity", "saturation/scaling reasoning", "energy recovery", "membrane diagnostics"],
        "suite_connections": ["app/total-ro-design", "engine/shared-water-chemistry", "engine/shared-waterstream"],
        "modules": [
            {"id": "L04-M01", "title": "Membrane Transport and Separation", "hours": 8},
            {"id": "L04-M02", "title": "RO/NF Configuration, Arrays and Staging", "hours": 10},
            {"id": "L04-M03", "title": "Concentration Polarization, Activity, Scaling & Fouling", "hours": 9},
            {"id": "L04-M04", "title": "Pumps, Energy Recovery and Hydraulic Limits", "hours": 9},
            {"id": "L04-M05", "title": "Membrane Design Mission in Total RO Design", "hours": 8},
        ],
    },
    {
        "id": "L05", "level": 5, "title": "Biological Treatment & Water Reuse", "hours": 40,
        "mission": "Connect biology, solids separation and polishing into a reliable reuse process.",
        "competencies": ["BOD/COD/nutrients", "activated sludge", "SRT/HRT concepts", "MBR", "nitrification/denitrification", "reuse barriers"],
        "suite_connections": ["app/total-bio-design", "app/total-pretreatment-design", "engine/shared-waterstream"],
        "modules": [
            {"id": "L05-M01", "title": "Wastewater Characteristics and Biological Kinetics", "hours": 8},
            {"id": "L05-M02", "title": "Activated Sludge, SRT, HRT and Oxygen", "hours": 10},
            {"id": "L05-M03", "title": "Nutrients, MBR and Advanced Biological Treatment", "hours": 9},
            {"id": "L05-M04", "title": "Reuse Treatment Trains and Polishing", "hours": 8},
            {"id": "L05-M05", "title": "Biological Design Mission", "hours": 5},
        ],
    },
    {
        "id": "L06", "level": 6, "title": "Pumps, Energy & Electrical Systems", "hours": 34,
        "mission": "Understand the equipment that makes the process move — mechanically and electrically.",
        "competencies": ["pump duty", "motor fundamentals", "single/three phase", "Y/Delta starting", "contactors/overloads", "soft starters", "VFDs", "basic one-lines"],
        "suite_connections": ["app/total-ro-design"],
        "modules": [
            {"id": "L06-M01", "title": "Pumps, Curves, Duty Points and Efficiency", "hours": 8},
            {"id": "L06-M02", "title": "Single-Phase and Three-Phase Power", "hours": 6},
            {"id": "L06-M03", "title": "Motors, Contactors, Overloads and Y/Delta Starting", "hours": 7},
            {"id": "L06-M04", "title": "Soft Starters, VFDs and Process Energy", "hours": 7},
            {"id": "L06-M05", "title": "Electrical/Mechanical Troubleshooting Mission", "hours": 6},
        ],
    },
    {
        "id": "L07", "level": 7, "title": "Instrumentation, Process Control & PLC", "hours": 32,
        "mission": "Make a water-treatment plant observable, controllable and safe to operate.",
        "competencies": ["P&ID interpretation", "instrument selection", "4-20 mA concepts", "interlocks/permissives", "PID concepts", "PLC logic", "alarms", "control narratives"],
        "suite_connections": ["platform/suite-core"],
        "modules": [
            {"id": "L07-M01", "title": "Sensors, Transmitters, Valves and Signals", "hours": 7},
            {"id": "L07-M02", "title": "Control Loops, PID and Process Dynamics", "hours": 7},
            {"id": "L07-M03", "title": "PLC Fundamentals, Ladder Logic and Sequencing", "hours": 7},
            {"id": "L07-M04", "title": "Permissives, Interlocks, Trips and Alarms", "hours": 6},
            {"id": "L07-M05", "title": "Write a Water Plant Control Narrative", "hours": 5},
        ],
    },
    {
        "id": "L08", "level": 8, "title": "Residuals, Brine Management & ZLD", "hours": 34,
        "mission": "Follow every reject stream while learning how concentrated solutions nucleate and grow crystals on the path to MLD/ZLD.",
        "competencies": [
            "residuals inventory", "brine concentration", "solution thermodynamics", "brine physical properties",
            "crystal structure/habit", "polymorphism/hydrates", "metastable zone/induction",
            "primary/secondary nucleation", "crystal-growth mechanisms", "growth kinetics/hydrodynamics",
            "Ostwald ripening", "crystal-size distribution", "thermal systems", "recycle", "ZLD train selection",
        ],
        "suite_connections": ["app/total-zld-design", "app/total-water-balance", "engine/shared-water-chemistry"],
        "modules": [
            {"id": "L08-M01", "title": "Residuals and Brine as Evolving Process Streams", "hours": 6},
            {"id": "L08-M02", "title": "Concentrated Solutions, Solubility, Solid Phases & Crystal Habit", "hours": 7},
            {"id": "L08-M03", "title": "Nucleation, Crystal Growth & Crystal-Size Distribution", "hours": 9},
            {"id": "L08-M04", "title": "Evaporation, Industrial Crystallizers & MLD/ZLD Train Design", "hours": 8},
            {"id": "L08-M05", "title": "ZLD Design Mission", "hours": 4},
        ],
    },
    {
        "id": "L09", "level": 9, "title": "Integrated Design, Treatment Selection & Economics", "hours": 34,
        "mission": "Compare technically viable alternatives and make an engineering recommendation.",
        "competencies": ["alternative selection", "CAPEX/OPEX literacy", "energy/cost tradeoffs", "risk/robustness", "integrated water balance", "design review"],
        "suite_connections": ["app/total-water-economics", "app/total-water-balance", "platform/suite-core"],
        "modules": [
            {"id": "L09-M01", "title": "From Design Basis to Alternatives", "hours": 7},
            {"id": "L09-M02", "title": "CAPEX, OPEX and Lifecycle Cost Fundamentals", "hours": 8},
            {"id": "L09-M03", "title": "Energy, Reliability, Redundancy and Risk", "hours": 7},
            {"id": "L09-M04", "title": "Integrated Treatment-Train Comparison", "hours": 8},
            {"id": "L09-M05", "title": "Design Review Board Challenge", "hours": 4},
        ],
    },
    {
        "id": "L10", "level": 10, "title": "Capstone — Design a Complete Water Treatment Plant", "hours": 36,
        "mission": "Use the Suite as a junior process engineer: define, design, justify, control and present a complete plant.",
        "competencies": ["design basis", "integrated process design", "controls philosophy", "electrical load awareness", "economics", "engineering communication", "defensible assumptions"],
        "suite_connections": ["all validated specialist applications"],
        "modules": [
            {"id": "L10-M01", "title": "Capstone Design Basis and Feed Characterization", "hours": 6},
            {"id": "L10-M02", "title": "Pretreatment + Biological + Membrane Train", "hours": 9},
            {"id": "L10-M03", "title": "Residuals/ZLD, Crystallization, Water Balance & Energy", "hours": 7},
            {"id": "L10-M04", "title": "Controls, Electrical Philosophy and Operability", "hours": 6},
            {"id": "L10-M05", "title": "Economics, Final Design Review and Defense", "hours": 8},
        ],
    },
)


PILOT_MODULE: dict[str, Any] = {
    "id": "L01-M01",
    "level_id": "L01",
    "title": "Build Your First Treatment Train",
    "hours": 7,
    "learning_objective": "Explain why treatment plants use multiple barriers and assemble a defensible first-pass treatment train from source water to product water.",
    "teaching_assumption": (
        "Pilot exercises intentionally simplify detailed sizing. The training scenario assumes a high-turbidity/algae-prone surface water source and a final low-salinity disinfected product. "
        "Exact design requirements depend on the validated specialist applications and project-specific water quality."
    ),
    "competencies": ["treatment-train reasoning", "barrier purpose", "process sequencing", "design-basis awareness"],
    "steps": [
        {
            "id": "concept-1", "kind": "concept", "title": "A plant is a chain of barriers",
            "body": (
                "Water treatment is not one magic unit. Each process removes or controls a different risk. A good design starts with the feed water, defines the required product water, then builds a sequence of barriers that protects the next process."
            ),
            "takeaway": "Never select equipment before you understand the feed, the product target and what each downstream unit must be protected from.",
        },
        {
            "id": "quiz-1", "kind": "quiz", "title": "Checkpoint 1",
            "question": "Why is pretreatment placed before a sensitive membrane process?",
            "choices": [
                "To make the plant drawing look complete",
                "To reduce loads or foulants that would make the membrane unstable or inefficient",
                "Because every water plant must use the same equipment",
                "Only to increase pressure before the membrane",
            ],
            "answer": 1,
            "correct_feedback": "Correct. Pretreatment is selected to control the water-quality risks that would otherwise reduce downstream reliability, performance or membrane life.",
            "incorrect_feedback": "Think about what reaches the membrane surface. Solids, colloids, organisms and some chemistry risks can make a membrane process unstable long before pressure becomes the main issue.",
            "hint": "Ask what the downstream membrane needs from its feed water.",
            "competency": "barrier purpose",
        },
        {
            "id": "concept-2", "kind": "concept", "title": "Design from water quality, not habit",
            "body": (
                "Two plants with the same product flow can need different trains because their feed waters are different. Surface water may need aggressive solids/algae control; a clean brackish well may need a much simpler solids barrier but stronger scaling control."
            ),
            "takeaway": "The feed-water problem determines the treatment train; the equipment list does not determine the problem.",
        },
        {
            "id": "quiz-2", "kind": "quiz", "title": "Checkpoint 2",
            "question": "A surface-water feed suddenly develops high algae and turbidity. What should an engineer do first?",
            "choices": [
                "Increase RO recovery immediately",
                "Revisit the design basis and pretreatment barriers for the changed feed condition",
                "Ignore the change if product flow is still correct",
                "Remove all upstream filtration",
            ],
            "answer": 1,
            "correct_feedback": "Correct. A changed feed condition can invalidate the assumptions that protect downstream processes. Recheck the design basis before pushing the plant harder.",
            "incorrect_feedback": "A water-treatment design is only valid inside its design envelope. When feed quality changes, first test whether the selected barriers and operating limits still protect the downstream train.",
            "hint": "What document tells you which feed conditions the plant was designed for?",
            "competency": "design-basis awareness",
        },
        {
            "id": "concept-3", "kind": "concept", "title": "Every unit has a job and a downstream customer",
            "body": (
                "Screening protects equipment from large debris; coagulation/flocculation groups difficult particles; clarification or DAF removes bulk suspended matter; filtration polishes solids; cartridge filtration protects RO from residual particles; RO removes dissolved salts; final disinfection protects the finished water."
            ),
            "takeaway": "For every unit operation, be able to say: what enters, what changes, what leaves, and which downstream unit benefits.",
        },
        {
            "id": "quiz-3", "kind": "quiz", "title": "Checkpoint 3",
            "question": "Which statement is the strongest engineering reason for sequencing unit operations?",
            "choices": [
                "The most expensive unit should always be first",
                "Each unit should prepare the stream for the next barrier while moving toward the product target",
                "The sequence should match the order in a vendor brochure",
                "All processes work equally well in any order",
            ],
            "answer": 1,
            "correct_feedback": "Correct. Treatment trains are systems: upstream decisions change what downstream equipment receives and how reliably it can perform.",
            "incorrect_feedback": "Think systemically. The order matters because each unit changes the stream received by the next process.",
            "hint": "Imagine sending raw algae-rich surface water directly into an RO pressure vessel.",
            "competency": "process sequencing",
        },
        {
            "id": "practical-1", "kind": "practical", "practical_type": "assemble_train", "title": "Design Mission: protect the membrane",
            "scenario": (
                "You have algae-prone, high-turbidity surface water. The client needs a low-salinity disinfected product. Build a simplified treatment train. Assume coagulation/DAF is appropriate for this teaching case and that RO is required for dissolved-salt removal."
            ),
            "available_units": [
                {"id": "coarse_screen", "label": "Coarse Screen"},
                {"id": "coag_floc", "label": "Coagulation + Flocculation"},
                {"id": "daf", "label": "DAF"},
                {"id": "uf", "label": "UF"},
                {"id": "cartridge", "label": "Cartridge Filter"},
                {"id": "ro", "label": "RO"},
                {"id": "disinfection", "label": "Final Disinfection"},
                {"id": "activated_sludge", "label": "Activated Sludge"},
                {"id": "crystallizer", "label": "Crystallizer"},
            ],
            "target_sequence": ["coarse_screen", "coag_floc", "daf", "uf", "cartridge", "ro", "disinfection"],
            "minimum_score": 75.0,
            "success_feedback": "Strong train. You created progressively finer barriers, protected the RO, used RO for dissolved salts and finished with a product-water barrier.",
            "retry_feedback": "Your train has the right idea but the sequence or selected processes need work. Ask what each unit receives and what the next unit needs.",
            "competency": "treatment-train reasoning",
        },
        {
            "id": "module-test", "kind": "test", "title": "Module Test",
            "pass_percent": DEFAULT_MODULE_PASS_PERCENT,
            "questions": [
                {"id": "t1", "prompt": "The best starting point for a treatment design is:", "choices": ["a favorite vendor", "the feed water and product requirements", "the largest pump available", "the lowest-cost unit alone"], "answer": 1},
                {"id": "t2", "prompt": "Why can pretreatment differ between a well and a surface-water intake?", "choices": ["Different feed-water risks require different barriers", "Pretreatment never depends on water quality", "Only the plant color changes", "Wells always use biological treatment"], "answer": 0},
                {"id": "t3", "prompt": "What is the main role of RO in the pilot train?", "choices": ["Remove large sticks", "Remove dissolved salts", "Grow biomass", "Set PLC scan time"], "answer": 1},
                {"id": "t4", "prompt": "A process train should be reconsidered when:", "choices": ["the feed/design basis changes materially", "a drawing has already been printed", "the same equipment is popular", "the operator likes the current sequence"], "answer": 0},
                {"id": "t5", "prompt": "A good engineer should be able to explain each unit by:", "choices": ["brand and paint color", "what enters, what changes, what leaves and what it protects", "only purchase price", "only motor horsepower"], "answer": 1},
            ],
            "competencies": ["water-quality literacy", "barrier purpose", "process sequencing", "design-basis awareness"],
        },
    ],
}


def curriculum() -> dict[str, Any]:
    """Return a JSON-safe curriculum snapshot for templates/APIs."""
    return {
        "course_id": COURSE_ID,
        "version": ACADEMY_VERSION,
        "title": "Total Water Academy — Applied Water Treatment Design",
        "diploma_title": DIPLOMA_TITLE,
        "diploma_disclaimer": DIPLOMA_DISCLAIMER,
        "guided_hours": TOTAL_GUIDED_HOURS,
        "learning_threads": [deepcopy(SOLUTION_PROPERTIES_THREAD), deepcopy(CRYSTAL_SCIENCE_THREAD)],
        "levels": deepcopy(list(LEVELS)),
    }


def level_by_id(level_id: str) -> dict[str, Any] | None:
    key = str(level_id or "").strip().upper()
    return next((deepcopy(item) for item in LEVELS if item["id"] == key), None)


def module_by_id(module_id: str) -> dict[str, Any] | None:
    key = str(module_id or "").strip().upper()
    if key == PILOT_MODULE["id"]:
        return deepcopy(PILOT_MODULE)
    for level in LEVELS:
        for module in level["modules"]:
            if module["id"] == key:
                return deepcopy(module)
    return None


def evaluate_activity(activity_id: str, answer: Any) -> dict[str, Any]:
    """Evaluate only authored pilot activities; no engineering equations live here."""
    activity = next((item for item in PILOT_MODULE["steps"] if item["id"] == str(activity_id)), None)
    if not activity:
        raise KeyError(f"Unknown Academy activity: {activity_id}")
    kind = activity["kind"]
    if kind == "quiz":
        try:
            chosen = int(answer)
        except (TypeError, ValueError):
            chosen = -1
        correct = chosen == int(activity["answer"])
        return {
            "correct": correct,
            "score": 100.0 if correct else 0.0,
            "feedback": activity["correct_feedback"] if correct else activity["incorrect_feedback"],
            "hint": None if correct else activity.get("hint"),
            "competencies": [activity.get("competency")],
        }
    if kind == "practical" and activity.get("practical_type") == "assemble_train":
        submitted = [str(item) for item in (answer or [])]
        target = list(activity["target_sequence"])
        target_set = set(target)
        required_present = len(target_set.intersection(submitted)) / len(target_set)
        exact_positions = sum(1 for i, item in enumerate(target) if i < len(submitted) and submitted[i] == item) / len(target)
        adjacency_pairs = list(zip(target, target[1:]))
        submitted_pairs = set(zip(submitted, submitted[1:]))
        adjacency = sum(1 for pair in adjacency_pairs if pair in submitted_pairs) / len(adjacency_pairs)
        distractors = sum(1 for item in submitted if item not in target_set)
        score = max(0.0, min(100.0, (required_present * 45.0) + (exact_positions * 35.0) + (adjacency * 20.0) - (distractors * 7.5)))
        correct = score >= float(activity.get("minimum_score", 75.0))
        return {
            "correct": correct,
            "score": round(score, 1),
            "feedback": activity["success_feedback"] if correct else activity["retry_feedback"],
            "hint": None if correct else "Trace the stream from large debris → destabilized solids → bulk solids removal → fine filtration → membrane protection → dissolved-salt removal → finished-water barrier.",
            "competencies": [activity.get("competency")],
        }
    if kind == "test":
        submitted = answer if isinstance(answer, dict) else {}
        questions = activity["questions"]
        correct_count = sum(1 for q in questions if str(submitted.get(q["id"], "")) == str(q["answer"]))
        score = 100.0 * correct_count / max(1, len(questions))
        passed = score >= float(activity.get("pass_percent", DEFAULT_MODULE_PASS_PERCENT))
        return {
            "correct": passed,
            "score": round(score, 1),
            "feedback": "Module passed. You are ready to continue the learning journey." if passed else "Review the concepts and practical reasoning, then try the module test again.",
            "hint": None if passed else "Focus on feed water → barrier purpose → downstream protection → product target.",
            "competencies": list(activity.get("competencies") or []),
        }
    raise ValueError(f"Activity {activity_id} is not an assessable activity")


def validate_curriculum() -> list[str]:
    errors: list[str] = []
    if len(LEVELS) != 10:
        errors.append("Academy curriculum must contain exactly ten levels.")
    if sum(int(level["hours"]) for level in LEVELS) != TOTAL_GUIDED_HOURS:
        errors.append("Level hours do not sum to the declared guided hours.")
    for level in LEVELS:
        if sum(int(module["hours"]) for module in level["modules"]) != int(level["hours"]):
            errors.append(f"Module hours do not sum to {level['id']} declared hours.")
    pilot_kinds = [step["kind"] for step in PILOT_MODULE["steps"]]
    expected = ["concept", "quiz", "concept", "quiz", "concept", "quiz", "practical", "test"]
    if pilot_kinds != expected:
        errors.append("Pilot flow must be Concept → Quiz → Concept → Quiz → Concept → Quiz → Practical → Test.")
    if PILOT_MODULE["id"] != LEVELS[0]["modules"][0]["id"]:
        errors.append("Pilot module must be the first module in Level 1.")
    solution_thread_levels = [stage["level_id"] for stage in SOLUTION_PROPERTIES_THREAD["stages"]]
    if solution_thread_levels != ["L02", "L04", "L08"]:
        errors.append("Solution-properties thread must progress through Levels 2, 4 and 8.")
    crystal_thread_levels = [stage["level_id"] for stage in CRYSTAL_SCIENCE_THREAD["stages"]]
    if crystal_thread_levels != ["L02", "L08", "L10"]:
        errors.append("Crystal-science thread must progress through Levels 2, 8 and 10.")
    return errors
