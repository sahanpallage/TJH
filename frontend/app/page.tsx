"use client";

import { useState } from "react";

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
  const [activeService, setActiveService] = useState<string | null>(null);

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
      // Escape quotes by doubling them, wrap in quotes if it contains special chars
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
        : activeService === "theirstack"
        ? "theirstack"
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

  const handleSearch = async (service: "jsearch" | "theirstack") => {
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

  return (
    <div className="min-h-screen bg-gradient-to-br from-zinc-50 to-zinc-100 dark:from-black dark:to-zinc-900 py-8 px-4 sm:px-6 lg:px-8">
      <div className="max-w-7xl mx-auto">
        <div className="text-center mb-8">
          <h1 className="text-4xl font-bold text-zinc-900 dark:text-zinc-50 mb-2">
            Job Search
          </h1>
          <p className="text-zinc-600 dark:text-zinc-400">
            Search for jobs using JSearch or TheirStack APIs
          </p>
        </div>

        {/* Search Form */}
        <div className="bg-white dark:bg-zinc-800 rounded-lg shadow-lg p-6 mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
            <div>
              <label
                htmlFor="jobTitle"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Job Title *
              </label>
              <input
                type="text"
                id="jobTitle"
                name="jobTitle"
                value={formData.jobTitle}
                onChange={handleInputChange}
                placeholder="e.g., Software Engineer"
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50"
                required
              />
            </div>

            <div>
              <label
                htmlFor="industry"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Industry
              </label>
              <input
                type="text"
                id="industry"
                name="industry"
                value={formData.industry}
                onChange={handleInputChange}
                placeholder="e.g., Technology"
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50"
              />
            </div>

            <div>
              <label
                htmlFor="salaryMin"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Salary Range (Min USD)
              </label>
              <input
                type="number"
                id="salaryMin"
                name="salaryMin"
                value={formData.salaryMin}
                onChange={handleInputChange}
                placeholder="e.g., 50000"
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50"
              />
            </div>

            <div>
              <label
                htmlFor="salaryMax"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Salary Range (Max USD)
              </label>
              <input
                type="number"
                id="salaryMax"
                name="salaryMax"
                value={formData.salaryMax}
                onChange={handleInputChange}
                placeholder="e.g., 150000"
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50"
              />
            </div>

            <div>
              <label
                htmlFor="jobType"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Job Type
              </label>
              <select
                id="jobType"
                name="jobType"
                value={formData.jobType}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50"
              >
                <option value="">Any</option>
                <option value="Remote">Remote</option>
                <option value="On-site">On-site</option>
                <option value="Hybrid">Hybrid</option>
                <option value="Full-time">Full-time</option>
                <option value="Part-time">Part-time</option>
              </select>
            </div>

            <div>
              <label
                htmlFor="city"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                City
              </label>
              <input
                type="text"
                id="city"
                name="city"
                value={formData.city}
                onChange={handleInputChange}
                placeholder="e.g., San Francisco"
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50"
              />
            </div>

            <div>
              <label
                htmlFor="country"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Country
              </label>
              <input
                type="text"
                id="country"
                name="country"
                value={formData.country}
                onChange={handleInputChange}
                placeholder="e.g., US or United States"
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50"
              />
            </div>

            <div>
              <label
                htmlFor="datePosted"
                className="block text-sm font-medium text-zinc-700 dark:text-zinc-300 mb-2"
              >
                Date Posted
              </label>
              <select
                id="datePosted"
                name="datePosted"
                value={formData.datePosted}
                onChange={handleInputChange}
                className="w-full px-4 py-2 border border-zinc-300 dark:border-zinc-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent bg-white dark:bg-zinc-700 text-zinc-900 dark:text-zinc-50"
              >
                <option value="">Any time</option>
                <option value="day">Past 24 hours</option>
                <option value="week">Past week</option>
                <option value="month">Past month</option>
              </select>
            </div>
          </div>

          {/* Search Buttons */}
          <div className="flex flex-col sm:flex-row gap-4">
            <button
              onClick={() => handleSearch("jsearch")}
              disabled={loading || !formData.jobTitle.trim()}
              className="flex-1 px-6 py-3 bg-blue-600 hover:bg-blue-700 disabled:bg-zinc-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors duration-200"
            >
              {loading && activeService === "jsearch"
                ? "Searching..."
                : "Search with JSearch (RapidAPI)"}
            </button>
            <button
              onClick={() => handleSearch("theirstack")}
              disabled={loading || !formData.jobTitle.trim()}
              className="flex-1 px-6 py-3 bg-green-600 hover:bg-green-700 disabled:bg-zinc-400 disabled:cursor-not-allowed text-white font-semibold rounded-lg transition-colors duration-200"
            >
              {loading && activeService === "theirstack"
                ? "Searching..."
                : "Search with TheirStack"}
            </button>
          </div>
        </div>

        {/* Error Message */}
        {error && (
          <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4 mb-6">
            <p className="text-red-800 dark:text-red-200">{error}</p>
          </div>
        )}

        {/* Results header + actions */}
        {jobs.length > 0 && (
          <div className="mb-4 flex flex-col gap-3 md:flex-row md:items-center md:justify-between">
            <div>
              <h2 className="text-2xl font-semibold text-zinc-900 dark:text-zinc-50 mb-1">
                Results ({jobs.length} jobs found)
              </h2>
              <p className="text-sm text-zinc-600 dark:text-zinc-400">
                Using:{" "}
                {activeService === "jsearch"
                  ? "JSearch (RapidAPI)"
                  : "TheirStack"}
              </p>
            </div>
            <button
              onClick={downloadCsv}
              className="inline-flex items-center justify-center px-4 py-2 rounded-lg border border-zinc-300 dark:border-zinc-600 text-sm font-medium text-zinc-800 dark:text-zinc-100 bg-white dark:bg-zinc-800 hover:bg-zinc-50 dark:hover:bg-zinc-700 transition-colors"
            >
              Download CSV
            </button>
          </div>
        )}

        {/* Job Cards */}
        <div className="grid grid-cols-1 gap-6">
          {jobs.map((job: Job) => (
            <div
              key={job.id}
              className="bg-white dark:bg-zinc-800 rounded-lg shadow-md p-6 hover:shadow-lg transition-shadow duration-200"
            >
              <div className="flex flex-col md:flex-row md:items-start md:justify-between mb-4">
                <div className="flex-1">
                  <h3 className="text-xl font-semibold text-zinc-900 dark:text-zinc-50 mb-2">
                    {job.title || "No title"}
                  </h3>
                  <p className="text-lg text-zinc-700 dark:text-zinc-300 mb-2">
                    {job.company || "Company not specified"}
                  </p>
                  <div className="flex flex-wrap gap-2 text-sm text-zinc-600 dark:text-zinc-400">
                    {job.location && (
                      <span className="flex items-center">
                        📍 {job.location}
                      </span>
                    )}
                    {job.salary && (
                      <span className="flex items-center">💰 {job.salary}</span>
                    )}
                    {job.type && (
                      <span className="flex items-center">
                        {job.remote ? "🏠 Remote" : "🏢 " + job.type}
                      </span>
                    )}
                    {job.posted && (
                      <span className="flex items-center">
                        📅{" "}
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
                      </span>
                    )}
                  </div>
                </div>
              </div>

              {job.description && (
                <p className="text-zinc-600 dark:text-zinc-400 mb-4 line-clamp-3">
                  {job.description.substring(0, 200)}...
                </p>
              )}

              {job.applyLink && (
                <a
                  href={job.applyLink}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-block px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors duration-200"
                >
                  Apply Now →
                </a>
              )}
            </div>
          ))}
        </div>

        {jobs.length === 0 && !loading && !error && (
          <div className="text-center py-12">
            <p className="text-zinc-500 dark:text-zinc-400">
              Fill in the form above and click a search button to find jobs
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
