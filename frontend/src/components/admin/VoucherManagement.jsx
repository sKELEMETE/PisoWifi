import { useState, useEffect, useCallback } from "react";
import {
    createVoucher,
    createVouchersBulk,
    listVouchers,
    getVoucherStats,
    deleteVoucher,
    expireVoucher,
    exportVouchers,
} from "../../api/voucherApi";
import { toast } from "../../store/toastStore";

// ── Voucher Status Badge ───────────────────────────────────────────────────────
function VoucherBadge({ status }) {
    const map = {
        UNUSED: { cls: "glass-badge-unused", label: "Unused" },
        USED:   { cls: "glass-badge-used",   label: "Used"   },
        EXPIRED:{ cls: "glass-badge-expired", label: "Expired"},
    };
    const current = map[status] || { cls: "glass-badge-expired", label: status };
    return <span className={`glass-badge ${current.cls}`}>{current.label}</span>;
}

// ── Sort Icon ──────────────────────────────────────────────────────────────────
function SortIcon({ field, sortBy, sortDesc }) {
    if (sortBy !== field) return <span style={{ color: "var(--admin-text-faint)", fontSize: "0.7em" }}>⇅</span>;
    return <span style={{ color: "var(--admin-primary)", fontSize: "0.8em" }}>{sortDesc ? "↓" : "↑"}</span>;
}

// ── Stat Card ──────────────────────────────────────────────────────────────────
function VoucherStat({ label, value, accentColor, textColor }) {
    return (
        <div className="voucher-stat-card">
            <div className="voucher-stat-indicator" style={{ background: accentColor }} />
            <span className="voucher-stat-label">{label}</span>
            <span className="voucher-stat-value" style={textColor ? { color: textColor } : {}}>
                {value ?? "—"}
            </span>
        </div>
    );
}

// ── Format helpers ─────────────────────────────────────────────────────────────
const formatDate = (iso) => {
    if (!iso) return "—";
    try {
        return new Date(iso).toLocaleString([], { dateStyle: "short", timeStyle: "short" });
    } catch { return "—"; }
};

