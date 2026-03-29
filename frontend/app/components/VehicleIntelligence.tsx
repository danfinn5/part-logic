"use client";

import { VehicleIntelligence as VehicleIntelligenceType } from "../lib/types";

const CATEGORY_LABELS: Record<string, string> = {
  oem_catalog: "OEM Parts Catalogs",
  fsm: "Factory Service Manuals",
  oem_service: "OEM Service Portals",
  wiring: "Wiring Diagrams",
  tsb_recall: "TSBs & Recalls",
  cross_reference: "Cross-Reference Tools",
  youtube: "YouTube Channels",
  forum: "Forums",
  reference: "Reference",
};

const CATEGORY_ORDER = [
  "oem_catalog",
  "fsm",
  "cross_reference",
  "wiring",
  "youtube",
  "forum",
  "oem_service",
  "tsb_recall",
  "reference",
];

export default function VehicleIntelligence({
  data,
}: {
  data: VehicleIntelligenceType;
}) {
  const hasRecalls = data.recalls.length > 0;
  const hasResources = data.repair_resources.length > 0;

  if (!hasRecalls && !hasResources && data.complaint_count === 0) return null;

  // Group resources by category
  const grouped: Record<string, typeof data.repair_resources> = {};
  for (const r of data.repair_resources) {
    if (!grouped[r.category]) grouped[r.category] = [];
    grouped[r.category].push(r);
  }

  return (
    <section className="space-y-4">
      {/* Recalls */}
      {hasRecalls && (
        <div className="card border-amber-200 dark:border-amber-800 bg-amber-50 dark:bg-amber-950/30 p-4">
          <h3 className="text-sm font-semibold text-amber-800 dark:text-amber-300 mb-2">
            NHTSA Recalls ({data.recalls.length})
          </h3>
          <div className="space-y-2">
            {data.recalls.map((r) => (
              <div key={r.campaign_number} className="text-xs">
                <div className="flex items-start gap-2">
                  <span className="font-mono text-amber-600 dark:text-amber-400 shrink-0">
                    {r.campaign_number}
                  </span>
                  <span className="text-amber-900 dark:text-amber-200 font-medium">
                    {r.component}
                  </span>
                </div>
                <p className="text-amber-700 dark:text-amber-300/80 mt-0.5 leading-relaxed">
                  {r.summary.length > 200
                    ? r.summary.slice(0, 200) + "..."
                    : r.summary}
                </p>
              </div>
            ))}
          </div>
          {data.complaint_count > 0 && (
            <p className="text-xs text-amber-600 dark:text-amber-400 mt-2">
              + {data.complaint_count} consumer complaint
              {data.complaint_count !== 1 ? "s" : ""} on file
            </p>
          )}
        </div>
      )}

      {/* Complaint count without recalls */}
      {!hasRecalls && data.complaint_count > 0 && (
        <p className="text-xs text-slate-500 dark:text-zinc-400">
          {data.complaint_count} NHTSA consumer complaint
          {data.complaint_count !== 1 ? "s" : ""} on file for this vehicle
        </p>
      )}

      {/* Repair Resources */}
      {hasResources && (
        <div className="card p-4">
          <h3 className="section-title text-base mb-3">Repair Resources</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-3">
            {CATEGORY_ORDER.filter((cat) => grouped[cat]).map((cat) => (
              <div key={cat}>
                <h4 className="text-xs font-semibold text-slate-500 dark:text-zinc-400 uppercase tracking-wider mb-1">
                  {CATEGORY_LABELS[cat] || cat}
                </h4>
                <ul className="space-y-0.5">
                  {grouped[cat].map((r) => (
                    <li key={r.url}>
                      <a
                        href={r.url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-sm text-blue-600 dark:text-blue-400 hover:text-blue-800 dark:hover:text-blue-300 transition-colors"
                        title={r.description}
                      >
                        {r.name}
                      </a>
                      <span className="text-xs text-slate-400 dark:text-zinc-500 ml-1.5">
                        {r.description.length > 60
                          ? r.description.slice(0, 60) + "..."
                          : r.description}
                      </span>
                    </li>
                  ))}
                </ul>
              </div>
            ))}
          </div>
        </div>
      )}
    </section>
  );
}
