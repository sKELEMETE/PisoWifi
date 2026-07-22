import { useEffect, useState, useCallback, useRef } from "react";
import { useNavigate } from "react-router-dom";
import useAdminStore from "../../store/adminStore";
import adminApi from "../../api/adminClient";
import VoucherManagement from "./VoucherManagement";
import AdminSettings from "./AdminSettings";
import { toast } from "../../store/toastStore";
import "../../styles/admin.css";

/* ==========================================================================
   Utility helpers
   ========================================================================== */

const formatUptime = (seconds) => {
    if (!seconds) return "0s";
    const d = Math.floor(seconds / 86400);
    const h = Math.floor((seconds % 86400) / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);
    const parts = [];
    if (d > 0) parts.push(`${d}d`);
    if (h > 0) parts.push(`${h}h`);
    if (m > 0) parts.push(`${m}m`);
    if (parts.length === 0 || s > 0) parts.push(`${s}s`);
    return parts.join(" ");
};

const formatSeconds = (sec) => {
    const h = Math.floor(sec / 3600);
    const m = Math.floor((sec % 3600) / 60);
    const s = sec % 60;
    return `${String(h).padStart(2, "0")}:${String(m).padStart(2, "0")}:${String(s).padStart(2, "0")}`;
};

const formatBytes = (bytes) => {
    if (!bytes) return "0 GB";
    return `${(bytes / 1073741824).toFixed(2)} GB`;
};

const formatDateTime = (isoString) => {
    if (!isoString) return "—";
    try {
        return new Date(isoString).toLocaleTimeString([], {
            hour: "2-digit", minute: "2-digit", second: "2-digit",
        });
    } catch {
        return "—";
    }
};

const formatPurchased = (seconds) => {
    if (!seconds) return "0m";
    const m = Math.floor(seconds / 60);
    return m >= 60 ? `${(m / 60).toFixed(1)}h` : `${m}m`;
};

/* ==========================================================================
   Sub-components
   ========================================================================== */

function ResourceBar({ label, valueLabel, percent, fillClass, danger, warning }) {
    const cls = danger ? "danger" : warning ? "warning" : "";
    return (
        <div className="resource-bar-group">
            <div className="resource-bar-header">
                <span className="resource-bar-label">{label}</span>
                <span className={`resource-bar-value ${cls}`}>{valueLabel}</span>
            </div>
            <div className="resource-bar-track">
                <div
                    className={`resource-bar-fill ${fillClass}`}
                    style={{ width: `${Math.min(100, percent || 0)}%` }}
                />
            </div>
        </div>
    );
}

function HealthItem({ label, online, detail }) {
    return (
        <div className="health-item">
            <div className="health-header">
                <span className="health-label">{label}</span>
                <span className={`health-status ${online ? "status-online" : "status-offline"}`} />
            </div>
            <span className="health-detail">{detail}</span>
        </div>
    );
}

function SalesCard({ icon, label, value, accentColor, iconBg }) {
    return (
        <div className="sales-card">
            <div className="sales-card-accent" style={{ background: accentColor }} />
            <div className="sales-card-icon" style={{ background: iconBg }}>{icon}</div>
            <span className="sales-title">{label}</span>
            <span className="sales-amount">{value}</span>
        </div>
    );
}

function InfoRow({ label, value, mono, small }) {
    return (
        <div className="info-item">
            <span className="info-label">{label}</span>
            {typeof value === "string" || typeof value === "number" ? (
                <span
                    className={`info-value${mono ? " info-value-mono" : ""}`}
                    style={small ? { fontSize: "0.76rem" } : undefined}
                >
                    {value}
                </span>
            ) : (
                <span className="info-value">{value}</span>
            )}
        </div>
    );
}

function StatusPill({ online }) {
    return (
        <span className={`admin-status-badge ${online ? "badge-active" : "badge-offline"}`}>
            {online ? "Online" : "Offline"}
        </span>
    );
}