// ── Main Component ─────────────────────────────────────────────────────────────
export default function VoucherManagement() {
    const [stats, setStats] = useState(null);
    const [vouchers, setVouchers] = useState([]);
    const [loading, setLoading] = useState(false);

    // Pagination
    const [pagination, setPagination] = useState({
        total: 0, limit: 50, offset: 0, hasMore: false,
    });

    // Filters
    const [statusFilter, setStatusFilter] = useState("");
    const [sortBy, setSortBy] = useState("created_at");
    const [sortDesc, setSortDesc] = useState(true);

    // Create modal
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [createForm, setCreateForm] = useState({ minutes: 60, count: 1, expiresAt: "" });
    const [createLoading, setCreateLoading] = useState(false);

    // Export
    const [exportLoading, setExportLoading] = useState(false);
    const [exportFormat, setExportFormat] = useState("csv");

    const fetchStats = useCallback(async () => {
        try {
            const res = await getVoucherStats();
            if (res.success) setStats(res.data);
        } catch (err) {
            console.error("Stats fetch failed:", err);
        }
    }, []);

    const fetchVouchers = useCallback(async () => {
        setLoading(true);
        try {
            const res = await listVouchers({
                status: statusFilter || undefined,
                limit: pagination.limit,
                offset: pagination.offset,
                orderBy: sortBy,
                orderDesc: sortDesc,
            });
            if (res.success) {
                setVouchers(res.data.vouchers || []);
                setPagination(prev => ({
                    ...prev,
                    total: res.data.pagination?.total || 0,
                    hasMore: res.data.pagination?.hasMore || false,
                }));
            }
        } catch (err) {
            toast.error(err.response?.data?.message || "Failed to load vouchers");
        } finally {
            setLoading(false);
        }
    }, [statusFilter, pagination.limit, pagination.offset, sortBy, sortDesc]);

    useEffect(() => {
        fetchStats();
        fetchVouchers();
    }, [fetchStats, fetchVouchers]);

    const handleCreate = async (e) => {
        e.preventDefault();
        setCreateLoading(true);

        try {
            if (createForm.count === 1) {
                const res = await createVoucher(createForm.minutes, createForm.expiresAt || null);
                if (res.success) {
                    toast.success(`Voucher ${res.data.code} created successfully`);
                    setCreateForm({ minutes: 60, count: 1, expiresAt: "" });
                    setShowCreateModal(false);
                    fetchVouchers();
                    fetchStats();
                }
            } else {
                const res = await createVouchersBulk(createForm.count, createForm.minutes, createForm.expiresAt || null);
                if (res.success) {
                    toast.success(`${res.data.created} vouchers created successfully`);
                    setCreateForm({ minutes: 60, count: 1, expiresAt: "" });
                    setShowCreateModal(false);
                    fetchVouchers();
                    fetchStats();
                }
            }
        } catch (err) {
            toast.error(err.response?.data?.message || "Failed to create voucher(s)");
        } finally {
            setCreateLoading(false);
        }
    };

    const handleDelete = async (voucherId, code) => {
        if (!window.confirm(`Delete voucher ${code}? This cannot be undone.`)) return;
        setLoading(true);
        try {
            const res = await deleteVoucher(voucherId);
            if (res.success) {
                toast.success(`Voucher ${code} deleted`);
                fetchVouchers();
                fetchStats();
            }
        } catch (err) {
            toast.error(err.response?.data?.message || "Failed to delete voucher");
        } finally {
            setLoading(false);
        }
    };

    const handleExpire = async (voucherId, code) => {
        if (!window.confirm(`Expire voucher ${code}? This cannot be undone.`)) return;
        setLoading(true);
        try {
            const res = await expireVoucher(voucherId);
            if (res.success) {
                toast.success(`Voucher ${code} expired`);
                fetchVouchers();
                fetchStats();
            }
        } catch (err) {
            toast.error(err.response?.data?.message || "Failed to expire voucher");
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async () => {
        setExportLoading(true);
        try {
            const res = await exportVouchers(exportFormat, statusFilter || undefined);
            const blob = new Blob([res.data], {
                type: exportFormat === "csv" ? "text/csv" : "application/json",
            });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `vouchers_${new Date().toISOString().slice(0, 10)}.${exportFormat}`;
            a.click();
            window.URL.revokeObjectURL(url);
            toast.info(`Exported as ${exportFormat.toUpperCase()}`);
        } catch {
            toast.error("Failed to export vouchers");
        } finally {
            setExportLoading(false);
        }
    };

    const handleSort = (field) => {
        if (sortBy === field) {
            setSortDesc(d => !d);
        } else {
            setSortBy(field);
            setSortDesc(true);
        }
        setPagination(p => ({ ...p, offset: 0 }));
    };

    const sortableColumns = ["code", "minutes", "status", "created_at", "expires_at"];

    const totalPages = Math.ceil(pagination.total / pagination.limit) || 1;
    const currentPage = Math.floor(pagination.offset / pagination.limit) + 1;

    return (
        <div className="voucher-management-container">

            {/* ── Section Header ─────────────────────────────── */}
            <div className="voucher-section-header">
                <div>
                    <h3 className="voucher-section-title">Voucher Management</h3>
                    <p className="voucher-section-subtitle">
                        Create, track, and export internet access vouchers
                    </p>
                </div>

                <div style={{ display: "flex", gap: "var(--admin-space-3)", alignItems: "center", flexWrap: "wrap" }}>
                    <button
                        onClick={handleExport}
                        disabled={exportLoading}
                        className="glass-btn glass-btn-ghost"
                        aria-label="Export vouchers"
                        id="voucher-export-btn"
                    >
                        {exportLoading ? "Exporting…" : "↑ Export"}
                    </button>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="glass-btn glass-btn-primary"
                        aria-label="Create new voucher"
                        id="voucher-create-btn"
                    >
                        + Create Voucher
                    </button>
                </div>
            </div>

            {/* ── Stat Cards ─────────────────────────────────── */}
            {stats && (
                <div className="voucher-stat-grid">
                    <VoucherStat
                        label="Total Vouchers"
                        value={stats.total}
                        accentColor="rgba(255,255,255,0.2)"
                    />
                    <VoucherStat
                        label="Available"
                        value={stats.unused}
                        accentColor="var(--admin-primary)"
                        textColor="#93C5FD"
                    />
                    <VoucherStat
                        label="Redeemed"
                        value={stats.used}
                        accentColor="var(--admin-success)"
                        textColor="#86EFAC"
                    />
                    <VoucherStat
                        label="Expired"
                        value={stats.expired}
                        accentColor="var(--admin-text-muted)"
                        textColor="var(--admin-text-muted)"
                    />
                </div>
            )}

            {/* ── Filter Bar ─────────────────────────────────── */}
            <div className="voucher-filter-bar">
                <select
                    className="glass-select"
                    value={statusFilter}
                    onChange={(e) => {
                        setStatusFilter(e.target.value);
                        setPagination(p => ({ ...p, offset: 0 }));
                    }}
                    aria-label="Filter by status"
                    style={{ minWidth: "140px" }}
                    id="voucher-status-filter"
                >
                    <option value="">All Statuses</option>
                    <option value="UNUSED">Unused</option>
                    <option value="USED">Used</option>
                    <option value="EXPIRED">Expired</option>
                </select>

                <select
                    className="glass-select"
                    value={exportFormat}
                    onChange={(e) => setExportFormat(e.target.value)}
                    aria-label="Export format"
                    style={{ minWidth: "90px" }}
                    id="voucher-export-format"
                >
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                </select>

                <div className="filter-bar-spacer" />

                <span className="filter-bar-info">
                    {pagination.total} total · Page {currentPage} of {totalPages}
                </span>
            </div>

            {/* ── Vouchers Table ─────────────────────────────── */}
            <div className="users-table-container" style={{ borderRadius: "var(--admin-radius-2xl)" }}>
                {loading ? (
                    <div className="table-empty-state">
                        <span className="table-empty-icon" style={{ animation: "spin 1s linear infinite" }}>⟳</span>
                        <span className="table-empty-title">Loading vouchers…</span>
                    </div>
                ) : vouchers.length === 0 ? (
                    <div className="table-empty-state">
                        <span className="table-empty-icon">🎫</span>
                        <span className="table-empty-title">No vouchers found</span>
                        <span className="table-empty-body">
                            {statusFilter
                                ? `No ${statusFilter.toLowerCase()} vouchers. Try clearing the filter.`
                                : "Click \"+ Create Voucher\" to generate your first voucher."}
                        </span>
                    </div>
                ) : (
                    <table className="users-table" aria-label="Vouchers list">
                        <thead>
                            <tr>
                                {[
                                    { key: "code",              label: "Code"         },
                                    { key: "minutes",           label: "Duration"     },
                                    { key: "status",            label: "Status"       },
                                    { key: "expires_at",        label: "Expires"      },
                                    { key: "used_at",           label: "Redeemed At"  },
                                    { key: "used_by_client_mac",label: "Redeemed By"  },
                                    { key: "created_at",        label: "Created"      },
                                    { key: "actions",           label: ""             },
                                ].map((col) => {
                                    const sortable = sortableColumns.includes(col.key);
                                    return (
                                        <th
                                            key={col.key}
                                            style={{ cursor: sortable ? "pointer" : "default" }}
                                            onClick={() => sortable && handleSort(col.key)}
                                            aria-sort={
                                                sortable && sortBy === col.key
                                                    ? sortDesc ? "descending" : "ascending"
                                                    : undefined
                                            }
                                        >
                                            {col.label}{" "}
                                            {sortable && (
                                                <SortIcon field={col.key} sortBy={sortBy} sortDesc={sortDesc} />
                                            )}
                                        </th>
                                    );
                                })}
                            </tr>
                        </thead>
                        <tbody>
                            {vouchers.map((v) => (
                                <tr key={v.id}>
                                    <td style={{
                                        fontFamily: "monospace",
                                        fontWeight: 700,
                                        color: "var(--admin-text-primary)",
                                        letterSpacing: "1.5px",
                                        fontSize: "0.88rem"
                                    }}>
                                        {v.code}
                                    </td>
                                    <td style={{ color: "var(--admin-text-secondary)" }}>
                                        {v.minutes}&thinsp;min
                                    </td>
                                    <td>
                                        <VoucherBadge status={v.status} />
                                    </td>
                                    <td style={{ color: "var(--admin-text-muted)", fontSize: "0.82rem" }}>
                                        {formatDate(v.expires_at)}
                                    </td>
                                    <td style={{ color: "var(--admin-text-muted)", fontSize: "0.82rem" }}>
                                        {formatDate(v.used_at)}
                                    </td>
                                    <td style={{ fontFamily: "monospace", fontSize: "0.82rem", color: "var(--admin-text-secondary)" }}>
                                        {v.used_by_client_mac || "—"}
                                    </td>
                                    <td style={{ color: "var(--admin-text-muted)", fontSize: "0.82rem" }}>
                                        {formatDate(v.created_at)}
                                    </td>
                                    <td>
                                        {v.status === "UNUSED" ? (
                                            <div style={{ display: "flex", gap: "var(--admin-space-2)", alignItems: "center" }}>
                                                <button
                                                    onClick={() => handleExpire(v.id, v.code)}
                                                    disabled={loading}
                                                    className="glass-btn glass-btn-ghost glass-btn-sm"
                                                    aria-label={`Expire voucher ${v.code}`}
                                                >
                                                    Expire
                                                </button>
                                                <button
                                                    onClick={() => handleDelete(v.id, v.code)}
                                                    disabled={loading}
                                                    className="glass-btn glass-btn-danger glass-btn-sm"
                                                    aria-label={`Delete voucher ${v.code}`}
                                                >
                                                    Delete
                                                </button>
                                            </div>
                                        ) : (
                                            <span style={{ color: "var(--admin-text-faint)", fontSize: "0.8rem" }}>—</span>
                                        )}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}

                {/* Pagination */}
                {pagination.total > pagination.limit && (
                    <div className="admin-pagination">
                        <button
                            onClick={() => setPagination(p => ({ ...p, offset: Math.max(0, p.offset - p.limit) }))}
                            disabled={pagination.offset === 0 || loading}
                            className="glass-btn glass-btn-ghost glass-btn-sm"
                            aria-label="Previous page"
                        >
                            ← Previous
                        </button>
                        <span className="admin-pagination-info">
                            Page {currentPage} of {totalPages}
                        </span>
                        <button
                            onClick={() => setPagination(p => ({ ...p, offset: p.offset + p.limit }))}
                            disabled={!pagination.hasMore || loading}
                            className="glass-btn glass-btn-ghost glass-btn-sm"
                            aria-label="Next page"
                        >
                            Next →
                        </button>
                    </div>
                )}
            </div>

            {/* ── Create Voucher Modal ─────────────────────────── */}
            {showCreateModal && (
                <div
                    className="glass-modal-overlay"
                    onClick={() => setShowCreateModal(false)}
                    role="dialog"
                    aria-modal="true"
                    aria-labelledby="modal-create-title"
                >
                    <div className="glass-modal" onClick={(e) => e.stopPropagation()}>
                        <h4 className="glass-modal-title" id="modal-create-title">
                            {createForm.count === 1 ? "Create Voucher" : `Create ${createForm.count} Vouchers`}
                        </h4>

                        <form onSubmit={handleCreate} id="voucher-create-form" noValidate>
                            <div style={{ display: "flex", flexDirection: "column", gap: "var(--admin-space-5)" }}>

                                <div className="admin-form-group">
                                    <label htmlFor="create-minutes" className="admin-form-label">
                                        Minutes per Voucher
                                    </label>
                                    <input
                                        id="create-minutes"
                                        type="number"
                                        min={1}
                                        max={100000}
                                        className="glass-input"
                                        value={createForm.minutes}
                                        onChange={(e) => setCreateForm(f => ({ ...f, minutes: parseInt(e.target.value) || 1 }))}
                                        required
                                    />
                                    <span className="admin-form-hint">
                                        {Math.floor(createForm.minutes / 60) > 0
                                            ? `${Math.floor(createForm.minutes / 60)}h ${createForm.minutes % 60}m`
                                            : `${createForm.minutes} minutes`}
                                    </span>
                                </div>

                                <div className="admin-form-group">
                                    <label htmlFor="create-count" className="admin-form-label">
                                        Quantity
                                    </label>
                                    <input
                                        id="create-count"
                                        type="number"
                                        min={1}
                                        max={10000}
                                        className="glass-input"
                                        value={createForm.count}
                                        onChange={(e) => setCreateForm(f => ({ ...f, count: parseInt(e.target.value) || 1 }))}
                                        required
                                    />
                                    <span className="admin-form-hint">Maximum 10,000 vouchers per bulk generation</span>
                                </div>

                                <div className="admin-form-group">
                                    <label htmlFor="create-expires" className="admin-form-label">
                                        Expiration Date
                                        <span style={{ color: "var(--admin-text-faint)", fontWeight: 400, marginLeft: "4px" }}>
                                            (optional)
                                        </span>
                                    </label>
                                    <input
                                        id="create-expires"
                                        type="datetime-local"
                                        className="glass-input"
                                        value={createForm.expiresAt}
                                        onChange={(e) => setCreateForm(f => ({ ...f, expiresAt: e.target.value }))}
                                    />
                                    <span className="admin-form-hint">Leave blank for vouchers with no expiration</span>
                                </div>

                            </div>

                            <div className="glass-modal-footer">
                                <button
                                    type="button"
                                    onClick={() => setShowCreateModal(false)}
                                    disabled={createLoading}
                                    className="glass-btn glass-btn-ghost"
                                >
                                    Cancel
                                </button>
                                <button
                                    type="submit"
                                    id="voucher-create-submit-btn"
                                    disabled={createLoading}
                                    className="glass-btn glass-btn-primary"
                                >
                                    {createLoading
                                        ? "Creating…"
                                        : createForm.count === 1
                                            ? "Create Voucher"
                                            : `Create ${createForm.count} Vouchers`
                                    }
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}

            <style>{`
                @keyframes spin {
                    from { transform: rotate(0deg); }
                    to { transform: rotate(360deg); }
                }
            `}</style>
        </div>
    );
}