"use client";

import React, { useState } from "react";

interface Job {
  id: string;
  title: string;
  company: string;
  location: string;
  city: string;
  state: string;
  country: string;
  salary: string;
  type: string;
  remote: boolean;
  posted: string;
  description: string;
  applyLink: string;
}

interface FormData {
  jobTitle: string;
  industry: string;
  salaryMin: string;
  salaryMax: string;
  jobType: string;
  city: string;
  country: string;
  datePosted: string;
}

export default function Home() {
  const [formData, setFormData] = useState<FormData>({
    jobTitle: "",
    industry: "",
    salaryMin: "",
    salaryMax: "",
    jobType: "",
    city: "",
    country: "",
    datePosted: "",
  });

  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeService, setActiveService] = useState<
    "jsearch" | "indeed" | "linkedin" | null
  >(null);

  const downloadCsv = () => {
    if (!jobs.length) return;

    const headers = [
      "id",
      "title",
      "company",
      "location",
      "city",
      "state",
      "country",
      "salary",
      "type",
      "remote",
      "posted",
      "description",
      "applyLink",
    ];

    const escapeCell = (value: unknown) => {
      if (value === null || value === undefined) return "";
      const str = String(value);
      const needsQuotes = /[",\n]/.test(str);
      const escaped = str.replace(/"/g, '""');
      return needsQuotes ? `"${escaped}"` : escaped;
    };

    const rows = jobs.map((job) =>
      [
        job.id,
        job.title,
        job.company,
        job.location,
        job.city,
        job.state,
        job.country,
        job.salary,
        job.type,
        job.remote ? "true" : "false",
        job.posted,
        job.description,
        job.applyLink,
      ].map(escapeCell)
    );

    const csvContent = [
      headers.join(","),
      ...rows.map((row) => row.join(",")),
    ].join("\r\n");

    const blob = new Blob([csvContent], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");

    const source =
      activeService === "jsearch"
        ? "jsearch"
        : activeService === "indeed"
        ? "indeed"
        : activeService === "linkedin"
        ? "linkedin"
        : "jobs";

    link.href = url;
    link.setAttribute(
      "download",
      `jobs-${source}-${new Date().toISOString().slice(0, 10)}.csv`
    );
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(url);
  };

  const handleInputChange = (
    e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>
  ) => {
    const { name, value } = e.target;
    setFormData((prev: FormData) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSearch = async (service: "jsearch" | "indeed" | "linkedin") => {
    setLoading(true);
    setError(null);
    setActiveService(service);
    setJobs([]);

    try {
      const response = await fetch(`/api/${service}`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(formData),
      });

      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.error || `Failed to search with ${service}`);
      }

      setJobs(data.jobs || []);
      if (data.jobs && data.jobs.length === 0) {
        setError("No jobs found. Try adjusting your search criteria.");
      }
    } catch (err: any) {
      setError(err.message || "An error occurred while searching for jobs");
      setJobs([]);
    } finally {
      setLoading(false);
    }
  };

  const disabledSearch = loading || !formData.jobTitle.trim();

  return (
    <div className="mx-auto flex min-h-[calc(100vh-104px)] max-w-7xl flex-col gap-8 px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
      <section className="grid gap-8 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] lg:items-stretch">
        <div className="glass-panel relative p-6 sm:p-8">
          <div className="pointer-events-none absolute inset-0 -z-10 rounded-[1.25rem] border border-white/10" />

          <div className="mb-6 flex items-center gap-3 text-xs text-zinc-400">
            <span className="pill-badge inline-flex items-center gap-1.5 px-3 py-1">
              <span className="h-1.5 w-1.5 rounded-full bg-sky-400 shadow-[0_0_18px_rgba(56,189,248,1)]" />
              <span className="font-medium text-[11px] uppercase tracking-[0.18em] text-zinc-200">
                Smart Job Search
              </span>
            </span>
            <span className="hidden sm:inline text-[11px] text-zinc-500">
              CSV export
            </span>
          </div>

          <div className="mb-7 space-y-4">
            <h1 className="text-balance text-3xl font-semibold tracking-tight text-zinc-50 sm:text-4xl lg:text-[2.6rem]">
              Find roles that match your stack,
              <span className="bg-linear-to-r from-sky-400 via-cyan-300 to-emerald-300 bg-clip-text text-transparent">
                {" "}
                not just your title.
              </span>
            </h1>
            <p className="max-w-xl text-sm leading-relaxed text-zinc-300 sm:text-[15px]">
              Surface engineering roles by skills, salary band, and
              location—without the noisy job board clutter.
            </p>
          </div>

          <div className="mb-6 grid gap-4 rounded-2xl border border-white/10 bg-black/30 p-4 text-xs text-zinc-300 sm:grid-cols-3 sm:gap-3 sm:p-5">
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-sky-500/20 text-sky-300">
                <span className="text-[13px]">1</span>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
                  Target
                </p>
                <p className="text-[13px]">Choose role & filters</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-emerald-500/20 text-emerald-300">
                <span className="text-[13px]">2</span>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
                  Scan
                </p>
                <p className="text-[13px]">
                  Hit Platform 1 / Platform 2 / LinkedIn
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <div className="flex h-7 w-7 items-center justify-center rounded-full bg-indigo-500/20 text-indigo-300">
                <span className="text-[13px]">3</span>
              </div>
              <div>
                <p className="text-[11px] font-semibold uppercase tracking-[0.16em] text-zinc-400">
                  Export
                </p>
                <p className="text-[13px]">Save your curated list</p>
              </div>
            </div>
          </div>

          <div className="space-y-4 rounded-2xl border border-white/5 bg-black/40 p-4 sm:p-5">
            <div className="grid gap-4 sm:grid-cols-[minmax(0,1.4fr)_minmax(0,1.1fr)]">
              <div className="space-y-3">
                <label
                  htmlFor="jobTitle"
                  className="flex items-center justify-between text-xs font-medium text-zinc-200"
                >
                  <span>Role or title *</span>
                  <span className="text-[11px] text-zinc-400">
                    Try &ldquo;Senior Backend Engineer&rdquo;
                  </span>
                </label>
                <input
                  type="text"
                  id="jobTitle"
                  name="jobTitle"
                  value={formData.jobTitle}
                  onChange={handleInputChange}
                  placeholder="e.g., Staff Frontend Engineer"
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-3.5 py-2.5 text-sm text-zinc-50 outline-none ring-0 transition focus:border-sky-400/70 focus:ring-2 focus:ring-sky-500/50"
                  required
                />
              </div>

              <div className="space-y-3">
                <label
                  htmlFor="industry"
                  className="flex items-center justify-between text-xs font-medium text-zinc-200"
                >
                  <span>Industry</span>
                  <span className="text-[11px] text-zinc-400">
                    Optional focus (fintech, AI, etc.)
                  </span>
                </label>
                <input
                  type="text"
                  id="industry"
                  name="industry"
                  value={formData.industry}
                  onChange={handleInputChange}
                  placeholder="e.g., Developer tools / AI infra"
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-3.5 py-2.5 text-sm text-zinc-50 outline-none ring-0 transition focus:border-emerald-400/70 focus:ring-2 focus:ring-emerald-500/50"
                />
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
              <div className="space-y-2.5">
                <label
                  htmlFor="salaryMin"
                  className="block text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-400"
                >
                  Min salary (USD)
                </label>
                <input
                  type="number"
                  id="salaryMin"
                  name="salaryMin"
                  value={formData.salaryMin}
                  onChange={handleInputChange}
                  placeholder="80,000"
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-zinc-50 outline-none ring-0 transition focus:border-sky-400/70 focus:ring-2 focus:ring-sky-500/50"
                />
              </div>

              <div className="space-y-2.5">
                <label
                  htmlFor="salaryMax"
                  className="block text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-400"
                >
                  Max salary (USD)
                </label>
                <input
                  type="number"
                  id="salaryMax"
                  name="salaryMax"
                  value={formData.salaryMax}
                  onChange={handleInputChange}
                  placeholder="220,000"
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-zinc-50 outline-none ring-0 transition focus:border-sky-400/70 focus:ring-2 focus:ring-sky-500/50"
                />
              </div>

              <div className="space-y-2.5">
                <label
                  htmlFor="jobType"
                  className="block text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-400"
                >
                  Work style / type
                </label>
                <select
                  id="jobType"
                  name="jobType"
                  value={formData.jobType}
                  onChange={handleInputChange}
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-zinc-50 outline-none ring-0 transition focus:border-emerald-400/70 focus:ring-2 focus:ring-emerald-500/50"
                >
                  <option value="">Any</option>
                  <option value="Remote">Remote</option>
                  <option value="On-site">On-site</option>
                  <option value="Hybrid">Hybrid</option>
                  <option value="Full-time">Full-time</option>
                  <option value="Part-time">Part-time</option>
                </select>
              </div>

              <div className="space-y-2.5">
                <label
                  htmlFor="datePosted"
                  className="block text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-400"
                >
                  Freshness
                </label>
                <select
                  id="datePosted"
                  name="datePosted"
                  value={formData.datePosted}
                  onChange={handleInputChange}
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-zinc-50 outline-none ring-0 transition focus:border-emerald-400/70 focus:ring-2 focus:ring-emerald-500/50"
                >
                  <option value="">Any time</option>
                  <option value="day">Past 24 hours</option>
                  <option value="week">Past week</option>
                  <option value="month">Past month</option>
                </select>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              <div className="space-y-2.5">
                <label
                  htmlFor="city"
                  className="block text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-400"
                >
                  City (optional)
                </label>
                <input
                  type="text"
                  id="city"
                  name="city"
                  value={formData.city}
                  onChange={handleInputChange}
                  placeholder="San Francisco, London..."
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-zinc-50 outline-none ring-0 transition focus:border-sky-400/70 focus:ring-2 focus:ring-sky-500/50"
                />
              </div>

              <div className="space-y-2.5">
                <label
                  htmlFor="country"
                  className="block text-[11px] font-medium uppercase tracking-[0.16em] text-zinc-400"
                >
                  Country / region
                </label>
                <input
                  type="text"
                  id="country"
                  name="country"
                  value={formData.country}
                  onChange={handleInputChange}
                  placeholder="US, UK, EU ..."
                  className="w-full rounded-lg border border-white/10 bg-black/40 px-3 py-2 text-sm text-zinc-50 outline-none ring-0 transition focus:border-sky-400/70 focus:ring-2 focus:ring-sky-500/50"
                />
              </div>

              <div className="flex items-end justify-end gap-2">
                <p className="hidden text-[11px] text-zinc-400 sm:inline">
                  Powered by curated job APIs. No spammy listings.
                </p>
              </div>
            </div>

            <div className="mt-1 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
              <div className="inline-flex items-center gap-2 text-[11px] text-zinc-400">
                <span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_10px_rgba(52,211,153,1)]" />
                <span>
                  Searches run directly against{" "}
                  <span className="font-medium text-zinc-200">
                    your backend
                  </span>
                  .
                </span>
              </div>

              <button
                onClick={() => handleSearch("linkedin")}
                disabled={disabledSearch}
                className="inline-flex items-center justify-center gap-2 rounded-lg border border-indigo-400/60 bg-slate-900/70 px-4 py-2.5 text-sm font-semibold text-zinc-50 shadow-[0_10px_30px_rgba(30,64,175,0.75)] transition hover:border-sky-400/70 hover:bg-slate-900/80 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading && activeService === "linkedin" ? (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-3 w-3 animate-spin rounded-full border border-zinc-300 border-t-transparent" />
                    <span>Scanning LinkedIn…</span>
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-2">
                    <span className="h-1.5 w-1.5 rounded-full bg-indigo-400" />
                    <span className="cursor-pointer">Search via LinkedIn</span>
                  </span>
                )}
              </button>
              <div className="flex flex-col gap-2 sm:flex-row sm:gap-3">
                <button
                  onClick={() => handleSearch("jsearch")}
                  disabled={disabledSearch}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-sky-400/60 bg-slate-900/60 px-4 py-2.5 text-sm font-semibold text-zinc-50 shadow-[0_10px_35px_rgba(56,189,248,0.85)] transition hover:border-sky-400/80 hover:bg-slate-900/70 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading && activeService === "jsearch" ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-3 w-3 animate-spin rounded-full border border-slate-300 border-t-transparent" />
                      <span>Scanning globally…</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-sky-400 shadow-[0_0_14px_rgba(56,189,248,1)]" />
                      <span className="cursor-pointer">Search via JSearch</span>
                    </span>
                  )}
                </button>

                <button
                  onClick={() => handleSearch("indeed")}
                  disabled={disabledSearch}
                  className="inline-flex items-center justify-center gap-2 rounded-lg border border-emerald-400/60 bg-slate-900/60 px-4 py-2.5 text-sm font-semibold text-zinc-50 shadow-[0_10px_30px_rgba(6,95,70,0.85)] transition hover:border-emerald-400/80 hover:bg-slate-900/70 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  {loading && activeService === "indeed" ? (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-3 w-3 animate-spin rounded-full border border-zinc-400 border-t-transparent" />
                      <span>Scanning Indeed…</span>
                    </span>
                  ) : (
                    <span className="inline-flex items-center gap-2">
                      <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
                      <span className="cursor-pointer">Search via Indeed</span>
                    </span>
                  )}
                </button>
              </div>
            </div>
          </div>
        </div>

        <aside className="subtle-card relative flex flex-col justify-between p-5 sm:p-6 lg:p-7">
          <div className="absolute inset-0 -z-10 rounded-[0.9rem] border border-white/5" />

          <div className="space-y-4">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-400">
              Snapshot
            </p>
            <p className="text-balance text-sm text-zinc-100">
              Design your search like a senior engineer: tighten your filters,
              compare stacks, and export a focused shortlist you can actually
              work through.
            </p>

            <div className="mt-4 grid gap-3 text-[11px] text-zinc-300">
              <div className="flex items-start justify-between rounded-lg border border-zinc-700/80 bg-zinc-900/70 px-3 py-2.5">
                <div>
                  <p className="font-semibold text-zinc-100">
                    Search confidence
                  </p>
                  <p className="mt-1 text-[11px] text-zinc-400">
                    Layer multiple filters to avoid generic listings.
                  </p>
                </div>
                <span className="ml-3 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                  Recommended
                </span>
              </div>

              <div className="flex items-start justify-between rounded-lg border border-zinc-700/80 bg-zinc-900/70 px-3 py-2.5">
                <div>
                  <p className="font-semibold text-zinc-100">
                    Three engines, one UI
                  </p>
                  <p className="mt-1 text-[11px] text-zinc-400">
                    Compare each engine's results for the same role.
                  </p>
                </div>
              </div>

              <div className="flex items-start justify-between rounded-lg border border-zinc-700/80 bg-zinc-900/70 px-3 py-2.5">
                <div>
                  <p className="font-semibold text-zinc-100">
                    CSV as source-of-truth
                  </p>
                  <p className="mt-1 text-[11px] text-zinc-400">
                    Export once, track outreach in your own system.
                  </p>
                </div>
              </div>
            </div>
          </div>

          <div className="mt-6 flex items-center justify-between rounded-xl border border-zinc-700/80 bg-zinc-900/80 px-3.5 py-2.5 text-[11px] text-zinc-300">
            <div className="space-y-0.5">
              <p className="font-semibold text-zinc-100">
                {jobs.length > 0
                  ? `Currently viewing ${jobs.length} ${
                      jobs.length === 1 ? "role" : "roles"
                    }`
                  : "No active results yet"}
              </p>
              <p className="text-[10px] text-zinc-400">
                {jobs.length > 0
                  ? "Refine filters or export to keep this snapshot."
                  : "Run a search to see live opportunities here."}
              </p>
            </div>

            <button
              onClick={downloadCsv}
              disabled={!jobs.length}
              className="inline-flex items-center gap-1.5 rounded-full border border-emerald-400/60 bg-emerald-500/15 px-3 py-1.5 text-[11px] font-semibold text-emerald-200 shadow-[0_10px_25px_rgba(6,78,59,0.7)] transition hover:bg-emerald-500/25 disabled:cursor-not-allowed disabled:border-zinc-600 disabled:bg-zinc-800 disabled:text-zinc-400"
            >
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-300" />
              <span className="cursor-pointer">Download CSV</span>
            </button>
          </div>
        </aside>
      </section>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-950/60 px-4 py-3 text-sm text-red-200 shadow-[0_15px_35px_rgba(127,29,29,0.65)] sm:px-5">
          {error}
        </div>
      )}

      <section className="space-y-4">
        {jobs.length > 0 && (
          <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
            <div>
              <p className="text-xs font-semibold uppercase tracking-[0.2em] text-zinc-400">
                Result set
              </p>
              <h2 className="mt-1 text-lg font-semibold text-zinc-50 sm:text-xl">
                {jobs.length}{" "}
                {jobs.length === 1 ? "matching role" : "matching roles"} found
              </h2>
              <p className="mt-1 text-[11px] text-zinc-400">
                Source:{" "}
                <span className="font-medium text-zinc-200">
                  {activeService === "jsearch"
                    ? "JSearch (RapidAPI)"
                    : activeService === "indeed"
                    ? "Indeed"
                    : activeService === "linkedin"
                    ? "LinkedIn (JobSpy)"
                    : "Unknown"}
                </span>
              </p>
            </div>

            <div className="flex gap-2 text-[11px] text-zinc-400">
              <span className="inline-flex items-center gap-1 rounded-full border border-zinc-600/70 bg-zinc-900/80 px-2.5 py-1">
                <span className="h-1.5 w-1.5 rounded-full bg-sky-400" />
                <span>Tip: open roles you like in new tabs</span>
              </span>
            </div>
          </div>
        )}

        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {jobs.map((job: Job) => (
            <article
              key={job.id}
              className="group flex flex-col justify-between rounded-2xl border border-zinc-700/80 bg-zinc-950/80 p-4 text-sm text-zinc-200 shadow-[0_16px_40px_rgba(15,23,42,0.98)] transition hover:-translate-y-0.5 hover:border-sky-400/70 hover:shadow-[0_22px_55px_rgba(8,47,73,0.95)] sm:p-5"
            >
              <div>
                <div className="mb-3 flex items-start justify-between gap-3">
                  <div>
                    <h3 className="line-clamp-2 text-sm font-semibold text-zinc-50 sm:text-[15px]">
                      {job.title || "Untitled role"}
                    </h3>
                    <p className="mt-1 text-[13px] text-zinc-300">
                      {job.company || "Company not specified"}
                    </p>
                  </div>
                  <div className="text-right text-[11px] text-zinc-400">
                    {job.posted && (
                      <p>
                        {(() => {
                          try {
                            const date = new Date(job.posted);
                            return isNaN(date.getTime())
                              ? job.posted
                              : date.toLocaleDateString();
                          } catch {
                            return job.posted;
                          }
                        })()}
                      </p>
                    )}
                    {job.remote && (
                      <p className="mt-1 rounded-full bg-emerald-500/15 px-2 py-0.5 text-[10px] font-semibold text-emerald-300">
                        Remote friendly
                      </p>
                    )}
                  </div>
                </div>

                <div className="mb-3 flex flex-wrap gap-1.5 text-[11px] text-zinc-300">
                  {job.location && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900/80 px-2 py-1">
                      <span className="text-zinc-500">📍</span>
                      <span>{job.location}</span>
                    </span>
                  )}
                  {job.salary && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900/80 px-2 py-1">
                      <span className="text-zinc-500">💰</span>
                      <span>{job.salary}</span>
                    </span>
                  )}
                  {job.type && (
                    <span className="inline-flex items-center gap-1 rounded-full bg-zinc-900/80 px-2 py-1">
                      <span className="text-zinc-500">💼</span>
                      <span>{job.type}</span>
                    </span>
                  )}
                </div>

                {job.description && (
                  <p className="line-clamp-4 text-[13px] leading-relaxed text-zinc-300/90">
                    {job.description.substring(0, 260)}...
                  </p>
                )}
              </div>

              <div className="mt-4 flex items-center justify-between pt-3">
                <span className="text-[10px] uppercase tracking-[0.18em] text-zinc-500">
                  {job.city || job.state || job.country
                    ? [job.city, job.state, job.country]
                        .filter(Boolean)
                        .join(", ")
                    : "Location not specified"}
                </span>

                {job.applyLink && (
                  <a
                    href={job.applyLink}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center gap-1.5 rounded-full border border-sky-400/70 bg-sky-500/15 px-3 py-1.5 text-[11px] font-semibold text-sky-200 transition group-hover:bg-sky-500/25"
                  >
                    <span>Open role</span>
                    <span className="text-[13px]">↗</span>
                  </a>
                )}
              </div>
            </article>
          ))}
        </div>

        {jobs.length === 0 && !loading && !error && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed border-zinc-700/80 bg-zinc-950/70 px-6 py-10 text-center text-sm text-zinc-300 sm:px-10">
            <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-zinc-500">
              Ready when you are
            </p>
            <p className="mt-2 max-w-md text-sm text-zinc-300">
              Start by entering a role title above, then pull in live
              opportunities from the platforms and export the shortlist that
              fits your profile.
            </p>
          </div>
        )}
      </section>
    </div>
  );
}
