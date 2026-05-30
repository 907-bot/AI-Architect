"use client";
import React, { useEffect, useState, useCallback } from "react";
import { useStore } from "@/lib/store";
import { Shield, AlertTriangle, CheckCircle, ChevronDown, ChevronUp, Loader2, RefreshCw } from "lucide-react";

interface NormSection {
  title: string;
  items: string[];
  type: "info" | "warning" | "success";
}

interface GovNorms {
  country: string;
  region: string;
  code_name: string;
  authority: string;
  sections: NormSection[];
  links: { label: string; url: string }[];
  fetched_at: string;
}

const NORMS_DB: Record<string, GovNorms> = {
  IN: {
    country:"India", region:"", code_name:"NBC 2016 (SP 7)",
    authority:"Bureau of Indian Standards (BIS) + Local Municipal Corporation",
    sections:[
      { title:"Floor Area Ratio (FAR)", type:"info", items:[
        "Residential: FAR 1.5–3.5 (varies by city/zone)",
        "Commercial: FAR 2.0–5.0 in metro areas",
        "Mumbai: FSI 1.0–3.0 (base); TDR available",
        "Delhi: FAR up to 3.5 (MPD 2041)",
        "Bengaluru: FAR 1.75–3.25 per BBMP norms",
      ]},
      { title:"Setbacks & Coverage", type:"warning", items:[
        "Ground coverage: max 50–60% (residential)",
        "Front setback: 3–6 m (varies by road width)",
        "Side setback: 1.2–3.0 m depending on height",
        "Rear setback: 3.0 m minimum",
        "High-rise (>15 m): 7.5 m all sides minimum",
      ]},
      { title:"Height & Structure", type:"info", items:[
        "G+4 (≤15 m): No lift mandatory",
        "G+5 and above: Lift + fire NOC compulsory",
        "Floor height: min 2.75 m habitable spaces",
        "Basement: Not counted in FAR if for parking",
        "Seismic Zone III–V: IS 1893 ductile detailing",
      ]},
      { title:"Fire Safety (NBC Part 4)", type:"warning", items:[
        ">15 m height: mandatory sprinkler system",
        "Fire exit staircase: min 1.5 m wide",
        "Fire pump room + overhead tank required",
        "Emergency lighting in all exit paths",
        "High-rise: refuge floor every 15 floors",
      ]},
      { title:"Green Building (ECBC 2017)", type:"success", items:[
        "ECBC compliance mandatory for >500 m² buildings",
        "Minimum 25% of roof as green/solar",
        "Rainwater harvesting mandatory (most states)",
        "EV charging: 20% of parking bays (new rule)",
        "GRIHA / IGBC rating encouraged for govt projects",
      ]},
      { title:"Vastu & Orientation", type:"success", items:[
        "Main entrance: North, East, or North-East preferred",
        "Kitchen: South-East quadrant (Agni corner)",
        "Master bedroom: South-West for stability",
        "Overhead water tank: North-West or South-West",
        "Swimming pool: North-East quadrant",
      ]},
    ],
    links:[
      { label:"NBC 2016 (BIS)", url:"https://bis.gov.in/index.php/standards/technical-department/national-building-code/" },
      { label:"ECBC 2017", url:"https://www.beeindia.gov.in/content/ecbc" },
      { label:"RERA India", url:"https://rera.gov.in/" },
    ],
    fetched_at: new Date().toISOString(),
  },
  US: {
    country:"United States", region:"", code_name:"IBC 2021 + Local Amendments",
    authority:"ICC (International Code Council) + AHJ (Authority Having Jurisdiction)",
    sections:[
      { title:"Zoning & FAR", type:"info", items:[
        "FAR: 0.5–15+ depending on zone (city-specific)",
        "Residential R-1: typically max 0.5–1.0 FAR",
        "Mixed-use / commercial: up to 10–15 FAR (NYC, SF)",
        "Setbacks defined by local zoning ordinance",
        "Height limits: varies (40 ft suburban, unlimited downtown)",
      ]},
      { title:"Structural (IBC 2021)", type:"warning", items:[
        "Seismic Design Category A–F per ASCE 7-22",
        "Snow load: ASCE 7 ground snow map",
        "Wind: ASCE 7 basic wind speed maps",
        "Foundation: Per soil report; min 12\" frost depth",
        "Fire-resistive construction: Type I–V",
      ]},
      { title:"Fire & Life Safety", type:"warning", items:[
        "Sprinklers: NFPA 13 (commercial), 13R/13D (residential)",
        "High-rise (>75 ft): full sprinkler + voice evac",
        "Means of egress: min 2 exits for >49 occupants",
        "Corridor: min 44\" width; stair: min 44\"",
        "Emergency lighting: 1.0 fc for 90 min",
      ]},
      { title:"Energy Code (IECC 2021)", type:"success", items:[
        "Climate zones 1–8 dictate R-values",
        "Whole-building energy compliance required",
        "Window-to-wall ratio: max 40% (prescriptive)",
        "HVAC: ASHRAE 90.1-2019 efficiency minimums",
        "EV ready: 10% parking spaces (CA, WA, others)",
      ]},
      { title:"Accessibility (ADA)", type:"success", items:[
        "All public buildings: full ADA compliance",
        "Accessible route from parking to entrance",
        "Elevator required if >3 floors (most cases)",
        "Accessible restroom on every occupied floor",
        "Braille signage at all room IDs",
      ]},
    ],
    links:[
      { label:"IBC 2021 (ICC)", url:"https://codes.iccsafe.org/content/IBC2021P1" },
      { label:"ADA Standards", url:"https://www.ada.gov/law-and-regs/design-standards/" },
      { label:"IECC 2021", url:"https://codes.iccsafe.org/content/IECC2021P2" },
    ],
    fetched_at: new Date().toISOString(),
  },
  GB: {
    country:"United Kingdom", region:"", code_name:"Building Regulations 2010 (England)",
    authority:"Local Planning Authority + LABC / Approved Inspector",
    sections:[
      { title:"Planning Permission", type:"info", items:[
        "Permitted Development: extensions up to 8 m (detached)",
        "Full planning permission for new builds",
        "Conservation areas: stricter controls apply",
        "Listed buildings: Listed Building Consent required",
        "Density: as per Local Plan (units/hectare)",
      ]},
      { title:"Approved Document Structure", type:"warning", items:[
        "Part A: Structure — BS EN Eurocodes",
        "Part B: Fire safety — compartmentation, escape",
        "Part C: Site preparation and moisture resistance",
        "Part K: Stairs, ramps, guards — min 2.0 m headroom",
        "Part M: Accessibility (Lifetime Homes standard)",
      ]},
      { title:"Fire Safety (Part B)", type:"warning", items:[
        "High-rise (>18 m): External wall systems non-combustible",
        "Sprinklers required >30 m (England from 2023)",
        "Fire stopping at all penetrations",
        "Protected staircase for >4 storeys",
        "Balcony cladding: A1/A2 fire rated",
      ]},
      { title:"Energy (Part L 2021)", type:"success", items:[
        "25% improvement on 2013 regulations",
        "SAP / SBEM energy assessment required",
        "Fabric-first approach: U-values walls 0.18 W/m²K",
        "Air permeability: max 8 m³/(h.m²) at 50 Pa",
        "Future Homes Standard 2025: net-zero ready",
      ]},
    ],
    links:[
      { label:"Building Regulations 2010", url:"https://www.gov.uk/government/collections/approved-documents" },
      { label:"Planning Portal", url:"https://www.planningportal.co.uk/" },
    ],
    fetched_at: new Date().toISOString(),
  },
  AU: {
    country:"Australia", region:"", code_name:"NCC 2022 (National Construction Code)",
    authority:"ABCB + State Building Authority",
    sections:[
      { title:"BCA Classes & FAR", type:"info", items:[
        "Class 1a: Single dwelling; Class 1b: guesthouses",
        "Class 2: Apartment buildings",
        "Class 5–9: Commercial/industrial",
        "FAR set by council LEP (varies by state)",
        "Height limits per Local Environment Plan",
      ]},
      { title:"Structural (AS/NZS 1170)", type:"warning", items:[
        "Wind: Region A–D per AS/NZS 1170.2",
        "Seismic: low risk generally; AS 1170.4",
        "Bushfire Attack Level (BAL): BAL-FZ highest",
        "Flood: council overlay maps determine requirements",
      ]},
      { title:"Energy (NatHERS)", type:"success", items:[
        "Minimum 7-star NatHERS rating (from 2023)",
        "Whole-of-home energy budget pathway",
        "Solar-ready: all new homes from 2023",
        "Electric vehicle charging: recommended",
        "NABERS rating for commercial buildings",
      ]},
    ],
    links:[
      { label:"NCC 2022 (ABCB)", url:"https://ncc.abcb.gov.au/" },
      { label:"NatHERS", url:"https://www.nathers.gov.au/" },
    ],
    fetched_at: new Date().toISOString(),
  },
  DEFAULT: {
    country:"International", region:"",
    code_name:"ISO 21542:2021 + Local Codes",
    authority:"Local Building Authority",
    sections:[
      { title:"Universal Design Principles", type:"info", items:[
        "Follow local authority zoning regulations",
        "Minimum floor height: 2.4–2.75 m (varies)",
        "Natural light: minimum 10% of floor area",
        "Ventilation: 5–10 ACH for habitable spaces",
        "Structural: follow national Eurocodes or equivalent",
      ]},
      { title:"Fire Safety (ISO 23601)", type:"warning", items:[
        "Minimum 2 means of egress for large buildings",
        "Fire compartmentation every 2000 m²",
        "Emergency exit signs in all corridors",
        "Sprinkler system recommended above 4 storeys",
      ]},
      { title:"Sustainability", type:"success", items:[
        "LEED / BREEAM / GRIHA certification available",
        "Energy performance certificate recommended",
        "Rainwater harvesting encouraged",
        "Green roof / solar panels beneficial",
      ]},
    ],
    links:[
      { label:"ISO Building Standards", url:"https://www.iso.org/committee/49070.html" },
      { label:"LEED Certification", url:"https://www.usgbc.org/leed" },
    ],
    fetched_at: new Date().toISOString(),
  },
};

