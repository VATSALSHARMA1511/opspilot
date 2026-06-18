  import Layout from '../components/Layout'
  import { useState, useEffect, useCallback } from "react";
  import { useNavigate } from "react-router-dom";
  import {
    Plus,
    ChevronLeft,
    ChevronRight,
    Search,
    AlertCircle,
    Loader2,
    X,
  } from "lucide-react";
  import api from "../api/client";

  // ─── Constants ────────────────────────────────────────────────────────────────

  const STATUS_OPTIONS = [
    { value: "", label: "All Statuses" },
    { value: "pending_review", label: "Pending Review" },
    { value: "accepted", label: "Accepted" },
    { value: "rejected", label: "Rejected" },
    { value: "assigned", label: "Assigned" },
    { value: "in_progress", label: "In Progress" },
    { value: "resolved", label: "Resolved" },
    { value: "closed", label: "Closed" },
  ];

  const PRIORITY_OPTIONS = [
    { value: "", label: "All Priorities" },
    { value: "low", label: "Low" },
    { value: "medium", label: "Medium" },
    { value: "high", label: "High" },
    { value: "critical", label: "Critical" },
  ];

  const CATEGORY_OPTIONS = [
    { value: "hardware", label: "Hardware" },
    { value: "software", label: "Software" },
    { value: "network", label: "Network" },
    { value: "access", label: "Access" },
    { value: "other", label: "Other" },
  ];

  const STATUS_STYLES = {
    open: "bg-yellow-500/10 text-yellow-400 border border-yellow-500/20",
    assigned: "bg-blue-500/10 text-blue-400 border border-blue-500/20",
    in_progress: "bg-purple-500/10 text-purple-400 border border-purple-500/20",
    resolved: "bg-green-500/10 text-green-400 border border-green-500/20",
    closed: "bg-zinc-700/50 text-zinc-400 border border-zinc-700",
  };

  const PRIORITY_STYLES = {
    low: "text-zinc-400",
    medium: "text-blue-400",
    high: "text-orange-400",
    critical: "text-red-400",
  };

  const PRIORITY_DOT = {
    low: "bg-zinc-500",
    medium: "bg-blue-500",
    high: "bg-orange-500",
    critical: "bg-red-500",
  };

  // ─── Helpers ──────────────────────────────────────────────────────────────────

  function formatDate(iso) {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  }

  function StatusBadge({ status }) {
    const style = STATUS_STYLES[status] ?? STATUS_STYLES.closed;
    return (
      <span
        className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${style}`}
      >
        {status?.replace("_", " ")}
      </span>
    );
  }

  function PriorityLabel({ priority }) {
    const dot = PRIORITY_DOT[priority] ?? "bg-zinc-500";
    const text = PRIORITY_STYLES[priority] ?? "text-zinc-400";
    return (
      <span className={`inline-flex items-center gap-1.5 text-xs font-medium ${text}`}>
        <span className={`w-1.5 h-1.5 rounded-full ${dot}`} />
        {priority}
      </span>
    );
  }

  // ─── Create Ticket Modal ───────────────────────────────────────────────────────

  function CreateTicketModal({ onClose, onCreated }) {
  const [form, setForm] = useState({
    title: "",
    description: "",
    priority: "medium",
    category: "other",
    target_department_id: "",
  });
  const [departments, setDepartments] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get("/api/v1/departments").then(res => setDepartments(res.data || [])).catch(() => {})
  }, [])

  function handleChange(e) {
    setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
  }

  async function handleSubmit() {
    if (!form.title.trim()) { setError("Title is required."); return; }
    if (!form.description.trim()) { setError("Description is required."); return; }
    if (!form.target_department_id) { setError("Please select a department."); return; }
    setError("");
    setLoading(true);
    try {
      await api.post("/api/v1/tickets", {
        ...form,
        target_department_id: Number(form.target_department_id),
      });
      onCreated();
    } catch (err) {
      const detail = err.response?.data?.detail;
      setError(typeof detail === "string" ? detail : "Failed to create ticket.");
    } finally {
      setLoading(false);
    }
  }

  function handleBackdrop(e) {
    if (e.target === e.currentTarget) onClose();
  }

    function handleChange(e) {
      setForm((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    }

    async function handleSubmit() {
      if (!form.title.trim()) {
        setError("Title is required.");
        return;
      }
      if (!form.description.trim()) {
        setError("Description is required.");
        return;
      }
      setError("");
      setLoading(true);
      try {
        await api.post("/api/v1/tickets", form);
        onCreated();
      } catch (err) {
        const detail = err.response?.data?.detail;
        setError(typeof detail === "string" ? detail : "Failed to create ticket.");
      } finally {
        setLoading(false);
      }
    }

    // Close on backdrop click
    function handleBackdrop(e) {
      if (e.target === e.currentTarget) onClose();
    }

    return (
      <div
        className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm"
        onClick={handleBackdrop}
      >
        <div className="bg-zinc-900 border border-zinc-800 rounded-lg w-full max-w-lg mx-4 shadow-2xl">
          {/* Header */}
          <div className="flex items-center justify-between px-6 py-4 border-b border-zinc-800">
            <h2 className="text-base font-semibold text-white">New Ticket</h2>
            <button
              onClick={onClose}
              className="text-zinc-500 hover:text-white transition-colors"
            >
              <X size={18} />
            </button>
          </div>

          {/* Body */}
          <div className="px-6 py-5 space-y-4">
            {error && (
              <div className="flex items-start gap-2 text-red-400 text-sm bg-red-500/10 border border-red-500/20 rounded-md px-3 py-2.5">
                <AlertCircle size={14} className="mt-0.5 flex-shrink-0" />
                {error}
              </div>
            )}

            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">Title</label>
              <input
                name="title"
                value={form.title}
                onChange={handleChange}
                placeholder="Brief summary of the issue"
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors"
              />
            </div>

            <div>
              <label className="block text-xs text-zinc-400 mb-1.5">Description</label>
              <textarea
                name="description"
                value={form.description}
                onChange={handleChange}
                placeholder="Steps to reproduce, expected vs actual behavior, affected systems..."
                rows={4}
                className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors resize-none"
              />
            </div>
            <div>
            <label className="block text-xs text-zinc-400 mb-1.5">Department</label>
            <select
              name="target_department_id"
              value={form.target_department_id}
              onChange={handleChange}
              className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-600 transition-colors"
            >
              <option value="" disabled>Select a department</option>
              {departments.map(d => (
                <option key={d.id} value={d.id}>{d.name}</option>
              ))}
            </select>
          </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <label className="block text-xs text-zinc-400 mb-1.5">Priority</label>
                <select
                  name="priority"
                  value={form.priority}
                  onChange={handleChange}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-600 transition-colors"
                >
                  {PRIORITY_OPTIONS.filter((p) => p.value).map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label className="block text-xs text-zinc-400 mb-1.5">Category</label>
                <select
                  name="category"
                  value={form.category}
                  onChange={handleChange}
                  className="w-full bg-zinc-950 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-600 transition-colors"
                >
                  {CATEGORY_OPTIONS.map((c) => (
                    <option key={c.value} value={c.value}>
                      {c.label}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-zinc-800">
            <button
              onClick={onClose}
              className="px-4 py-2 text-sm text-zinc-400 hover:text-white transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSubmit}
              disabled={loading}
              className="flex items-center gap-2 px-4 py-2 bg-white text-zinc-950 text-sm font-medium rounded-md hover:bg-zinc-100 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
            >
              {loading && <Loader2 size={14} className="animate-spin" />}
              {loading ? "Creating..." : "Create Ticket"}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // ─── Main Page ────────────────────────────────────────────────────────────────

  export default function TicketsPage() {
    const navigate = useNavigate();

    const [tickets, setTickets] = useState([]);
    const [total, setTotal] = useState(0);
    const [page, setPage] = useState(1);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState("");

    const [filters, setFilters] = useState({ status: "", priority: "", search: "" });
    const [debouncedSearch, setDebouncedSearch] = useState("");
    const [showModal, setShowModal] = useState(false);

    const PAGE_SIZE = 10;
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));

    // Debounce search input
    useEffect(() => {
      const t = setTimeout(() => setDebouncedSearch(filters.search), 400);
      return () => clearTimeout(t);
    }, [filters.search]);

    // Reset to page 1 when filters change
    useEffect(() => {
      setPage(1);
    }, [filters.status, filters.priority, debouncedSearch]);

    const fetchTickets = useCallback(async () => {
      setLoading(true);
      setError("");
      try {
        const params = { page, page_size: PAGE_SIZE };
        if (filters.status) params.status = filters.status;
        if (filters.priority) params.priority = filters.priority;
        if (debouncedSearch) params.search = debouncedSearch;

        const res = await api.get("/api/v1/tickets", { params });
        setTickets(res.data.items ?? []);
        setTotal(res.data.total ?? 0);
      } catch (err) {
        setError("Failed to load tickets.");
      } finally {
        setLoading(false);
      }
    }, [page, filters.status, filters.priority, debouncedSearch]);

    useEffect(() => {
      fetchTickets();
    }, [fetchTickets]);

    function handleFilterChange(e) {
      setFilters((prev) => ({ ...prev, [e.target.name]: e.target.value }));
    }

    function handleTicketCreated() {
      setShowModal(false);
      fetchTickets();
    }

    // ── Render ──

    return (
      <Layout>
        <div className="space-y-5">
          {showModal && (
            <CreateTicketModal
              onClose={() => setShowModal(false)}
              onCreated={handleTicketCreated}
            />
          )}

          {/* Page Header */}
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-xl font-semibold text-white">Tickets</h1>
              <p className="text-xs text-zinc-500 mt-0.5">
                {total} ticket{total !== 1 ? "s" : ""} total
              </p>
            </div>
            <button
              onClick={() => setShowModal(true)}
              className="flex items-center gap-2 px-4 py-2 bg-white text-zinc-950 text-sm font-medium rounded-md hover:bg-zinc-100 transition-colors"
            >
              <Plus size={15} />
              New Ticket
            </button>
          </div>

          {/* Filters */}
          <div className="flex flex-wrap items-center gap-3">
            {/* Search */}
            <div className="relative">
              <Search
                size={14}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-zinc-500 pointer-events-none"
              />
              <input
                name="search"
                value={filters.search}
                onChange={handleFilterChange}
                placeholder="Search tickets..."
                className="pl-8 pr-3 py-2 bg-zinc-900 border border-zinc-800 rounded-md text-sm text-white placeholder-zinc-600 focus:outline-none focus:border-zinc-600 transition-colors w-56"
              />
            </div>

            {/* Status filter */}
            <select
              name="status"
              value={filters.status}
              onChange={handleFilterChange}
              className="bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-600 transition-colors"
            >
              {STATUS_OPTIONS.map((s) => (
                <option key={s.value} value={s.value}>
                  {s.label}
                </option>
              ))}
            </select>

            {/* Priority filter */}
            <select
              name="priority"
              value={filters.priority}
              onChange={handleFilterChange}
              className="bg-zinc-900 border border-zinc-800 rounded-md px-3 py-2 text-sm text-white focus:outline-none focus:border-zinc-600 transition-colors"
            >
              {PRIORITY_OPTIONS.map((p) => (
                <option key={p.value} value={p.value}>
                  {p.label}
                </option>
              ))}
            </select>

            {/* Clear filters */}
            {(filters.status || filters.priority || filters.search) && (
              <button
                onClick={() => setFilters({ status: "", priority: "", search: "" })}
                className="text-xs text-zinc-500 hover:text-white transition-colors flex items-center gap-1"
              >
                <X size={12} />
                Clear
              </button>
            )}
          </div>

          {/* Table */}
          <div className="bg-zinc-900 border border-zinc-800 rounded-lg overflow-hidden">
            {/* Table header */}
            <div className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr] gap-4 px-5 py-3 border-b border-zinc-800 bg-zinc-950">
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Title</span>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Status</span>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Priority</span>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Created by</span>
              <span className="text-xs font-medium text-zinc-500 uppercase tracking-wider">Date</span>
            </div>

            {/* Loading */}
            {loading && (
              <div className="flex items-center justify-center gap-2 py-16 text-zinc-500 text-sm">
                <Loader2 size={16} className="animate-spin" />
                Loading tickets...
              </div>
            )}

            {/* Error */}
            {!loading && error && (
              <div className="flex items-center justify-center gap-2 py-16 text-red-400 text-sm">
                <AlertCircle size={16} />
                {error}
              </div>
            )}

            {/* Empty */}
            {!loading && !error && tickets.length === 0 && (
              <div className="flex flex-col items-center justify-center py-16 text-zinc-500">
                <p className="text-sm">No tickets found.</p>
                {(filters.status || filters.priority || filters.search) ? (
                  <p className="text-xs mt-1">Try clearing the filters.</p>
                ) : (
                  <button
                    onClick={() => setShowModal(true)}
                    className="mt-3 text-xs text-white underline underline-offset-2"
                  >
                    Create the first ticket
                  </button>
                )}
              </div>
            )}

            {/* Rows */}
            {!loading && !error && tickets.map((ticket) => (
              <div
                key={ticket.id}
                onClick={() => navigate(`/tickets/${ticket.id}`)}
                className="grid grid-cols-[2fr_1fr_1fr_1fr_1fr] gap-4 px-5 py-4 border-b border-zinc-800 last:border-0 hover:bg-zinc-800/50 cursor-pointer transition-colors group"
              >
                {/* Title + ID */}
                <div className="min-w-0">
                  <p className="text-sm text-white font-medium truncate group-hover:text-white/90">
                    {ticket.title}
                  </p>
                  <p className="text-xs text-zinc-600 mt-0.5">#{String(ticket.id).slice(0, 8)}</p>
                </div>

                {/* Status */}
                <div className="flex items-center">
                  <StatusBadge status={ticket.status} />
                </div>

                {/* Priority */}
                <div className="flex items-center">
                  <PriorityLabel priority={ticket.priority} />
                </div>

                {/* Created by */}
                <div className="flex items-center">
                  <span className="text-sm text-zinc-400 truncate">
                    {ticket.created_by?.email ?? ticket.created_by?.id ?? "—"}
                  </span>
                </div>

                {/* Date */}
                <div className="flex items-center">
                  <span className="text-sm text-zinc-500">{formatDate(ticket.created_at)}</span>
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {!loading && !error && total > PAGE_SIZE && (
            <div className="flex items-center justify-between">
              <p className="text-xs text-zinc-500">
                Page {page} of {totalPages} — {total} results
              </p>
              <div className="flex items-center gap-1">
                <button
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                  disabled={page === 1}
                  className="flex items-center justify-center w-8 h-8 rounded-md border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronLeft size={14} />
                </button>

                {/* Page number pills */}
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter((n) => n === 1 || n === totalPages || Math.abs(n - page) <= 1)
                  .reduce((acc, n, idx, arr) => {
                    if (idx > 0 && n - arr[idx - 1] > 1) acc.push("...");
                    acc.push(n);
                    return acc;
                  }, [])
                  .map((item, idx) =>
                    item === "..." ? (
                      <span key={`ellipsis-${idx}`} className="px-1 text-zinc-600 text-xs">
                        ...
                      </span>
                    ) : (
                      <button
                        key={item}
                        onClick={() => setPage(item)}
                        className={`w-8 h-8 rounded-md text-xs font-medium border transition-colors ${page === item
                          ? "bg-white text-zinc-950 border-white"
                          : "border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700"
                          }`}
                      >
                        {item}
                      </button>
                    )
                  )}

                <button
                  onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
                  disabled={page === totalPages}
                  className="flex items-center justify-center w-8 h-8 rounded-md border border-zinc-800 text-zinc-400 hover:text-white hover:border-zinc-700 disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
                >
                  <ChevronRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      </Layout>
    );
  }