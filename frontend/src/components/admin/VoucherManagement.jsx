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

export default function VoucherManagement() {
    const [stats, setStats] = useState(null);
    const [vouchers, setVouchers] = useState([]);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState("");
    const [message, setMessage] = useState("");

    // Pagination
    const [pagination, setPagination] = useState({
        total: 0,
        limit: 50,
        offset: 0,
        hasMore: false,
    });

    // Filters
    const [statusFilter, setStatusFilter] = useState("");
    const [sortBy, setSortBy] = useState("created_at");
    const [sortDesc, setSortDesc] = useState(true);

    // Create modal
    const [showCreateModal, setShowCreateModal] = useState(false);
    const [createForm, setCreateForm] = useState({
        minutes: 60,
        count: 1,
        expiresAt: "",
    });
    const [createLoading, setCreateLoading] = useState(false);

    // Export
    const [exportLoading, setExportLoading] = useState(false);
    const [exportFormat, setExportFormat] = useState("csv");

    const fetchStats = useCallback(async () => {
        try {
            const res = await getVoucherStats();
            if (res.success) setStats(res.data);
        } catch (err) {
            console.error("Failed to fetch stats:", err);
        }
    }, []);

    const fetchVouchers = useCallback(async () => {
        setLoading(true);
        setError("");
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
                setPagination((prev) => ({
                    ...prev,
                    total: res.data.pagination?.total || 0,
                    hasMore: res.data.pagination?.hasMore || false,
                }));
            }
        } catch (err) {
            setError(err.response?.data?.message || "Failed to load vouchers");
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
        setError("");
        setMessage("");

        try {
            if (createForm.count === 1) {
                const res = await createVoucher(createForm.minutes, createForm.expiresAt || null);
                if (res.success) {
                    setMessage(`Voucher ${res.data.code} created successfully`);
                    setCreateForm({ minutes: 60, count: 1, expiresAt: "" });
                    setShowCreateModal(false);
                    fetchVouchers();
                    fetchStats();
                }
            } else {
                const res = await createVouchersBulk(createForm.count, createForm.minutes, createForm.expiresAt || null);
                if (res.success) {
                    setMessage(`${res.data.created} vouchers created successfully`);
                    setCreateForm({ minutes: 60, count: 1, expiresAt: "" });
                    setShowCreateModal(false);
                    fetchVouchers();
                    fetchStats();
                }
            }
        } catch (err) {
            setError(err.response?.data?.message || "Failed to create voucher(s)");
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
                setMessage("Voucher deleted");
                fetchVouchers();
                fetchStats();
            }
        } catch (err) {
            setError(err.response?.data?.message || "Failed to delete voucher");
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
                setMessage("Voucher expired");
                fetchVouchers();
                fetchStats();
            }
        } catch (err) {
            setError(err.response?.data?.message || "Failed to expire voucher");
        } finally {
            setLoading(false);
        }
    };

    const handleExport = async () => {
        setExportLoading(true);
        try {
            const res = await exportVouchers(exportFormat, statusFilter || undefined);
            const blob = new Blob([res.data], { type: exportFormat === "csv" ? "text/csv" : "application/json" });
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `vouchers_${new Date().toISOString().slice(0, 10)}.${exportFormat}`;
            a.click();
            window.URL.revokeObjectURL(url);
            setMessage(`Exported vouchers as ${exportFormat.toUpperCase()}`);
        } catch (err) {
            setError("Failed to export vouchers");
        } finally {
            setExportLoading(false);
        }
    };

    const handleSort = (field) => {
        if (sortBy === field) {
            setSortDesc(!sortDesc);
        } else {
            setSortBy(field);
            setSortDesc(true);
        }
    };

    const sortIcon = (field) => {
        if (sortBy !== field) return "⇅";
        return sortDesc ? "⇓" : "⇑";
    };

    const formatDate = (iso) => {
        if (!iso) return "—";
        try {
            return new Date(iso).toLocaleString([], { dateStyle: "short", timeStyle: "short" });
        } catch {
            return "—";
        }
    };

    const renderStatusBadge = (status) => {
        const statusMap = {
            UNUSED: { class: "glass-badge-unused", label: "Unused" },
            USED: { class: "glass-badge-used", label: "Used" },
            EXPIRED: { class: "glass-badge-expired", label: "Expired" },
        };
        const current = statusMap[status] || { class: "glass-badge-expired", label: status };
        return <span className={`glass-badge ${current.class}`}>{current.label}</span>;
    };

    return (
        <div className="voucher-management-container" style={{ width: "100%" }}>
            {/* Header Section */}
            <div
                style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    marginBottom: "24px",
                    flexWrap: "wrap",
                    gap: "16px",
                }}
            >
                <div>
                    <h3 style={{ fontSize: "1.35rem", fontWeight: "700", color: "#ffffff", letterSpacing: "-0.5px", margin: 0 }}>
                        Voucher Management
                    </h3>
                    <p style={{ color: "var(--muted)", fontSize: "0.85rem", marginTop: "4px", margin: 0 }}>
                        Create, track, and export internet access vouchers
                    </p>
                </div>

                <div style={{ display: "flex", gap: "10px", alignItems: "center", flexWrap: "wrap" }}>
                    <button
                        onClick={handleExport}
                        disabled={exportLoading}
                        className="glass-btn glass-btn-ghost"
                        aria-label="Export Vouchers"
                    >
                        {exportLoading ? "Exporting..." : "Export"}
                    </button>
                    <button
                        onClick={() => setShowCreateModal(true)}
                        className="glass-btn glass-btn-primary"
                        aria-label="Create Voucher"
                    >
                        + Create Voucher
                    </button>
                </div>
            </div>

            {/* Stat Cards Grid */}
            {stats && (
                <div className="voucher-stat-grid">
                    <div className="voucher-stat-card">
                        <div className="voucher-stat-indicator" style={{ background: "rgba(255, 255, 255, 0.3)" }} />
                        <span className="voucher-stat-label">Total Vouchers</span>
                        <span className="voucher-stat-value">{stats.total}</span>
                    </div>

                    <div className="voucher-stat-card">
                        <div className="voucher-stat-indicator" style={{ background: "#60a5fa" }} />
                        <span className="voucher-stat-label">Available (Unused)</span>
                        <span className="voucher-stat-value" style={{ color: "#60a5fa" }}>{stats.unused}</span>
                    </div>

                    <div className="voucher-stat-card">
                        <div className="voucher-stat-indicator" style={{ background: "#34d399" }} />
                        <span className="voucher-stat-label">Redeemed (Used)</span>
                        <span className="voucher-stat-value" style={{ color: "#34d399" }}>{stats.used}</span>
                    </div>

                    <div className="voucher-stat-card">
                        <div className="voucher-stat-indicator" style={{ background: "#94a3b8" }} />
                        <span className="voucher-stat-label">Expired</span>
                        <span className="voucher-stat-value" style={{ color: "#94a3b8" }}>{stats.expired}</span>
                    </div>
                </div>
            )}

            {/* Filter & Controls Bar */}
            <div className="voucher-filter-bar">
                <select
                    className="glass-select"
                    value={statusFilter}
                    onChange={(e) => setStatusFilter(e.target.value)}
                    aria-label="Filter by Status"
                    style={{ minWidth: "140px" }}
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
                    aria-label="Export Format"
                    style={{ minWidth: "100px" }}
                >
                    <option value="csv">CSV</option>
                    <option value="json">JSON</option>
                </select>

                <div style={{ flex: 1 }} />

                <span style={{ color: "var(--muted)", fontSize: "0.82rem", fontWeight: "500" }}>
                    {pagination.total} Total • Page {Math.floor(pagination.offset / pagination.limit) + 1} of {Math.ceil(pagination.total / pagination.limit) || 1}
                </span>
            </div>

            {/* Vouchers Table */}
            <div className="users-table-container" style={{ borderRadius: "20px" }}>
                {loading ? (
                    <div style={{ padding: "48px", textAlign: "center", color: "var(--muted)", fontSize: "0.9rem" }}>
                        Loading vouchers...
                    </div>
                ) : vouchers.length === 0 ? (
                    <div style={{ padding: "48px", textAlign: "center", color: "var(--muted)", fontSize: "0.9rem" }}>
                        No vouchers found
                    </div>
                ) : (
                    <table className="users-table">
                        <thead>
                            <tr>
                                {[
                                    { key: "code", label: "Code" },
                                    { key: "minutes", label: "Minutes" },
                                    { key: "status", label: "Status" },
                                    { key: "expires_at", label: "Expires" },
                                    { key: "used_at", label: "Redeemed" },
                                    { key: "used_by_client_mac", label: "Redeemed By" },
                                    { key: "created_at", label: "Created" },
                                    { key: "actions", label: "Actions" },
                                ].map((col) => (
                                    <th
                                        key={col.key}
                                        style={{
                                            cursor: ["code", "minutes", "status", "created_at", "expires_at"].includes(col.key) ? "pointer" : "default",
                                        }}
                                        onClick={() => ["code", "minutes", "status", "created_at", "expires_at"].includes(col.key) && handleSort(col.key)}
                                    >
                                        {col.label} {["code", "minutes", "status", "created_at", "expires_at"].includes(col.key) && sortIcon(col.key)}
                                    </th>
                                ))}
                            </tr>
                        </thead>
                        <tbody>
                            {vouchers.map((v) => (
                                <tr key={v.id}>
                                    <td style={{ fontFamily: "monospace", fontWeight: "600", color: "#ffffff", letterSpacing: "1px" }}>
                                        {v.code}
                                    </td>
                                    <td>{v.minutes}m</td>
                                    <td>{renderStatusBadge(v.status)}</td>
                                    <td style={{ color: "var(--muted)", fontSize: "0.82rem" }}>{formatDate(v.expires_at)}</td>
                                    <td style={{ color: "var(--muted)", fontSize: "0.82rem" }}>{formatDate(v.used_at)}</td>
                                    <td style={{ color: "#ffffff", fontFamily: "monospace", fontSize: "0.85rem" }}>
                                        {v.used_by_client_mac || "—"}
                                    </td>
                                    <td style={{ color: "var(--muted)", fontSize: "0.82rem" }}>{formatDate(v.created_at)}</td>
                                    <td>
                                        <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                                            {v.status === "UNUSED" && (
                                                <>
                                                    <button
                                                        onClick={() => handleExpire(v.id, v.code)}
                                                        disabled={loading}
                                                        className="glass-btn glass-btn-ghost"
                                                        style={{ padding: "4px 10px", minHeight: "32px", fontSize: "0.75rem" }}
                                                    >
                                                        Expire
                                                    </button>
                                                    <button
                                                        onClick={() => handleDelete(v.id, v.code)}
                                                        disabled={loading}
                                                        className="glass-btn glass-btn-danger"
                                                        style={{ padding: "4px 10px", minHeight: "32px", fontSize: "0.75rem" }}
                                                    >
                                                        Delete
                                                    </button>
                                                </>
                                            )}
                                            {v.status !== "UNUSED" && (
                                                <span style={{ color: "var(--muted)", fontSize: "0.75rem" }}>—</span>
                                            )}
                                        </div>
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                )}

                {/* Pagination */}
                {pagination.total > pagination.limit && (
                    <div
                        style={{
                            display: "flex",
                            alignItems: "center",
                            justifyContent: "center",
                            gap: "14px",
                            paddingTop: "20px",
                            marginTop: "12px",
                            borderTop: "1px solid rgba(255, 255, 255, 0.05)",
                        }}
                    >
                        <button
                            onClick={() => setPagination((p) => ({ ...p, offset: Math.max(0, p.offset - p.limit) }))}
                            disabled={pagination.offset === 0 || loading}
                            className="glass-btn glass-btn-ghost"
                            style={{ padding: "8px 16px" }}
                        >
                            Previous
                        </button>
                        <span style={{ color: "var(--muted)", fontSize: "0.85rem", fontWeight: "500" }}>
                            Page {Math.floor(pagination.offset / pagination.limit) + 1} of {Math.ceil(pagination.total / pagination.limit)}
                        </span>
                        <button
                            onClick={() => setPagination((p) => ({ ...p, offset: p.offset + p.limit }))}
                            disabled={!pagination.hasMore || loading}
                            className="glass-btn glass-btn-ghost"
                            style={{ padding: "8px 16px" }}
                        >
                            Next
                        </button>
                    </div>
                )}
            </div>

            {/* Error / Success Feedback Banners */}
            {error && (
                <div
                    role="alert"
                    style={{
                        marginTop: "16px",
                        padding: "12px 18px",
                        background: "rgba(239, 68, 68, 0.12)",
                        border: "1px solid rgba(239, 68, 68, 0.25)",
                        borderRadius: "14px",
                        color: "#fca5a5",
                        fontSize: "0.85rem",
                        fontWeight: "500",
                        backdropFilter: "blur(10px)",
                        WebkitBackdropFilter: "blur(10px)",
                    }}
                >
                    {error}
                </div>
            )}
            {message && (
                <div
                    role="status"
                    style={{
                        marginTop: "16px",
                        padding: "12px 18px",
                        background: "rgba(52, 211, 153, 0.12)",
                        border: "1px solid rgba(52, 211, 153, 0.25)",
                        borderRadius: "14px",
                        color: "#6ee7b7",
                        fontSize: "0.85rem",
                        fontWeight: "500",
                        backdropFilter: "blur(10px)",
                        WebkitBackdropFilter: "blur(10px)",
                    }}
                >
                    {message}
                </div>
            )}

            {/* Glass Modal (Create Single / Bulk Voucher) */}
            {showCreateModal && (
                <div className="glass-modal-overlay" onClick={() => setShowCreateModal(false)}>
                    <div className="glass-modal" onClick={(e) => e.stopPropagation()}>
                        <h4 style={{ margin: "0 0 20px", fontSize: "1.15rem", fontWeight: "700", color: "#ffffff", letterSpacing: "-0.3px" }}>
                            {createForm.count === 1 ? "Create Voucher" : "Create Vouchers (Bulk)"}
                        </h4>

                        <form onSubmit={handleCreate}>
                            <div style={{ marginBottom: "16px" }}>
                                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                                    Minutes per Voucher
                                </label>
                                <input
                                    type="number"
                                    min="1"
                                    max="100000"
                                    className="glass-input"
                                    style={{ width: "100%" }}
                                    value={createForm.minutes}
                                    onChange={(e) => setCreateForm((f) => ({ ...f, minutes: parseInt(e.target.value) || 1 }))}
                                />
                            </div>

                            <div style={{ marginBottom: "16px" }}>
                                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                                    Quantity
                                </label>
                                <input
                                    type="number"
                                    min="1"
                                    max="10000"
                                    className="glass-input"
                                    style={{ width: "100%" }}
                                    value={createForm.count}
                                    onChange={(e) => setCreateForm((f) => ({ ...f, count: parseInt(e.target.value) || 1 }))}
                                />
                                <p style={{ fontSize: "0.72rem", color: "var(--muted)", marginTop: "4px", margin: 0 }}>
                                    Max 10,000 vouchers per bulk generation
                                </p>
                            </div>

                            <div style={{ marginBottom: "24px" }}>
                                <label style={{ display: "block", fontSize: "0.8rem", color: "var(--muted)", fontWeight: "500", marginBottom: "6px" }}>
                                    Expiration Date (Optional)
                                </label>
                                <input
                                    type="datetime-local"
                                    className="glass-input"
                                    style={{ width: "100%" }}
                                    value={createForm.expiresAt}
                                    onChange={(e) => setCreateForm((f) => ({ ...f, expiresAt: e.target.value }))}
                                />
                                <p style={{ fontSize: "0.72rem", color: "var(--muted)", marginTop: "4px", margin: 0 }}>
                                    Leave blank for vouchers with no expiration date
                                </p>
                            </div>

                            <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
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
                                    disabled={createLoading}
                                    className="glass-btn glass-btn-primary"
                                >
                                    {createLoading ? "Creating..." : createForm.count === 1 ? "Create Voucher" : "Create Vouchers"}
                                </button>
                            </div>
                        </form>
                    </div>
                </div>
            )}
        </div>
    );
}