function DashboardSkeleton() {
    return (
        <div style={{ display: "flex", flexDirection: "column", gap: "var(--sp-5)" }}>
            <div className="sales-grid">
                {[1, 2, 3].map(i => (
                    <div key={i} className="sales-card" style={{ minHeight: 110 }}>
                        <div className="admin-skeleton" style={{ width: 36, height: 36, borderRadius: 10 }} />
                        <div className="admin-skeleton admin-skeleton-text" style={{ width: "55%", marginTop: 14 }} />
                        <div className="admin-skeleton" style={{ height: 36, width: "70%", borderRadius: 8 }} />
                    </div>
                ))}
            </div>
            <div className="dashboard-sections">
                <div className="section-card" style={{ minHeight: 280 }}>
                    <div className="admin-skeleton admin-skeleton-title" />
                    {[1,2,3,4,5].map(i => <div key={i} className="admin-skeleton admin-skeleton-text" />)}
                </div>
                <div className="section-card" style={{ minHeight: 280 }}>
                    <div className="admin-skeleton admin-skeleton-title" />
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: 10 }}>
                        {[1,2,3,4,5,6].map(i => (
                            <div key={i} className="admin-skeleton" style={{ height: 60, borderRadius: 12 }} />
                        ))}
                    </div>
                </div>
            </div>
        </div>
    );
}

/* ==========================================================================
   Main component
   ========================================================================== */