async function detectCountry(lat: number, lng: number): Promise<string> {
  try {
    const r = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${lat}&lon=${lng}&format=json`,
      { headers: { "Accept-Language": "en" } }
    );
    const d = await r.json();
    return d.address?.country_code?.toUpperCase() || "DEFAULT";
  } catch { return "DEFAULT"; }
}

export default function GovernmentNorms() {
  const plotLat = useStore(s => s.plotLat);
  const plotLng = useStore(s => s.plotLng);
  const compliance = useStore(s => s.complianceData);
  const [norms, setNorms]       = useState<GovNorms | null>(null);
  const [loading, setLoading]   = useState(false);
  const [expanded, setExpanded] = useState<string | null>("Floor Area Ratio (FAR)");

  const loadNorms = useCallback(async () => {
    setLoading(true);
    const code = await detectCountry(plotLat, plotLng);
    const data  = NORMS_DB[code] ?? { ...NORMS_DB.DEFAULT, country: code };
    setNorms(data);
    setLoading(false);
  }, [plotLat, plotLng]);

  useEffect(() => { loadNorms(); }, [loadNorms]);

  if (loading) return (
    <div className="flex flex-col items-center justify-center h-40 gap-2">
      <Loader2 className="w-5 h-5 animate-spin text-[#7c93c3]" />
      <p className="text-[10px] text-slate-400">Detecting location norms…</p>
    </div>
  );

  if (!norms) return null;

  const typeIcon = (t: string) =>
    t === "warning"  ? <AlertTriangle className="w-3 h-3 text-amber-500" /> :
    t === "success"  ? <CheckCircle   className="w-3 h-3 text-emerald-500" /> :
                       <Shield        className="w-3 h-3 text-[#7c93c3]" />;

  const typeBg = (t: string) =>
    t === "warning"  ? "bg-amber-50   border-amber-100"  :
    t === "success"  ? "bg-emerald-50 border-emerald-100" :
                       "bg-blue-50    border-blue-100";

  return (
    <div className="absolute inset-0 overflow-y-auto bg-white">
      {/* Header */}
      <div className="sticky top-0 z-10 bg-white border-b border-slate-100 px-4 py-3">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-sm font-bold text-slate-800 flex items-center gap-2">
              <Shield className="w-4 h-4 text-[#7c93c3]" />
              Government Norms
            </h2>
            <p className="text-[9px] text-slate-400 mt-0.5">{norms.country} · {norms.code_name}</p>
          </div>
          <button onClick={loadNorms}
            className="p-1.5 rounded-lg hover:bg-slate-100 transition text-slate-400">
            <RefreshCw className="w-3.5 h-3.5" />
          </button>
        </div>
        <p className="text-[9px] text-slate-400 mt-1">Authority: {norms.authority}</p>
      </div>

      {/* NBC Compliance from last generation */}
      {compliance && (
        <div className={`mx-3 mt-3 rounded-xl p-3 border ${compliance.compliant ? "bg-emerald-50 border-emerald-200" : "bg-red-50 border-red-200"}`}>
          <div className="flex items-center gap-2 mb-2">
            {compliance.compliant
              ? <CheckCircle className="w-3.5 h-3.5 text-emerald-600" />
              : <AlertTriangle className="w-3.5 h-3.5 text-red-500" />}
            <span className={`text-[10px] font-bold ${compliance.compliant ? "text-emerald-700" : "text-red-700"}`}>
              Your Building: {compliance.compliant ? "NBC Compliant ✓" : "Issues Found"}
            </span>
          </div>
          <div className="grid grid-cols-3 gap-1.5 mb-2">
            {[
              ["FAR",      `${compliance.actual_far} / ${compliance.allowed_far}`],
              ["Coverage", `${compliance.actual_coverage_pct}% / ${compliance.allowed_coverage_pct}%`],
              ["Height",   `${(compliance as any).actual_height_m}m`],
            ].map(([k,v]) => (
              <div key={k} className="bg-white/70 rounded-lg p-1.5 text-center">
                <p className="text-[8px] text-slate-400">{k}</p>
                <p className="text-[9px] font-bold text-slate-700">{v}</p>
              </div>
            ))}
          </div>
          {compliance.issues.map((issue, i) => (
            <p key={i} className="text-[9px] text-red-600 flex gap-1">
              <span>•</span>{issue}
            </p>
          ))}
        </div>
      )}

      {/* Sections */}
      <div className="p-3 space-y-2">
        {norms.sections.map(sec => (
          <div key={sec.title} className={`rounded-xl border overflow-hidden ${typeBg(sec.type)}`}>
            <button
              className="w-full flex items-center justify-between px-3 py-2.5 text-left"
              onClick={() => setExpanded(expanded === sec.title ? null : sec.title)}>
              <div className="flex items-center gap-2">
                {typeIcon(sec.type)}
                <span className="text-[10px] font-bold text-slate-700">{sec.title}</span>
              </div>
              {expanded === sec.title
                ? <ChevronUp className="w-3 h-3 text-slate-400" />
                : <ChevronDown className="w-3 h-3 text-slate-400" />}
            </button>
            {expanded === sec.title && (
              <div className="px-3 pb-3 pt-0.5 space-y-1">
                {sec.items.map((item, i) => (
                  <div key={i} className="flex gap-2 text-[9px] text-slate-600">
                    <span className="text-slate-300 flex-shrink-0">→</span>
                    <span>{item}</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        ))}

        {/* Links */}
        <div className="pt-2 border-t border-slate-100">
          <p className="text-[9px] font-bold text-slate-400 uppercase tracking-wider mb-2">Official References</p>
          <div className="flex flex-wrap gap-2">
            {norms.links.map(link => (
              <a key={link.label} href={link.url} target="_blank" rel="noopener noreferrer"
                className="text-[9px] text-[#7c93c3] hover:underline bg-[#7c93c3]/10 px-2 py-1 rounded-lg">
                {link.label} ↗
              </a>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