export default function AdminDashboard() {
    const { isAuthenticated, isLoading, logout, username, checkAuth } = useAdminStore();
    const [data, setData]           = useState(null);
    const [fetchError, setFetchError] = useState(null);
    const navigate = useNavigate();

    useEffect(() => { checkAuth(); }, [checkAuth]);

    const fetchDashboard = useCallback(async (isRefresh = false) => {
        try {
            const url = isRefresh ? "/dashboard?refresh=1" : "/dashboard";
            const res = await adminApi.get(url);
            if (res.data?.success) {
                setData(res.data.data);
                setFetchError(null);
            } else {
                const errText = res.data?.message || "Failed to compile dashboard data";
                setFetchError(errText);
                toast.error(errText);
            }
        } catch (err) {
            console.error("Dashboard fetch failed:", err);
            const errText = err.response?.status === 401
                ? "Session expired. Redirecting to login…"
                : "Unable to connect to backend API";
            setFetchError(errText);
            toast.error(errText);
        }
    }, []);

    // ── Immediate forced refresh on initial mount / auth confirm ──────────────
    // Fires once the moment isAuthenticated becomes true — requesting refresh=1
    // to bypass stale cache and calculate fresh system health immediately.
    const didImmediateFetch = useRef(false);

    useEffect(() => {
        if (!isAuthenticated) {
            didImmediateFetch.current = false; // reset on logout
            return;
        }
        if (didImmediateFetch.current) return; // guard: only once per session
        didImmediateFetch.current = true;
        fetchDashboard(true);
    }, [isAuthenticated, fetchDashboard]);

    // ── Polling — pauses when tab is hidden to save resources ─────────────────
    // Calls fetchDashboard(false) every 15 seconds to fetch cached health.
    useEffect(() => {
        if (!isAuthenticated) return;
        let id = null;

        const start = () => {
            if (id) return;
            id = setInterval(() => fetchDashboard(false), 15000);
        };
        const stop = () => { if (id) { clearInterval(id); id = null; } };
        const onVisibility = () => document.visibilityState === "visible" ? start() : stop();

        if (document.visibilityState === "visible") start();
        document.addEventListener("visibilitychange", onVisibility);
        return () => { stop(); document.removeEventListener("visibilitychange", onVisibility); };
    }, [isAuthenticated, fetchDashboard]);

    // Redirect when unauthenticated
    useEffect(() => {
        if (!isLoading && !isAuthenticated) navigate("/admin/login");
    }, [isAuthenticated, isLoading, navigate]);

    if (isLoading) {
        return (
            <section className="admin-layout">
                <div className="admin-content">
                    <div style={{ display: "flex", justifyContent: "center", alignItems: "center", height: 300 }}>
                        <span style={{ color: "var(--admin-text-muted)", fontSize: "0.9rem" }}>
                            Initializing…
                        </span>
                    </div>
                </div>
            </section>
        );
    }

    if (!isAuthenticated) return null;

    const handleLogout = async () => {
        await logout();
        toast.info("Signed out of admin portal");
        navigate("/admin/login");
    };

    const sh = data?.system_health;
    const cpuDanger  = sh?.cpu_usage_percent  > 90;
    const cpuWarn    = sh?.cpu_usage_percent  > 70;
    const ramDanger  = sh?.ram_usage_percent  > 90;
    const ramWarn    = sh?.ram_usage_percent  > 75;
    const tempDanger = sh?.cpu_temperature    > 75;
    const tempWarn   = sh?.cpu_temperature    > 60;
    const diskDanger = sh?.disk_usage_percent > 90;
    const diskWarn   = sh?.disk_usage_percent > 75;

    return (
        <section className="admin-layout">
            <div className="admin-content">

                {/* ── Page Header ─────────────────────────────────── */}
                <header className="admin-header">
                    <div className="admin-header-left">
                        <h1 className="admin-page-title">Walay Lag DOSEWIFI</h1>
                    </div>

                    <div className="admin-header-right">
                        <div className="live-indicator">
                            <span className="live-dot" />
                            <span>Live</span>
                        </div>

                        <div className="admin-user-chip">
                            <div className="admin-user-avatar" aria-hidden="true">
                                {username ? username.charAt(0).toUpperCase() : "A"}
                            </div>
                            <span className="admin-user-name">{username || "Admin"}</span>
                            <button
                                onClick={handleLogout}
                                className="signout-btn"
                                id="admin-signout-btn"
                                aria-label="Sign out"
                            >
                                Sign out
                            </button>
                        </div>
                    </div>
                </header>

                {/* ── Error Banner ────────────────────────────────── */}
                {fetchError && (
                    <div className="admin-alert admin-alert-danger" role="alert">
                        <span className="admin-alert-icon">⚠️</span>
                        <div>
                            <div className="admin-alert-title">Connection Issue</div>
                            <div className="admin-alert-body">
                                {fetchError} — polling continues in background
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Security Warning ─────────────────────────────── */}
                {data?.system_health?.admin_mode?.default_credentials_detected && (
                    <div className="admin-alert admin-alert-danger" role="alert">
                        <span className="admin-alert-icon">🔴</span>
                        <div>
                            <div className="admin-alert-title">
                                Critical Security Warning — Default Credentials Detected
                            </div>
                            <div className="admin-alert-body">
                                Your system is using the default credentials (<strong>admin / admin123</strong>).
                                Update them immediately in the{" "}
                                <code style={{ fontSize: "0.78rem", background: "rgba(255,255,255,0.07)", padding: "1px 5px", borderRadius: 4 }}>
                                    .env
                                </code>{" "}
                                file to protect this gateway.
                            </div>
                        </div>
                    </div>
                )}

                {/* ── Content ──────────────────────────────────────── */}
                {!data ? (
                    <DashboardSkeleton />
                ) : (
                    <>
                        {/* Revenue Cards */}
                        <div className="sales-grid">
                            <SalesCard
                                icon="₱"
                                label="Today's Revenue"
                                value={`₱${data.sales.today}`}
                                accentColor="linear-gradient(90deg, #2563EB, #60A5FA)"
                                iconBg="rgba(59,130,246,0.10)"
                            />
                            <SalesCard
                                icon="📅"
                                label="Weekly Revenue"
                                value={`₱${data.sales.week}`}
                                accentColor="linear-gradient(90deg, #7C3AED, #A78BFA)"
                                iconBg="rgba(124,58,237,0.10)"
                            />
                            <SalesCard
                                icon="📈"
                                label="Monthly Revenue"
                                value={`₱${data.sales.month}`}
                                accentColor="linear-gradient(90deg, #0891B2, #67E8F9)"
                                iconBg="rgba(6,182,212,0.10)"
                            />
                        </div>

                        {/* Server Info + System Health */}
                        <div className="dashboard-sections">

                            {/* Server Info */}
                            <div className="section-card">
                                <div className="section-card-header">
                                    <div>
                                        <h3 className="section-title">Server Information</h3>
                                        <p className="section-subtitle">Gateway system details</p>
                                    </div>
                                    <StatusPill online={sh.internet_connected} />
                                </div>
                                <div className="info-list">
                                    <InfoRow label="Hostname"    value={sh.hostname} />
                                    <InfoRow label="Uptime"      value={formatUptime(sh.system_uptime)} />
                                    <InfoRow label="LAN"         value={sh.lan_interface}   mono />
                                    <InfoRow label="WAN"         value={sh.wan_interface}   mono />
                                    <InfoRow label="Timezone"    value={sh.timezone} />
                                    <InfoRow label="Python"      value={sh.python_version}  mono />
                                    <InfoRow label="Kernel"      value={sh.kernel_version}  mono small />
                                    <InfoRow
                                        label="Sessions"
                                        value={
                                            <span>
                                                <strong style={{ color: "#86EFAC" }}>
                                                    {sh.active_sessions_count}
                                                </strong>
                                                <span style={{ color: "var(--admin-text-muted)" }}> active / </span>
                                                <strong>{sh.authenticated_clients_count}</strong>
                                                <span style={{ color: "var(--admin-text-muted)" }}> auth</span>
                                            </span>
                                        }
                                    />
                                </div>
                            </div>

                            {/* System Health */}
                            <div className="section-card">
                                <div className="section-card-header">
                                    <div>
                                        <h3 className="section-title">System Health</h3>
                                        <p className="section-subtitle">Service status &amp; resource usage</p>
                                    </div>
                                </div>

                                <div className="health-grid">
                                    <HealthItem label="Backend"     online={sh.backend_service_active}  detail={sh.backend_status} />
                                    <HealthItem label="Database"    online={sh.database_connected}       detail={sh.database_connected ? "Connected" : "Offline"} />
                                    <HealthItem label="Coin Serial" online={sh.coin_listener_connected}  detail={sh.coin_listener_port || "No device"} />
                                    <HealthItem label="Scheduler"   online={sh.scheduler_active}         detail={sh.scheduler_active ? "Running" : "Inactive"} />
                                    <HealthItem label="Firewall"    online={sh.firewall_active}          detail="nftables" />
                                    <HealthItem label="Internet"    online={sh.internet_connected}       detail={sh.internet_connected ? "Connected" : "Offline"} />
                                    <HealthItem label="DNS"         online={sh.dns_ok}                   detail={sh.dns_ok ? "Resolving" : "Failed"} />
                                    <HealthItem label="Nginx"       online={sh.nginx_active}             detail={sh.nginx_active ? "Serving" : "Stopped"} />
                                    <HealthItem label="MariaDB"     online={sh.mariadb_active}           detail={sh.mariadb_active ? "Active" : "Stopped"} />
                                </div>

                                <div className="resource-bars">
                                    <ResourceBar
                                        label="CPU Usage"
                                        valueLabel={`${sh.cpu_usage_percent}%`}
                                        percent={sh.cpu_usage_percent}
                                        fillClass={cpuDanger ? "resource-bar-fill-danger" : cpuWarn ? "resource-bar-fill-warning" : "resource-bar-fill-primary"}
                                        danger={cpuDanger} warning={cpuWarn}
                                    />
                                    <ResourceBar
                                        label={`RAM — ${formatBytes(sh.ram_used)} / ${formatBytes(sh.ram_total)}`}
                                        valueLabel={`${sh.ram_usage_percent}%`}
                                        percent={sh.ram_usage_percent}
                                        fillClass={ramDanger ? "resource-bar-fill-danger" : ramWarn ? "resource-bar-fill-warning" : "resource-bar-fill-secondary"}
                                        danger={ramDanger} warning={ramWarn}
                                    />
                                    <div className="resource-2col">
                                        <ResourceBar
                                            label={`Disk — ${formatBytes(sh.disk_used)}`}
                                            valueLabel={`${sh.disk_usage_percent}%`}
                                            percent={sh.disk_usage_percent}
                                            fillClass={diskDanger ? "resource-bar-fill-danger" : diskWarn ? "resource-bar-fill-warning" : "resource-bar-fill-neutral"}
                                            danger={diskDanger} warning={diskWarn}
                                        />
                                        <ResourceBar
                                            label="CPU Temp"
                                            valueLabel={sh.cpu_temperature ? `${sh.cpu_temperature}°C` : "N/A"}
                                            percent={sh.cpu_temperature ? Math.min(100, (sh.cpu_temperature / 90) * 100) : 0}
                                            fillClass={tempDanger ? "resource-bar-fill-danger" : tempWarn ? "resource-bar-fill-warning" : "resource-bar-fill-primary"}
                                            danger={tempDanger} warning={tempWarn}
                                        />
                                    </div>
                                </div>
                            </div>
                        </div>

                        {/* Active Clients Table */}
                        <div className="users-table-container">
                            <div className="table-header">
                                <h3 className="table-header-title">
                                    Active Clients
                                    <span className="table-header-count">{data.active_users.length}</span>
                                </h3>
                            </div>

                            {data.active_users.length === 0 ? (
                                <div className="table-empty-state">
                                    <span className="table-empty-icon">🌐</span>
                                    <span className="table-empty-title">No active sessions</span>
                                    <span className="table-empty-body">
                                        Connected clients will appear here once they start a session.
                                    </span>
                                </div>
                            ) : (
                                <table className="users-table" aria-label="Active clients">
                                    <thead>
                                        <tr>
                                            <th>IP Address</th>
                                            <th>MAC Address</th>
                                            <th>Remaining</th>
                                            <th>Purchased</th>
                                            <th>Status</th>
                                            <th>Connected</th>
                                            <th>Last Active</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.active_users.map((user) => (
                                            <tr key={user.mac}>
                                                <td style={{ fontFamily: "monospace", fontSize: "0.84rem" }}>
                                                    {user.ip}
                                                </td>
                                                <td style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--admin-text-muted)" }}>
                                                    {user.mac}
                                                </td>
                                                <td style={{ fontFamily: "monospace", fontWeight: 700, color: "var(--admin-primary)", letterSpacing: "0.4px" }}>
                                                    {formatSeconds(user.remaining_time)}
                                                </td>
                                                <td style={{ color: "var(--admin-text-muted)" }}>
                                                    {formatPurchased(user.purchased_time)}
                                                </td>
                                                <td>
                                                    <span className={`admin-status-badge ${
                                                        (user.status || "").toUpperCase() === "ACTIVE"  ? "badge-active"
                                                        : (user.status || "").toUpperCase() === "PAUSED"  ? "badge-paused"
                                                        : (user.status || "").toUpperCase() === "EXPIRED" ? "badge-expired"
                                                        : "badge-offline"
                                                    }`}>
                                                        {(user.status || "").toUpperCase()}
                                                    </span>
                                                </td>
                                                <td style={{ color: "var(--admin-text-muted)", fontSize: "0.8rem" }}>
                                                    {formatDateTime(user.connected_time)}
                                                </td>
                                                <td style={{ color: "var(--admin-text-muted)", fontSize: "0.8rem" }}>
                                                    {formatDateTime(user.last_activity)}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            )}
                        </div>

                        {/* Voucher Management */}
                        <div className="section-card">
                            <VoucherManagement />
                        </div>

                        {/* Settings */}
                        <div className="section-card">
                            <AdminSettings currentUsername={username} />
                        </div>
                    </>
                )}
            </div>
        </section>
    );
}
